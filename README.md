# Doppelganger

TTS voice cloning Discord bot powered by Chatterbox TTS.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Docker and Docker Compose

## Quick Start

```bash
# Install dependencies
uv sync

# Start PostgreSQL
make docker-db

# Run database migrations
make migrate

# Start dev server at http://localhost:8000
make dev
```
