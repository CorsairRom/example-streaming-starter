from __future__ import annotations

import re

from fastapi.testclient import TestClient

LOGIN = "/admin/login"


def _csrf_from(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, "csrf token not found in form"
    return match.group(1)


def _login(client: TestClient) -> str:
    page = client.get(LOGIN)
    token = _csrf_from(page.text)
    response = client.post(
        LOGIN,
        data={"username": "admin", "password": "super-secret", "csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 303
    dashboard = client.get("/admin")
    return _csrf_from(dashboard.text)


def test_admin_requires_login(client: TestClient) -> None:
    response = client.get("/admin", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].endswith(LOGIN)


def test_login_with_wrong_password_fails(client: TestClient) -> None:
    page = client.get(LOGIN)
    token = _csrf_from(page.text)

    response = client.post(
        LOGIN,
        data={"username": "admin", "password": "wrong", "csrf_token": token},
    )

    assert response.status_code == 401


def test_login_and_create_key(client: TestClient) -> None:
    csrf = _login(client)

    response = client.post("/admin/keys", data={"name": "c-conecta-prod", "csrf_token": csrf})

    assert response.status_code == 200
    assert "cck_" in response.text
    assert "c-conecta-prod" in response.text


def test_create_key_requires_csrf(client: TestClient) -> None:
    _login(client)

    response = client.post("/admin/keys", data={"name": "no-csrf"})

    assert response.status_code == 403


def test_created_key_works_against_the_webhook(
    client: TestClient, payload: dict[str, object]
) -> None:
    csrf = _login(client)
    page = client.post("/admin/keys", data={"name": "e2e", "csrf_token": csrf})
    key = re.search(r"(cck_[A-Za-z0-9_]+)", page.text)
    assert key is not None

    response = client.post(
        "/webhooks/streams",
        json=payload,
        headers={"X-API-Key": key.group(1)},
    )

    assert response.status_code == 200


def test_revoke_from_panel(client: TestClient, app) -> None:
    csrf = _login(client)
    response = client.post("/admin/keys", data={"name": "revocable", "csrf_token": csrf})
    assert "cck_" in response.text

    record = app.state.container.api_keys.list_all()[0]
    revoked = client.post(f"/admin/keys/{record.id}/revoke", data={"csrf_token": csrf})

    assert revoked.status_code == 200
    assert app.state.container.api_keys.list_all()[0].revoked_at is not None
