from __future__ import annotations

import hmac
import secrets
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from app.container import Container
from app.domain.errors import CsrfTokenInvalidError

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(prefix="/admin", tags=["admin"])


def _container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


def _ensure_csrf(request: Request) -> str:
    token = request.session.get("csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf"] = token
    return str(token)


def _check_csrf(request: Request, submitted: str) -> None:
    expected = request.session.get("csrf")
    if not expected or not hmac.compare_digest(str(expected), submitted or ""):
        raise CsrfTokenInvalidError()


def _is_admin(request: Request) -> bool:
    return bool(request.session.get("admin"))


def _login_redirect() -> RedirectResponse:
    return RedirectResponse("/admin/login", status_code=303)


def _page(request: Request, **extra: object) -> dict[str, object]:
    context: dict[str, object] = {
        "app_name": _container(request).settings.app_name,
        "app_version": _container(request).settings.app_version,
        "csrf_token": _ensure_csrf(request),
    }
    context.update(extra)
    return context


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> Response:
    if _is_admin(request):
        return RedirectResponse("/admin", status_code=303)
    return templates.TemplateResponse(request, "login.html", _page(request, error=None))


@router.post("/login")
def login(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    csrf_token: Annotated[str, Form()] = "",
) -> Response:
    _check_csrf(request, csrf_token)
    settings = _container(request).settings
    valid = hmac.compare_digest(username, settings.admin_username) and hmac.compare_digest(
        password, settings.admin_password
    )
    if not valid:
        return templates.TemplateResponse(
            request,
            "login.html",
            _page(request, error="Usuario o contraseña inválidos."),
            status_code=401,
        )

    request.session.clear()
    request.session["admin"] = True
    request.session["csrf"] = secrets.token_urlsafe(32)
    return RedirectResponse("/admin", status_code=303)


@router.post("/logout")
def logout(
    request: Request,
    csrf_token: Annotated[str, Form()] = "",
) -> Response:
    _check_csrf(request, csrf_token)
    request.session.clear()
    return _login_redirect()


@router.get("", response_class=HTMLResponse)
def dashboard(request: Request) -> Response:
    if not _is_admin(request):
        return _login_redirect()
    keys = _container(request).api_keys.list_all()
    return templates.TemplateResponse(request, "index.html", _page(request, keys=keys))


@router.post("/keys", response_class=HTMLResponse)
def create_key(
    request: Request,
    name: Annotated[str, Form()],
    csrf_token: Annotated[str, Form()] = "",
) -> Response:
    if not _is_admin(request):
        return _login_redirect()
    _check_csrf(request, csrf_token)
    clean_name = name.strip() or "sin nombre"
    _, plaintext = _container(request).api_keys.create(clean_name)
    return templates.TemplateResponse(
        request,
        "key_created.html",
        _page(request, api_key=plaintext, name=clean_name, action="creada"),
        headers={"Cache-Control": "no-store"},
    )


@router.post("/keys/{key_id}/rotate", response_class=HTMLResponse)
def rotate_key(
    request: Request,
    key_id: int,
    csrf_token: Annotated[str, Form()] = "",
) -> Response:
    if not _is_admin(request):
        return _login_redirect()
    _check_csrf(request, csrf_token)
    record, plaintext = _container(request).api_keys.rotate(key_id)
    return templates.TemplateResponse(
        request,
        "key_created.html",
        _page(request, api_key=plaintext, name=record.name, action="rotada"),
        headers={"Cache-Control": "no-store"},
    )


@router.post("/keys/{key_id}/revoke")
def revoke_key(
    request: Request,
    key_id: int,
    csrf_token: Annotated[str, Form()] = "",
) -> Response:
    if not _is_admin(request):
        return _login_redirect()
    _check_csrf(request, csrf_token)
    _container(request).api_keys.revoke(key_id)
    return RedirectResponse("/admin", status_code=303)
