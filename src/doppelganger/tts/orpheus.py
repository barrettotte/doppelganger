"""Orpheus TTS engine using vLLM-served LoRA adapters and SNAC decoding."""

import logging
import re
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

# Special Orpheus token IDs (must match train_lora.py)
_END_OF_AI = 128262

# Audio tokens start at this vocab offset (128266 = first SNAC codebook 0 token)
_AUDIO_TOKEN_MIN = 128266

# Matches "<custom_token_1234>" and extracts the integer.
# Orpheus uses a Llama tokenizer where custom tokens start at vocab ID 128000,
# so <custom_token_N> corresponds to token ID 128000 + N.
_CUSTOM_TOKEN_RE = re.compile(r"<custom_token_(\d+)>")
_CUSTOM_TOKEN_BASE = 128256


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
        """Build the Orpheus prompt format matching train_lora.py sequence layout."""
        return f"<custom_token_3>{text}<custom_token_4><custom_token_5>"

    def _extract_token_ids(self, response_data: dict[str, Any]) -> list[int]:
        """Parse audio token IDs from the vLLM completion response."""
        choices = response_data.get("choices", [])
        if not choices:
            raise TTSGenerationError("vLLM returned no choices")

        # Extract token IDs from logprobs
        logprobs = choices[0].get("logprobs")
        if logprobs and "tokens" in logprobs:
            token_ids = self._parse_token_strings(logprobs["tokens"])
            return self._filter_audio_tokens(token_ids)

        # Fallback: parse from text output
        text_output = choices[0].get("text", "")
        token_ids = self._parse_token_strings(_CUSTOM_TOKEN_RE.findall(text_output))
        if not token_ids:
            # Try space-separated integers
            for part in text_output.strip().split():
                try:
                    token_ids.append(int(part))
                except ValueError:
                    continue

        return self._filter_audio_tokens(token_ids)

    def _parse_token_strings(self, tokens: list[str]) -> list[int]:
        """Parse token IDs from raw strings, handling both integer and <custom_token_N> formats."""
        token_ids: list[int] = []
        for t in tokens:
            try:
                token_ids.append(int(t))
                continue
            except ValueError:
                pass

            match = _CUSTOM_TOKEN_RE.match(t)
            if match:
                token_ids.append(_CUSTOM_TOKEN_BASE + int(match.group(1)))

        return token_ids

    def _filter_audio_tokens(self, token_ids: list[int]) -> list[int]:
        """Keep only audio tokens, stripping control tokens and truncating to a multiple of 7."""
        audio_tokens = []

        for tid in token_ids:
            if tid == _END_OF_AI:
                break
            if tid >= _AUDIO_TOKEN_MIN:
                audio_tokens.append(tid)

        # Truncate to a complete frame (7 codebooks per frame)
        remainder = len(audio_tokens) % 7
        if remainder:
            audio_tokens = audio_tokens[:-remainder]

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

        logger.debug(
            "Orpheus request: lora=%s, text_len=%d, max_tokens=%d", lora_name, len(text), payload["max_tokens"]
        )

        try:
            resp = client.post("/completions", json=payload)
            resp.raise_for_status()

        except httpx.TimeoutException as e:
            logger.error("vLLM request timed out for lora=%s", lora_name)
            raise TTSEngineUnavailableError(f"vLLM request timed out: {e}") from e

        except httpx.HTTPStatusError as e:
            error_text = e.response.text
            if "out of memory" in error_text.lower():
                logger.error("vLLM OOM for lora=%s", lora_name)
                raise TTSOutOfMemoryError("vLLM out of memory during generation") from e

            logger.error("vLLM HTTP %d for lora=%s: %s", e.response.status_code, lora_name, error_text[:500])
            raise TTSGenerationError(f"vLLM request failed ({e.response.status_code}): {error_text}") from e

        except httpx.HTTPError as e:
            logger.error("vLLM connection error for lora=%s: %s", lora_name, e)
            raise TTSEngineUnavailableError(f"vLLM connection error: {e}") from e

        response_data = resp.json()
        token_ids = self._extract_token_ids(response_data)

        if not token_ids:
            logger.error(
                "No audio tokens in vLLM response for lora=%s (response keys: %s)",
                lora_name,
                list(response_data.keys()),
            )
            raise TTSGenerationError("No audio tokens in vLLM response")

        logger.debug(
            "Orpheus got %d audio tokens (%d frames) for lora=%s", len(token_ids), len(token_ids) // 7, lora_name
        )

        audio_bytes = self._snac.decode(token_ids, self._settings.sample_rate)
        # Estimate duration from token count (7 codebooks, ~86 tokens/sec at 24kHz SNAC)
        n_frames = len(token_ids) // 7
        duration_ms = int(n_frames / 86 * 1000) if n_frames > 0 else 0

        return TTSResult(audio_bytes=audio_bytes, sample_rate=self._settings.sample_rate, duration_ms=duration_ms)
