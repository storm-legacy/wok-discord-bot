# syntax=docker/dockerfile:1
FROM python:3.12-slim AS builder

RUN pip install uv

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev --no-install-project


FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        libopus0 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -r -u 1001 -s /sbin/nologin botuser

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv

COPY main.py ./

RUN mkdir -p sounds && chown -R botuser:botuser /app

USER botuser

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SOUNDS_DIR=/app/sounds

ENTRYPOINT ["python", "main.py"]
