FROM python:3.12-slim AS builder

ENV VENV_PATH=/opt/venv \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN python -m venv "${VENV_PATH}"
ENV PATH="${VENV_PATH}/bin:${PATH}"

COPY requirements.txt .
RUN pip install pip==25.0.1 && pip install --requirement requirements.txt


FROM python:3.12-slim AS runtime

ENV VENV_PATH=/opt/venv \
    PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd -r app && useradd -r -g app app

WORKDIR /app

COPY --from=builder "${VENV_PATH}" "${VENV_PATH}"
COPY worker.py .

RUN chown -R app:app /app

USER app

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os, redis, sys; client = redis.Redis(host=os.getenv('REDIS_HOST', 'redis'), port=int(os.getenv('REDIS_PORT', '6379')), decode_responses=True); client.ping(); sys.exit(0)"

CMD ["python", "worker.py"]
