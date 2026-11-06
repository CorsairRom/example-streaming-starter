from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.models import Base
from app.settings import Settings

SQLITE_PREFIX = "sqlite+pysqlite:///"


def _ensure_sqlite_directory(database_url: str) -> None:
    if not database_url.startswith(SQLITE_PREFIX):
        return
    raw_path = database_url.removeprefix(SQLITE_PREFIX)
    if not raw_path or raw_path == ":memory:":
        return
    Path(raw_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


def build_engine(settings: Settings) -> Engine:
    """Create the SQLAlchemy engine, preparing the SQLite folder when needed."""
    _ensure_sqlite_directory(settings.database_url)
    return create_engine(settings.database_url, future=True)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def create_schema(engine: Engine) -> None:
    """Create missing tables. There is no migration tool yet; see BACKLOG.md."""
    Base.metadata.create_all(engine)
