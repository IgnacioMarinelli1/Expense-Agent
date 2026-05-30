# Expense Agent — Documentación del Proyecto

El código es la fuente de verdad. Este documento describe el estado actual del repo.

Expense Agent, hoy presentado en la UI como **Al Día**, es un asistente contable personal para registrar gastos, pagos, servicios recurrentes y cuotas por chat, audio, imagen o PDF. Está pensado como demo para la **Google Cloud Rapid Agent Hackathon** con arquitectura multi-agente y pasos de razonamiento visibles en la interfaz.

---

## Stack

| Capa | Tecnología |
|---|---|
| Backend | FastAPI + Python |
| Agente | Google ADK 2.1.0 |
| DB | MongoDB Atlas via Motor |
| MCP | `mongodb-mcp-server` via npx |
| HTTP externo | `httpx` |
| Frontend | SvelteKit 5 (runes mode) + Tailwind |
| Gráficos | Apache ECharts + ECharts GL |
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
MONGO_DB_NAME=expense_agent_db          # opcional
```

El frontend usa `VITE_API_URL` si existe; si no, asume el backend en el mismo host, puerto `8000`.

---

## Estructura del proyecto

```
Expense-Agent/
├── main.py                          # FastAPI app, lifespan, CORS, routers
├── .env                             # MONGO_URI, GOOGLE_API_KEY
├── .mcp.json                        # Config del MongoDB MCP server (referencia)
├── sessions.db                      # SQLite de sesiones ADK (auto-generado)
├── requirements.txt                  # Dependencias Python, ADK fijado en 2.1.0
│
├── expense_agent/
│   ├── agent.py                     # Root agent (LlmAgent) + override de features
│   ├── tools.py                     # Tools del agente raíz (gastos, servicios, presupuesto, sueldo)
│   ├── tools_ipc.py                 # Tool para fetchear IPC del INDEC (datos.gob.ar)
│   └── subagents/
│       ├── __init__.py              # Exporta sub-agentes
│       ├── agente_inflacion.py      # Ajuste por inflación con IPC real
│       ├── agente_cuotas.py         # Análisis de compromisos recurrentes
│       ├── agente_diagnostico.py    # Diagnóstico financiero
│       └── agente_visualizacion.py  # Gráficos interactivos
│   └── charting.py                  # Tool y builder de ChartSpec seguro
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
├── helpers/
│   └── db_helpers.py                 # Creación segura de colecciones
├── tests/
│   └── test_frontend_api_params.py   # Check de compat frontend/backend
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
│           ├── ThinkingSteps.svelte # Componente de thinking steps
│           └── ChatChart.svelte     # Render ECharts/ECharts GL en chat
```

---

## Arquitectura del agente

### Agente raíz: `expense_agent` (`expense_agent/agent.py`)

El orquestador principal. Maneja directamente las operaciones cotidianas y delega análisis complejos.

ADK 2.1.0 tiene `JSON_SCHEMA_FOR_FUNC_DECL` habilitado por defecto; en este proyecto se deshabilita antes de crear cualquier `LlmAgent` porque provocaba que Gemini ignorara tools:
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
- `save_monthly_finance` — guarda/actualiza sueldo y presupuesto de un mes
- `get_monthly_finance` — consulta sueldo y presupuesto guardados
- `get_monthly_finance_summary` — compara gastos contra presupuesto/sueldo
- `MCPToolset` — acceso directo a MongoDB (operaciones complejas)
- `AgentTool(agente_diagnostico)` — delegación de análisis financiero complejo
- `AgentTool(agente_visualizacion)` — delegación de gráficos interactivos

**Cuándo delega a `agente_diagnostico`** (según el prompt):
- "¿cómo me fue este mes?" / "resumen de mayo"
- "ajustado por inflación" / "en términos reales"
- "¿cuánto pago en cuotas?" / "mis compromisos"
- "diagnóstico" / "salud financiera"

**Nunca delega para**: registrar un gasto, listar, queries simples.

**Cuándo delega a `agente_visualizacion`**:
- "haceme un gráfico", "visualizá", "mostrame"
- "compará", "evolución", "distribución", "ranking"
- "por categoría", "por mes", "en 3D", "en torta", "en barras"

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

#### `agente_visualizacion`
- **Misión**: elegir el gráfico adecuado y producir una visualización interactiva segura
- **Tools**: `get_chart_source_data`, `generate_custom_chart`, `generate_financial_chart`
- **Flujo recomendado**: interpreta intención visual → lee pagos crudos → decide categorías semánticas → diseña un `option` completo de ECharts → llama a `generate_custom_chart`
- **Fallback**: `generate_financial_chart` queda para gráficos simples/rápidos
- **Regla**: el agente tiene libertad total sobre el diseño del gráfico, pero el backend valida que el `option` sea JSON puro sin funciones ni strings ejecutables
- **Tono**: no debe mencionar campos internos (`service_id`, `category_overrides`), MongoDB, tools, JSON/specs ni pasos operativos; solo muestra el gráfico y una lectura contable

### ChartSpec
`expense_agent/charting.py` genera specs compatibles con ECharts:
```
id, title, subtitle, mode ("2d"|"3d"), chartType, option,
insights, source, generatedAt
```

Hay dos caminos:
- `generate_custom_chart`: el sub-agente arma libremente las opciones completas de ECharts (`dataset`, `series`, `encode`, `grid`, `legend`, `xAxis`, `yAxis`, `grid3D`, etc.) y el backend solo sanitiza/encola.
- Todos los charts se normalizan a tema oscuro/transparente para integrarse con el chat negro.
- `generate_financial_chart`: builder determinístico con catálogo curado, usado como fallback.

Catálogo fallback:
- 2D: `bar`, `stacked_bar`, `line`, `area`, `pie`, `donut`, `treemap`, `heatmap`, `radar`, `scatter`, `waterfall`
- 3D: `bar3d`, `scatter3d`, `category_month_bar3d`
- `auto` elige 2D para claridad simple y 3D cuando hay dos dimensiones relevantes

---

## MongoDB

**DB name**: `expense_agent_db` (configurable via `MONGO_DB_NAME` en `.env`)

**Colecciones:**

### `payments` — gastos y pagos
```
user_id, amount, currency, payment_date (datetime|ISO string),
due_date, status (paid|pending|overdue), notes, period (YYYY-MM),
service_id, property_id, input_method, metadata, ai_extracted, created_at
```

### `services` — servicios recurrentes y suscripciones
```
user_id, name, normalized_name, category, provider,
billing_frequency (monthly|weekly|yearly|quarterly|unknown),
currency, active, default_due_day, metadata.recurring_amount,
metadata.notes, created_at, updated_at
```

### `monthly_finances` — sueldo y presupuesto mensual
```
user_id, period (YYYY-MM), salary, budget, currency, notes,
created_at, updated_at
```

El agente usa esta colección para registrar frases como "mi sueldo este mes es X" o "quiero gastar máximo Y" y para responder "cómo vengo con el presupuesto" cruzándolo con `payments`.

### `users`, `properties`
Existen como soporte para una etapa posterior. Hoy no son el centro del flujo.

**`user_id` fijo**: `"demo_user"` en tools y rutas compat. Es intencional por ahora: todavía no hay login ni multiusuario.

---

## SSE Streaming (backend)

Endpoints streaming:
- `POST /agent/message/stream`
- `POST /agent/audio/stream`
- `POST /agent/image/stream`

Eventos SSE emitidos por `_stream_agent` en `routes/agent.py`:

| Evento | Payload | Cuándo |
|---|---|---|
| `token` | `{"text": "..."}` | Cada chunk de texto del agente |
| `thinking` | `{"agent": "agente_inflacion", "status": "running"\|"done", "label": "..."}` | Cuando el root agent invoca/recibe respuesta de un sub-agente |
| `chart` | `ChartSpec` | Cuando `generate_financial_chart` devuelve una visualización exitosa |
| `error` | `{"message": "..."}` | Error del modelo o del agente |
| `done` | `{}` | Fin del turno |

`_stream_agent` detecta primero los `function_calls` para evitar duplicar texto cuando ADK cierra un agregado con texto + tool call. Ese texto ya fue emitido como delta parcial.

**Thinking events**: cuando `event.get_function_calls()` contiene el nombre de un sub-agente conocido (`agente_diagnostico`, `agente_inflacion`, `agente_cuotas`, `agente_visualizacion`), se emite `thinking` con `status: "running"`. Cuando llega el `function_response` correspondiente, se emite `thinking` con `status: "done"`.

**Chart events**: cuando `generate_financial_chart` produce un `ChartSpec`, la tool lo deja en una cola efímera local. `_stream_agent` drena esa cola y emite `event: chart`. Esto cubre tanto llamadas directas como llamadas internas del sub-agente `agente_visualizacion`, porque ADK no siempre expone las tool calls anidadas como `function_response` del runner raíz.

---

## Frontend — Chat (`+page.svelte`)

Usa Svelte 5 **runes mode** (`$state`, `$effect`, `$props`). No usar sintaxis Svelte 4 (`export let`, `$:`).

**Tipo `Message`** (en `stores/expenses.ts`):
```ts
type TraceStep = { agent: string; label: string; status: 'running' | 'done' | 'error' }
type Message = {
  id: number; type: 'usuario' | 'agente'; text: string;
  loading?: boolean; fileUrl?: string; fileType?: 'image' | 'pdf';
  traces?: TraceStep[]; charts?: ChartSpec[]
}
```

**Flujo de un mensaje con thinking steps:**
1. Usuario manda mensaje → se crea mensaje agente con `traces: []`
2. SSE `thinking` llega → `upsertTrace()` actualiza el TraceStep del agente correspondiente
3. SSE `token` llega → texto se acumula en `responseText`
4. SSE `chart` llega → `ChatChart.svelte` renderiza el gráfico interactivo arriba del texto
5. `ThinkingSteps.svelte` se muestra arriba del texto mientras `loading=true`, se auto-colapsa 1.5s después de que todos los pasos terminan

**Animación de tokens**: cada palabra del stream tiene `animation-delay` calculado por offset en el HTML. Ver `parseAndAnimate()` en `+page.svelte`.

**Media input**:
- Audio: `MediaRecorder` captura audio del navegador, se convierte a WAV en cliente y se envía a `/agent/audio/stream`.
- Imagen/PDF: se previsualiza en el chat y se envía a `/agent/image/stream`.

**Gráficos**:
- `ChatChart.svelte` carga `echarts` y `echarts-gl` solo en cliente.
- Sanitiza strings ejecutables antes de pasar opciones a ECharts.
- Los gráficos son efímeros en el mensaje; no se persisten en MongoDB ni ADK Artifacts.

**`StreamHandlers`** en `api/client.ts`:
```ts
type StreamHandlers = {
  onToken: (text: string) => void
  onError?: (message: string) => void
  onDone?: () => void
  onThinking?: (agent: string, status: string, label: string) => void
  onChart?: (chart: ChartSpec) => void
}
```

---

## MCPToolset — MongoDB MCP

El `mongodb-mcp-server` se lanza via `npx` desde cada `MCPToolset` configurado en el agente raíz y subagentes.

En código se mapea `MONGO_URI` a la variable esperada por el proceso MCP:
```
MDB_MCP_CONNECTION_STRING=<MONGO_URI>
```

`.mcp.json` queda como referencia para usar MCP fuera del runtime de ADK.

---

## Endpoints principales

| Método | Path | Descripción |
|---|---|---|
| POST | `/agent/message` | Chat no-streaming |
| POST | `/agent/message/stream` | Chat streaming (SSE) — **el principal** |
| POST | `/agent/audio` | Audio no-streaming |
| POST | `/agent/audio/stream` | Audio streaming (SSE) |
| POST | `/agent/image` | Imagen/PDF no-streaming |
| POST | `/agent/image/stream` | Imagen/PDF streaming (SSE) |
| GET | `/expenses?month=YYYY-MM` | Lista gastos para frontend |
| POST | `/expenses` | Crea gasto manualmente desde frontend |
| PATCH | `/expenses/{id}/pay` | Marca gasto como pagado |
| GET | `/summary?month=YYYY-MM` | Resumen para dashboard |
| CRUD | `/payments/*` | CRUD genérico de pagos |
| GET | `/payments/summary/?user_id=...&period=YYYY-MM` | Resumen genérico por status |
| POST/GET | `/users/*` | CRUD mínimo de usuarios |
| GET | `/health` | Health check |

---

## ADK — Detalles importantes

- **Versión usada/local**: `google-adk==2.1.0`
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

## Frontend — Vistas

### `/`
Chat principal. Es la experiencia primaria del producto.

### `/expenses`
Lista gastos desde `GET /expenses`, separa pendientes y pagados, y permite marcar un pendiente como pagado con `PATCH /expenses/{id}/pay`.

### `/dashboard`
Dashboard básico para el mes actual. Consume `GET /summary?month=YYYY-MM`. Tiene tarjetas de gastado, pendiente y pagos; gráfico por categoría y calendario siguen como placeholders.

---

## Estado Actual y Deuda Conocida

- No hay autenticación ni multiusuario; `demo_user` es deliberado.
- La categorización del frontend compat es heurística por texto (`luz`, `gas`, `agua`, etc.).
- El dashboard todavía no implementa gráficos ni calendario real.
- Los gráficos generados por agente viven en el chat; el dashboard sigue separado y básico.
- `sessions.db` es estado local de ADK. Puede cambiar al usar el agente.
- Hay dos lockfiles en frontend (`package-lock.json` y `pnpm-lock.yaml`) porque el proyecto se puede levantar con npm o pnpm; hoy los scripts documentados usan npm.
- Los tests actuales son mínimos y cubren la compatibilidad del query param mensual entre frontend y backend.

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
