"""SNAC audio decoder for converting Orpheus token IDs to WAV audio."""

import io
import logging
import wave
from typing import Any

import snac
import torch

from doppelganger.tts.exceptions import TTSGenerationError, TTSModelNotLoadedError
from doppelganger.tts.snac_constants import AUDIO_VOCAB_OFFSET, CODEBOOK_OFFSETS, NUM_CODEBOOKS

logger = logging.getLogger(__name__)


class SNACDecoder:
    """Decodes Orpheus-style interleaved SNAC tokens into PCM16 WAV audio."""

    def __init__(self, device: str = "cpu") -> None:
        self._device = device
        self._model: Any | None = None

    def load(self) -> None:
        """Load the SNAC model from HuggingFace hub."""
        logger.info("Loading SNAC decoder on device=%s", self._device)
        model = snac.SNAC.from_pretrained("hubertsiuzdak/snac_24khz").to(self._device)
        model.eval()

        self._model = model
        logger.info("SNAC decoder loaded")

    def unload(self) -> None:
        """Release the SNAC model."""
        if self._model is not None:
            del self._model
            self._model = None
            logger.info("SNAC decoder unloaded")

    @property
    def is_loaded(self) -> bool:
        """Whether the SNAC model is loaded."""
        return self._model is not None

    def _require_model(self) -> Any:
        """Return the loaded model, or raise if not loaded."""
        if self._model is None:
            raise TTSModelNotLoadedError("SNAC decoder is not loaded")
        return self._model

    def _redistribute_codes(self, token_ids: list[int]) -> tuple[list[int], list[int], list[int]]:
        """Regroup interleaved Orpheus tokens into SNAC's 3 codebook levels.

        Orpheus outputs 7 tokens per frame in round-robin order. Per frame:
          - Level 0 (coarse, 1x): position 0
          - Level 1 (mid, 2x): positions 1, 4 (interleaved per frame)
          - Level 2 (fine, 4x): positions 2, 3, 5, 6 (interleaved per frame)
        """
        if not token_ids:
            raise TTSGenerationError("No audio tokens to decode")

        layer_0: list[int] = []
        layer_1: list[int] = []
        layer_2: list[int] = []

        n_frames = len(token_ids) // NUM_CODEBOOKS
        for i in range(n_frames):
            base = NUM_CODEBOOKS * i
            layer_0.append(token_ids[base] - AUDIO_VOCAB_OFFSET)
            layer_1.append(token_ids[base + 1] - AUDIO_VOCAB_OFFSET - CODEBOOK_OFFSETS[1])
            layer_2.append(token_ids[base + 2] - AUDIO_VOCAB_OFFSET - CODEBOOK_OFFSETS[2])
            layer_2.append(token_ids[base + 3] - AUDIO_VOCAB_OFFSET - CODEBOOK_OFFSETS[3])
            layer_1.append(token_ids[base + 4] - AUDIO_VOCAB_OFFSET - CODEBOOK_OFFSETS[4])
            layer_2.append(token_ids[base + 5] - AUDIO_VOCAB_OFFSET - CODEBOOK_OFFSETS[5])
            layer_2.append(token_ids[base + 6] - AUDIO_VOCAB_OFFSET - CODEBOOK_OFFSETS[6])

        return layer_0, layer_1, layer_2

    def decode(self, token_ids: list[int], sample_rate: int) -> bytes:
        """Decode Orpheus token IDs into PCM16 WAV bytes."""
        model = self._require_model()
        layer_0, layer_1, layer_2 = self._redistribute_codes(token_ids)

        with torch.no_grad():
            codes = [
                torch.tensor(layer_0, device=self._device).unsqueeze(0),
                torch.tensor(layer_1, device=self._device).unsqueeze(0),
                torch.tensor(layer_2, device=self._device).unsqueeze(0),
            ]
            audio = model.decode(codes)

        # Convert to PCM16 WAV
        audio_np = audio.squeeze().cpu().numpy()
        pcm16 = (audio_np.clip(-1.0, 1.0) * 32767).astype("int16")

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm16.tobytes())

        return buf.getvalue()
