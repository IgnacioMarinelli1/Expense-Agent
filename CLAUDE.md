# Expense Agent — Documentación para IA

Proyecto para la **Google Cloud Rapid Agent Hackathon** (deadline: 11 junio 2026).
Es un asistente contable personal con voz, imagen y chat, con arquitectura multi-agente y thinking steps visibles en la UI.

---

## Stack

| Capa | Tecnología |
|---|---|
| Backend | FastAPI + Python 3.14 |
| Agente | Google ADK 2.1.0 (`google-adk`) |
| DB | MongoDB Atlas via Motor (async) |
| MCP | `mongodb-mcp-server` via npx |
| HTTP externo | `httpx` (async) |
| Frontend | SvelteKit 5 (runes mode) + Tailwind |
| Sesiones | SQLite (`sessions.db`) |

---

## Cómo levantar

```bash
# Backend (desde la raíz del proyecto)
source venv/bin/activate
uvicorn main:app --reload --port 8000

# Frontend (desde /frontend)
npm run dev
```

Variables de entorno requeridas en `.env`:
```
MONGO_URI=mongodb+srv://...
GOOGLE_API_KEY=AIza...
EXPENSE_AGENT_MODEL=gemini-2.5-flash   # opcional, este es el default
```

---

## Estructura del proyecto

```
Expense-Agent/
├── main.py                          # FastAPI app, lifespan, CORS, routers
├── .env                             # MONGO_URI, GOOGLE_API_KEY
├── .mcp.json                        # Config del MongoDB MCP server (referencia)
├── sessions.db                      # SQLite de sesiones ADK (auto-generado)
│
├── expense_agent/
│   ├── agent.py                     # Root agent (LlmAgent) + override de features
│   ├── tools.py                     # 6 tools del agente raíz (save_expense, etc.)
│   ├── tools_ipc.py                 # Tool para fetchear IPC del INDEC (datos.gob.ar)
│   └── subagents/
│       ├── __init__.py              # Exporta los 3 sub-agentes
│       ├── agente_inflacion.py      # Ajuste por inflación con IPC real
│       ├── agente_cuotas.py         # Análisis de compromisos recurrentes
│       └── agente_diagnostico.py   # Diagnóstico financiero (orquesta los otros dos)
│
├── routes/
│   ├── agent.py                     # /agent/* endpoints (SSE streaming)
│   ├── frontend_compat.py           # /expenses, /summary (para el dashboard)
│   ├── payments.py                  # CRUD de pagos
│   ├── users.py                     # CRUD de usuarios
│   ├── summary.py                   # Endpoint de resumen
│   └── health.py                    # GET /health
│
├── db/
│   ├── db.py                        # Motor client singleton (get_db, get_client)
│   └── schema.py                    # Definiciones de colecciones
│
├── frontend/src/
│   ├── routes/
│   │   ├── +page.svelte             # Chat principal
│   │   ├── dashboard/+page.svelte  # Dashboard de gastos
│   │   └── expenses/+page.svelte   # Lista de gastos
│   └── lib/
│       ├── api/client.ts            # API client con SSE streaming
│       ├── stores/expenses.ts       # Svelte stores: messages, expenses, TraceStep
│       └── components/
│           └── ThinkingSteps.svelte # Componente de thinking steps
```

---

## Arquitectura del agente

### Agente raíz: `expense_agent` (`expense_agent/agent.py`)

El orquestador principal. Maneja directamente las operaciones cotidianas y delega análisis complejos.

**Bug crítico resuelto**: ADK 2.1.0 tiene `JSON_SCHEMA_FOR_FUNC_DECL` habilitado por defecto, lo que hace que Gemini ignore todas las tools. Se deshabilita así **antes** de crear cualquier LlmAgent:
```python
override_feature_enabled(FeatureName.JSON_SCHEMA_FOR_FUNC_DECL, False)
```

**Tools del root agent:**
- `save_expense` — guarda un pago/gasto
- `save_service` — crea/actualiza un servicio recurrente
- `get_expenses` — lista gastos (filtros: status, period)
- `get_expense` — obtiene un gasto por ID
- `get_services` — lista servicios recurrentes
- `get_monthly_summary` — resumen mensual por status
- `MCPToolset` — acceso directo a MongoDB (operaciones complejas)
- `AgentTool(agente_diagnostico)` — delegación de análisis financiero complejo

**Cuándo delega a `agente_diagnostico`** (según el prompt):
- "¿cómo me fue este mes?" / "resumen de mayo"
- "ajustado por inflación" / "en términos reales"
- "¿cuánto pago en cuotas?" / "mis compromisos"
- "diagnóstico" / "salud financiera"

**Nunca delega para**: registrar un gasto, listar, queries simples.

---

### Sub-agentes (`expense_agent/subagents/`)

#### `agente_inflacion`
- **Misión**: calcular gastos en pesos constantes de hoy usando IPC real del INDEC
- **Tools**: `calculate_inflation_coefficient`, `get_current_period`, `MCPToolset`
- **API**: `https://apis.datos.gob.ar/series/api/series/?ids=103.1_I2N_2016_M_15`
- **Flujo**: fetchea índice del período origen y actual → calcula coeficiente → ajusta montos

#### `agente_cuotas`
- **Misión**: analizar compromisos financieros recurrentes
- **Tools**: `MCPToolset` (lee colecciones `services` y `payments`)
- **Calcula**: compromiso mensual total (ARS y USD por separado), breakdown por categoría, próximos vencimientos

#### `agente_diagnostico`
- **Misión**: reporte de salud financiera completo
- **Tools**: `AgentTool(agente_inflacion)`, `AgentTool(agente_cuotas)`, `MCPToolset`
- **Flujo**: llama a inflación → llama a cuotas → sintetiza → genera reporte con insights accionables

---

## MongoDB

**DB name**: `expense_agent_db` (configurable via `MONGO_DB_NAME` en `.env`)

**Colecciones:**

### `payments` — gastos y pagos
```
user_id, amount, currency, payment_date (datetime|ISO string),
due_date, status (paid|pending|overdue), notes, period (YYYY-MM),
service_id, input_method, created_at
```

### `services` — servicios recurrentes y suscripciones
```
user_id, name, normalized_name, category, provider,
billing_frequency (monthly|weekly|yearly|quarterly|unknown),
currency, active, default_due_day, metadata.recurring_amount,
metadata.notes, created_at, updated_at
```

### `users`, `properties` — soporte futuro (aún no usados en profundidad)

**`user_id` fijo**: `"demo_user"` — hardcodeado en `tools.py` y `routes/frontend_compat.py`. El modelo nunca lo recibe como input.

---

## SSE Streaming (backend)

Endpoint principal: `POST /agent/message/stream`

Eventos SSE emitidos por `_stream_agent` en `routes/agent.py`:

| Evento | Payload | Cuándo |
|---|---|---|
| `token` | `{"text": "..."}` | Cada chunk de texto del agente |
| `thinking` | `{"agent": "agente_inflacion", "status": "running"\|"done", "label": "..."}` | Cuando el root agent invoca/recibe respuesta de un sub-agente |
| `error` | `{"message": "..."}` | Error del modelo o del agente |
| `done` | `{}` | Fin del turno |

**Fix crítico de duplicados** (`_stream_agent`): ADK's `StreamingResponseAggregator.close()` genera un evento `partial=False` con texto + function_call juntos. Este evento tiene `is_final_response()=False` (por la FC), así que sin el fix iría al branch de deltas y emitiría el texto de nuevo. El fix detecta `event.get_function_calls()` primero y lo ignora (el texto ya fue streameado via deltas).

**Thinking events**: cuando `event.get_function_calls()` contiene el nombre de un sub-agente conocido (`agente_diagnostico`, `agente_inflacion`, `agente_cuotas`), se emite `thinking` con `status: "running"`. Cuando llega el `function_response` correspondiente, se emite `thinking` con `status: "done"`.

---

## Frontend — Chat (`+page.svelte`)

Usa Svelte 5 **runes mode** (`$state`, `$effect`, `$props`). No usar sintaxis Svelte 4 (`export let`, `$:`).

**Tipo `Message`** (en `stores/expenses.ts`):
```ts
type TraceStep = { agent: string; label: string; status: 'running' | 'done' | 'error' }
type Message = {
  id: number; type: 'usuario' | 'agente'; text: string;
  loading?: boolean; fileUrl?: string; fileType?: 'image' | 'pdf';
  traces?: TraceStep[]
}
```

**Flujo de un mensaje con thinking steps:**
1. Usuario manda mensaje → se crea mensaje agente con `traces: []`
2. SSE `thinking` llega → `upsertTrace()` actualiza el TraceStep del agente correspondiente
3. SSE `token` llega → texto se acumula en `responseText`
4. `ThinkingSteps.svelte` se muestra arriba del texto mientras `loading=true`, se auto-colapsa 1.5s después de que todos los pasos terminan

**Animación de tokens**: cada palabra del stream tiene `animation-delay` calculado por offset en el HTML. Ver `parseAndAnimate()` en `+page.svelte`.

**`StreamHandlers`** en `api/client.ts`:
```ts
type StreamHandlers = {
  onToken: (text: string) => void
  onError?: (message: string) => void
  onDone?: () => void
  onThinking?: (agent: string, status: string, label: string) => void
}
```

---

## MCPToolset — MongoDB MCP

El `mongodb-mcp-server` se lanza via `npx` cada vez que un agente necesita usarlo. Cada instancia de `MCPToolset` en un sub-agente crea su propio proceso.

**Variable de entorno requerida por el MCP**: `MDB_MCP_CONNECTION_STRING` (se pasa desde `MONGO_URI`).

Nota: `.mcp.json` en la raíz usa `MONGODB_URI` (distinto nombre), pero en el código de los agentes se usa `MDB_MCP_CONNECTION_STRING` mapeado desde `MONGO_URI`.

---

## Endpoints principales

| Método | Path | Descripción |
|---|---|---|
| POST | `/agent/message/stream` | Chat streaming (SSE) — **el principal** |
| POST | `/agent/audio/stream` | Audio streaming (SSE) |
| POST | `/agent/image/stream` | Imagen/PDF streaming (SSE) |
| GET | `/expenses` | Lista gastos (para el dashboard) |
| POST | `/expenses` | Crea gasto manualmente |
| PATCH | `/expenses/{id}/pay` | Marca gasto como pagado |
| GET | `/summary` | Resumen de totales |
| GET | `/health` | Health check |

---

## ADK — Detalles importantes

- **Versión**: `google-adk==2.1.0`
- **Sesiones**: `SqliteSessionService("sessions.db")` — si hay problemas de compatibilidad de historial (ej: cambio de modelo), borrar `sessions.db`
- **Runner**: singleton en `routes/agent.py`, sesión fija `SESSION_ID="demo_session"`, `USER_ID="demo_user"`
- **Streaming**: `RunConfig(streaming_mode=StreamingMode.SSE)` + `PROGRESSIVE_SSE_STREAMING` feature habilitada por defecto en ADK 2.1.0
- **`is_final_response()`** retorna `True` cuando: no hay function calls, no hay function responses, `partial=False`, no hay trailing code execution

---

## Features experimentales ADK (importante)

| Feature | Estado | Motivo |
|---|---|---|
| `JSON_SCHEMA_FOR_FUNC_DECL` | **DESHABILITADO** | Causa que Gemini ignore todas las tools |
| `PROGRESSIVE_SSE_STREAMING` | habilitado (default) | Streaming word-by-word |
| `PLUGGABLE_AUTH` | habilitado (default) | Sin impacto en este proyecto |
| `_MCP_GRACEFUL_ERROR_HANDLING` | habilitado (default) | Sin impacto |

---

## Tool IPC — datos.gob.ar

Archivo: `expense_agent/tools_ipc.py`

```python
# Serie IPC Nacional base dic 2016
_IPC_SERIES_ID = "103.1_I2N_2016_M_15"
_API_BASE = "https://apis.datos.gob.ar/series/api/series/"

# Ejemplo de uso:
result = await calculate_inflation_coefficient("2026-01", "2026-04")
# → {"coefficient": 1.084595, "inflation_pct": 8.46, ...}
```

API pública, sin auth, sin rate limiting estricto. Responde en ~200ms.

---

## Contexto de la hackathon

- **Nombre**: Google Cloud Rapid Agent Hackathon
- **Deadline**: 11 junio 2026 (submisión) / juicio: 22 jun – 6 jul 2026
- **Criterios**: innovación, implementación técnica, impacto, completitud
- **Diferenciadores del proyecto**:
  1. Arquitectura multi-agente real (no solo chatbot)
  2. Thinking steps visibles en UI durante la delegación
  3. Ajuste por inflación con datos reales del INDEC (único a Argentina)
  4. Soporte de voz, imagen y PDF además de texto
- **Target**: persona física / familia argentina
