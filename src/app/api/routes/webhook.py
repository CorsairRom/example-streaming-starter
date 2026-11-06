from __future__ import annotations

import datetime as dt
from datetime import UTC
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.deps import get_container, require_api_key
from app.container import Container
from app.domain.entities import ApiKeyRecord, StreamEvent, StreamState

router = APIRouter(prefix="/webhooks", tags=["qforest webhook"])


class StreamEventBody(BaseModel):
    """The payload documented in `requerimiento-integracion-streaming-cconecta`.

    Unknown fields are ignored on purpose: if QForest adds a field later the
    receiver keeps working instead of rejecting valid events.
    """

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    camera_device_id: str = Field(min_length=1, max_length=64, examples=["CLA58"])
    datetime: dt.datetime = Field(examples=["2026-10-27T15:32:24.935000+00:00"])
    url: str = Field(examples=["wss://hls.media.qforest.online/qforest/CLA58"])
    electromagnetic_spectrum: str = Field(default="combined", min_length=1, max_length=64)
    state: StreamState = Field(examples=["LIVE"])

    @field_validator("datetime")
    @classmethod
    def require_timezone(cls, value: dt.datetime) -> dt.datetime:
        if value.tzinfo is None:
            msg = "datetime must include a timezone offset (UTC is expected)."
            raise ValueError(msg)
        return value.astimezone(UTC)

    @field_validator("url")
    @classmethod
    def require_wss(cls, value: str) -> str:
        if not value.startswith("wss://") or len(value) <= len("wss://"):
            msg = "url must be a WebSocket URL starting with wss://"
            raise ValueError(msg)
        return value

    @field_validator("state", mode="before")
    @classmethod
    def normalize_state(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value


@router.post(
    "/qforest/streams",
    summary="Receive one QForest stream lifecycle event",
    status_code=200,
    responses={
        200: {"description": "Event accepted."},
        401: {"description": "Missing or invalid API key."},
        422: {"description": "Payload does not match the contract."},
    },
)
def receive_stream_event(
    payload: StreamEventBody,
    _: Annotated[ApiKeyRecord, Depends(require_api_key)],
    container: Annotated[Container, Depends(get_container)],
) -> dict[str, str]:
    container.stream_events.receive(
        StreamEvent(
            camera_device_id=payload.camera_device_id,
            occurred_at=payload.datetime,
            url=payload.url,
            electromagnetic_spectrum=payload.electromagnetic_spectrum,
            state=payload.state,
        )
    )
    return {"status": "accepted"}
