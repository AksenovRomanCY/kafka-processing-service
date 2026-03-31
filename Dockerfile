FROM python:3.13.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends adduser \
 && rm -rf /var/lib/apt/lists/*

RUN adduser --uid 1000 --disabled-password --gecos "" appuser

WORKDIR /app

COPY --chown=appuser:appuser requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser . .

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import os; os.getpid()"]

USER appuser
