"""Audio cleanup - splits, normalizes, and trims audio clips for LoRA training."""

import argparse
import logging
import math
from pathlib import Path

import torch
import torchaudio

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

_SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg"}


def load_audio(path: Path, target_sr: int) -> tuple[torch.Tensor, int]:
    """Load an audio file, convert to mono, and resample to the target rate."""
    waveform, sample_rate = torchaudio.load(str(path))

    # Mix to mono if stereo
    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)

    # Resample if needed
    if sample_rate != target_sr:
        resampler = torchaudio.transforms.Resample(sample_rate, target_sr)
        waveform = resampler(waveform)

    return waveform, target_sr


def normalize_loudness(audio: torch.Tensor, target_db: float) -> torch.Tensor:
    """Normalize audio loudness to a target dBFS using RMS, then clamp to [-1, 1]."""
    rms = audio.pow(2).mean().sqrt()
    if rms < 1e-8:
        return audio

    current_db = 20 * math.log10(rms.item())
    gain_db = target_db - current_db
    gain = 10 ** (gain_db / 20)

    return (audio * gain).clamp(-1.0, 1.0)


def trim_silence(audio: torch.Tensor, sample_rate: int, threshold_db: float) -> torch.Tensor:
    """Remove leading and trailing silence based on energy threshold."""
    threshold_linear = 10 ** (threshold_db / 20)
    abs_audio = audio.abs().squeeze(0)

    # Find first sample above threshold
    above = abs_audio > threshold_linear
    if not above.any():
        return audio

    indices = torch.nonzero(above, as_tuple=True)[0]
    start = indices[0].item()
    end = indices[-1].item() + 1

    return audio[:, start:end]


def _compute_energy(audio: torch.Tensor, sample_rate: int, window_ms: int = 50) -> torch.Tensor:
    """Compute short-time energy in sliding windows."""

    window_size = int(sample_rate * window_ms / 1000)
    if window_size < 1:
        window_size = 1

    flat = audio.squeeze(0)
    n_windows = len(flat) // window_size
    if n_windows == 0:
        return torch.tensor([flat.pow(2).mean()])

    trimmed = flat[: n_windows * window_size]
    frames = trimmed.reshape(n_windows, window_size)
    return frames.pow(2).mean(dim=1)


def split_on_silence(
    audio: torch.Tensor,
    sample_rate: int,
    silence_threshold_db: float,
    silence_min_len_ms: int,
    min_duration: float,
    max_duration: float,
) -> list[torch.Tensor]:
    """Split audio at silence boundaries, respecting min/max duration constraints."""
    total_duration = audio.shape[1] / sample_rate

    # If short enough already, return as-is (if above minimum)
    if total_duration <= max_duration:
        if total_duration >= min_duration:
            return [audio]
        return []

    # Compute energy in 50ms windows
    window_ms = 50
    window_size = int(sample_rate * window_ms / 1000)
    energy = _compute_energy(audio, sample_rate, window_ms)
    threshold_linear = (10 ** (silence_threshold_db / 20)) ** 2  # energy = amplitude^2

    # Find silence regions (consecutive low-energy windows)
    min_silence_windows = silence_min_len_ms // window_ms
    is_silent = energy < threshold_linear

    # Find split points at silence boundaries
    split_points: list[int] = []  # sample indices
    silence_start: int | None = None

    for i in range(len(is_silent)):
        if is_silent[i]:
            if silence_start is None:
                silence_start = i
        else:
            if silence_start is not None:
                silence_len = i - silence_start

                if silence_len >= min_silence_windows:
                    # Split at the middle of the silence region
                    mid_window = silence_start + silence_len // 2
                    split_points.append(mid_window * window_size)

                silence_start = None

    # Create clips from split points
    clips: list[torch.Tensor] = []
    boundaries = [0] + split_points + [audio.shape[1]]

    for start, end in zip(boundaries[:-1], boundaries[1:], strict=True):
        clip = audio[:, start:end]
        duration = clip.shape[1] / sample_rate

        if duration < min_duration:
            continue

        # If a segment is still too long, subdivide it evenly
        if duration > max_duration:
            n_sub = math.ceil(duration / max_duration)
            sub_len = clip.shape[1] // n_sub

            for j in range(n_sub):
                sub_start = j * sub_len
                sub_end = clip.shape[1] if j == n_sub - 1 else (j + 1) * sub_len
                sub_clip = clip[:, sub_start:sub_end]
                sub_duration = sub_clip.shape[1] / sample_rate

                if sub_duration >= min_duration:
                    clips.append(sub_clip)
        else:
            clips.append(clip)

    return clips


def save_clip(audio: torch.Tensor, path: Path, sample_rate: int) -> None:
    """Save audio tensor as 16-bit PCM WAV."""
    torchaudio.save(str(path), audio, sample_rate, encoding="PCM_S", bits_per_sample=16)


def main() -> None:
    """Run the audio preparation pipeline."""
    parser = argparse.ArgumentParser(description="Prepare audio clips for LoRA training")
    parser.add_argument("input_dir", type=Path, help="Directory containing raw audio files")
    parser.add_argument("output_dir", type=Path, help="Directory for cleaned output clips")
    parser.add_argument("--sample-rate", type=int, default=24000, help="Target sample rate in Hz (default: 24000)")
    parser.add_argument("--min-duration", type=float, default=3.0, help="Minimum clip duration in seconds (default: 3.0)")
    parser.add_argument("--max-duration", type=float, default=13.0, help="Maximum clip duration in seconds (default: 13.0)")
    parser.add_argument("--silence-threshold", type=float, default=-40.0, help="Silence threshold in dB (default: -40.0)")
    parser.add_argument("--silence-min-len", type=int, default=500, help="Min silence length in ms for splitting (default: 500)")
    parser.add_argument("--target-loudness", type=float, default=-20.0, help="Target loudness in dBFS (default: -20.0)")
    args = parser.parse_args()

    input_dir: Path = args.input_dir
    output_dir: Path = args.output_dir

    if not input_dir.is_dir():
        print(f"Error: input directory does not exist: {input_dir}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    # Collect audio files
    audio_files = sorted(f for f in input_dir.iterdir() if f.suffix.lower() in _SUPPORTED_EXTENSIONS)
    if not audio_files:
        print(f"No audio files found in {input_dir}")
        return

    print(f"Found {len(audio_files)} audio file(s) in {input_dir}")

    total_clips = 0
    skipped = 0
    errored = 0
    for audio_file in audio_files:
        try:
            waveform, sr = load_audio(audio_file, args.sample_rate)
            waveform = trim_silence(waveform, sr, args.silence_threshold)
            waveform = normalize_loudness(waveform, args.target_loudness)
            clips = split_on_silence(
                audio=waveform,
                sample_rate=sr,
                silence_threshold_db=args.silence_threshold,
                silence_min_len_ms=args.silence_min_len,
                min_duration=args.min_duration,
                max_duration=args.max_duration,
            )

            if not clips:
                logger.info("Skipped %s (no valid clips after processing)", audio_file.name)
                skipped += 1
                continue

            for i, clip in enumerate(clips):
                out_path = output_dir / f"{audio_file.stem}_{i:03d}.wav"
                save_clip(clip, out_path, sr)

            total_clips += len(clips)
            logger.info("Processed %s -> %d clip(s)", audio_file.name, len(clips))

        except Exception:
            logger.exception("Error processing %s", audio_file.name)
            errored += 1

    print(f"\nDone: {total_clips} clip(s) from {len(audio_files)} file(s)")

    if skipped:
        print(f"  Skipped: {skipped}")
    if errored:
        print(f"  Errors: {errored}")


if __name__ == "__main__":
    main()
