import os
from datetime import datetime
from google.adk.agents import LlmAgent
from db.security import current_user_id

CURRENT_USER_ID = current_user_id()
CURRENT_DATE = datetime.now().date().isoformat()

# BACKEND_PUBLIC_URL: URL pública del backend principal (sin trailing slash).
# En local dev, setear a http://localhost:8000.
# En Cloud Run (agent service), setear BACKEND_PUBLIC_URL a la URL del backend principal.
BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8000").rstrip("/")


async def get_excel_download_url(month: str = None) -> dict:
    """Genera la URL de descarga para un Excel con los gastos del usuario.
    month: período en formato YYYY-MM. Si es None, exporta todos los gastos.
    Retorna la URL completa lista para usar en un link de descarga."""
    if month:
        url = f"{BACKEND_PUBLIC_URL}/export/expenses?month={month}"
        filename = f"gastos_{month}.xlsx"
        label = f"Descargar Excel de gastos ({month})"
    else:
        url = f"{BACKEND_PUBLIC_URL}/export/expenses"
        filename = "gastos_todos.xlsx"
        label = "Descargar Excel con todos los gastos"
    return {"status": "success", "download_url": url, "filename": filename, "label": label}


_INSTRUCTION = f"""
# Identity
Sos el agente de exportación de reportes de Expense Agent.
Tu misión: entender qué período quiere exportar el usuario y generar el link de descarga del Excel.
CRÍTICO: Respondé siempre en español rioplatense, de forma breve y directa.

# Contexto
Fecha actual: {CURRENT_DATE}.

# Flujo de trabajo

1. Determiná el período que pide el usuario:
   - Si menciona un mes o período específico, usalo en formato YYYY-MM.
   - Si dice "todos", "completo", "todo", llamá a get_excel_download_url sin month (exporta todo).
   - Si no especifica, usá el mes actual ({CURRENT_DATE[:7]}).

2. Llamá a get_excel_download_url con el month correspondiente.
   - Si pide ambos meses o varios períodos, hacé UNA llamada por cada período.

3. Respondé con el/los links de descarga en formato markdown, usando EXACTAMENTE la download_url que devolvió la tool — nunca inventes ni modifiques la URL.

# Reglas
- CRÍTICO: el link de descarga debe ser la download_url exacta que retornó get_excel_download_url. No uses URLs de ejemplo ni placeholders.
- Si el usuario pide varios meses, generá un link por mes en la misma respuesta.
- NO consultés MongoDB. Solo llamá a get_excel_download_url y devolvé el link.
- No respondas con JSON, IDs ni nombres internos.
- Máximo 2 oraciones + los links.
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
