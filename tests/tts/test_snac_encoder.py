"""Tests for the SNAC audio encoder with mocked snac, torch, and torchaudio modules."""

from unittest.mock import MagicMock

import pytest

from doppelganger.tts.exceptions import TTSModelNotLoadedError
from doppelganger.tts.snac_constants import AUDIO_VOCAB_OFFSET, CODEBOOK_OFFSETS
from doppelganger.tts.snac_decoder import SNACDecoder
from doppelganger.tts.snac_encoder import SNACEncoder


@pytest.fixture
def mock_encoder_modules(monkeypatch: pytest.MonkeyPatch) -> tuple[MagicMock, MagicMock, MagicMock]:
    """Mock snac, torch, and torchaudio modules at the module level."""
    mock_torch = MagicMock()
    mock_snac = MagicMock()
    mock_torchaudio = MagicMock()

    # torch.no_grad context manager
    mock_torch.no_grad.return_value.__enter__ = MagicMock(return_value=None)
    mock_torch.no_grad.return_value.__exit__ = MagicMock(return_value=False)

    # SNAC model
    model = MagicMock()
    model.to.return_value = model
    snac_class = MagicMock()
    snac_class.from_pretrained.return_value = model
    mock_snac.SNAC = snac_class

    monkeypatch.setattr("doppelganger.tts.snac_encoder.torch", mock_torch)
    monkeypatch.setattr("doppelganger.tts.snac_encoder.snac", mock_snac)
    monkeypatch.setattr("doppelganger.tts.snac_encoder.torchaudio", mock_torchaudio)

    return mock_snac, mock_torch, mock_torchaudio


def test_not_loaded_raises() -> None:
    """Encoding without loading raises TTSModelNotLoadedError."""
    encoder = SNACEncoder()
    with pytest.raises(TTSModelNotLoadedError):
        encoder.encode("test.wav")


def test_is_loaded_property() -> None:
    """is_loaded is False before loading."""
    encoder = SNACEncoder()
    assert encoder.is_loaded is False


def test_load_and_unload(mock_encoder_modules: tuple[MagicMock, MagicMock, MagicMock]) -> None:
    """Loading and unloading toggle is_loaded."""
    encoder = SNACEncoder()
    encoder.load()
    assert encoder.is_loaded is True

    encoder.unload()
    assert encoder.is_loaded is False


def _make_fake_codes(n_frames: int, base: int = 0) -> list[MagicMock]:
    """Build 3-level fake SNAC codes with known values.

    Level 0: N values starting at base
    Level 1: 2*N values starting at base + 100
    Level 2: 4*N values starting at base + 200
    """
    level_0 = MagicMock()
    level_0.shape = (1, n_frames)
    level_0.__getitem__ = lambda self, idx: self._row if idx == 0 else None
    row_0 = MagicMock()
    row_0_values = [base + i for i in range(n_frames)]
    row_0.__getitem__ = lambda self, idx: row_0_values[idx]
    level_0._row = row_0
    level_0.__getitem__ = lambda self, idx: row_0

    level_1 = MagicMock()
    level_1.shape = (1, 2 * n_frames)
    row_1 = MagicMock()
    row_1_values = [base + 100 + i for i in range(2 * n_frames)]
    row_1.__getitem__ = lambda self, idx: row_1_values[idx]
    level_1.__getitem__ = lambda self, idx: row_1

    level_2 = MagicMock()
    level_2.shape = (1, 4 * n_frames)
    row_2 = MagicMock()
    row_2_values = [base + 200 + i for i in range(4 * n_frames)]
    row_2.__getitem__ = lambda self, idx: row_2_values[idx]
    level_2.__getitem__ = lambda self, idx: row_2

    return [level_0, level_1, level_2]


def test_interleave_codes_single_frame() -> None:
    """Single frame (N=1) produces 7 tokens with correct offsets."""
    encoder = SNACEncoder()
    codes = _make_fake_codes(1, base=10)

    tokens = encoder._interleave_codes(codes)

    assert len(tokens) == 7
    # Frame 0: codes[0][0][0]=10,  codes[1][0][0]=110, codes[2][0][0]=210,
    #          codes[2][0][1]=211, codes[1][0][1]=111, codes[2][0][2]=212, codes[2][0][3]=213
    expected = [
        10 + AUDIO_VOCAB_OFFSET + CODEBOOK_OFFSETS[0],
        110 + AUDIO_VOCAB_OFFSET + CODEBOOK_OFFSETS[1],
        210 + AUDIO_VOCAB_OFFSET + CODEBOOK_OFFSETS[2],
        211 + AUDIO_VOCAB_OFFSET + CODEBOOK_OFFSETS[3],
        111 + AUDIO_VOCAB_OFFSET + CODEBOOK_OFFSETS[4],
        212 + AUDIO_VOCAB_OFFSET + CODEBOOK_OFFSETS[5],
        213 + AUDIO_VOCAB_OFFSET + CODEBOOK_OFFSETS[6],
    ]
    assert tokens == expected


def test_interleave_codes_multiple_frames() -> None:
    """Two frames produce 14 tokens in correct interleaved order."""
    encoder = SNACEncoder()
    codes = _make_fake_codes(2, base=0)
    # level_0=[0,1], level_1=[100,101,102,103], level_2=[200..207]

    tokens = encoder._interleave_codes(codes)
    assert len(tokens) == 14

    # Frame 0 (i=0): coarse[0]=0, mid[0]=100, fine[0]=200, fine[1]=201, mid[1]=101, fine[2]=202, fine[3]=203
    frame_0 = [
        0 + AUDIO_VOCAB_OFFSET + CODEBOOK_OFFSETS[0],
        100 + AUDIO_VOCAB_OFFSET + CODEBOOK_OFFSETS[1],
        200 + AUDIO_VOCAB_OFFSET + CODEBOOK_OFFSETS[2],
        201 + AUDIO_VOCAB_OFFSET + CODEBOOK_OFFSETS[3],
        101 + AUDIO_VOCAB_OFFSET + CODEBOOK_OFFSETS[4],
        202 + AUDIO_VOCAB_OFFSET + CODEBOOK_OFFSETS[5],
        203 + AUDIO_VOCAB_OFFSET + CODEBOOK_OFFSETS[6],
    ]

    # Frame 1 (i=1): coarse[1]=1, mid[2]=102, fine[4]=204, fine[5]=205, mid[3]=103, fine[6]=206, fine[7]=207
    frame_1 = [
        1 + AUDIO_VOCAB_OFFSET + CODEBOOK_OFFSETS[0],
        102 + AUDIO_VOCAB_OFFSET + CODEBOOK_OFFSETS[1],
        204 + AUDIO_VOCAB_OFFSET + CODEBOOK_OFFSETS[2],
        205 + AUDIO_VOCAB_OFFSET + CODEBOOK_OFFSETS[3],
        103 + AUDIO_VOCAB_OFFSET + CODEBOOK_OFFSETS[4],
        206 + AUDIO_VOCAB_OFFSET + CODEBOOK_OFFSETS[5],
        207 + AUDIO_VOCAB_OFFSET + CODEBOOK_OFFSETS[6],
    ]
    assert tokens == frame_0 + frame_1


def test_interleave_codes_empty() -> None:
    """Zero frames produce an empty list."""
    encoder = SNACEncoder()
    codes = _make_fake_codes(0)
    tokens = encoder._interleave_codes(codes)
    assert tokens == []


def test_encode_returns_token_ids(mock_encoder_modules: tuple[MagicMock, MagicMock, MagicMock]) -> None:
    """Full encode path returns token IDs from interleaved SNAC codes."""
    _, mock_torch, mock_torchaudio = mock_encoder_modules
    encoder = SNACEncoder()
    encoder.load()

    # Mock torchaudio.load to return mono audio at correct sample rate
    waveform = MagicMock()
    waveform.shape = (1, 24000)
    waveform.abs.return_value.max.return_value = 1.0
    waveform.mean.return_value = waveform
    waveform.unsqueeze.return_value.to.return_value = waveform
    waveform.__truediv__ = lambda self, other: self
    mock_torchaudio.load.return_value = (waveform, 24000)

    # Mock model.encode to return known codes
    codes = _make_fake_codes(1, base=5)
    encoder._model.encode.return_value = codes  # type: ignore[union-attr]
    tokens = encoder.encode("test.wav")

    assert len(tokens) == 7
    assert all(isinstance(t, int) for t in tokens)
    mock_torchaudio.load.assert_called_once_with("test.wav")


def test_encode_converts_stereo_to_mono(mock_encoder_modules: tuple[MagicMock, MagicMock, MagicMock]) -> None:
    """Stereo input is averaged to mono before encoding."""
    _, mock_torch, mock_torchaudio = mock_encoder_modules
    encoder = SNACEncoder()
    encoder.load()

    # Mock stereo waveform (2 channels)
    waveform = MagicMock()
    waveform.shape = (2, 24000)
    mono_waveform = MagicMock()
    mono_waveform.shape = (1, 24000)
    mono_waveform.abs.return_value.max.return_value = 1.0
    mono_waveform.unsqueeze.return_value.to.return_value = mono_waveform
    mono_waveform.__truediv__ = lambda self, other: self
    waveform.mean.return_value = mono_waveform
    mock_torchaudio.load.return_value = (waveform, 24000)

    codes = _make_fake_codes(1, base=0)
    encoder._model.encode.return_value = codes  # type: ignore[union-attr]
    encoder.encode("stereo.wav")
    waveform.mean.assert_called_once_with(dim=0, keepdim=True)


def test_round_trip_with_decoder() -> None:
    """Encoding then decoding recovers the original code values.

    Creates known 3-level codes, runs through encoder's _interleave_codes,
    strips AUDIO_VOCAB_OFFSET, then runs through decoder's _redistribute_codes
    to verify the codes match the original values.
    """
    encoder = SNACEncoder()
    decoder = SNACDecoder()

    n_frames = 3

    # Original code values (no offsets, no vocab shift)
    level_0_vals = [10, 20, 30]
    level_1_vals = [40, 50, 60, 70, 80, 90]  # 2 * n_frames
    level_2_vals = [100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200, 210]  # 4 * n_frames

    # Build mock codes for the encoder
    codes = _make_fake_codes(n_frames, base=0)
    # Override with our specific values
    row_0 = MagicMock()
    row_0.__getitem__ = lambda self, idx: level_0_vals[idx]
    codes[0].shape = (1, n_frames)
    codes[0].__getitem__ = lambda self, idx: row_0

    row_1 = MagicMock()
    row_1.__getitem__ = lambda self, idx: level_1_vals[idx]
    codes[1].shape = (1, 2 * n_frames)
    codes[1].__getitem__ = lambda self, idx: row_1

    row_2 = MagicMock()
    row_2.__getitem__ = lambda self, idx: level_2_vals[idx]
    codes[2].shape = (1, 4 * n_frames)
    codes[2].__getitem__ = lambda self, idx: row_2

    # Encode: interleave into flat token IDs
    token_ids = encoder._interleave_codes(codes)
    assert len(token_ids) == n_frames * 7

    # Decode: redistribute back to 3 SNAC levels
    layer_0, layer_1, layer_2 = decoder._redistribute_codes(token_ids)

    # With correct sequential indexing, encode then decode is a perfect round-trip:
    # the decoder recovers the original SNAC code values in temporal order.
    assert layer_0 == level_0_vals
    assert layer_1 == level_1_vals
    assert layer_2 == level_2_vals
