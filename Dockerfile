FROM python:3.11-slim

WORKDIR /app

# Install agent-only Python deps (no FastAPI/uvicorn)
COPY agent_runtime/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent source — manually resolve symlinks (Docker can't follow relative symlinks)
COPY expense_agent/ ./expense_agent/
COPY db/ ./db/
COPY agent_runtime/agent.py ./agent_runtime/agent.py
COPY agent_runtime/__init__.py ./agent_runtime/__init__.py

# Make /app importable so `from expense_agent.agent import ...` and `from db...` work
ENV PYTHONPATH=/app
ENV PORT=8080
EXPOSE 8080

CMD ["adk", "api_server", "--host", "0.0.0.0", "--port", "8080", "agent_runtime/"]
