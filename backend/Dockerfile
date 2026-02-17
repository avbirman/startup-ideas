FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ .

# Create data directory for SQLite
RUN mkdir -p /data

# Environment
ENV DATABASE_PATH=/data/startup_ideas.db
ENV PYTHONPATH=/app
ENV PORT=8000

EXPOSE ${PORT}

CMD uvicorn api.main:app --host 0.0.0.0 --port ${PORT}
