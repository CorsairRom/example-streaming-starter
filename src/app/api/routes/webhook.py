from __future__ import annotations

import datetime as dt
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.api.deps import get_container, require_api_key
from app.container import Container
from app.domain.entities import ApiKeyRecord, StreamEvent, StreamState
from app.domain.errors import StreamPayloadInvalidError

router = APIRouter(prefix="/webhooks", tags=["streams"])


class StreamEventBody(BaseModel):
    """The payload agreed for a stream lifecycle event.

    Unknown fields are ignored on purpose: if the sender adds a field later the
    receiver keeps working instead of rejecting valid events.
    """

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    camera_device_id: str = Field(min_length=1, max_length=64, examples=["CLA58"])
    datetime: dt.datetime = Field(examples=["2026-10-27T15:32:24.935000+00:00"])
    url: str = Field(examples=["wss://media.example.com/live/CLA58"])
    electromagnetic_spectrum: str = Field(default="combined", min_length=1, max_length=64)
    state: StreamState = Field(examples=["LIVE"])

    @field_validator("datetime")
    @classmethod
    def require_timezone(cls, value: dt.datetime) -> dt.datetime:
        if value.tzinfo is None:
            msg = "datetime must include a timezone offset (UTC is expected)."
            raise ValueError(msg)
        return value.astimezone(dt.UTC)

    @field_validator("url")
    @classmethod
    def require_wss_with_host(cls, value: str) -> str:
        if not value.startswith("wss://"):
            msg = "url must be a WebSocket URL starting with wss://"
            raise ValueError(msg)
        host = value.removeprefix("wss://").split("/", 1)[0]
        if not host.strip() or any(char.isspace() for char in host):
            msg = "url must include a host after wss://"
            raise ValueError(msg)
        return value

    @field_validator("state", mode="before")
    @classmethod
    def normalize_state(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value


def _validation_details(exc: ValidationError) -> list[dict[str, Any]]:
    return [
        {
            "loc": ["body", *error.get("loc", [])],
            "msg": error.get("msg", ""),
            "type": error.get("type", ""),
        }
        for error in exc.errors()
    ]


def _parse_event(raw_body: bytes) -> StreamEventBody:
    """Parse the body inside the handler so authentication is resolved first.

    FastAPI parses a declared body parameter before solving dependencies, which
    would let an unauthenticated request with malformed JSON reach validation.
    """
    try:
        return StreamEventBody.model_validate_json(raw_body)
    except ValidationError as exc:
        raise StreamPayloadInvalidError(details=_validation_details(exc)) from exc


@router.post(
    "/streams",
    summary="Receive one stream lifecycle event",
    status_code=200,
    responses={
        200: {"description": "Event accepted."},
        401: {"description": "Missing or invalid API key."},
        422: {"description": "Payload does not match the contract."},
    },
)
async def receive_stream_event(
    request: Request,
    api_key: Annotated[ApiKeyRecord, Depends(require_api_key)],
    container: Annotated[Container, Depends(get_container)],
) -> dict[str, str]:
    payload = _parse_event(await request.body())

    container.stream_events.receive(
        StreamEvent(
            camera_device_id=payload.camera_device_id,
            occurred_at=payload.datetime,
            url=payload.url,
            electromagnetic_spectrum=payload.electromagnetic_spectrum,
            state=payload.state,
        )
    )
    container.api_keys.mark_used(api_key.id)
    return {"status": "accepted"}
