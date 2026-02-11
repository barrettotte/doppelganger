"""Tests for the Orpheus TTS engine with mocked vLLM and SNAC."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from doppelganger.config import OrpheusSettings
from doppelganger.tts.exceptions import (
    TTSEngineUnavailableError,
    TTSGenerationError,
    TTSModelNotLoadedError,
)
from doppelganger.tts.orpheus import (
    _AUDIO_TOKEN_MIN,
    _END_OF_AI,
    OrpheusEngine,
)


@pytest.fixture
def orpheus_settings() -> OrpheusSettings:
    """Default Orpheus settings for testing."""
    return OrpheusSettings(enabled=True, vllm_base_url="http://localhost:8001/v1")


@pytest.fixture
def mock_snac() -> MagicMock:
    """Mock SNACDecoder that returns fake WAV bytes."""
    snac = MagicMock()
    snac.is_loaded = True
    snac.decode.return_value = b"RIFF-fake-wav"
    return snac


@pytest.fixture
def mock_client() -> MagicMock:
    """Mock httpx.Client for vLLM calls."""
    client = MagicMock(spec=httpx.Client)
    return client


@pytest.fixture
def engine(orpheus_settings: OrpheusSettings, mock_snac: MagicMock, mock_client: MagicMock) -> OrpheusEngine:
    """Create an OrpheusEngine with mocked internals."""
    eng = OrpheusEngine(orpheus_settings)
    eng._snac = mock_snac
    eng._client = mock_client
    return eng


def test_not_loaded_raises(orpheus_settings: OrpheusSettings) -> None:
    """Generating without loading raises TTSModelNotLoadedError."""
    eng = OrpheusEngine(orpheus_settings)

    with pytest.raises(TTSModelNotLoadedError):
        eng.generate("/fake/adapter", "hello")


def test_is_loaded(engine: OrpheusEngine) -> None:
    """is_loaded is True when both SNAC and client are ready."""
    assert engine.is_loaded is True


def test_is_loaded_false_when_snac_not_loaded(engine: OrpheusEngine) -> None:
    """is_loaded is False when SNAC is not loaded."""
    engine._snac.is_loaded = False
    assert engine.is_loaded is False


def test_resolve_lora_name(engine: OrpheusEngine) -> None:
    """LoRA name is derived from the directory basename."""
    assert engine._resolve_lora_name("/voices/sauron") == "sauron"
    assert engine._resolve_lora_name("/voices/my-character") == "my-character"


def test_build_prompt(engine: OrpheusEngine) -> None:
    """Prompt follows Orpheus format."""
    prompt = engine._build_prompt("hello world")
    assert "<custom_token_3>" in prompt
    assert "hello world" in prompt
    assert "<custom_token_4>" in prompt
    assert "<custom_token_5>" in prompt


def test_generate_success(engine: OrpheusEngine, mock_client: MagicMock) -> None:
    """Successful generation returns TTSResult with audio bytes."""
    # Mock vLLM response with 14 audio token IDs (2 frames of 7) above _AUDIO_TOKEN_MIN
    audio_tokens = list(range(_AUDIO_TOKEN_MIN, _AUDIO_TOKEN_MIN + 14)) + [_END_OF_AI]
    token_strings = [str(t) for t in audio_tokens]

    response = MagicMock()
    response.json.return_value = {
        "choices": [
            {
                "logprobs": {"tokens": token_strings},
                "text": "",
            }
        ]
    }
    response.raise_for_status = MagicMock()
    mock_client.post.return_value = response

    result = engine.generate("/voices/sauron", "hello")

    assert result.audio_bytes == b"RIFF-fake-wav"
    assert result.sample_rate == 24000
    mock_client.post.assert_called_once()
    engine._snac.decode.assert_called_once()


def test_generate_text_fallback(engine: OrpheusEngine, mock_client: MagicMock) -> None:
    """Falls back to parsing text output when no logprobs."""
    # 7 audio tokens (1 frame) above _AUDIO_TOKEN_MIN, followed by END_OF_AI
    audio_tokens = list(range(_AUDIO_TOKEN_MIN, _AUDIO_TOKEN_MIN + 7))
    response = MagicMock()
    response.json.return_value = {
        "choices": [
            {
                "text": " ".join(str(t) for t in audio_tokens + [_END_OF_AI]),
            }
        ]
    }
    response.raise_for_status = MagicMock()
    mock_client.post.return_value = response

    result = engine.generate("/voices/sauron", "test")
    assert result.audio_bytes == b"RIFF-fake-wav"


def test_generate_no_audio_tokens_raises(engine: OrpheusEngine, mock_client: MagicMock) -> None:
    """Raises TTSGenerationError when no audio tokens in response."""
    response = MagicMock()
    response.json.return_value = {"choices": [{"text": ""}]}
    response.raise_for_status = MagicMock()
    mock_client.post.return_value = response

    with pytest.raises(TTSGenerationError, match="No audio tokens"):
        engine.generate("/voices/sauron", "hello")


def test_generate_timeout_raises(engine: OrpheusEngine, mock_client: MagicMock) -> None:
    """vLLM timeout is mapped to TTSEngineUnavailableError."""
    mock_client.post.side_effect = httpx.TimeoutException("timed out")

    with pytest.raises(TTSEngineUnavailableError, match="timed out"):
        engine.generate("/voices/sauron", "hello")


def test_generate_connection_error_raises(engine: OrpheusEngine, mock_client: MagicMock) -> None:
    """vLLM connection error is mapped to TTSEngineUnavailableError."""
    mock_client.post.side_effect = httpx.ConnectError("connection refused")

    with pytest.raises(TTSEngineUnavailableError, match="connection"):
        engine.generate("/voices/sauron", "hello")


def test_generate_no_choices_raises(engine: OrpheusEngine, mock_client: MagicMock) -> None:
    """Empty choices from vLLM raises TTSGenerationError."""
    response = MagicMock()
    response.json.return_value = {"choices": []}
    response.raise_for_status = MagicMock()
    mock_client.post.return_value = response

    with pytest.raises(TTSGenerationError, match="no choices"):
        engine.generate("/voices/sauron", "hello")


def test_filter_audio_tokens_keeps_valid_range(engine: OrpheusEngine) -> None:
    """_filter_audio_tokens keeps tokens >= _AUDIO_TOKEN_MIN and truncates to multiple of 7."""
    # 999 is below _AUDIO_TOKEN_MIN so it's dropped; 7 valid audio tokens kept
    valid = list(range(_AUDIO_TOKEN_MIN, _AUDIO_TOKEN_MIN + 7))
    tokens = [999, *valid, _END_OF_AI, _AUDIO_TOKEN_MIN + 100]
    result = engine._filter_audio_tokens(tokens)
    assert result == valid


def test_unload(engine: OrpheusEngine, mock_client: MagicMock) -> None:
    """Unloading clears SNAC and closes client."""
    engine.unload_model()
    engine._snac.unload.assert_called_once()
    mock_client.close.assert_called_once()


def test_load_model(orpheus_settings: OrpheusSettings) -> None:
    """load_model creates client and loads SNAC."""
    eng = OrpheusEngine(orpheus_settings)

    with patch.object(eng._snac, "load"), patch("doppelganger.tts.orpheus.httpx.Client") as mock_client_cls:
        mock_inst = MagicMock()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_inst.get.return_value = mock_resp
        mock_client_cls.return_value = mock_inst

        eng.load_model()

        assert eng._client is mock_inst
        eng._snac.load.assert_called_once()
