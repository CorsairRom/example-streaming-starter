from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.api_keys import ApiKeyService
from app.application.stream_events import StreamEventController
from app.settings import Settings


@dataclass(slots=True)
class Container:
    """Composition root: every dependency the HTTP layer needs, wired once."""

    settings: Settings
    engine: Engine
    session_factory: sessionmaker[Session]
    api_keys: ApiKeyService
    stream_events: StreamEventController
