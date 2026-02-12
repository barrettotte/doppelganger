# LoRA Fine-Tuning Guide

End-to-end workflow for fine-tuning Orpheus TTS voices with LoRA adapters.

## Prerequisites

- NVIDIA GPU with 18+ GB VRAM (RTX 3090 Ti or better)
- CUDA toolkit installed
- Hugging Face account with Orpheus model access
- 5-60 minutes of clean reference audio per character

```sh
# Accept the Orpheus model agreement - https://huggingface.co/canopylabs/orpheus-tts-0.1-pretrained

# Log in to Hugging Face CLI
uv run huggingface-cli login
```

## End-to-End Workflow

### Source Audio

Get clean speech audio for the target character.

```sh
export CHARACTER=my_character

# download from YouTube
yt-dlp -x --audio-format wav --no-playlist \
  -o "raw_audio/$CHARACTER/%(title)s.%(ext)s" "<youtube_url>"

# or place existing WAV/MP3/FLAC/OGG files in raw_audio/$CHARACTER/
```

Tips:
- Prefer studio-quality recordings or isolated dialogue over noisy game/movie rips
- Background music and sound effects degrade voice cloning quality
- Consistent microphone and recording conditions across clips help the model converge
- Mono audio at 22-48kHz is ideal; stereo is auto-converted

### Prepare Audio Clips

Split raw audio into 3-13 second training clips with normalized volume.

```sh
make prepare-audio ARGS="raw_audio/$CHARACTER/ prepared/$CHARACTER/"
```

**CLI arguments:**

| Flag | Default | Description |
|---|---|---|
| `--sample-rate` | 24000 | Target sample rate in Hz |
| `--min-duration` | 3.0 | Minimum clip duration (seconds) |
| `--max-duration` | 13.0 | Maximum clip duration (seconds) |
| `--silence-threshold` | -40.0 | Silence detection threshold (dB) |
| `--silence-min-len` | 500 | Minimum silence length for splitting (ms) |
| `--target-loudness` | -20.0 | Target RMS loudness (dBFS) |

The script trims silence, normalizes loudness, and splits on natural pauses.
Output is 16-bit PCM WAV files named `{stem}_{index:03d}.wav`.

Tips:
- Shoot for 20-100+ clips for meaningful training
- Clips under 3 seconds are too short for the model to learn from
- Clips over 13 seconds might exceed sequence length limit
- If silence splitting produces bad cuts, try adjusting `--silence-threshold` and `--silence-min-len`

### Transcribe Clips

Generate a transcript CSV using OpenAI Whisper.

```sh
make transcribe ARGS="prepared/$CHARACTER/ --model large"
```

**CLI arguments:**

| Flag | Default | Description |
|---|---|---|
| `--output` | `{input_dir}/transcript.csv` | Output CSV path |
| `--model` | medium | Whisper model size (tiny/base/small/medium/large) |
| `--language` | en | Language code |
| `--device` | cuda | Torch device |

**Output format** (`transcript.csv`):
```csv
filename,text
clip_000,this is what was spoken in the first clip
clip_001,another sentence from the second clip
```

Tips:
- Use `large` model for best accuracy (slower but fewer errors)
- Review CSV and fix obvious transcription errors - bad transcripts teach the model wrong associations
- Empty transcriptions are automatically skipped

### Train LoRA Adapter

Fine-tune Orpheus with the prepared dataset.

```sh
# if you have multiple GPUs, make sure it uses the right one
export CUDA_VISIBLE_DEVICES=0

make train-lora ARGS="$CHARACTER prepared/$CHARACTER/ --device cuda --epochs 1"
```

**CLI arguments:**

| Flag | Default | Description |
|---|---|---|
| `--transcript` | `{dataset_dir}/transcript.csv` | Transcript CSV path |
| `--voices-dir` | voices | Root voices directory for output |
| `--base-model` | canopylabs/orpheus-tts-0.1-pretrained | HuggingFace model ID |
| `--epochs` | 1 | Training epochs |
| `--batch-size` | 1 | Per-device batch size |
| `--learning-rate` | 5e-5 | Learning rate |
| `--lora-rank` | 32 | LoRA rank (adapter capacity) |
| `--lora-alpha` | 64 | LoRA alpha (scaling factor) |
| `--max-seq-len` | 2048 | Maximum sequence length |
| `--save-steps` | 500 | Checkpoint interval |
| `--device` | cuda | Training device |
| `--snac-device` | cpu | SNAC encoder device |
| `--no-cache` | false | Skip SNAC encoding cache |

**Output:** Adapter files are saved to `voices/{CHARACTER}/` and automatically detected by voice registry on next server restart.

### Inference

After training, the adapter is ready to use.
The voice registry detects `adapter_config.json` in the voice directory and routes requests through the Orpheus engine.

Orpheus requires a running vLLM server with the LoRA adapter loaded:

```sh
# Start vLLM with LoRA support
make vllm

# Restart the API to pick up the new voice
make dev
```

## Hyperparameter Tuning

### Dataset Size vs Quality

| Dataset Size | Expected Quality | Notes |
|---|---|---|
| 5-10 clips (~1 min) | Poor | Model barely adapts, often sounds like base model |
| 20-50 clips (~5 min) | Moderate | Recognizable voice characteristics, some artifacts |
| 50-100 clips (~15 min) | Good | Clear voice identity, natural prosody |
| 100-200 clips (~30 min) | Very good | Consistent quality, handles varied text well |
| 200+ clips (~60 min) | Diminishing returns | More data helps but gains taper off |

### Epochs

| Epochs | Use Case |
|---|---|
| 1 | Large datasets (100+ clips), quick iteration |
| 2-3 | Medium datasets (30-100 clips), balanced quality |
| 5+ | Small datasets (< 30 clips), risk of overfitting |

More epochs on small datasets can cause overfitting - the model memorizes training phrases instead of learning the voice.
Signs of overfitting: generated audio sounds like it's repeating training clips verbatim, or quality degrades on novel text.

### LoRA Rank

| Rank | Parameters | Use Case |
|---|---|---|
| 8 | ~2M | Minimal adaptation, fast training |
| 16 | ~4M | Subtle voice characteristics |
| 32 (default) | ~8M | Good balance of quality and efficiency |
| 64 | ~16M | Maximum expressiveness, more VRAM |

Higher rank gives the adapter more capacity to capture voice characteristics but increases VRAM usage and training time.
For most voices, rank 32 is sufficient.

### Learning Rate

| Rate | Use Case |
|---|---|
| 1e-5 | Conservative, less likely to diverge |
| 5e-5 (default) | Good starting point |
| 1e-4 | Faster convergence, risk of instability |

If training loss oscillates wildly, reduce the learning rate.
If loss plateaus early, try increasing it.
