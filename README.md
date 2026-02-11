# Doppelganger

TTS voice cloning Discord bot powered by [Chatterbox TTS](https://github.com/resemble-ai/chatterbox).

Users trigger `/say <character> <text>` in Discord and the bot joins a voice channel, plays the generated speech, and leaves.
Characters are registered from short reference audio clips - no fine-tuning needed.

## Quick Start

```sh
# Install dependencies (includes TTS engine, requires CUDA GPU)
uv sync

# Start PostgreSQL
make docker-db

# Run database migrations
make migrate

# Copy and configure environment
cp .env.example .env
# Edit .env with your Discord bot token and guild ID

# Start dev server at http://localhost:8000
make dev
```

## Dependencies

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Docker and Docker Compose
- NVIDIA GPU + CUDA with 8-16GB VRAM for TTS inference
- FFmpeg (for Discord voice audio playback)

## Discord Bot

The Discord bot runs inside the FastAPI process. So starting the API will start the bot.
Setup bot using instructions in [docs/bot-setup.md](docs/bot-setup.md).

| Command | Description |
|---|---|
| `!dg say <character> <text> [channel]` | Generate TTS audio and play it in a voice channel. Defaults to your current channel if not specified. |
| `!dg voices` | List all available character voices. |

All command responses are ephemeral (only visible to the requesting user).

## Voice Cloning

To register a character voice, provide a 5-30 second WAV reference clip of clean speech (16-48kHz, minimal background noise). Around 10 seconds mono 22050 Hz works best.

```sh
# Upload reference audio via API
curl -X POST "http://localhost:8000/api/characters?name=my-character" \
  -F "audio=@/path/to/reference.wav"

# Or manually place the file and restart the server
# voices/my-character/reference.wav

# Generate TTS via API
curl -X POST "http://localhost:8000/api/tts/generate" \
  -H "Content-Type: application/json" \
  -d '{"character": "my-character", "text": "Hello world"}' \
  --output output.wav
```

## API Endpoints

Interactive docs are available at [http://localhost:8000/docs](http://localhost:8000/docs) when the server is running.

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Service health check (DB connectivity, TTS model state, GPU status) |
| `GET` | `/api/characters` | List all registered character voices |
| `POST` | `/api/characters` | Create a new character from a reference audio upload |
| `DELETE` | `/api/characters/{character_id}` | Delete a character and its reference audio |
| `POST` | `/api/tts/generate` | Generate full speech audio as WAV (with caching) |
| `POST` | `/api/tts/stream` | Stream speech audio in chunks |

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

## Docker

```sh
# Start postgres only
make docker-db

# Start fullstack (API + PostgreSQL)
make docker-up

# Stop all containers
make docker-down
```

## Fine-Tuning

- Accept agreement - visit https://huggingface.co/canopylabs/orpheus-tts-0.1-pretrained and click "Agree and access repository"
- Log in
  - run `uv run huggingface-cli login`
  - It'll ask for a token - grab one from https://huggingface.co/settings/tokens (needs read scope).


```sh
export CUDA_VISIBLE_DEVICES=0
export CHARACTER=my_character

# download training audio
yt-dlp -x --audio-format wav --no-playlist -o "raw_audio/$CHARACTER/%(title)s.%(ext)s" "<youtube_url>"

# split large file to multiple 3-13s clips
make prepare-audio ARGS="raw_audio/$CHARACTER/ prepared/$CHARACTER/"

# transcribe each clip
make transcribe ARGS="prepared/$CHARACTER/ --model large"

# fine-tune the model
make train-lora ARGS="$CHARACTER prepared/$CHARACTER/ --device cuda --epochs 1"
```
