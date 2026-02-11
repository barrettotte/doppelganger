"""Character management API endpoints."""

import logging
import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, UploadFile
from starlette.responses import Response

from doppelganger.db.queries.characters import (
    create_character as db_create_character,
)
from doppelganger.db.queries.characters import (
    delete_character as db_delete_character,
)
from doppelganger.db.queries.characters import (
    get_character as db_get_character,
)
from doppelganger.db.queries.characters import (
    list_characters as db_list_characters,
)
from doppelganger.models.tts import (
    CharacterListResponse,
    CharacterResponse,
)
from doppelganger.tts.audio_validation import AudioValidationError, validate_reference_audio

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/characters", tags=["characters"])


@router.get("", response_model=CharacterListResponse)
async def list_characters(request: Request) -> CharacterListResponse:
    """List all registered characters with their IDs."""
    engine = request.app.state.db_engine
    registry = request.app.state.voice_registry

    async with engine.connect() as conn:
        rows = await db_list_characters(conn)

    characters = []
    for r in rows:
        voice = registry.get_voice(r.name)
        engine_type = voice.engine.value if voice is not None else "chatterbox"
        characters.append(
            CharacterResponse(
                id=r.id,
                name=r.name,
                reference_audio_path=r.reference_audio_path,
                created_at=r.created_at,
                engine=engine_type,
            )
        )

    return CharacterListResponse(characters=characters, count=len(characters))


@router.post("", response_model=CharacterResponse, status_code=201)
async def create_character(request: Request, name: str, audio: UploadFile) -> CharacterResponse:
    """Create a new character with a reference audio file."""
    name = name.lower().strip()
    if not name or not all(c.isalnum() or c == "-" for c in name):
        raise HTTPException(status_code=422, detail="Name must match pattern ^[a-z0-9-]+$")

    registry = request.app.state.voice_registry
    if registry.get_voice(name) is not None:
        raise HTTPException(status_code=409, detail=f"Character '{name}' already exists")

    file_data = await audio.read()
    try:
        validate_reference_audio(file_data)
    except AudioValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    voices_dir = registry.voices_dir
    char_dir = voices_dir / name
    char_dir.mkdir(parents=True, exist_ok=True)
    ref_path = char_dir / "reference.wav"
    ref_path.write_bytes(file_data)

    engine = request.app.state.db_engine
    async with engine.begin() as conn:
        row = await db_create_character(conn, name, str(ref_path))

    registry.refresh()
    logger.info("Created character: %s", name)

    return CharacterResponse(
        id=row.id,
        name=row.name,
        reference_audio_path=row.reference_audio_path,
        created_at=row.created_at,
    )


@router.delete("/{character_id}", status_code=204)
async def delete_character(request: Request, character_id: int) -> Response:
    """Delete a character by ID."""
    engine = request.app.state.db_engine
    registry = request.app.state.voice_registry

    async with engine.begin() as conn:
        row = await db_get_character(conn, character_id)

        if row is None:
            raise HTTPException(status_code=404, detail="Character not found")

        ref_path = Path(row.reference_audio_path)
        char_dir = ref_path.parent

        await db_delete_character(conn, character_id)

    if char_dir.exists():
        shutil.rmtree(char_dir)

    registry.refresh()
    logger.info("Deleted character id=%d name=%s", character_id, row.name)

    return Response(status_code=204)
