import asyncio
import logging

from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.errors import ServerError
from google.genai.types import Content, Part

from expense_agent.agent import root_agent

router = APIRouter(prefix="/agente", tags=["agente"])
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

_session_service = InMemorySessionService()
_runner = Runner(
    agent=root_agent,
    app_name="expense_agent",
    session_service=_session_service,
)

SESSION_ID = "demo_session"
USER_ID = "demo_user"


class MensajeRequest(BaseModel):
    texto: str


async def _run_agent(content: Content) -> str:
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

    for attempt in range(AGENT_MAX_ATTEMPTS):
        try:
            respuesta = ""
            async for event in _runner.run_async(
                user_id=USER_ID,
                session_id=SESSION_ID,
                new_message=content,
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    respuesta = event.content.parts[0].text or ""
            return respuesta or "No pude procesar tu mensaje."
        except ServerError as exc:
            is_transient = exc.status in {"UNAVAILABLE", "INTERNAL"} or "503" in str(exc) or "500" in str(exc)
            if is_transient and attempt < AGENT_MAX_ATTEMPTS - 1:
                await asyncio.sleep(1)
                continue
            if is_transient:
                logger.warning("Gemini server error after retries: %s", exc)
                return (
                    "Gemini no pudo procesar esto ahora mismo. "
                    "El audio llegó bien, pero el modelo no pudo procesarlo. Probá reenviarlo en unos segundos."
                )
            raise
        except Exception as exc:
            is_rate_limited = "RESOURCE_EXHAUSTED" in str(exc) or "429" in str(exc)
            if is_rate_limited:
                logger.warning("Gemini quota/rate limit reached: %s", exc)
                return (
                    "Gemini recibió el audio, pero tu cuota o límite de uso está agotado para este modelo. "
                    "Esperá unos segundos y probá de nuevo, o cambiá `EXPENSE_AGENT_MODEL` por un modelo con cuota disponible."
                )
            raise


@router.post("/mensaje")
async def agente_mensaje(body: MensajeRequest):
    content = Content(role="user", parts=[Part.from_text(text=body.texto)])
    return {"respuesta": await _run_agent(content)}


@router.post("/audio")
async def agente_audio(audio: UploadFile = File(...)):
    data = await audio.read()
    mime_type = (audio.content_type or "audio/wav").split(";")[0]
    if mime_type not in SUPPORTED_AUDIO_TYPES:
        logger.warning("Unsupported audio MIME type received: %s", audio.content_type)
        return {
            "respuesta": (
                "No pude procesar ese formato de audio. "
                "Probá grabar de nuevo; la app va a enviarlo en formato WAV."
            )
        }
    content = Content(
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
    return {"respuesta": await _run_agent(content)}
