FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY expense_agent/ ./expense_agent/
COPY db/ ./db/
COPY routes/ ./routes/
COPY helpers/ ./helpers/
COPY models/ ./models/
COPY agent_runtime/ ./agent_runtime/
COPY main.py ./main.py

ENV PYTHONPATH=/app
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]
