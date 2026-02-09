import os
import torch

# This import will now work because we installed from source
from TTS.tts.layers.xtts.trainer.gpt_trainer import GPTTrainer

from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts
from TTS.utils.manage import ModelManager
from trainer import TrainerArgs, Trainer

# --- Configuration ---
CHARACTER = "sam_hyde"
OUT_PATH = f"checkpoints/{CHARACTER}"
DATASET_ROOT = f"train/{CHARACTER}"
MANIFEST_FILE = f"train/{CHARACTER}/metadata.csv"

# RTX 3090 Ti Settings
BATCH_SIZE = 4
GRAD_ACCUMULATION = 8 
NUM_EPOCHS = 10 
LEARNING_RATE = 5e-5

def custom_formatter(root_path, manifest_file, **kwargs):
    """
    Parses our Step 3 CSV format:
    wavs/filename.wav|text|speaker_name|language
    """
    items = []
    with open(manifest_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            cols = line.split("|")
            if len(cols) < 4: continue
            
            # XTTS training requires specific keys
            wav_rel = cols[0]
            text = cols[1]
            speaker = cols[2]
            language = cols[3]
            
            wav_full = os.path.join(root_path, wav_rel)
            items.append({
                "text": text,
                "audio_file": wav_full,
                "speaker_name": speaker,
                "language": language
            })
    return items

def train_gpt():
    # 1. Download/Locate Base Model
    print("Locating base XTTS v2 model...")
    manager = ModelManager()
    model_name = "tts_models/multilingual/multi-dataset/xtts_v2"
    model_path = str(manager.download_model(model_name)[0])
    print(f"Base model folder found at: {model_path}")

    # 2. Load & Update XTTS Config
    print("Loading configuration...")
    config = XttsConfig()
    config.load_json(os.path.join(model_path, "config.json"))

    config.model_args.dvae_checkpoint = os.path.join(model_path, "dvae.pth")
    config.model_args.mel_stats_path = os.path.join(model_path, "mel_stats.pth")
    config.tokenizer_path = os.path.join(model_path, "vocab.json")

    config.run_name = "xtts_lora_finetune"
    config.output_path = OUT_PATH
    config.batch_size = BATCH_SIZE
    config.eval_batch_size = BATCH_SIZE
    config.num_loader_workers = 4
    config.epochs = NUM_EPOCHS 
    config.grad_accum_steps = GRAD_ACCUMULATION
    
    config.audio.sample_rate = 22050 
    config.optimizer = "AdamW"
    config.optimizer_params = {"betas": [0.9, 0.96], "eps": 1e-8, "weight_decay": 1e-2}
    config.lr = LEARNING_RATE

    config.model_args.use_lora = True 
    config.model_args.lora_r = 16 
    config.model_args.lora_alpha = 32
    config.model_args.lora_dropout = 0.05
    config.model_args.gpt_train_only_xtts_decoder_layers = True 

    # 3. Prepare Data
    print("Formatting dataset...")
    all_samples = custom_formatter(DATASET_ROOT, MANIFEST_FILE)
    eval_size = max(1, int(len(all_samples) * 0.1))
    eval_samples = all_samples[:eval_size]
    train_samples = all_samples[eval_size:]
    print(f"Training on {len(train_samples)} samples, validating on {len(eval_samples)}.")

    # 4. Initialize Model
    model = Xtts.init_from_config(config)
    print("Loading base checkpoint...")
    model.load_checkpoint(config, checkpoint_dir=model_path, eval=False)

    # 5. Initialize the Specialized GPT Trainer
    print("Initializing GPTTrainer...")
    args = TrainerArgs(
        restore_path=None, 
        skip_train_epoch=False,
    )

    trainer = Trainer(
        args,
        config,
        output_path=OUT_PATH,
        model=model,
        train_samples=train_samples,
        eval_samples=eval_samples,
    )

    # 6. Start Training
    print("Starting training loop...")
    trainer.fit()

if __name__ == "__main__":
    train_gpt()