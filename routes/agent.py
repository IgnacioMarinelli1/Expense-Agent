import asyncio
import base64
import json
import logging
import os

import httpx
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions.sqlite_session_service import SqliteSessionService
from google.genai.errors import ServerError
from google.genai.types import Content, Part

from expense_agent.agent import root_agent
from expense_agent.charting import pop_pending_chart_specs
from helpers.spreadsheet import SUPPORTED_SPREADSHEET_MIME, spreadsheet_to_text
from db.security import current_session_id, current_user_id

router = APIRouter(prefix="/agent", tags=["agent"])
logger = logging.getLogger(__name__)

# When set, all streaming runs are proxied to the remote Cloud Run agent service.
# When unset, the agent runs in-process (local dev mode).
AGENT_URL = os.getenv("AGENT_URL", "").rstrip("/")

AGENT_MAX_ATTEMPTS = 2
SUPPORTED_AUDIO_TYPES = {
    "audio/wav",
    "audio/mp3",
    "audio/mpeg",
    "audio/aiff",
    "audio/aac",
    "audio/ogg",
    "audio/flac",
}
SUPPORTED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
    "application/pdf",
}

_session_service = SqliteSessionService("sessions.db")
_runner = Runner(
    agent=root_agent,
    app_name="expense_agent",
    session_service=_session_service,
)

_SUBAGENT_LABELS: dict[str, dict[str, str]] = {
    "agente_diagnostico": {
        "running": "Generando diagnóstico financiero...",
        "done": "Diagnóstico listo",
    },
    "agente_inflacion": {
        "running": "Consultando índices del INDEC...",
        "done": "Ajuste por inflación calculado",
    },
    "agente_cuotas": {
        "running": "Analizando compromisos y cuotas...",
        "done": "Cuotas analizadas",
    },
    "agente_visualizacion": {
        "running": "Preparando visualización interactiva...",
        "done": "Gráfico listo",
    },
}
_SUBAGENT_NAMES = set(_SUBAGENT_LABELS.keys())
_CHART_TOOL_NAME = "generate_financial_chart"
_CHART_TOOL_NAMES = {"generate_financial_chart", "generate_custom_chart"}

# ---------------------------------------------------------------------------
# Remote proxy helpers (used when AGENT_URL is set)
# ---------------------------------------------------------------------------

def _part_to_dict(part) -> dict:
    """Serialize a google.genai Part to a plain dict suitable for JSON."""
    if getattr(part, "text", None) is not None:
        return {"text": part.text}
    inline = getattr(part, "inline_data", None)
    if inline is not None:
        data = inline.data
        if isinstance(data, bytes):
            data = base64.b64encode(data).decode()
        return {"inline_data": {"mime_type": inline.mime_type, "data": data}}
    return {}


def _content_to_dict(content: Content) -> dict:
    return {
        "role": content.role or "user",
        "parts": [d for d in (_part_to_dict(p) for p in (content.parts or [])) if d],
    }


_remote_sessions_ready: set[tuple[str, str]] = set()


async def _ensure_remote_session(user_id: str, session_id: str) -> None:
    """Create the configured session on the remote ADK api_server if needed."""
    session_key = (user_id, session_id)
    if session_key in _remote_sessions_ready:
        return
    url = f"{AGENT_URL}/apps/agent_runtime/users/{user_id}/sessions"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, json={"session_id": session_id})
            if r.status_code not in (200, 201, 409):
                logger.warning("Remote session create returned %s: %s", r.status_code, r.text)
            else:
                _remote_sessions_ready.add(session_key)
    except Exception as exc:
        logger.warning("Remote session init failed (will proceed anyway): %s", exc)


async def _stream_agent_remote(content: Content, modality_label: str = "mensaje"):
    """Proxy streaming to Cloud Run ADK api_server, translating events to frontend SSE."""
    user_id = current_user_id()
    session_id = current_session_id(user_id)
    await _ensure_remote_session(user_id, session_id)

    body = {
        "app_name": "agent_runtime",
        "user_id": user_id,
        "session_id": session_id,
        "new_message": _content_to_dict(content),
    }

    total_streamed = ""
    turn_boundary_pending = False
    emitted_chart_ids: set[str] = set()

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(180.0, connect=10.0)
        ) as client:
            async with client.stream("POST", f"{AGENT_URL}/run_sse", json=body) as resp:
                try:
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        raw = line[6:].strip()
                        if not raw or raw == "[DONE]":
                            continue
                        try:
                            event = json.loads(raw)
                        except json.JSONDecodeError:
                            continue

                        parts = (event.get("content") or {}).get("parts") or []
                        text = "".join(p.get("text") or "" for p in parts if "text" in p)

                        # ADK 2.x serializes to camelCase; support both conventions
                        fc_parts = [
                            p.get("functionCall") or p.get("function_call")
                            for p in parts
                            if "functionCall" in p or "function_call" in p
                        ]
                        fr_parts = [
                            p.get("functionResponse") or p.get("function_response")
                            for p in parts
                            if "functionResponse" in p or "function_response" in p
                        ]

                        # ADK may use camelCase or snake_case for these fields
                        is_final = event.get("is_final_response") or event.get("isFinalResponse", False)
                        turn_complete = event.get("turn_complete") or event.get("turnComplete", False)
                        error = event.get("error_message") or event.get("errorMessage")

                        if fc_parts:
                            for fc in fc_parts:
                                if fc and fc.get("name") in _SUBAGENT_NAMES:
                                    yield _thinking_sse(fc["name"], "running")
                            turn_boundary_pending = True
                        elif text:
                            if is_final:
                                if not total_streamed:
                                    total_streamed = text
                                    yield _sse("token", {"text": text})
                                elif text.startswith(total_streamed):
                                    remainder = text[len(total_streamed):]
                                    if remainder:
                                        total_streamed += remainder
                                        yield _sse("token", {"text": remainder})
                                turn_boundary_pending = True
                            else:
                                if turn_boundary_pending and total_streamed:
                                    yield _sse("token", {"text": "\n\n"})
                                    total_streamed += "\n\n"
                                    turn_boundary_pending = False
                                total_streamed += text
                                yield _sse("token", {"text": text})

                        for fr in fr_parts:
                            if not fr:
                                continue
                            chart_payload = None
                            if fr.get("name") in _CHART_TOOL_NAMES:
                                resp_data = fr.get("response", {})
                                if isinstance(resp_data, dict) and resp_data.get("status") == "success":
                                    chart_payload = resp_data.get("chart_spec")
                            if chart_payload and isinstance(chart_payload, dict):
                                chart_id = chart_payload.get("id")
                                if chart_id not in emitted_chart_ids:
                                    if chart_id:
                                        emitted_chart_ids.add(chart_id)
                                    yield _sse("chart", chart_payload)
                            if fr.get("name") in _SUBAGENT_NAMES:
                                yield _thinking_sse(fr["name"], "done")

                        if error:
                            yield _sse("error", {"message": _safe_agent_error_message(error, modality_label)})
                            return
                        if turn_complete:
                            yield _sse("done", {})
                            return
                except httpx.RemoteProtocolError:
                    # Server closed SSE connection normally after finishing
                    pass
        yield _sse("done", {})
    except Exception as exc:
        logger.exception("Remote agent stream failed")
        message = _agent_error_message(exc, modality_label) or "No pude procesar tu mensaje."
        yield _sse("error", {"message": message})


# ---------------------------------------------------------------------------

class MessageRequest(BaseModel):
    text: str


async def _ensure_session(user_id: str, session_id: str):
    session = await _session_service.get_session(
        app_name="expense_agent",
        user_id=user_id,
        session_id=session_id,
    )
    if session is None:
        await _session_service.create_session(
            app_name="expense_agent",
            user_id=user_id,
            session_id=session_id,
        )


def _event_text(event) -> str:
    if not event.content or not event.content.parts:
        return ""
    return "".join(part.text or "" for part in event.content.parts if getattr(part, "text", None))


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _thinking_sse(agent_name: str, status: str) -> str:
    labels = _SUBAGENT_LABELS.get(agent_name, {})
    label = labels.get(status, agent_name)
    return _sse("thinking", {"agent": agent_name, "status": status, "label": label})


def _chart_payload_from_function_response(function_response) -> dict | None:
    if getattr(function_response, "name", None) != _CHART_TOOL_NAME:
        return None
    response = getattr(function_response, "response", None)
    if not isinstance(response, dict) or response.get("status") != "success":
        return None
    chart_spec = response.get("chart_spec")
    return chart_spec if isinstance(chart_spec, dict) else None


def _drain_pending_chart_sse():
    for chart_spec in pop_pending_chart_specs():
        yield _sse("chart", chart_spec)


def _agent_error_message(exc: Exception, modality_label: str) -> str | None:
    if isinstance(exc, ServerError):
        is_transient = exc.status in {"UNAVAILABLE", "INTERNAL"} or "503" in str(exc) or "500" in str(exc)
        if is_transient:
            logger.warning("Gemini server error: %s", exc)
            return (
                "Gemini no pudo procesar esto ahora mismo. "
                f"El {modality_label} llegó bien, pero el modelo no pudo procesarlo. "
                "Probá reenviarlo en unos segundos."
            )

    is_rate_limited = "RESOURCE_EXHAUSTED" in str(exc) or "429" in str(exc)
    if is_rate_limited:
        logger.warning("Gemini quota/rate limit reached: %s", exc)
        return (
            f"Gemini recibió el {modality_label}, pero tu cuota o límite de uso está agotado para este modelo. "
            "Esperá unos segundos y probá de nuevo, o cambiá `EXPENSE_AGENT_MODEL` por un modelo con cuota disponible."
        )
    return None


def _safe_agent_error_message(error: str, modality_label: str) -> str:
    return _agent_error_message(Exception(error), modality_label) or "No pude procesar tu mensaje."


async def _run_agent(content: Content, modality_label: str = "mensaje") -> str | None:
    user_id = current_user_id()
    session_id = current_session_id(user_id)
    await _ensure_session(user_id, session_id)

    for attempt in range(AGENT_MAX_ATTEMPTS):
        try:
            response = ""
            async for event in _runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=content,
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    response = event.content.parts[0].text or ""
            return response or "No pude procesar tu mensaje."
        except Exception as exc:
            is_transient = isinstance(exc, ServerError) and (
                exc.status in {"UNAVAILABLE", "INTERNAL"} or "503" in str(exc) or "500" in str(exc)
            )
            if is_transient and attempt < AGENT_MAX_ATTEMPTS - 1:
                await asyncio.sleep(1)
                continue
            message = _agent_error_message(exc, modality_label)
            if message:
                return message
            raise


async def _stream_agent(content: Content, modality_label: str = "mensaje"):
    if AGENT_URL:
        async for chunk in _stream_agent_remote(content, modality_label):
            yield chunk
        return

    user_id = current_user_id()
    session_id = current_session_id(user_id)
    await _ensure_session(user_id, session_id)
    run_config = RunConfig(streaming_mode=StreamingMode.SSE)
    try:
        total_streamed = ""
        turn_boundary_pending = False
        emitted_chart_ids: set[str] = set()
        async for event in _runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
            run_config=run_config,
        ):
            text = _event_text(event)
            has_fc = bool(event.get_function_calls())

            if has_fc:
                # aggregator.close() produces a non-partial event with text+FC when
                # the agent speaks before calling a tool. is_final_response() returns
                # False (because FC present), so without this branch the text would go
                # to the delta path and be emitted again (duplicate). The text was
                # already streamed via partial delta events — skip it.
                for fc in event.get_function_calls():
                    if fc.name in _SUBAGENT_NAMES:
                        yield _thinking_sse(fc.name, "running")
                turn_boundary_pending = True
            elif text:
                if event.is_final_response():
                    if not total_streamed:
                        total_streamed = text
                        yield _sse("token", {"text": text})
                    elif text.startswith(total_streamed):
                        remainder = text[len(total_streamed):]
                        if remainder:
                            total_streamed += remainder
                            yield _sse("token", {"text": remainder})
                    turn_boundary_pending = True
                else:
                    if turn_boundary_pending and total_streamed:
                        yield _sse("token", {"text": "\n\n"})
                        total_streamed += "\n\n"
                        turn_boundary_pending = False
                    total_streamed += text
                    yield _sse("token", {"text": text})

            for fr in event.get_function_responses():
                chart_payload = _chart_payload_from_function_response(fr)
                chart_id = chart_payload.get("id") if chart_payload else None
                if chart_payload and chart_id not in emitted_chart_ids:
                    if chart_id:
                        emitted_chart_ids.add(chart_id)
                    yield _sse("chart", chart_payload)
                if fr.name in _SUBAGENT_NAMES:
                    yield _thinking_sse(fr.name, "done")

            for chart_event in _drain_pending_chart_sse():
                try:
                    event_data = json.loads(chart_event.split("data: ", 1)[1])
                    chart_id = event_data.get("id")
                except Exception:
                    chart_id = None
                if chart_id in emitted_chart_ids:
                    continue
                if chart_id:
                    emitted_chart_ids.add(chart_id)
                yield chart_event

            if event.error_message:
                yield _sse("error", {"message": _safe_agent_error_message(event.error_message, modality_label)})
                return
            if event.turn_complete:
                yield _sse("done", {})
                return
        yield _sse("done", {})
    except Exception as exc:
        message = _agent_error_message(exc, modality_label) or "No pude procesar tu mensaje."
        yield _sse("error", {"message": message})


def _streaming_response(content: Content, modality_label: str):
    return StreamingResponse(
        _stream_agent(content, modality_label=modality_label),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _audio_content(audio: UploadFile):
    data = await audio.read()
    mime_type = (audio.content_type or "audio/wav").split(";")[0]
    if mime_type not in SUPPORTED_AUDIO_TYPES:
        logger.warning("Unsupported audio MIME type received: %s", audio.content_type)
        return {
            "response": (
                "No pude procesar ese formato de audio. "
                "Probá grabar de nuevo; la app va a enviarlo en formato WAV."
            )
        }
    return Content(
        role="user",
        parts=[
            Part.from_text(
                text=(
                    "Transcribí este audio y respondé como ExpenseBot. "
                    "Si menciona un gasto, extraelo y guardalo usando las herramientas."
                )
            ),
            Part.from_bytes(data=data, mime_type=mime_type),
        ],
    )


async def _image_content(image: UploadFile):
    data = await image.read()
    mime_type = (image.content_type or "image/jpeg").split(";")[0]

    if mime_type in SUPPORTED_SPREADSHEET_MIME:
        try:
            table_text = spreadsheet_to_text(data, mime_type, image.filename or "archivo")
        except Exception as exc:
            logger.warning("Failed to parse spreadsheet %s: %s", image.filename, exc)
            return {"response": "No pude leer el archivo. Verificá que sea un CSV o Excel (.xlsx) válido."}
        prompt = (
            "El usuario compartió el siguiente archivo con datos financieros. "
            "Analizá el contenido, identificá gastos, pagos o servicios, "
            "y guardá los registros relevantes usando las herramientas disponibles.\n\n"
            + table_text
        )
        return Content(role="user", parts=[Part.from_text(text=prompt)])

    if mime_type not in SUPPORTED_IMAGE_TYPES:
        logger.warning("Unsupported file MIME type received: %s", image.content_type)
        return {
            "response": (
                "No pude procesar ese formato de archivo. "
                "Soportamos imágenes, PDF, CSV y Excel (.xlsx)."
            )
        }
    return Content(
        role="user",
        parts=[
            Part.from_text(
                text=(
                    "Extraé los datos de este recibo o factura y guardá el gasto usando las herramientas disponibles."
                )
            ),
            Part.from_bytes(data=data, mime_type=mime_type),
        ],
    )


@router.post("/message")
async def agent_message(body: MessageRequest):
    content = Content(role="user", parts=[Part.from_text(text=body.text)])
    return {"response": await _run_agent(content, modality_label="mensaje")}


@router.post("/message/stream")
async def agent_message_stream(body: MessageRequest):
    content = Content(role="user", parts=[Part.from_text(text=body.text)])
    return _streaming_response(content, modality_label="mensaje")


@router.post("/audio")
async def agent_audio(audio: UploadFile = File(...)):
    content_or_error = await _audio_content(audio)
    if isinstance(content_or_error, dict):
        return content_or_error
    return {"response": await _run_agent(content_or_error, modality_label="audio")}


@router.post("/audio/stream")
async def agent_audio_stream(audio: UploadFile = File(...)):
    content_or_error = await _audio_content(audio)
    if isinstance(content_or_error, dict):
        return StreamingResponse(
            iter([_sse("error", {"message": content_or_error["response"]})]),
            media_type="text/event-stream",
        )
    return _streaming_response(content_or_error, modality_label="audio")


@router.post("/image")
async def agent_image(image: UploadFile = File(...)):
    content_or_error = await _image_content(image)
    if isinstance(content_or_error, dict):
        return content_or_error
    return {"response": await _run_agent(content_or_error, modality_label="imagen")}


@router.post("/image/stream")
async def agent_image_stream(image: UploadFile = File(...)):
    content_or_error = await _image_content(image)
    if isinstance(content_or_error, dict):
        return StreamingResponse(
            iter([_sse("error", {"message": content_or_error["response"]})]),
            media_type="text/event-stream",
        )
    return _streaming_response(content_or_error, modality_label="imagen")
