from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.domain.errors import AppError

WEBHOOK_PATH_PREFIX = "/webhooks/"


def _error_body(
    code: str, message: str, details: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    body: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return body


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.code, exc.message, exc.details),
    )


def _missing_header_code(exc: RequestValidationError) -> str | None:
    for error in exc.errors():
        if error.get("type") == "missing" and "header" in error.get("loc", ()):
            return "STREAM_API_KEY_MISSING"
    return None


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    missing_header = _missing_header_code(exc)
    if missing_header:
        return JSONResponse(
            status_code=401,
            content=_error_body(missing_header, "The X-API-Key header is required."),
        )

    code = (
        "STREAM_PAYLOAD_INVALID"
        if request.url.path.startswith(WEBHOOK_PATH_PREFIX)
        else "VALIDATION_ERROR"
    )
    details = [
        {
            "loc": list(error.get("loc", [])),
            "msg": error.get("msg", ""),
            "type": error.get("type", ""),
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=_error_body(code, "The request body is invalid.", details),
    )
