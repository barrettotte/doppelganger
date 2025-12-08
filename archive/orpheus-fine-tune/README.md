# Fine-Tune Orpheus

First attempt at trying to accomplish this project...probably wasn't smart to spin wheels on this for so long.

This kind of worked...but ran into a lot of issues with hums and gibberish toward end of generation.
Also, the latency of generation and hot swapping "characters" might not be sufficient for a Discord bot.

## Summary

- `split_audio.py` - splits 45 minute sample wav file into 10-15 second clips and uses Whisper to transcribe each
- `tokenize_audio.py` - tokenizes each audio clip using SNAC encoding and builds dataset
- `train_lora.py` - fine-tunes `unsloth/orpheus-3b-0.1-pretrained` and saves LoRA adapter
- `inference.py` - loads LoRA adapter and attempts to generate audio

## Training Process

- Record 30-60 minutes of clear audio
  - If using video, convert with `ffmpeg -i input.mp4 output.wav`
- Manually clean noise using Audacity
  - build noise sample wav file of at least 5 seconds
  - use noise sample with `Effect > Noise Removal and Repair > Noise Reduction`
- run `bash fine-tune.sh {CHARACTER}`

## References

- [Fine-tuning Orpheus with Unsloth](https://colab.research.google.com/github/unslothai/notebooks/blob/main/nb/Orpheus_(3B)-TTS.ipynb)
- https://docs.unsloth.ai/get-started/fine-tuning-llms-guide/lora-hyperparameters-guide
