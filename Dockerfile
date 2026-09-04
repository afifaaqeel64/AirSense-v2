# AirSense Pakistan Production Deployment Dockerfile
FROM python:3.12-slim as builder

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Final Runtime Stage
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user & required volume directories
RUN groupadd -g 1000 airsense && \
    useradd -u 1000 -g airsense -m -s /bin/bash airsense && \
    mkdir -p /app/data/models /app/data/imports /app/data/exports /app/data/backups && \
    chown -R airsense:airsense /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY --chown=airsense:airsense . /app

USER airsense

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/liveness || exit 1

CMD ["python", "-m", "uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
