from __future__ import annotations

from typing import Protocol

from app.domain.entities import ApiKeyRecord, StoredSecret


class ApiKeyRepository(Protocol):
    """Persistence boundary for API keys. The application layer only sees this."""

    def add(self, *, name: str, prefix: str, key_hash: str, salt: str) -> ApiKeyRecord: ...

    def list_all(self) -> list[ApiKeyRecord]: ...

    def get(self, key_id: int) -> ApiKeyRecord | None: ...

    def find_by_prefix(self, prefix: str) -> StoredSecret | None: ...

    def touch(self, key_id: int) -> None: ...

    def revoke(self, key_id: int) -> ApiKeyRecord: ...

    def replace_secret(
        self, key_id: int, *, prefix: str, key_hash: str, salt: str
    ) -> ApiKeyRecord: ...
