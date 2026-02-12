"""Shared SNAC codec constants used by both encoder and decoder."""

# Orpheus interleaves 7 codebook layers and offsets each by a vocab constant.
CODEBOOK_OFFSETS = [0, 4096, 8192, 12288, 16384, 20480, 24576]
NUM_CODEBOOKS = 7

# Base shift into the Orpheus tokenizer vocabulary for audio tokens.
AUDIO_VOCAB_OFFSET = 128266
