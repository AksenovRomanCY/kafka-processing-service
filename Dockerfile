FROM python:3.14.5-slim

ENV POETRY_VERSION=2.2.1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

RUN apt-get update \
 && apt-get install -y --no-install-recommends adduser \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

RUN adduser --uid 1000 --disabled-password --gecos "" appuser

WORKDIR /app

COPY --chown=appuser:appuser pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root && rm -rf ${POETRY_CACHE_DIR}

COPY --chown=appuser:appuser . .

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["sh", "-c", "test -f /tmp/consumer-alive && find /tmp/consumer-alive -mmin -1 | grep -q ."]

USER appuser
