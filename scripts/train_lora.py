"""Orpheus LoRA training - encodes audio with SNAC, then fine-tunes via PEFT."""

import argparse
import csv
import json
import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import torch
from datasets import Dataset
from peft import LoraConfig, TaskType, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments

from doppelganger.tts.snac_encoder import SNACEncoder

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Special token IDs from the Orpheus tokenizer.
_START_OF_HUMAN = 128259
_END_OF_HUMAN = 128260
_START_OF_AI = 128261
_END_OF_AI = 128262
_PAD_TOKEN = 128263


@dataclass
class TrainingSample:
    """A single training example with text and encoded audio tokens."""

    filename: str
    text: str
    audio_tokens: list[int] = field(default_factory=list)


def load_transcript(csv_path: Path) -> dict[str, str]:
    """Read a CSV file mapping filename (without extension) to transcript text."""
    transcript: dict[str, str] = {}

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            filename = row["filename"].strip()
            text = row["text"].strip()

            if filename and text:
                transcript[filename] = text

    return transcript


def load_snac_cache(cache_path: Path) -> dict[str, list[int]]:
    """Load cached SNAC token encodings from a JSON file."""
    if not cache_path.is_file():
        return {}

    with open(cache_path, encoding="utf-8") as f:
        data: dict[str, list[int]] = json.load(f)

    return data


def save_snac_cache(cache_path: Path, cache: dict[str, list[int]]) -> None:
    """Write SNAC token encodings to a JSON cache file."""
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache, f)


def encode_dataset(
    dataset_dir: Path,
    transcript: dict[str, str],
    encoder: SNACEncoder,
    use_cache: bool = True,
) -> list[TrainingSample]:
    """Encode each WAV clip in the dataset directory using SNAC, with optional disk cache."""

    samples: list[TrainingSample] = []
    wav_files = sorted(dataset_dir.glob("*.wav"))

    if not wav_files:
        print(f"No WAV files found in {dataset_dir}")
        return samples

    cache_path = dataset_dir / "snac_cache.json"
    cache: dict[str, list[int]] = {}
    if use_cache:
        cache = load_snac_cache(cache_path)

    cached_count = 0
    encoded_count = 0

    for wav_path in wav_files:
        stem = wav_path.stem

        if stem not in transcript:
            logger.warning("No transcript for %s, skipping", wav_path.name)
            continue

        if stem in cache:
            sample = TrainingSample(filename=stem, text=transcript[stem], audio_tokens=cache[stem])
            samples.append(sample)
            cached_count += 1
            continue

        try:
            audio_tokens = encoder.encode(str(wav_path))
            cache[stem] = audio_tokens
            sample = TrainingSample(filename=stem, text=transcript[stem], audio_tokens=audio_tokens)
            samples.append(sample)
            encoded_count += 1
            logger.info("Encoded %s: %d tokens", wav_path.name, len(audio_tokens))

        except Exception:
            logger.exception("Failed to encode %s", wav_path.name)

    if use_cache and encoded_count > 0:
        save_snac_cache(cache_path, cache)
        logger.info("Saved SNAC cache to %s", cache_path)

    if cached_count > 0:
        print(f"  {cached_count} clip(s) loaded from cache")
    if encoded_count > 0:
        print(f"  {encoded_count} clip(s) freshly encoded")

    return samples


def build_training_sequence(sample: TrainingSample, tokenizer: Any) -> dict[str, list[int]]:
    """Build input_ids and labels for a single training sample.

    Format: [START_OF_HUMAN] + text_tokens + [END_OF_HUMAN, START_OF_AI] + audio_tokens + [END_OF_AI]
    Labels mask the prompt portion with -100 so the model only learns audio generation.
    """
    text_tokens: list[int] = tokenizer.encode(sample.text, add_special_tokens=False)
    prompt = [_START_OF_HUMAN] + text_tokens + [_END_OF_HUMAN, _START_OF_AI]
    target = sample.audio_tokens + [_END_OF_AI]

    input_ids = prompt + target
    labels = [-100] * len(prompt) + target

    return {"input_ids": input_ids, "labels": labels}


def create_dataset(samples: list[TrainingSample], tokenizer: Any, max_seq_len: int) -> Dataset:
    """Build a HuggingFace Dataset from training samples."""
    all_input_ids: list[list[int]] = []
    all_labels: list[list[int]] = []
    all_attention_mask: list[list[int]] = []

    for sample in samples:
        seq = build_training_sequence(sample, tokenizer)
        input_ids = seq["input_ids"][:max_seq_len]
        labels = seq["labels"][:max_seq_len]

        # Pad to max_seq_len
        pad_len = max_seq_len - len(input_ids)
        attention_mask = [1] * len(input_ids) + [0] * pad_len
        input_ids = input_ids + [_PAD_TOKEN] * pad_len
        labels = labels + [-100] * pad_len

        all_input_ids.append(input_ids)
        all_labels.append(labels)
        all_attention_mask.append(attention_mask)

    return Dataset.from_dict(
        {
            "input_ids": all_input_ids,
            "labels": all_labels,
            "attention_mask": all_attention_mask,
        }
    )


def train(args: argparse.Namespace) -> None:
    """Run the full LoRA training pipeline."""
    dataset_dir = Path(args.dataset_dir)
    voices_dir = Path(args.voices_dir)
    output_dir = voices_dir / args.character

    # Load transcript
    transcript_path = Path(args.transcript) if args.transcript else dataset_dir / "transcript.csv"
    if not transcript_path.is_file():
        print(f"Error: transcript not found: {transcript_path}")
        return

    transcript = load_transcript(transcript_path)
    print(f"Loaded {len(transcript)} transcript entries from {transcript_path}")

    # Encode audio with SNAC (skips cached clips)
    use_cache = not args.no_cache
    cache_path = dataset_dir / "snac_cache.json"
    all_cached = False

    if use_cache:
        cache = load_snac_cache(cache_path)
        stems_needed = {p.stem for p in dataset_dir.glob("*.wav")} & set(transcript.keys())
        all_cached = len(stems_needed) > 0 and stems_needed <= set(cache.keys())

    if all_cached:
        print("All clips found in SNAC cache, skipping encoder load")
        encoder = SNACEncoder(device="cpu")
    else:
        print("Encoding audio clips with SNAC...")
        encoder = SNACEncoder(device=args.snac_device)
        encoder.load()

    samples = encode_dataset(dataset_dir, transcript, encoder, use_cache=use_cache)
    if not samples:
        print("No samples encoded, aborting")
        return

    print(f"Encoded {len(samples)} sample(s)")

    # Free SNAC VRAM before loading the training model
    if encoder.is_loaded:
        encoder.unload()
    del encoder

    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # Load base model and tokenizer
    print(f"Loading base model: {args.base_model}")
    tokenizer = AutoTokenizer.from_pretrained(args.base_model)
    model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        torch_dtype=torch.bfloat16,
        attn_implementation="sdpa",
    )

    # Apply LoRA
    lora_config = LoraConfig(
        r=args.lora_rank,
        lora_alpha=args.lora_alpha,
        lora_dropout=0.0,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "down_proj", "up_proj"],
        task_type=TaskType.CAUSAL_LM,
    )
    model = get_peft_model(model, lora_config)
    model.enable_input_require_grads()
    model.gradient_checkpointing_enable()
    model.print_trainable_parameters()

    # Build dataset
    print("Building training dataset...")
    dataset = create_dataset(samples, tokenizer, args.max_seq_len)
    print(f"Dataset size: {len(dataset)} sample(s)")

    # Configure and run Trainer
    training_args = TrainingArguments(
        output_dir=str(output_dir / "checkpoints"),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        bf16=True,
        gradient_checkpointing=True,
        logging_steps=10,
        save_steps=args.save_steps,
        save_total_limit=2,
        remove_unused_columns=False,
        dataloader_pin_memory=False,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
    )
    print("Starting training...")
    trainer.train()

    # Save adapter
    print(f"Saving adapter to {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(output_dir))

    # Copy tokenizer files alongside adapter
    tokenizer.save_pretrained(str(output_dir))

    # Clean up checkpoints directory
    checkpoints_dir = output_dir / "checkpoints"
    if checkpoints_dir.exists():
        shutil.rmtree(checkpoints_dir)

    print(f"Adapter saved to {output_dir}")
    print("The voice registry will detect this adapter automatically.")


def main() -> None:
    """Parse CLI arguments and launch training."""
    parser = argparse.ArgumentParser(description="Train an Orpheus LoRA adapter for voice cloning")
    parser.add_argument("character", help="Character name (becomes the adapter directory name)")
    parser.add_argument("dataset_dir", help="Directory of WAV clips from prepare_audio")
    parser.add_argument("--transcript", default=None, help="CSV mapping filename to text (default: dataset_dir/transcript.csv)")
    parser.add_argument("--voices-dir", default="voices", help="Root voices directory (default: voices)")
    parser.add_argument("--base-model", default="canopylabs/orpheus-tts-0.1-pretrained", help="HuggingFace base model ID")
    parser.add_argument("--epochs", type=int, default=1, help="Number of training epochs (default: 1)")
    parser.add_argument("--batch-size", type=int, default=1, help="Per-device batch size (default: 1)")
    parser.add_argument("--learning-rate", type=float, default=5e-5, help="Learning rate (default: 5e-5)")
    parser.add_argument("--lora-rank", type=int, default=32, help="LoRA rank (default: 32)")
    parser.add_argument("--lora-alpha", type=int, default=64, help="LoRA alpha (default: 64)")
    parser.add_argument("--max-seq-len", type=int, default=2048, help="Max sequence length (default: 2048)")
    parser.add_argument("--save-steps", type=int, default=500, help="Save checkpoint every N steps (default: 500)")
    parser.add_argument("--device", default="cuda", help="Training device (default: cuda)")
    parser.add_argument("--snac-device", default="cpu", help="SNAC encoding device (default: cpu)")
    parser.add_argument("--no-cache", action="store_true", help="Disable SNAC encoding cache, re-encode all clips")
    args = parser.parse_args()

    train(args)


if __name__ == "__main__":
    main()
