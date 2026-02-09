# Doppelganger

TTS voice cloning Discord bot.

Uses [Chatterbox TTS](https://github.com/resemble-ai/chatterbox). 

## Quick Start

```sh
# Install base dependencies
uv sync

# Install with TTS engine (requires CUDA GPU)
uv sync --extra tts

# Start PostgreSQL
make docker-db

# Run database migrations
make migrate

# Start dev server at http://localhost:8000
make dev
```

## Dependencies

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Docker and Docker Compose
- NVIDIA GPU + CUDA with 8-16GB VRAM for inference

## Voice Cloning

To register a character voice, provide a 5-30 second WAV reference clip of clean speech (16-48kHz, minimal background noise).
Around 10 seconds mono 22050 Hz works best.


```sh
# create a new character
curl -X POST "http://localhost:8000/api/characters?name=my-character" \
  -F "audio=@/path/to/reference.wav"

# Manually place file at voices/my-character/reference.wav and restart the server

# generate TTS
curl -X POST "http://localhost:8000/api/tts/generate" \
  -H "Content-Type: application/json" \
  -d '{"character_voice": "my-character", "text": "Hello world"}' \
  --output output.wav
```

## Configuration

| Variable | Default | Description |
|---|---|---|
| `DOPPELGANGER_TTS__DEVICE` | `cuda` | Torch device (`cuda`, `cpu`) |
| `DOPPELGANGER_TTS__VOICES_DIR` | `voices` | Directory for character reference audio |
| `DOPPELGANGER_TTS__EXAGGERATION` | `0.5` | Vocal expressiveness (0.0-1.0) |
| `DOPPELGANGER_TTS__CFG_WEIGHT` | `0.5` | Voice cloning fidelity |
| `DOPPELGANGER_TTS__CACHE_MAX_SIZE` | `100` | Max entries in audio LRU cache |
| `DOPPELGANGER_DATABASE__HOST` | `localhost` | PostgreSQL host |
| `DOPPELGANGER_DATABASE__PORT` | `5432` | PostgreSQL port |

See `.env.example` for the full list.

## Development

```sh
# Run all tests (unit + integration)
make test

# Run only unit tests (no Docker needed)
make test-unit

# Run only integration tests (needs Docker for testcontainers)
make test-integration

# Format, lint, and type-check
make check

# Format code
make fmt

# Lint
make lint

# Type-check
make type-check
```
