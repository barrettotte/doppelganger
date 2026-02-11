"""Audio transcription - uses Whisper to generate transcript CSV for LoRA training."""

import argparse
import csv
import logging
from pathlib import Path

import whisper

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def transcribe_clips(
    input_dir: Path,
    output_path: Path,
    model_name: str,
    language: str,
    device: str,
) -> None:
    """Transcribe all WAV clips in a directory and write a transcript CSV."""
    wav_files = sorted(input_dir.glob("*.wav"))
    if not wav_files:
        print(f"No WAV files found in {input_dir}")
        return

    print(f"Found {len(wav_files)} WAV file(s) in {input_dir}")
    print(f"Loading Whisper model '{model_name}' on {device}...")
    model = whisper.load_model(model_name, device=device)

    results: list[tuple[str, str]] = []
    errors = 0
    for wav_path in wav_files:
        try:
            result = model.transcribe(str(wav_path), language=language)
            text = result["text"].strip()

            if not text:
                logger.warning("Empty transcription for %s, skipping", wav_path.name)
                continue

            results.append((wav_path.stem, text))
            logger.info("%s: %s", wav_path.stem, text)

        except Exception:
            logger.exception("Failed to transcribe %s", wav_path.name)
            errors += 1

    # Write transcript CSV
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "text"])
        for stem, text in results:
            writer.writerow([stem, text])

    print(f"\nDone: {len(results)} transcription(s) written to {output_path}")
    if errors:
        print(f"  Errors: {errors}")


def main() -> None:
    """Parse CLI arguments and run transcription."""
    parser = argparse.ArgumentParser(description="Transcribe WAV clips using Whisper for LoRA training")
    parser.add_argument("input_dir", type=Path, help="Directory of WAV clips (output of prepare_audio)")
    parser.add_argument("--output", type=Path, default=None, help="Output CSV path (default: input_dir/transcript.csv)")
    parser.add_argument("--model", default="medium", choices=["tiny", "base", "small", "medium", "large"], help="Whisper model size (default: medium)")
    parser.add_argument("--language", default="en", help="Language code (default: en)")
    parser.add_argument("--device", default="cuda", help="Device for Whisper (default: cuda)")
    args = parser.parse_args()

    input_dir: Path = args.input_dir
    if not input_dir.is_dir():
        print(f"Error: input directory does not exist: {input_dir}")
        return

    output_path: Path = args.output if args.output else input_dir / "transcript.csv"
    transcribe_clips(input_dir, output_path, args.model, args.language, args.device)


if __name__ == "__main__":
    main()
