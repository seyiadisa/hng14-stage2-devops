FROM python:3.14-slim AS builder

ENV VENV_PATH=/opt/venv \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN python -m venv "${VENV_PATH}"
ENV PATH="${VENV_PATH}/bin:${PATH}"

COPY requirements.txt .
RUN pip install pip==25.0.1 && pip install --requirement requirements.txt


FROM python:3.14-slim AS runtime

ENV VENV_PATH=/opt/venv \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd -r app && useradd -r -g app app

WORKDIR /app

ENV PATH="${VENV_PATH}/bin:${PATH}"

COPY --from=builder "${VENV_PATH}" "${VENV_PATH}"
COPY main.py .

RUN chown -R app:app /app

USER app

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os, sys, urllib.request; port=os.getenv('API_PORT', '8000'); url=f'http://127.0.0.1:{port}/health';\
response=urllib.request.urlopen(url, timeout=3); sys.exit(0 if response.status == 200 else 1)"

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${API_PORT:-8000}"]
