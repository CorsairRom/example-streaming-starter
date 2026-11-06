from __future__ import annotations

from app.domain.entities import ApiKeyRecord
from app.domain.errors import (
    ApiKeyAlreadyRevokedError,
    ApiKeyNotFoundError,
    StreamApiKeyInvalidError,
    StreamApiKeyMissingError,
)
from app.domain.ports import ApiKeyRepository
from app.infrastructure.security import generate_key, hash_secret, split_key, verify_secret


class ApiKeyService:
    """Create, rotate, revoke and verify the API keys the operator hands to the sender."""

    def __init__(self, repository: ApiKeyRepository) -> None:
        self._repository = repository

    def create(self, name: str) -> tuple[ApiKeyRecord, str]:
        plaintext, prefix, secret = generate_key()
        key_hash, salt = hash_secret(secret)
        record = self._repository.add(name=name, prefix=prefix, key_hash=key_hash, salt=salt)
        return record, plaintext

    def rotate(self, key_id: int) -> tuple[ApiKeyRecord, str]:
        current = self._repository.get(key_id)
        if current is None:
            raise ApiKeyNotFoundError()
        if not current.is_active:
            raise ApiKeyAlreadyRevokedError()

        plaintext, prefix, secret = generate_key()
        key_hash, salt = hash_secret(secret)
        updated = self._repository.replace_secret(
            key_id, prefix=prefix, key_hash=key_hash, salt=salt
        )
        return updated, plaintext

    def revoke(self, key_id: int) -> ApiKeyRecord:
        current = self._repository.get(key_id)
        if current is None:
            raise ApiKeyNotFoundError()
        if not current.is_active:
            raise ApiKeyAlreadyRevokedError()
        return self._repository.revoke(key_id)

    def list_all(self) -> list[ApiKeyRecord]:
        return self._repository.list_all()

    def authenticate(self, raw_key: str | None) -> ApiKeyRecord:
        """Return the active record for `raw_key` or raise an `AppError`."""
        if not raw_key or not raw_key.strip():
            raise StreamApiKeyMissingError()

        parsed = split_key(raw_key)
        if parsed is None:
            raise StreamApiKeyInvalidError()
        prefix, secret = parsed

        stored = self._repository.find_by_prefix(prefix)
        if stored is None or not stored.record.is_active:
            raise StreamApiKeyInvalidError()
        if not verify_secret(secret, stored.salt, stored.key_hash):
            raise StreamApiKeyInvalidError()

        return stored.record

    def mark_used(self, key_id: int) -> None:
        """Record a successful use. Never called for a rejected request."""
        self._repository.touch(key_id)
