# Stage 1: Build frontend
FROM node:22-slim AS frontend

RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /frontend
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY frontend/ ./
RUN pnpm build

# Stage 2: Python application
FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen --extra tts

COPY alembic.ini ./
COPY alembic/ alembic/
COPY src/ src/
COPY voices/ voices/

# Copy frontend build output
COPY --from=frontend /frontend/dist frontend/dist/

# Run migrations then start the server
CMD uv run alembic upgrade head && \
    uv run uvicorn --factory doppelganger.app:create_app --host 0.0.0.0 --port 8000
