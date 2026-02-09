import os
import whisper
import torch
from tqdm import tqdm

# --- Configuration ---
CHARACTER = "sam_hyde"
WAVS_DIR = f"train/{CHARACTER}/wavs"
OUTPUT_CSV = f"train/{CHARACTER}/metadata.csv"
SPEAKER_NAME = CHARACTER # Change this to your bot's character name
LANGUAGE = "en"               # Language code

def transcribe_dataset():
    # 1. Verify Hardware
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading Whisper model on {device}...")

    # 2. Load Whisper (using 'large' for best accuracy on 3090 Ti)
    # If it's too slow, change "large" to "medium" or "small"
    model = whisper.load_model("large", device=device)

    # 3. Get list of files
    if not os.path.exists(WAVS_DIR):
        print(f"Error: {WAVS_DIR} not found. Did you run Step 2?")
        return

    wav_files = [f for f in os.listdir(WAVS_DIR) if f.endswith(".wav")]
    wav_files.sort() # Ensure consistent order
    
    print(f"Found {len(wav_files)} segments. Starting transcription...")

    # 4. Transcribe loop
    results = []
    
    # We use tqdm for a nice progress bar
    for filename in tqdm(wav_files):
        filepath = os.path.join(WAVS_DIR, filename)
        
        # Transcribe
        # beam_size=5 improves accuracy slightly
        result = model.transcribe(filepath, language=LANGUAGE, beam_size=5)
        text = result["text"].strip()

        # Simple filter: Ignore empty or extremely short hallucinations
        if len(text) < 2:
            continue

        # Format: wav_filename|text|speaker|language
        # Note: We store relative path "wavs/filename" or just "filename" depending on loader.
        # Standard XTTS formatter often likes the filename relative to dataset root.
        line = f"wavs/{filename}|{text}|{SPEAKER_NAME}|{LANGUAGE}"
        results.append(line)

    # 5. Save to CSV
    with open(OUTPUT_CSV, "w", encoding="utf-8") as f:
        # Write header (optional, but good for reference)
        # XTTS custom splitters often ignore headers, but let's stick to raw data lines 
        # to be safe. If strict CSV is needed, we add header. 
        # For now, raw pipe-delimited lines are standard for Coqui.
        for line in results:
            f.write(line + "\n")

    print(f"Success! Transcribed {len(results)} segments to {OUTPUT_CSV}")

if __name__ == "__main__":
    transcribe_dataset()
