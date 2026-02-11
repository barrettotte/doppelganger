"""Response models for the read-only config endpoint."""

from pydantic import BaseModel


class ConfigEntry(BaseModel):
    """A single key-value config entry for display."""

    key: str
    value: str


class ConfigSection(BaseModel):
    """A named group of config entries."""

    name: str
    entries: list[ConfigEntry]


class FullConfigResponse(BaseModel):
    """Response model for the full read-only config dump."""

    sections: list[ConfigSection]
