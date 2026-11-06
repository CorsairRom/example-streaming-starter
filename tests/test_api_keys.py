from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.infrastructure.models import ApiKeyModel

WEBHOOK = "/webhooks/qforest/streams"


def test_key_is_not_stored_in_plaintext(app, api_key: str) -> None:
    container = app.state.container

    with container.session_factory() as session:
        stored = session.execute(select(ApiKeyModel)).scalars().all()

    assert len(stored) == 1
    assert stored[0].key_hash != api_key
    assert api_key not in stored[0].key_hash
    assert stored[0].salt


def test_revoked_key_stops_working(
    client: TestClient,
    app,
    payload: dict[str, object],
) -> None:
    record, plaintext = app.state.container.api_keys.create(name="to-revoke")
    assert client.post(WEBHOOK, json=payload, headers={"X-API-Key": plaintext}).status_code == 200

    app.state.container.api_keys.revoke(record.id)

    response = client.post(WEBHOOK, json=payload, headers={"X-API-Key": plaintext})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "STREAM_API_KEY_INVALID"


def test_rotation_invalidates_the_previous_key(
    client: TestClient,
    app,
    payload: dict[str, object],
) -> None:
    record, old_key = app.state.container.api_keys.create(name="rotating")

    rotated, new_key = app.state.container.api_keys.rotate(record.id)

    assert rotated.id == record.id
    assert new_key != old_key
    assert client.post(WEBHOOK, json=payload, headers={"X-API-Key": old_key}).status_code == 401
    assert client.post(WEBHOOK, json=payload, headers={"X-API-Key": new_key}).status_code == 200


def test_last_used_at_is_recorded(app, api_key: str, payload: dict[str, object], client) -> None:
    client.post(WEBHOOK, json=payload, headers={"X-API-Key": api_key})

    records = app.state.container.api_keys.list_all()
    assert records[0].last_used_at is not None
