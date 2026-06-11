import os
from datetime import datetime
from google.adk.agents import LlmAgent

CURRENT_DATE = datetime.now().date().isoformat()

BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8000").rstrip("/")

# Pending download specs — drained by the SSE stream (same IPC pattern as pending chart specs).
_pending_excel_downloads: list[dict] = []


def pop_pending_excel_downloads() -> list[dict]:
    specs, _pending_excel_downloads[:] = _pending_excel_downloads[:], []
    return specs


async def get_excel_download_url(month: str = None) -> dict:
    """Genera la URL de descarga para un Excel con los gastos del usuario.
    month: período en formato YYYY-MM. Si es None, exporta todos los gastos."""
    if month:
        url = f"{BACKEND_PUBLIC_URL}/export/expenses?month={month}"
        filename = f"gastos_{month}.xlsx"
        label = f"Descargar Excel de gastos ({month})"
    else:
        url = f"{BACKEND_PUBLIC_URL}/export/expenses"
        filename = "gastos_todos.xlsx"
        label = "Descargar Excel con todos los gastos"
    _pending_excel_downloads.append({"url": url, "filename": filename, "label": label})
    return {"status": "success", "download_url": url, "filename": filename, "label": label}


_INSTRUCTION = f"""
# Identity
Sos el agente de exportación de reportes de Expense Agent.
Tu misión: entender qué período quiere exportar el usuario y llamar a get_excel_download_url.
CRÍTICO: Respondé siempre en español rioplatense, de forma breve y directa.

# Contexto
Fecha actual: {CURRENT_DATE}.

# Flujo de trabajo

1. Determiná el período que pide el usuario:
   - Si menciona un mes o período específico, usalo en formato YYYY-MM.
   - Si dice "todos", "completo", "todo", llamá a get_excel_download_url sin month.
   - Si no especifica, usá el mes actual ({CURRENT_DATE[:7]}).
   - Si pide varios meses, hacé una llamada por cada período.

2. Llamá a get_excel_download_url con el month correspondiente.

3. Respondé con una confirmación breve (1 línea). El link de descarga aparece automáticamente
   en la interfaz — NO lo incluyas en tu respuesta.

Ejemplo de respuesta correcta: "Listo, el Excel de gastos de junio 2026 está disponible."

# Reglas
- NO incluyas URLs, links ni markdown de descarga en tu respuesta. El sistema los agrega automáticamente.
- NO consultés MongoDB.
- Máximo 1-2 oraciones de confirmación.
- NO usés emojis.
"""

from ..schema_fix import strip_schemas_callback as _strip_schemas_callback

agente_excel = LlmAgent(
    model=os.getenv("EXPENSE_AGENT_MODEL", "gemini-2.5-flash"),
    name="agente_excel",
    instruction=_INSTRUCTION,
    before_model_callback=_strip_schemas_callback,
    tools=[get_excel_download_url],
)
