# Al Día — Expense Agent

AI-powered personal finance assistant for families. Register expenses, recurring services, installments and income by **chat, audio, image or PDF**, and get dashboards, inflation-aware analysis and Excel exports — all driven by a multi-agent system whose reasoning steps are visible in the UI.

Built for the **Google Cloud Rapid Agent Hackathon** (MongoDB partner track).

## Live demo

- **App (frontend):** https://al-dia-expense-agent--al-dia-expense-agent.us-east4.hosted.app
- **API (backend health):** https://expense-agent-thm7giy46q-rj.a.run.app/health

## Hackathon tech requirements

| Requirement | Where it lives |
|---|---|
| **Gemini** | `gemini-2.5-flash` powers the root agent and all subagents (`expense_agent/agent.py`, `expense_agent/subagents/`) |
| **Google Cloud Agent Builder** | Google ADK 2.1.0 multi-agent system: root agent + 5 specialized subagents, deployed on Cloud Run |
| **MongoDB MCP server** | Official `mongodb-mcp-server` deployed as its own Cloud Run service (`Dockerfile.mcp`), consumed via ADK `MCPToolset` over streamable HTTP by the root agent, `agente_cuotas` and `agente_inflacion` |

## Architecture

```
SvelteKit 5 frontend ──► FastAPI backend ──► ADK root agent (Gemini 2.5 Flash)
(Firebase App Hosting)      (Cloud Run)         ├── agente_cuotas        ─┐
                                │               ├── agente_inflacion     ─┤── MCPToolset ──► mongodb-mcp-server ──► MongoDB Atlas
                                │               ├── agente_diagnostico    │                     (Cloud Run)
                                │               ├── agente_visualizacion  │
                                ▼               └── agente_excel          │
                          MongoDB Atlas (Motor) ◄─────────────────────────┘
```

- **Backend:** FastAPI + Motor (async MongoDB), SSE streaming for chat, Apache ECharts payloads for visualizations, `openpyxl` Excel exports with automatic download cards.
- **Agents:** root agent routes to subagents for installments (cuotas), inflation analysis, financial diagnosis, charting and Excel export. Multi-currency ARS/USD with live exchange rate.
- **MCP:** complex/ad-hoc MongoDB queries go through the official MongoDB MCP server; CRUD-style operations use first-party Python tools.

## Run it locally

### Prerequisites

- Python 3.11+, Node 20+, `pnpm`
- A MongoDB Atlas cluster (connection string)
- A Gemini API key ([Google AI Studio](https://aistudio.google.com/apikey))

### 1. MongoDB MCP server

```bash
MDB_MCP_CONNECTION_STRING="<your MongoDB Atlas URI>" \
npx -y mongodb-mcp-server --transport http --httpPort 8081
```

### 2. Backend

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cat > .env <<'EOF'
MONGO_URI=<your MongoDB Atlas URI>
GOOGLE_API_KEY=<your Gemini API key>
EXPENSE_AGENT_MODEL=gemini-2.5-flash
MDB_MCP_URL=http://localhost:8081/mcp
EOF

uvicorn main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
pnpm install
VITE_API_URL=http://localhost:8000 pnpm dev
```

Open http://localhost:5173.

### Tests

```bash
pytest tests/
```

## Deploy (Google Cloud)

- **Backend → Cloud Run:** `gcloud builds submit --config cloudbuild.yaml` (secrets `MONGO_URI`, `GOOGLE_API_KEY` injected via Cloud Run).
- **MCP server → Cloud Run:** `gcloud builds submit --config cloudbuild-mcp.yaml`, then point the backend's `MDB_MCP_URL` at the service (OIDC auth between services is handled at startup).
- **Frontend → Firebase App Hosting:** see [DEPLOY_FRONT.md](DEPLOY_FRONT.md).

## Environment variables

| Variable | Component | Description |
|---|---|---|
| `MONGO_URI` | backend | MongoDB Atlas connection string |
| `GOOGLE_API_KEY` | backend | Gemini API key |
| `EXPENSE_AGENT_MODEL` | backend | Gemini model id (default `gemini-2.5-flash`) |
| `MDB_MCP_URL` | backend | MongoDB MCP server URL (default `http://localhost:8081/mcp`) |
| `CORS_ALLOW_ORIGINS` | backend | Comma-separated allowed origins (optional) |
| `MDB_MCP_CONNECTION_STRING` | MCP server | MongoDB Atlas connection string |
| `VITE_API_URL` | frontend | Backend base URL (build-time) |

## License

[MIT](LICENSE)
