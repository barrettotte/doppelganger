import os
import torch
import torchaudio
import torchaudio.transforms as T
from TTS.api import TTS

INPUT_WAV = "raw_audio/sam_hyde/sample-30s.wav"
PROCESSED_WAV = "processed_ref.wav"
TARGET_SAMPLE_RATE = 24000

def preprocess_audio(input_path, output_path):
    """
    Converts audio to Mono and resamples to 24kHz for XTTS v2.
    """
    print(f"Processing {input_path}...")

    waveform, sample_rate = torchaudio.load(input_path)

    # convert from stereo to mono
    if waveform.shape[0] > 1:
        waveform = torch.mean(waveform, dim=0, keepdim=True)

    # resample if needed
    if sample_rate != TARGET_SAMPLE_RATE:
        resampler = T.Resample(orig_freq=sample_rate, new_freq=TARGET_SAMPLE_RATE)
        waveform = resampler(waveform)

    torchaudio.save(output_path, waveform, TARGET_SAMPLE_RATE, encoding="PCM_S", bits_per_sample=16)
    print(f"Saved processed audio to {output_path} (Mono, {TARGET_SAMPLE_RATE}Hz)")


device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Running on: {device}")

if not os.path.exists(INPUT_WAV):
    print(f"Error: Could not find {INPUT_WAV}. Please place your audio file in this folder.")
    exit(1)

preprocess_audio(INPUT_WAV, PROCESSED_WAV)

print("Loading XTTS v2 model...")
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)

print("Generating audio...")
tts.tts_to_file(
    text="This is a test. I have converted the reference audio to mono 24 kilohertz automatically.",
    speaker_wav=PROCESSED_WAV,
    language="en",
    file_path="output.wav"
)

print("Done! Saved to output.wav")
