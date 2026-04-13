# ---------- Build Stage ----------
FROM python:3.10-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- Runtime Stage ----------
FROM python:3.10-slim

WORKDIR /app

# Nur libpq für psycopg2 zur Laufzeit nötig
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

RUN mkdir -p /app/logs && chmod 755 /app/logs

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
