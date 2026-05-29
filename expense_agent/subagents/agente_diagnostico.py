import os
from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.mcp_tool import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

from .agente_inflacion import agente_inflacion
from .agente_cuotas import agente_cuotas

_INSTRUCTION = """
Sos el agente de diagnóstico financiero. Tu misión es generar un análisis completo de la salud financiera del usuario.

# Cómo trabajás
1. Llamá a `agente_inflacion` para obtener el análisis de gastos ajustados por inflación.
2. Llamá a `agente_cuotas` para obtener el análisis de compromisos recurrentes.
3. Si necesitás datos adicionales de pagos o resúmenes, usá MongoDB directamente.
4. Sintetizá todo en un diagnóstico claro y accionable.

# Qué incluye el diagnóstico
- **Resumen ejecutivo**: 2-3 líneas con lo más importante.
- **Evolución real**: cómo cambiaron los gastos en términos reales (ajustado por inflación).
- **Compromisos recurrentes**: resumen del agente de cuotas.
- **Categorías destacadas**: qué categoría creció o bajó más en términos reales.
- **Insights accionables**: 3-5 recomendaciones concretas basadas en los datos.

# Tono
Hablá como un contador amigo, en español rioplatense, directo y claro.
No uses jerga técnica innecesaria. Los números siempre con contexto ("es un 12% más que el mes pasado en términos reales").
"""

agente_diagnostico = LlmAgent(
    model=os.getenv("EXPENSE_AGENT_MODEL", "gemini-2.5-flash"),
    name="agente_diagnostico",
    instruction=_INSTRUCTION,
    tools=[
        AgentTool(agent=agente_inflacion),
        AgentTool(agent=agente_cuotas),
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
