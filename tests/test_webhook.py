from __future__ import annotations

from fastapi.testclient import TestClient

WEBHOOK = "/webhooks/streams"


def test_health_reports_version(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"].startswith("v")


def test_missing_api_key_is_rejected(client: TestClient, payload: dict[str, object]) -> None:
    response = client.post(WEBHOOK, json=payload)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "STREAM_API_KEY_MISSING"


def test_unknown_api_key_is_rejected(client: TestClient, payload: dict[str, object]) -> None:
    response = client.post(WEBHOOK, json=payload, headers={"X-API-Key": "cck_nope_nope"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "STREAM_API_KEY_INVALID"


def test_live_event_is_accepted(
    client: TestClient, payload: dict[str, object], api_key: str
) -> None:
    response = client.post(WEBHOOK, json=payload, headers={"X-API-Key": api_key})

    assert response.status_code == 200
    assert response.json() == {"status": "accepted"}


def test_state_is_case_insensitive(
    client: TestClient, payload: dict[str, object], api_key: str
) -> None:
    payload["state"] = "Live"

    response = client.post(WEBHOOK, json=payload, headers={"X-API-Key": api_key})

    assert response.status_code == 200


def test_deferred_event_is_accepted(
    client: TestClient, payload: dict[str, object], api_key: str
) -> None:
    payload["state"] = "deferred"

    response = client.post(WEBHOOK, json=payload, headers={"X-API-Key": api_key})

    assert response.status_code == 200


def test_non_wss_url_is_rejected(
    client: TestClient, payload: dict[str, object], api_key: str
) -> None:
    payload["url"] = "https://media.example.com/live/CLA58"

    response = client.post(WEBHOOK, json=payload, headers={"X-API-Key": api_key})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "STREAM_PAYLOAD_INVALID"


def test_naive_datetime_is_rejected(
    client: TestClient, payload: dict[str, object], api_key: str
) -> None:
    payload["datetime"] = "2026-10-27T15:32:24"

    response = client.post(WEBHOOK, json=payload, headers={"X-API-Key": api_key})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "STREAM_PAYLOAD_INVALID"


def test_unknown_state_is_rejected(
    client: TestClient, payload: dict[str, object], api_key: str
) -> None:
    payload["state"] = "PAUSED"

    response = client.post(WEBHOOK, json=payload, headers={"X-API-Key": api_key})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "STREAM_PAYLOAD_INVALID"


def test_extra_fields_are_ignored(
    client: TestClient, payload: dict[str, object], api_key: str
) -> None:
    payload["future_field"] = "whatever"

    response = client.post(WEBHOOK, json=payload, headers={"X-API-Key": api_key})

    assert response.status_code == 200


def test_api_key_is_required_before_payload_validation(client: TestClient) -> None:
    response = client.post(WEBHOOK, json={"garbage": True})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "STREAM_API_KEY_MISSING"


def test_openapi_docs_are_available(client: TestClient) -> None:
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200
