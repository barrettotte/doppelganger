FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

COPY alembic.ini ./
COPY alembic/ alembic/
COPY src/ src/

# Run migrations then start the server
CMD uv run alembic upgrade head && \
    uv run uvicorn --factory doppelganger.app:create_app --host 0.0.0.0 --port 8000
