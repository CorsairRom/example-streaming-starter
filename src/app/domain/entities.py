from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class StreamState(StrEnum):
    """Lifecycle state reported by QForest for a camera stream."""

    LIVE = "LIVE"
    DEFERRED = "DEFERRED"


@dataclass(frozen=True, slots=True)
class StreamEvent:
    """A stream lifecycle event exactly as QForest sends it."""

    camera_device_id: str
    occurred_at: datetime
    url: str
    electromagnetic_spectrum: str
    state: StreamState


@dataclass(frozen=True, slots=True)
class ApiKeyRecord:
    """An API key as stored by the service. It never holds the plaintext key."""

    id: int
    name: str
    prefix: str
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None


@dataclass(frozen=True, slots=True)
class StoredSecret:
    """Hash material kept in the database for one API key."""

    record: ApiKeyRecord
    key_hash: str
    salt: str
