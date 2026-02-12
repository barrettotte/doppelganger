"""SNAC audio encoder for converting WAV audio to interleaved Orpheus token IDs."""

import logging
from typing import Any

import snac
import torch
import torchaudio

from doppelganger.tts.exceptions import TTSModelNotLoadedError
from doppelganger.tts.snac_constants import AUDIO_VOCAB_OFFSET, CODEBOOK_OFFSETS

logger = logging.getLogger(__name__)


class SNACEncoder:
    """Encodes WAV audio into Orpheus-style interleaved SNAC token IDs."""

    def __init__(self, device: str = "cpu") -> None:
        """Initialize the encoder with the target device."""
        self._device = device
        self._model: Any | None = None

    def load(self) -> None:
        """Load the SNAC model from HuggingFace hub."""
        logger.info("Loading SNAC encoder on device=%s", self._device)
        model = snac.SNAC.from_pretrained("hubertsiuzdak/snac_24khz").to(self._device)
        model.eval()

        self._model = model
        logger.info("SNAC encoder loaded")

    def unload(self) -> None:
        """Release the SNAC model."""
        if self._model is not None:
            del self._model
            self._model = None
            logger.info("SNAC encoder unloaded")

    @property
    def is_loaded(self) -> bool:
        """Whether the SNAC model is loaded."""
        return self._model is not None

    def _require_model(self) -> Any:
        """Return the loaded model, or raise if not loaded."""
        if self._model is None:
            raise TTSModelNotLoadedError("SNAC encoder is not loaded")
        return self._model

    def _interleave_codes(self, codes: list[Any]) -> list[int]:
        """Interleave 3-level SNAC codes into flat Orpheus token IDs.

        SNAC codes are sequential in time within each level:
          codes[0] shape [1, N]  - coarse, 1 per frame
          codes[1] shape [1, 2N] - mid, 2 per frame (indices 2*i, 2*i+1)
          codes[2] shape [1, 4N] - fine, 4 per frame (indices 4*i .. 4*i+3)

        Per frame i, the 7 interleaved positions are:
          pos 0: coarse[i]
          pos 1: mid[2*i]       (first mid)
          pos 2: fine[4*i]      (first fine)
          pos 3: fine[4*i+1]    (second fine)
          pos 4: mid[2*i+1]     (second mid)
          pos 5: fine[4*i+2]    (third fine)
          pos 6: fine[4*i+3]    (fourth fine)
        """
        n_frames = codes[0].shape[1]
        if n_frames == 0:
            return []

        tokens: list[int] = []
        for i in range(n_frames):
            tokens.append(int(codes[0][0][i]) + AUDIO_VOCAB_OFFSET + CODEBOOK_OFFSETS[0])
            tokens.append(int(codes[1][0][2 * i]) + AUDIO_VOCAB_OFFSET + CODEBOOK_OFFSETS[1])
            tokens.append(int(codes[2][0][4 * i]) + AUDIO_VOCAB_OFFSET + CODEBOOK_OFFSETS[2])
            tokens.append(int(codes[2][0][4 * i + 1]) + AUDIO_VOCAB_OFFSET + CODEBOOK_OFFSETS[3])
            tokens.append(int(codes[1][0][2 * i + 1]) + AUDIO_VOCAB_OFFSET + CODEBOOK_OFFSETS[4])
            tokens.append(int(codes[2][0][4 * i + 2]) + AUDIO_VOCAB_OFFSET + CODEBOOK_OFFSETS[5])
            tokens.append(int(codes[2][0][4 * i + 3]) + AUDIO_VOCAB_OFFSET + CODEBOOK_OFFSETS[6])

        return tokens

    def encode(self, audio_path: str, target_sample_rate: int = 24000) -> list[int]:
        """Encode a WAV file into interleaved Orpheus token IDs."""
        model = self._require_model()

        # Load and preprocess audio
        waveform, sample_rate = torchaudio.load(audio_path)

        # Mix stereo to mono by averaging channels
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)

        # Resample if needed
        if sample_rate != target_sample_rate:
            resampler = torchaudio.transforms.Resample(sample_rate, target_sample_rate)
            waveform = resampler(waveform)

        # Normalize amplitude to [-1, 1]
        peak = waveform.abs().max()
        if peak > 0:
            waveform = waveform / peak

        # SNAC expects shape [batch, channels, samples]
        audio_tensor = waveform.unsqueeze(0).to(self._device)

        with torch.no_grad():
            codes = model.encode(audio_tensor)

        return self._interleave_codes(codes)
