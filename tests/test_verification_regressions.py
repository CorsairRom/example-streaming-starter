"""Regression probes derived from odd/tasks/cconecta-streaming-starter.md (S1-S8).

These pin the behaviour that the independent verification exercised, including the
two defects it found: authentication must win over an unparseable body, and a
rejected request must not update `last_used_at`.
"""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.domain.entities import StreamState
from app.infrastructure.models import ApiKeyModel

WEBHOOK = "/webhooks/qforest/streams"
LOGIN = "/admin/login"
COOKIE = "cconecta_admin"
ADMIN_PASSWORD = "super-secret"  # tests/conftest.py
KEY_RE = re.compile(r"cck_[0-9a-f]{10}_[0-9a-f]{48}")


def _csrf(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, "csrf token not found"
    return match.group(1)


def _login(client: TestClient) -> str:
    token = _csrf(client.get(LOGIN).text)
    response = client.post(
        LOGIN,
        data={"username": "admin", "password": ADMIN_PASSWORD, "csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 303
    return _csrf(client.get("/admin").text)


def _rows(app) -> list[ApiKeyModel]:
    with app.state.container.session_factory() as session:
        return list(session.execute(select(ApiKeyModel).order_by(ApiKeyModel.id)).scalars())


def _db_path(app) -> Path:
    return Path(app.state.container.settings.database_url.split("///")[1])


def test_s1_pdf_payload_is_accepted(client, app, payload):
    payload["state"] = "Live"  # exactly as the PDF example
    _, key = app.state.container.api_keys.create(name="s1")
    response = client.post(WEBHOOK, json=payload, headers={"X-API-Key": key})
    assert (response.status_code, response.json()) == (200, {"status": "accepted"})


def test_s2_missing_header_wins_over_unparseable_json(client):
    response = client.post(
        WEBHOOK, content=b"not-json", headers={"Content-Type": "application/json"}
    )
    assert (response.status_code, response.json()["error"]["code"]) == (
        401,
        "STREAM_API_KEY_MISSING",
    )


def test_s2_invalid_key_wins_over_unparseable_json(client):
    response = client.post(
        WEBHOOK,
        content=b"not-json",
        headers={"Content-Type": "application/json", "X-API-Key": "garbage"},
    )
    assert (response.status_code, response.json()["error"]["code"]) == (
        401,
        "STREAM_API_KEY_INVALID",
    )


def test_s2_missing_header_wins_over_schema_errors(client):
    response = client.post(WEBHOOK, json={"garbage": True})
    assert (response.status_code, response.json()["error"]["code"]) == (
        401,
        "STREAM_API_KEY_MISSING",
    )


def test_s2_revoked_key_is_invalid(client, app, payload):
    record, key = app.state.container.api_keys.create(name="revoked")
    app.state.container.api_keys.revoke(record.id)
    response = client.post(WEBHOOK, json=payload, headers={"X-API-Key": key})
    assert (response.status_code, response.json()["error"]["code"]) == (
        401,
        "STREAM_API_KEY_INVALID",
    )


def test_s3_state_normalised_and_datetime_converted_to_utc(client, app, payload):
    captured = {}

    class Capture:
        def receive(self, event):
            captured["event"] = event
            return "accepted"

    app.state.container.stream_events = Capture()
    _, key = app.state.container.api_keys.create(name="s3")
    payload["state"] = " Live "
    payload["datetime"] = "2026-10-27T15:32:24.935000+05:30"
    assert client.post(WEBHOOK, json=payload, headers={"X-API-Key": key}).status_code == 200
    event = captured["event"]
    assert event.state is StreamState.LIVE
    assert event.occurred_at == datetime(2026, 10, 27, 10, 2, 24, 935000, tzinfo=UTC)


@pytest.mark.parametrize(
    "mutation",
    [
        {"url": "https://example.test/stream"},
        {"url": "wss://"},
        {"url": "wss:///no-host"},
        {"datetime": "2026-10-27T15:32:24"},
        {"state": "PAUSED"},
    ],
)
def test_s3_invalid_payload_is_422(client, app, payload, mutation):
    _, key = app.state.container.api_keys.create(name=f"s3-{abs(hash(str(mutation)))}")
    response = client.post(WEBHOOK, json={**payload, **mutation}, headers={"X-API-Key": key})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "STREAM_PAYLOAD_INVALID"
    assert response.json()["error"]["details"]


def test_s4_event_is_not_persisted(client, app, payload):
    _, key = app.state.container.api_keys.create(name="s4")
    with app.state.container.session_factory() as session:
        before = set(
            session.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).scalars()
        )
    assert client.post(WEBHOOK, json=payload, headers={"X-API-Key": key}).status_code == 200
    with app.state.container.session_factory() as session:
        after = set(
            session.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).scalars()
        )
    assert after == before
    assert not any("event" in table for table in after)


def test_s5_admin_requires_session_and_csrf(client, app):
    assert client.get("/admin", follow_redirects=False).status_code == 303
    _login(client)
    record, _ = app.state.container.api_keys.create(name="csrf")
    for path, form in [
        ("/admin/keys", {"name": "x"}),
        (f"/admin/keys/{record.id}/rotate", {}),
        (f"/admin/keys/{record.id}/revoke", {}),
        ("/admin/logout", {}),
    ]:
        for token in (None, "wrong"):
            data = dict(form)
            if token:
                data["csrf_token"] = token
            response = client.post(path, data=data, follow_redirects=False)
            assert (response.status_code, response.json()["error"]["code"]) == (
                403,
                "ADMIN_CSRF_TOKEN_INVALID",
            )


def test_s5_tampered_session_cookie_is_unauthenticated(client):
    _login(client)
    value = client.cookies.get(COOKIE)
    assert value
    client.cookies.set(COOKIE, value[:-1] + ("A" if value[-1] != "A" else "B"))
    assert client.get("/admin", follow_redirects=False).status_code == 303


def test_s5_rotation_and_revocation_from_panel(client, app, payload):
    csrf = _login(client)
    created = client.post("/admin/keys", data={"name": "life", "csrf_token": csrf})
    old_key = KEY_RE.search(created.text).group(0)
    record = _rows(app)[0]
    rotated = client.post(f"/admin/keys/{record.id}/rotate", data={"csrf_token": csrf})
    new_key = KEY_RE.search(rotated.text).group(0)
    assert new_key != old_key
    assert client.post(WEBHOOK, json=payload, headers={"X-API-Key": old_key}).status_code == 401
    assert client.post(WEBHOOK, json=payload, headers={"X-API-Key": new_key}).status_code == 200
    revoked = client.post(
        f"/admin/keys/{record.id}/revoke", data={"csrf_token": csrf}, follow_redirects=False
    )
    assert revoked.status_code == 303
    assert client.post(WEBHOOK, json=payload, headers={"X-API-Key": new_key}).status_code == 401


def test_s6_key_is_only_hashed_at_rest_and_shown_once(client, app):
    _, key = app.state.container.api_keys.create(name="s6")
    row = _rows(app)[0]
    assert key not in (row.prefix, row.key_hash, row.salt)
    raw = _db_path(app).read_bytes()
    assert key.encode() not in raw
    assert key.split("_")[2].encode() not in raw
    csrf = _login(client)
    created = client.post("/admin/keys", data={"name": "once", "csrf_token": csrf})
    shown = KEY_RE.search(created.text).group(0)
    assert created.headers.get("cache-control") == "no-store"
    assert shown not in client.get("/admin").text


def test_s7_health_reports_configured_version(client, app):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["version"] == app.state.container.settings.app_version


@pytest.mark.parametrize(
    "path",
    [
        "README.md",
        "ARCHITECTURE.md",
        "docs/modules/webhook-streams/README.md",
        "docs/error-codes-catalog.md",
        "BACKLOG.md",
    ],
)
def test_s8_required_docs_exist(path):
    assert Path(path).is_file()


def test_rejected_payload_does_not_touch_last_used_at(client, app, payload):
    _, key = app.state.container.api_keys.create(name="invariant")
    before_rows = [(r.id, r.revoked_at, r.last_used_at) for r in _rows(app)]
    before_hash = hashlib.sha256(_db_path(app).read_bytes()).hexdigest()
    response = client.post(
        WEBHOOK,
        json={**payload, "url": "https://example.test/stream"},
        headers={"X-API-Key": key},
    )
    assert response.status_code == 422
    assert [(r.id, r.revoked_at, r.last_used_at) for r in _rows(app)] == before_rows
    assert hashlib.sha256(_db_path(app).read_bytes()).hexdigest() == before_hash
