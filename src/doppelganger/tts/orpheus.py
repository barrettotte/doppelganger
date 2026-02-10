"""Orpheus TTS engine using vLLM-served LoRA adapters and SNAC decoding."""

import logging
from pathlib import Path
from typing import Any

import httpx

from doppelganger.config import OrpheusSettings
from doppelganger.tts.engine import EngineType, TTSEngine, TTSResult
from doppelganger.tts.exceptions import (
    TTSEngineUnavailableError,
    TTSGenerationError,
    TTSModelNotLoadedError,
    TTSOutOfMemoryError,
)
from doppelganger.tts.snac_decoder import SNACDecoder

logger = logging.getLogger(__name__)

# Special tokens marking the start/end of audio output in Orpheus
_AUDIO_START_TOKEN = 128259
_AUDIO_END_TOKEN = 128009
_AUDIO_PAD_TOKEN = 128258


class OrpheusEngine(TTSEngine):
    """Calls a vLLM server hosting the Orpheus base model with per-request LoRA adapters."""

    engine_type = EngineType.ORPHEUS

    def __init__(self, settings: OrpheusSettings) -> None:
        self._settings = settings
        self._snac = SNACDecoder(device=settings.snac_device)
        self._client: httpx.Client | None = None

    def load_model(self) -> None:
        """Load the SNAC decoder and verify vLLM connectivity."""
        self._snac.load()
        self._client = httpx.Client(base_url=self._settings.vllm_base_url, timeout=120.0)

        try:
            resp = self._client.get("/models")
            resp.raise_for_status()
            logger.info("Connected to vLLM at %s", self._settings.vllm_base_url)
        except httpx.HTTPError as e:
            logger.warning("vLLM health check failed (engine will retry on requests): %s", e)

    def unload_model(self) -> None:
        """Release the SNAC decoder and close the HTTP client."""
        self._snac.unload()
        if self._client is not None:
            self._client.close()
            self._client = None
            logger.info("Orpheus engine unloaded")

    @property
    def is_loaded(self) -> bool:
        """Whether SNAC is loaded and the HTTP client is ready."""
        return self._snac.is_loaded and self._client is not None

    def _require_loaded(self) -> None:
        """Raise if the engine is not ready."""
        if not self.is_loaded:
            raise TTSModelNotLoadedError("Orpheus engine is not loaded")

    def _resolve_lora_name(self, voice_path: str) -> str:
        """Derive the vLLM LoRA adapter name from the voice directory path."""
        return Path(voice_path).name

    def _build_prompt(self, text: str) -> str:
        """Build the Orpheus prompt format."""
        return f"<custom_token_3>{text}<custom_token_1>"

    def _extract_token_ids(self, response_data: dict[str, Any]) -> list[int]:
        """Parse audio token IDs from the vLLM completion response."""
        choices = response_data.get("choices", [])
        if not choices:
            raise TTSGenerationError("vLLM returned no choices")

        # Extract token IDs from logprobs
        logprobs = choices[0].get("logprobs")
        if logprobs and "tokens" in logprobs:
            token_strings = logprobs["tokens"]
            token_ids = []
            for t in token_strings:
                try:
                    token_ids.append(int(t))
                except ValueError:
                    continue
            return self._filter_audio_tokens(token_ids)

        # Fallback: parse from text output (space-separated integers)
        text_output = choices[0].get("text", "")
        token_ids = []
        for part in text_output.strip().split():
            try:
                token_ids.append(int(part))
            except ValueError:
                continue

        return self._filter_audio_tokens(token_ids)

    def _filter_audio_tokens(self, token_ids: list[int]) -> list[int]:
        """Keep only audio tokens between start and end markers."""
        audio_tokens = []
        in_audio = False

        for tid in token_ids:
            if tid == _AUDIO_START_TOKEN:
                in_audio = True
                continue
            if tid == _AUDIO_END_TOKEN:
                break
            if tid == _AUDIO_PAD_TOKEN:
                continue
            if in_audio:
                audio_tokens.append(tid)

        # If no start marker found, treat all as audio tokens (some model versions)
        if not audio_tokens and token_ids:
            audio_tokens = [t for t in token_ids if t not in (_AUDIO_START_TOKEN, _AUDIO_END_TOKEN, _AUDIO_PAD_TOKEN)]

        return audio_tokens

    def generate(self, voice_path: str, text: str) -> TTSResult:
        """Generate speech via vLLM and decode with SNAC."""
        self._require_loaded()
        client = self._client
        if client is None:
            raise TTSModelNotLoadedError("Orpheus HTTP client is not initialized")

        lora_name = self._resolve_lora_name(voice_path)
        prompt = self._build_prompt(text)

        payload = {
            "model": lora_name,
            "prompt": prompt,
            "max_tokens": self._settings.max_tokens,
            "temperature": self._settings.temperature,
            "top_p": self._settings.top_p,
            "repetition_penalty": self._settings.repetition_penalty,
            "logprobs": 1,
        }

        try:
            resp = client.post("/completions", json=payload)
            resp.raise_for_status()

        except httpx.TimeoutException as e:
            raise TTSEngineUnavailableError(f"vLLM request timed out: {e}") from e

        except httpx.HTTPStatusError as e:
            error_text = e.response.text
            if "out of memory" in error_text.lower():
                raise TTSOutOfMemoryError("vLLM out of memory during generation") from e

            raise TTSGenerationError(f"vLLM request failed ({e.response.status_code}): {error_text}") from e

        except httpx.HTTPError as e:
            raise TTSEngineUnavailableError(f"vLLM connection error: {e}") from e

        response_data = resp.json()
        token_ids = self._extract_token_ids(response_data)

        if not token_ids:
            raise TTSGenerationError("No audio tokens in vLLM response")

        audio_bytes = self._snac.decode(token_ids, self._settings.sample_rate)
        # Estimate duration from token count (7 codebooks, ~86 tokens/sec at 24kHz SNAC)
        n_frames = len(token_ids) // 7
        duration_ms = int(n_frames / 86 * 1000) if n_frames > 0 else 0

        return TTSResult(audio_bytes=audio_bytes, sample_rate=self._settings.sample_rate, duration_ms=duration_ms)
