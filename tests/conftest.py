from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        env="test",
        database_url=f"sqlite+pysqlite:///{tmp_path / 'test.db'}",
        admin_username="admin",
        admin_password="super-secret",
        session_secret="test-session-secret",
    )


@pytest.fixture
def app(settings: Settings):
    return create_app(settings)


@pytest.fixture
def client(app) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def api_key(app) -> str:
    """Create one active API key through the service layer and return the plaintext."""
    _, plaintext = app.state.container.api_keys.create(name="tests")
    return plaintext


@pytest.fixture
def payload() -> dict[str, object]:
    return {
        "camera_device_id": "CLA58",
        "datetime": "2026-10-27T15:32:24.935000+00:00",
        "url": "wss://hls.media.qforest.online/qforest/CLA58",
        "electromagnetic_spectrum": "combined",
        "state": "LIVE",
    }
