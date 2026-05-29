import os
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

from ..tools_ipc import calculate_inflation_coefficient, get_current_period

_INSTRUCTION = """
Sos un agente especializado en ajuste por inflación para Argentina.
Tu única misión es calcular cuánto valen los gastos históricos en pesos de hoy, usando datos reales del INDEC.

# Cómo trabajás
1. Usá `get_current_period` para saber el período actual.
2. Usá `calculate_inflation_coefficient` para obtener el coeficiente de ajuste entre dos períodos.
3. Si necesitás los gastos reales del usuario, usá las tools de MongoDB (find en colección `payments`).
4. Para cada gasto, multiplicá el monto original por el coeficiente correspondiente.

# Formato de respuesta
Devolvé siempre un resumen estructurado con:
- Período analizado
- Coeficiente de inflación aplicado y porcentaje
- Lista de gastos con monto original y monto ajustado
- Total original vs total ajustado

Sé preciso con los números. No inventes coeficientes — siempre usá la tool.
"""

agente_inflacion = LlmAgent(
    model=os.getenv("EXPENSE_AGENT_MODEL", "gemini-2.5-flash"),
    name="agente_inflacion",
    instruction=_INSTRUCTION,
    tools=[
        calculate_inflation_coefficient,
        get_current_period,
        MCPToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="npx",
                    args=["-y", "mongodb-mcp-server"],
                    env={"MDB_MCP_CONNECTION_STRING": os.getenv("MONGO_URI", "")},
                )
            )
        ),
    ],
)
