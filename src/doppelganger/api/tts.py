"""TTS generation API endpoints."""

import asyncio
import logging
from collections.abc import AsyncIterator
from functools import partial

from fastapi import APIRouter, HTTPException, Request
from starlette.responses import Response, StreamingResponse

from doppelganger.models.schemas import TTSGenerateRequest
from doppelganger.tts.exceptions import (
    TTSEngineUnavailableError,
    TTSGenerationError,
    TTSModelNotLoadedError,
    TTSOutOfMemoryError,
    TTSVoiceNotFoundError,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tts", tags=["tts"])
_generation_lock = asyncio.Lock()
# Force download in Swagger UI - browser can't play audio inline
_WAV_HEADERS = {"Content-Disposition": "attachment; filename=output.wav"}


def _map_tts_error(e: Exception) -> HTTPException:
    """Map TTS exceptions to HTTP errors."""

    if isinstance(e, TTSVoiceNotFoundError):
        return HTTPException(status_code=404, detail=str(e))
    if isinstance(e, TTSOutOfMemoryError):
        return HTTPException(status_code=503, detail=str(e))
    if isinstance(e, TTSModelNotLoadedError):
        return HTTPException(status_code=503, detail=str(e))
    if isinstance(e, TTSEngineUnavailableError):
        return HTTPException(status_code=503, detail=str(e))
    if isinstance(e, TTSGenerationError):
        return HTTPException(status_code=500, detail=str(e))

    return HTTPException(status_code=500, detail="Unexpected TTS error")


@router.post("/generate")
async def generate_speech(request: Request, body: TTSGenerateRequest) -> Response:
    """Generate speech audio for the given text and character voice."""
    tts_service = request.app.state.tts_service
    cache = request.app.state.audio_cache

    cached = cache.get(body.character, body.text)
    if cached is not None:
        logger.debug("Cache hit for %s: %s", body.character, body.text[:30])
        return Response(content=cached, media_type="audio/wav", headers=_WAV_HEADERS)

    loop = asyncio.get_running_loop()
    async with _generation_lock:
        try:
            result = await loop.run_in_executor(
                executor=None,
                func=partial(tts_service.generate, body.character, body.text),
            )
        except Exception as e:
            raise _map_tts_error(e) from e

    cache.put(body.character, body.text, result.audio_bytes)
    return Response(content=result.audio_bytes, media_type="audio/wav", headers=_WAV_HEADERS)


@router.post("/stream")
async def stream_speech(request: Request, body: TTSGenerateRequest) -> StreamingResponse:
    """Stream speech audio chunks for the given text and character voice."""
    tts_service = request.app.state.tts_service
    queue: asyncio.Queue[bytes | None] = asyncio.Queue()

    # Producer-consumer pattern: _producer generates audio chunks in a thread
    # pool and pushes them into an asyncio.Queue; _stream yields from the
    # queue so StreamingResponse can send bytes as they become available.
    async def _producer() -> None:
        loop = asyncio.get_running_loop()
        try:
            chunks = await loop.run_in_executor(
                executor=None,
                func=partial(list, tts_service.generate_stream(body.character, body.text)),
            )
            for chunk in chunks:
                await queue.put(chunk.audio_bytes)

        except Exception as e:
            logger.error("Stream generation error: %s", e)
        finally:
            await queue.put(None)

    async def _stream() -> AsyncIterator[bytes]:
        task = asyncio.create_task(_producer())
        try:
            while True:
                data = await queue.get()
                if data is None:
                    break

                yield data
        finally:
            await task

    return StreamingResponse(_stream(), media_type="audio/wav")
