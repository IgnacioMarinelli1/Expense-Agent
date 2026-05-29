import asyncio
import json
import logging

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions.sqlite_session_service import SqliteSessionService
from google.genai.errors import ServerError
from google.genai.types import Content, Part

from expense_agent.agent import root_agent

router = APIRouter(prefix="/agent", tags=["agent"])
logger = logging.getLogger(__name__)

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

SESSION_ID = "demo_session"
USER_ID = "demo_user"


class MessageRequest(BaseModel):
    text: str


async def _ensure_session():
    session = await _session_service.get_session(
        app_name="expense_agent",
        user_id=USER_ID,
        session_id=SESSION_ID,
    )
    if session is None:
        await _session_service.create_session(
            app_name="expense_agent",
            user_id=USER_ID,
            session_id=SESSION_ID,
        )


def _event_text(event) -> str:
    if not event.content or not event.content.parts:
        return ""
    return "".join(part.text or "" for part in event.content.parts if getattr(part, "text", None))


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


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


async def _run_agent(content: Content, modality_label: str = "mensaje") -> str:
    await _ensure_session()

    for attempt in range(AGENT_MAX_ATTEMPTS):
        try:
            response = ""
            async for event in _runner.run_async(
                user_id=USER_ID,
                session_id=SESSION_ID,
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
    await _ensure_session()
    run_config = RunConfig(streaming_mode=StreamingMode.SSE)
    try:
        total_streamed = ""
        turn_boundary_pending = False
        async for event in _runner.run_async(
            user_id=USER_ID,
            session_id=SESSION_ID,
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

            if event.error_message:
                yield _sse("error", {"message": event.error_message})
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
    if mime_type not in SUPPORTED_IMAGE_TYPES:
        logger.warning("Unsupported file MIME type received: %s", image.content_type)
        return {
            "response": (
                "No pude procesar ese formato de archivo. "
                "Soportamos JPEG, PNG, WEBP, HEIC y PDF."
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
