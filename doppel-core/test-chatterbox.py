import torch
import torchaudio as ta
from chatterbox.tts import ChatterboxTTS

if torch.cuda.is_available():
    device = "cuda"
elif torch.backends.mps.is_available():
    device = "mps"
else:
    device = "cpu"
print(f"Using device: {device}")

model = ChatterboxTTS.from_pretrained(device=device)

to_clone_wav = "../voice-samples/sam_hyde/sam-dear-elon-noise-reduced-3m30s.wav"
gen_text = "Hello world. I am drinking coors light and petting my cat. I am having a freaking epic time"

out_wav = model.generate(
    gen_text, 
    audio_prompt_path=to_clone_wav,
    exaggeration=0.65,
    cfg_weight=0.5,
    temperature=0.25,
)
ta.save("hyde-test-chatterbox.wav", out_wav, model.sr)
