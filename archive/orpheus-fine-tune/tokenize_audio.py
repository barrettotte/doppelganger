import torch
import librosa
import pandas as pd
import json
from snac import SNAC
from pathlib import Path
from tqdm import tqdm
from transformers import AutoTokenizer

CHARACTER = "test_character"
TRAINING_DIR = Path("../training") / CHARACTER / "train"
METADATA_FILE = TRAINING_DIR / "metadata.csv"
OUTPUT_JSONL = Path("../training") / CHARACTER / "dataset.jsonl"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

GLOBAL_OFFSET = 128266
AUDIO_START_TOKEN = 128257
EOS_TOKEN = 128001 # Llama 3 default EOS

def pack_snac_codes(codes):
    """
    Interleaves SNAC layers into the 7-token repeating pattern Orpheus expects.
    Input: List of 3 tensors [Layer1, Layer2, Layer3]
    """
    L1, L2, L3 = codes[0].squeeze(), codes[1].squeeze(), codes[2].squeeze()
    
    # SNAC structure: L1 is coarsest. L2 is 2x L1. L3 is 4x L1.
    token_ids = []
    n_steps = L1.shape[0]

    for t in range(n_steps):
        if (2*t + 1 >= L2.shape[0]) or (4*t + 3 >= L3.shape[0]):
            break

        # 7-token pattern
        token_ids.append(L1[t].item())
        
        token_ids.append(L2[2*t].item() + 4096)
        
        token_ids.append(L3[4*t].item() + 8192)
        token_ids.append(L3[4*t + 1].item() + 12288)
        
        token_ids.append(L2[2*t + 1].item() + 16384)
        
        token_ids.append(L3[4*t + 2].item() + 20480)
        token_ids.append(L3[4*t + 3].item() + 24576)

    # apply global vocabulary offset
    final_tokens = [x + GLOBAL_OFFSET for x in token_ids]
    return final_tokens

def main():
    print(f"Loading SNAC model on {DEVICE}...")
    model = SNAC.from_pretrained("hubertsiuzdak/snac_24khz").to(DEVICE)
    model.eval()

    df = pd.read_csv(METADATA_FILE)
    tokenizer = AutoTokenizer.from_pretrained("unsloth/orpheus-3b-0.1-pretrained")
    
    with open(OUTPUT_JSONL, "w", encoding="utf-8") as f:
        for _, row in tqdm(df.iterrows(), total=len(df), desc="Tokenizing"):
            audio_path = TRAINING_DIR / row['audio_file']
            text_prompt = row['text']
            
            try:
                audio, sr = librosa.load(audio_path, sr=24000)
                audio_tensor = torch.tensor(audio).unsqueeze(0).unsqueeze(0).to(DEVICE)

                with torch.no_grad():
                    codes = model.encode(audio_tensor)
                
                audio_tokens = pack_snac_codes(codes)
                full_prompt = f"""Below is an instruction that describes a task. Write a response that appropriately completes the request.

### Instruction:
Convert this text to speech: {text_prompt}

### Response:
"""
                # encode text to IDs
                text_ids = tokenizer.encode(full_prompt, add_special_tokens=True)
                combined_ids = text_ids + [AUDIO_START_TOKEN] + audio_tokens + [EOS_TOKEN]

                # create mask - train on audio only, mask text
                labels = [-100] * len(text_ids) + [AUDIO_START_TOKEN] + audio_tokens + [EOS_TOKEN]
                entry = {
                    "input_ids": combined_ids,
                    "labels": labels
                }
                f.write(json.dumps(entry) + "\n")
                
            except Exception as e:
                print(f"Skipping {audio_path}: {e}")

    print(f"Dataset saved to {OUTPUT_JSONL}")

if __name__ == "__main__":
    main()
