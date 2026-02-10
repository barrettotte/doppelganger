"""Tests for Pydantic schema text sanitization."""

import pytest
from pydantic import ValidationError

from doppelganger.models.schemas import TTSGenerateRequest, TTSRequestCreate


def test_strips_null_bytes() -> None:
    """Null bytes should be removed from text fields."""
    req = TTSGenerateRequest(character="test", text="hello\x00world")
    assert req.text == "helloworld"


def test_strips_escape_chars() -> None:
    """Escape and backspace characters should be removed."""
    req = TTSGenerateRequest(character="test", text="hello\x1bworld\x08!")
    assert req.text == "helloworld!"


def test_preserves_newlines_and_tabs() -> None:
    """Newlines, tabs, and carriage returns should be preserved."""
    req = TTSGenerateRequest(character="test", text="line1\nline2\ttab\r")
    assert "\n" in req.text
    assert "\t" in req.text
    assert "\r" in req.text


def test_preserves_normal_unicode() -> None:
    """Normal unicode text should pass through unchanged."""
    text = "Hello, world! Testing 123 - some unicode: cafe"
    req = TTSGenerateRequest(character="test", text=text)
    assert req.text == text


def test_empty_after_strip_raises() -> None:
    """Text that becomes empty after sanitization should raise ValidationError."""
    with pytest.raises(ValidationError, match="empty after sanitization"):
        TTSGenerateRequest(character="test", text="\x00\x01\x02")


def test_strips_c1_control_chars() -> None:
    """C1 control characters (0x7f-0x9f) should be removed."""
    req = TTSGenerateRequest(character="test", text="hello\x7fworld\x80!")
    assert req.text == "helloworld!"


def test_tts_request_create_sanitizes() -> None:
    """TTSRequestCreate should also sanitize text."""
    req = TTSRequestCreate(character="test", text="hello\x00world")
    assert req.text == "helloworld"


def test_tts_request_create_empty_raises() -> None:
    """TTSRequestCreate should reject text that is empty after sanitization."""
    with pytest.raises(ValidationError, match="empty after sanitization"):
        TTSRequestCreate(character="test", text="\x00\x01")
