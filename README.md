# Doppelganger

TTS voice cloning Discord bot.

Two TTS engines are supported:
- **Chatterbox TTS** - zero-shot voice cloning from a short reference audio clip, no fine-tuning needed
- **Orpheus TTS** - LoRA fine-tuned voices via vLLM for higher quality on specific characters

## Quick Start

```sh
# Install dependencies (requires CUDA GPU)
uv sync

# Start Postgres
make docker-db

# Run database migrations
make migrate

# Copy and configure environment
cp .env.example .env

# Build dashboard
make frontend

# Start dev server at http://localhost:8000
make dev
```

## Dependencies

- Python 3.12+ and uv
- Docker and Docker Compose
- NVIDIA GPU with CUDA (8-16 GB VRAM for inference)
- FFmpeg (for Discord voice audio)
- Node.js + pnpm (for frontend build)

## Discord Bot

The bot runs inside the FastAPI process. 
Starting the API starts the bot. 
See [docs/bot-setup.md](docs/bot-setup.md) for Discord Developer Portal setup.

| Command | Description |
|---|---|
| `/say <character> <text>` | Generate TTS and play it in a voice channel |
| `/voices` | List available character voices |

## Dashboard

The Svelte dashboard is served at `http://localhost:8000`:

- **Dashboard** - request metrics, recent activity
- **Queue** - view, cancel, and bump TTS requests
- **Cache** - manage audio cache entries, playback, download
- **Characters** - register, delete, and tune character voices
- **Users** - view users, blacklist/unblacklist
- **Config** - read-only view of current settings
- **Metrics** - per-character and per-user request breakdowns
- **System** - GPU stats, engine status, cache hit rate, uptime

## Voice Cloning

### Chatterbox (Zero-Shot)

Register a character with a 5-30 second WAV reference clip.
Around 10 seconds of clean mono speech at 22050 Hz works best.

```sh
# Upload via API
curl -X POST "http://localhost:8000/api/characters?name=my-character" \
  -F "audio=@/path/to/reference.wav"

# Or place manually and restart
# voices/my-character/reference.wav
```

### Orpheus (Fine-Tuned)

Train a LoRA adapter from multiple audio clips for higher quality.
See [docs/lora-tuning.md](docs/lora-tuning.md) for the full guide.

```sh
export CUDA_VISIBLE_DEVICES=0
export CHARACTER=my_character

# Prepare audio clips (3-13s each, normalized)
make prepare-audio ARGS="raw_audio/$CHARACTER/ prepared/$CHARACTER/"

# Transcribe with Whisper
make transcribe ARGS="prepared/$CHARACTER/ --model large"

# Train LoRA adapter
make train-lora ARGS="$CHARACTER prepared/$CHARACTER/ --device cuda --epochs 1"
```

The voice registry auto-detects adapter files (`adapter_config.json`) and routes to the Orpheus engine.

## API

OpenAPI docs at [http://localhost:8000/docs](http://localhost:8000/docs).

### Health and Status

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | DB, TTS model, and GPU status |
| `GET` | `/api/status` | Bot connection, guilds, config |
| `GET` | `/api/metrics` | Request counts, top users, queue depth |
| `GET` | `/api/system/stats` | GPU VRAM, engine status, cache stats, uptime |

### TTS

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/tts/generate` | Generate speech as WAV (cached) |
| `POST` | `/api/tts/stream` | Stream speech in chunks |

### Characters

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/characters` | List all characters |
| `POST` | `/api/characters` | Create character (name + audio upload) |
| `PUT` | `/api/characters/{id}/tuning` | Update per-character TTS parameters |
| `DELETE` | `/api/characters/{id}` | Delete character and reference audio |

### Queue

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/queue` | Current queue state |
| `POST` | `/api/queue/{id}/cancel` | Cancel a pending request |
| `POST` | `/api/queue/{id}/bump` | Move request to front |

### Requests

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/requests` | List requests (filterable, paginated) |
| `GET` | `/api/requests/{id}` | Get single request |

### Users

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/users` | List all users |
| `POST` | `/api/users/{id}/blacklist` | Toggle blacklist |
| `GET` | `/api/users/{id}/requests` | User's request history |

### Cache

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/cache` | Cache state with all entries |
| `POST` | `/api/cache/toggle` | Enable/disable cache |
| `POST` | `/api/cache/flush` | Clear all entries |
| `DELETE` | `/api/cache/{key}` | Delete single entry |
| `GET` | `/api/cache/{key}/download` | Download cached WAV |

### Other

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/audit` | Audit log (filterable) |
| `GET` | `/api/config` | Current settings (secrets redacted) |

## Configuration

### Application

| Variable | Default | Description |
|---|---|---|
| `DOPPELGANGER_DEBUG` | false | Enable debug logging |
| `DOPPELGANGER_HOST` | 0.0.0.0 | Server bind host |
| `DOPPELGANGER_PORT` | 8000 | Server bind port |
| `DOPPELGANGER_ALLOWED_ORIGINS` | ["*"] | CORS allowed origins |
| `DOPPELGANGER_VOICES_DIR` | voices | Character voice files directory |
| `DOPPELGANGER_CACHE_MAX_SIZE` | 100 | Max audio cache entries |

### Database

| Variable | Default | Description |
|---|---|---|
| `DOPPELGANGER_DATABASE__HOST` | localhost | PostgreSQL host |
| `DOPPELGANGER_DATABASE__PORT` | 5432 | PostgreSQL port |
| `DOPPELGANGER_DATABASE__USER` | doppelganger | Database user |
| `DOPPELGANGER_DATABASE__PASSWORD` | doppelganger | Database password |
| `DOPPELGANGER_DATABASE__NAME` | doppelganger | Database name |
| `DOPPELGANGER_DATABASE__POOL_SIZE` | 5 | Connection pool size |
| `DOPPELGANGER_DATABASE__POOL_MAX_OVERFLOW` | 10 | Max pool overflow |

### Chatterbox TTS

| Variable | Default | Description |
|---|---|---|
| `DOPPELGANGER_CHATTERBOX__DEVICE` | cuda | Torch device |
| `DOPPELGANGER_CHATTERBOX__EXAGGERATION` | 0.3 | Vocal expressiveness (0.0-1.0) |
| `DOPPELGANGER_CHATTERBOX__CFG_WEIGHT` | 3.0 | Classifier-free guidance strength |
| `DOPPELGANGER_CHATTERBOX__TEMPERATURE` | 0.75 | Sampling temperature |
| `DOPPELGANGER_CHATTERBOX__CHUNK_SIZE` | 50 | Tokens per streaming chunk |

### Orpheus TTS

| Variable | Default | Description |
|---|---|---|
| `DOPPELGANGER_ORPHEUS__ENABLED` | true | Enable Orpheus engine |
| `DOPPELGANGER_ORPHEUS__VLLM_BASE_URL` | http://localhost:8001/v1 | vLLM API endpoint |
| `DOPPELGANGER_ORPHEUS__TEMPERATURE` | 0.6 | Generation temperature |
| `DOPPELGANGER_ORPHEUS__TOP_P` | 0.95 | Nucleus sampling threshold |
| `DOPPELGANGER_ORPHEUS__REPETITION_PENALTY` | 1.1 | Repetition penalty |
| `DOPPELGANGER_ORPHEUS__FREQUENCY_PENALTY` | 0.0 | Frequency penalty |
| `HUGGING_FACE_HUB_TOKEN` | - | HF token for model access |

### Discord

| Variable | Default | Description |
|---|---|---|
| `DOPPELGANGER_DISCORD__TOKEN` | - | Bot token (required for bot) |
| `DOPPELGANGER_DISCORD__GUILD_ID` | - | Guild ID for slash commands |
| `DOPPELGANGER_DISCORD__REQUIRED_ROLE_ID` | - | Optional required role |
| `DOPPELGANGER_DISCORD__COOLDOWN_SECONDS` | 5 | Cooldown between plays |
| `DOPPELGANGER_DISCORD__ENTRANCE_SOUND` | - | Optional WAV on channel join |
| `DOPPELGANGER_DISCORD__MAX_TEXT_LENGTH` | 255 | Max chars per request |
| `DOPPELGANGER_DISCORD__MAX_QUEUE_DEPTH` | 20 | Max pending requests |
| `DOPPELGANGER_DISCORD__REQUESTS_PER_MINUTE` | 3 | Per-user rate limit |

## Development

```sh
make test             # All tests (unit + integration)
make test-unit        # Unit tests only (no Docker)
make test-integration # Integration tests (needs Docker)
make check            # Format + lint + type-check
make fmt              # Format with ruff
make lint             # Lint with ruff
```

## Docker

```sh
make docker-db        # PostgreSQL only
make docker-up        # API + PostgreSQL
make docker-down      # Stop all containers
make vllm             # Start vLLM for Orpheus
make psql             # Connect to database
```

## References

- repos
  - https://github.com/canopyai/Orpheus-TTS
  - https://github.com/resemble-ai/chatterbox
  - https://github.com/openai/whisper
  - https://github.com/hubertsiuzdak/snac
  - https://github.com/ytdl-org/youtube-dl
  - https://github.com/pyannote/pyannote-audio
- tested/unused repos
  - https://github.com/RVC-Boss/GPT-SoVITS
  - https://huggingface.co/coqui/XTTS-v2
  - https://huggingface.co/SWivid/F5-TTS
  - https://github.com/idiap/coqui-ai-TTS (maintained version)
