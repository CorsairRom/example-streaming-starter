"""The server must take HOST and PORT from the configuration, not from the Makefile."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

import run
from app.settings import get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _capture(monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> dict[str, object]:
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        run.uvicorn,
        "run",
        lambda target, **kwargs: captured.update(kwargs, target=target),
    )
    monkeypatch.setattr(sys, "argv", argv)
    run.main()
    return captured


def test_run_uses_host_and_port_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOST", "127.0.0.2")
    monkeypatch.setenv("PORT", "8123")

    captured = _capture(monkeypatch, ["run.py"])

    assert captured["target"] == "app.main:app"
    assert captured["host"] == "127.0.0.2"
    assert captured["port"] == 8123
    assert captured["reload"] is False


def test_run_enables_reload_with_the_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PORT", "8124")

    captured = _capture(monkeypatch, ["run.py", "--reload"])

    assert captured["reload"] is True


def test_makefile_does_not_hardcode_a_port() -> None:
    """Regression: `make run` used to pass `--port 8000`, shadowing `.env`."""
    makefile = Path("Makefile").read_text()

    assert "uv run python src/run.py" in makefile
    assert "--port" not in makefile
    assert "--host" not in makefile
