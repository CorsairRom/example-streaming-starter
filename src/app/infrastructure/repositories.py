from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.domain.entities import ApiKeyRecord, StoredSecret
from app.domain.errors import ApiKeyAlreadyRevokedError, ApiKeyNotFoundError
from app.infrastructure.models import ApiKeyModel


def utc_now() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _to_record(row: ApiKeyModel) -> ApiKeyRecord:
    return ApiKeyRecord(
        id=row.id,
        name=row.name,
        prefix=row.prefix,
        created_at=_as_utc(row.created_at) or utc_now(),
        last_used_at=_as_utc(row.last_used_at),
        revoked_at=_as_utc(row.revoked_at),
    )


class SqlAlchemyApiKeyRepository:
    """SQLAlchemy implementation of `ApiKeyRepository`."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def add(self, *, name: str, prefix: str, key_hash: str, salt: str) -> ApiKeyRecord:
        with self._session_factory() as session:
            row = ApiKeyModel(
                name=name,
                prefix=prefix,
                key_hash=key_hash,
                salt=salt,
                created_at=utc_now(),
            )
            session.add(row)
            session.commit()
            return _to_record(row)

    def list_all(self) -> list[ApiKeyRecord]:
        with self._session_factory() as session:
            rows = session.execute(select(ApiKeyModel).order_by(ApiKeyModel.id)).scalars().all()
            return [_to_record(row) for row in rows]

    def get(self, key_id: int) -> ApiKeyRecord | None:
        with self._session_factory() as session:
            row = session.get(ApiKeyModel, key_id)
            return _to_record(row) if row else None

    def find_by_prefix(self, prefix: str) -> StoredSecret | None:
        with self._session_factory() as session:
            row = session.execute(
                select(ApiKeyModel).where(ApiKeyModel.prefix == prefix)
            ).scalar_one_or_none()
            if row is None:
                return None
            return StoredSecret(
                record=_to_record(row),
                key_hash=row.key_hash,
                salt=row.salt,
            )

    def touch(self, key_id: int) -> None:
        with self._session_factory() as session:
            row = session.get(ApiKeyModel, key_id)
            if row is None:
                return
            row.last_used_at = utc_now()
            session.commit()

    def revoke(self, key_id: int) -> ApiKeyRecord:
        with self._session_factory() as session:
            row = session.get(ApiKeyModel, key_id)
            if row is None:
                raise ApiKeyNotFoundError()
            if row.revoked_at is not None:
                raise ApiKeyAlreadyRevokedError()
            row.revoked_at = utc_now()
            session.commit()
            return _to_record(row)

    def replace_secret(self, key_id: int, *, prefix: str, key_hash: str, salt: str) -> ApiKeyRecord:
        with self._session_factory() as session:
            row = session.get(ApiKeyModel, key_id)
            if row is None:
                raise ApiKeyNotFoundError()
            row.prefix = prefix
            row.key_hash = key_hash
            row.salt = salt
            row.last_used_at = None
            session.commit()
            return _to_record(row)
