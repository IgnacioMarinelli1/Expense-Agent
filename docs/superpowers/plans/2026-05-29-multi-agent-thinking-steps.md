# Multi-Agent Architecture + Thinking Steps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Agregar 3 sub-agentes especializados (inflación, cuotas, diagnóstico) al agente raíz existente, con thinking steps visibles en la UI durante la delegación.

**Architecture:** Root agent (ExpenseBot) maneja queries simples directamente y delega análisis complejos a AgenteDiagnostico via AgentTool. AgenteDiagnostico orquesta AgenteInflacion y AgenteCuotas. Backend emite SSE `"thinking"` events cuando detecta function calls a sub-agentes. Frontend renderiza TraceStep[] sobre la respuesta.

**Tech Stack:** Google ADK 2.1.0, Python/httpx, datos.gob.ar IPC API, SvelteKit 5, TypeScript

---

### Task 1: IPC Tool

**Files:**
- Create: `expense_agent/tools_ipc.py`

- [ ] Crear tool que fetchea índice IPC de datos.gob.ar y calcula coeficiente de ajuste
- [ ] Verificar manualmente con curl que la API responde
- [ ] Commit

---

### Task 2: AgenteInflacion

**Files:**
- Create: `expense_agent/subagents/__init__.py`
- Create: `expense_agent/subagents/agente_inflacion.py`

- [ ] Crear sub-agente con tools_ipc + MCPToolset
- [ ] Commit

---

### Task 3: AgenteCuotas

**Files:**
- Create: `expense_agent/subagents/agente_cuotas.py`

- [ ] Crear sub-agente de cuotas con MCPToolset
- [ ] Commit

---

### Task 4: AgenteDiagnostico

**Files:**
- Create: `expense_agent/subagents/agente_diagnostico.py`

- [ ] Crear sub-agente que orquesta inflacion + cuotas via AgentTool
- [ ] Commit

---

### Task 5: Actualizar root agent

**Files:**
- Modify: `expense_agent/agent.py`

- [ ] Agregar AgentTool(agente_diagnostico) al tools list
- [ ] Actualizar prompt del orquestador con instrucciones de delegación
- [ ] Commit

---

### Task 6: Thinking events en backend

**Files:**
- Modify: `routes/agent.py`

- [ ] En `_stream_agent`: detectar function calls/responses a sub-agentes y emitir SSE "thinking"
- [ ] Commit

---

### Task 7: Frontend — stores + tipos

**Files:**
- Modify: `frontend/src/lib/stores/expenses.ts`

- [ ] Agregar tipo TraceStep, actualizar Message para incluir traces[]
- [ ] Commit

---

### Task 8: ThinkingSteps component

**Files:**
- Create: `frontend/src/lib/components/ThinkingSteps.svelte`

- [ ] Componente que renderiza trace steps con animación running/done/error
- [ ] Commit

---

### Task 9: API client — thinking handler

**Files:**
- Modify: `frontend/src/lib/api/client.ts`

- [ ] Agregar onThinking handler a StreamHandlers, procesar evento SSE "thinking"
- [ ] Commit

---

### Task 10: Chat page — integración

**Files:**
- Modify: `frontend/src/routes/+page.svelte`

- [ ] Pasar onThinking al streamRequest, renderizar ThinkingSteps sobre cada mensaje agente
- [ ] Commit
