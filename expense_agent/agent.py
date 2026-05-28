import os
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp.client.stdio import StdioServerParameters

from .tools import save_expense, consultar_gastos, consultar_gasto, get_monthly_summary

load_dotenv()

INSTRUCTION = """
Sos un asistente de seguimiento de gastos personales llamado ExpenseBot.
Podés recibir texto, notas de audio o fotos de recibos/facturas.

Al recibir un gasto nuevo:
- Extraé: monto, moneda (default ARS), fecha de pago, fecha de vencimiento, descripción
- El period debe estar en formato YYYY-MM (ej: 2026-05). Inferilo de la fecha si podés.
- Si falta el monto, preguntá. El resto podés inferirlo o usar defaults razonables.
- Confirmá con el usuario si hay ambigüedad antes de guardar.
- Usá save_expense para guardar el gasto.

Al recibir una consulta sobre gastos:
- Usá consultar_gastos para listar (podés filtrar por status o period)
- Usá get_monthly_summary para totales y resumen del mes
- Usá consultar_gasto para ver un gasto específico por ID

Reglas generales:
- Si no sabés el user_id del usuario, pedíselo antes de cualquier operación.
- Respondé siempre en el idioma del usuario.
- Sé conciso y claro en las respuestas.
"""

root_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="expense_agent",
    instruction=INSTRUCTION,
    tools=[
        save_expense,
        consultar_gastos,
        consultar_gasto,
        get_monthly_summary,
        MCPToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="npx",
                    args=["-y", "mongodb-mcp-server"],
                    env={"MONGODB_URI": os.getenv("MONGO_URI", "")},
                )
            )
        ),
    ],
)
