from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from expense_agent.agent import root_agent

router = APIRouter(prefix="/agente", tags=["agente"])

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
    respuesta = ""
    async for event in _runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=content,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            respuesta = event.content.parts[0].text or ""
    return respuesta or "No pude procesar tu mensaje."


@router.post("/mensaje")
async def agente_mensaje(body: MensajeRequest):
    content = Content(role="user", parts=[Part.from_text(body.texto)])
    return {"respuesta": await _run_agent(content)}


@router.post("/audio")
async def agente_audio(audio: UploadFile = File(...)):
    data = await audio.read()
    content = Content(
        role="user",
        parts=[Part.from_bytes(data=data, mime_type="audio/webm")],
    )
    return {"respuesta": await _run_agent(content)}
