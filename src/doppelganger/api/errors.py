"""Structured JSON error handlers for the API."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

logger = logging.getLogger(__name__)


def _get_request_id(request: Request) -> str:
    """Extract request ID from request state, falling back to empty string."""
    return getattr(request.state, "request_id", "")


def register_error_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI app."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """Return structured JSON for HTTP errors."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "status_code": exc.status_code,
                    "message": exc.detail,
                    "request_id": _get_request_id(request),
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Return structured JSON for validation errors."""
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "status_code": 422,
                    "message": "Validation error",
                    "details": exc.errors(),
                    "request_id": _get_request_id(request),
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Return structured JSON for unhandled exceptions."""
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "status_code": 500,
                    "message": "Internal server error",
                    "request_id": _get_request_id(request),
                }
            },
        )
