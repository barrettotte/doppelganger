"""SNAC audio decoder for converting Orpheus token IDs to WAV audio."""

import io
import logging
import wave
from typing import Any

import snac
import torch

from doppelganger.tts.exceptions import TTSGenerationError, TTSModelNotLoadedError

logger = logging.getLogger(__name__)

# Orpheus interleaves 7 codebook layers and offsets each by a vocab constant.
# These offsets must be subtracted to recover the raw SNAC code indices.
_CODEBOOK_OFFSETS = [0, 4096, 8192, 12288, 16384, 20480, 24576]
_NUM_CODEBOOKS = 7


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

    def _redistribute_codes(self, token_ids: list[int]) -> list[list[int]]:
        """Regroup interleaved Orpheus tokens into per-codebook lists.

        Orpheus outputs tokens in round-robin across 7 codebooks with vocab offsets.
        This function strips the offsets and groups tokens by codebook index.
        """
        if not token_ids:
            raise TTSGenerationError("No audio tokens to decode")

        codebooks: list[list[int]] = [[] for _ in range(_NUM_CODEBOOKS)]
        for i, token_id in enumerate(token_ids):
            codebook_idx = i % _NUM_CODEBOOKS
            code = token_id - _CODEBOOK_OFFSETS[codebook_idx]
            codebooks[codebook_idx].append(code)

        return codebooks

    def decode(self, token_ids: list[int], sample_rate: int) -> bytes:
        """Decode Orpheus token IDs into PCM16 WAV bytes."""
        model = self._require_model()
        codes = self._redistribute_codes(token_ids)

        # SNAC expects 3 codebook levels: coarse (1x), mid (2x), fine (4x)
        # Orpheus uses 7 interleaved layers that map to these 3 levels
        with torch.no_grad():
            # Build the 3-level code tensors SNAC expects
            codes_0 = torch.tensor(codes[0], device=self._device).unsqueeze(0)
            codes_1 = torch.tensor(codes[1] + codes[4], device=self._device).unsqueeze(0)
            codes_2 = torch.tensor(codes[2] + codes[3] + codes[5] + codes[6], device=self._device).unsqueeze(0)

            audio = model.decode(codes_0, codes_1, codes_2)

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
