"""Read-only endpoint exposing all application settings (secrets redacted)."""

import logging
from pathlib import Path

from fastapi import APIRouter, Request
from pydantic import BaseModel, SecretStr

from doppelganger.config import get_settings
from doppelganger.models.config import ConfigEntry, ConfigSection, FullConfigResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["config"])

_REDACTED = "********"
_PATH_FIELDS = {"voices_dir", "entrance_sound"}


def _serialize_section(name: str, model: BaseModel) -> ConfigSection:
    """Convert a pydantic model into a ConfigSection with redacted secrets."""
    entries: list[ConfigEntry] = []

    for field_name in model.model_fields:
        raw = getattr(model, field_name)

        if isinstance(raw, BaseModel):
            continue

        if isinstance(raw, SecretStr):
            display = _REDACTED
        elif isinstance(raw, list):
            display = ", ".join(str(v) for v in raw)
        elif field_name in _PATH_FIELDS and raw:
            display = str(Path(raw).resolve())
        else:
            display = str(raw)

        entries.append(ConfigEntry(key=field_name, value=display))

    return ConfigSection(name=name, entries=entries)


@router.get("", response_model=FullConfigResponse)
async def get_config(request: Request) -> FullConfigResponse:
    """Return all application settings grouped by section, with secrets redacted."""
    settings = get_settings()

    sections = [
        _serialize_section("General", settings),
        _serialize_section("Database", settings.database),
        _serialize_section("Discord", settings.discord),
        _serialize_section("Chatterbox", settings.chatterbox),
        _serialize_section("Orpheus", settings.orpheus),
    ]

    return FullConfigResponse(sections=sections)
