# Multi-Agent Architecture + Thinking Steps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

Estado actual: este plan ya fue implementado en el código. Se conserva como referencia histórica del trabajo hecho.

**Goal:** Agregar 3 sub-agentes especializados (inflación, cuotas, diagnóstico) al agente raíz existente, con thinking steps visibles en la UI durante la delegación.

**Architecture:** Root agent (ExpenseBot) maneja queries simples directamente y delega análisis complejos a AgenteDiagnostico via AgentTool. AgenteDiagnostico orquesta AgenteInflacion y AgenteCuotas. Backend emite SSE `"thinking"` events cuando detecta function calls a sub-agentes. Frontend renderiza TraceStep[] sobre la respuesta.

**Tech Stack:** Google ADK 2.1.0, Python/httpx, datos.gob.ar IPC API, SvelteKit 5, TypeScript

---

### Task 1: IPC Tool

**Files:**
- Create: `expense_agent/tools_ipc.py`

- [x] Crear tool que fetchea índice IPC de datos.gob.ar y calcula coeficiente de ajuste
- [x] Verificar manualmente con curl que la API responde
- [x] Commit

---

### Task 2: AgenteInflacion

**Files:**
- Create: `expense_agent/subagents/__init__.py`
- Create: `expense_agent/subagents/agente_inflacion.py`

- [x] Crear sub-agente con tools_ipc + MCPToolset
- [x] Commit

---

### Task 3: AgenteCuotas

**Files:**
- Create: `expense_agent/subagents/agente_cuotas.py`

- [x] Crear sub-agente de cuotas con MCPToolset
- [x] Commit

---

### Task 4: AgenteDiagnostico

**Files:**
- Create: `expense_agent/subagents/agente_diagnostico.py`

- [x] Crear sub-agente que orquesta inflacion + cuotas via AgentTool
- [x] Commit

---

### Task 5: Actualizar root agent

**Files:**
- Modify: `expense_agent/agent.py`

- [x] Agregar AgentTool(agente_diagnostico) al tools list
- [x] Actualizar prompt del orquestador con instrucciones de delegación
- [x] Commit

---

### Task 6: Thinking events en backend

**Files:**
- Modify: `routes/agent.py`

- [x] En `_stream_agent`: detectar function calls/responses a sub-agentes y emitir SSE "thinking"
- [x] Commit

---

### Task 7: Frontend — stores + tipos

**Files:**
- Modify: `frontend/src/lib/stores/expenses.ts`

- [x] Agregar tipo TraceStep, actualizar Message para incluir traces[]
- [x] Commit

---

### Task 8: ThinkingSteps component

**Files:**
- Create: `frontend/src/lib/components/ThinkingSteps.svelte`

- [x] Componente que renderiza trace steps con animación running/done/error
- [x] Commit

---

### Task 9: API client — thinking handler

**Files:**
- Modify: `frontend/src/lib/api/client.ts`

- [x] Agregar onThinking handler a StreamHandlers, procesar evento SSE "thinking"
- [x] Commit

---

### Task 10: Chat page — integración

**Files:**
- Modify: `frontend/src/routes/+page.svelte`

- [x] Pasar onThinking al streamRequest, renderizar ThinkingSteps sobre cada mensaje agente
- [x] Commit
