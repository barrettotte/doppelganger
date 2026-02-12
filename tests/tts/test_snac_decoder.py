"""Tests for the SNAC audio decoder with mocked snac and torch modules."""

from unittest.mock import MagicMock

import numpy as np
import pytest

from doppelganger.tts.exceptions import TTSGenerationError, TTSModelNotLoadedError
from doppelganger.tts.snac_decoder import SNACDecoder


@pytest.fixture
def mock_snac_modules(monkeypatch: pytest.MonkeyPatch) -> tuple[MagicMock, MagicMock]:
    """Mock snac and torch modules at the module level."""
    mock_torch = MagicMock()
    mock_snac = MagicMock()

    # torch.no_grad context manager
    mock_torch.no_grad.return_value.__enter__ = MagicMock(return_value=None)
    mock_torch.no_grad.return_value.__exit__ = MagicMock(return_value=False)

    # torch.tensor returns a MagicMock that supports .unsqueeze
    def fake_tensor(data: list[int], device: str = "cpu") -> MagicMock:
        """Create a fake tensor from a list."""
        t = MagicMock()
        t.unsqueeze.return_value = t
        return t

    mock_torch.tensor = fake_tensor

    # SNAC model returns a fake audio tensor with a numpy chain that produces real bytes
    model = MagicMock()
    audio_array = np.zeros(2400, dtype=np.float32)

    # Build a mock that mimics: audio.squeeze().cpu().numpy().clip(-1, 1) * 32767 -> .astype("int16")
    audio_tensor = MagicMock()
    audio_tensor.squeeze.return_value = audio_tensor
    audio_tensor.cpu.return_value = audio_tensor
    audio_tensor.numpy.return_value = audio_array
    model.decode.return_value = audio_tensor

    # .from_pretrained(...).to(device) must return the model mock
    model.to.return_value = model

    snac_class = MagicMock()
    snac_class.from_pretrained.return_value = model
    mock_snac.SNAC = snac_class

    monkeypatch.setattr("doppelganger.tts.snac_decoder.torch", mock_torch)
    monkeypatch.setattr("doppelganger.tts.snac_decoder.snac", mock_snac)

    return mock_snac, mock_torch


def test_not_loaded_raises() -> None:
    """Decoding without loading raises TTSModelNotLoadedError."""
    decoder = SNACDecoder()
    with pytest.raises(TTSModelNotLoadedError):
        decoder.decode([1, 2, 3], 24000)


def test_is_loaded_property() -> None:
    """is_loaded is False before loading."""
    decoder = SNACDecoder()
    assert decoder.is_loaded is False


def test_load_and_unload(mock_snac_modules: tuple[MagicMock, MagicMock]) -> None:
    """Loading and unloading toggle is_loaded."""
    decoder = SNACDecoder()
    decoder.load()
    assert decoder.is_loaded is True

    decoder.unload()
    assert decoder.is_loaded is False


def test_redistribute_codes_interleaves_per_frame() -> None:
    """_redistribute_codes splits tokens into 3 SNAC levels with per-frame interleaving."""
    decoder = SNACDecoder()
    # 14 tokens = 2 frames of 7
    # Use values that are offset by AUDIO_VOCAB_OFFSET (128266) + codebook offsets
    # so the de-offset result is predictable.
    offset = 128266
    tokens = [
        # Frame 0: positions 0-6
        offset + 10,  # pos 0: coarse, code=10
        offset + 4096 + 20,  # pos 1: mid, code=20
        offset + 8192 + 30,  # pos 2: fine, code=30
        offset + 12288 + 40,  # pos 3: fine, code=40
        offset + 16384 + 50,  # pos 4: mid, code=50
        offset + 20480 + 60,  # pos 5: fine, code=60
        offset + 24576 + 70,  # pos 6: fine, code=70
        # Frame 1: positions 0-6
        offset + 11,  # pos 0: coarse, code=11
        offset + 4096 + 21,  # pos 1: mid, code=21
        offset + 8192 + 31,  # pos 2: fine, code=31
        offset + 12288 + 41,  # pos 3: fine, code=41
        offset + 16384 + 51,  # pos 4: mid, code=51
        offset + 20480 + 61,  # pos 5: fine, code=61
        offset + 24576 + 71,  # pos 6: fine, code=71
    ]
    layer_0, layer_1, layer_2 = decoder._redistribute_codes(tokens)

    # Coarse: 1 per frame
    assert layer_0 == [10, 11]
    # Mid: 2 per frame, interleaved [pos1, pos4, pos1, pos4]
    assert layer_1 == [20, 50, 21, 51]
    # Fine: 4 per frame, interleaved [pos2, pos3, pos5, pos6, ...]
    assert layer_2 == [30, 40, 60, 70, 31, 41, 61, 71]


def test_redistribute_codes_empty_raises() -> None:
    """Empty token list raises TTSGenerationError."""
    decoder = SNACDecoder()
    with pytest.raises(TTSGenerationError, match="No audio tokens"):
        decoder._redistribute_codes([])


def test_decode_returns_wav_bytes(mock_snac_modules: tuple[MagicMock, MagicMock]) -> None:
    """decode returns bytes starting with RIFF WAV header."""
    decoder = SNACDecoder()
    decoder.load()

    # 7 tokens = one frame per codebook
    tokens = list(range(7))
    result = decoder.decode(tokens, 24000)

    assert isinstance(result, bytes)
    assert result[:4] == b"RIFF"
