import os
import auditok
import torchaudio
import torchaudio.transforms as T
import torch

# --- Configuration ---
CHARACTER = "sam_hyde"
INPUT_FILE = f"raw_audio/{CHARACTER}/sample.wav"
OUTPUT_DIR = f"train/{CHARACTER}/wavs"
MIN_DURATION = 2.0  # Seconds (ignore tiny blips)
MAX_DURATION = 10.0 # Seconds (XTTS prefers shorter sentences)
TARGET_SR = 22050   # Standard training sample rate for TTS datasets

def preprocess_and_slice(input_path, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"Loading {input_path}...")
    waveform, sample_rate = torchaudio.load(input_path)

    # 1. Force Mono
    if waveform.shape[0] > 1:
        print("Converting to mono...")
        waveform = torch.mean(waveform, dim=0, keepdim=True)

    # 2. Resample to Target Rate (22050Hz)
    if sample_rate != TARGET_SR:
        print(f"Resampling from {sample_rate}Hz to {TARGET_SR}Hz...")
        resampler = T.Resample(sample_rate, TARGET_SR)
        waveform = resampler(waveform)
        sample_rate = TARGET_SR

    # Save a temporary processed full file for auditok to read
    temp_file = "temp_full_processed.wav"
    
    # --- FIX IS HERE ---
    # We must enforce 16-bit PCM Integer encoding so the 'wave' library can read it.
    torchaudio.save(
        temp_file, 
        waveform, 
        sample_rate, 
        encoding="PCM_S", 
        bits_per_sample=16
    )
    # -------------------

    print("Slicing audio based on silence...")
    
    # 3. Slice using Auditok
    audio_events = auditok.split(
        temp_file,
        min_dur=MIN_DURATION,     
        max_dur=MAX_DURATION,     
        max_silence=0.5,          
        energy_threshold=50       
    )

    count = 0
    for i, event in enumerate(audio_events):
        out_name = f"segment_{i:04d}.wav"
        out_path = os.path.join(output_dir, out_name)
        
        # Save the region
        event.save(out_path, standard_order=True) 
        count += 1

    print(f"Done! Created {count} slices in '{output_dir}'.")
    
    # Cleanup
    if os.path.exists(temp_file):
        os.remove(temp_file)

if __name__ == "__main__":
    if not os.path.exists(INPUT_FILE):
        print(f"Please make sure '{INPUT_FILE}' exists.")
    else:
        preprocess_and_slice(INPUT_FILE, OUTPUT_DIR)
