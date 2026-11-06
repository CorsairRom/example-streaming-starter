from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from app.api.error_handlers import app_error_handler, validation_error_handler
from app.api.routes import admin, health, webhook
from app.application.api_keys import ApiKeyService
from app.application.stream_events import StreamEventController
from app.container import Container
from app.domain.errors import AppError
from app.infrastructure.db import build_engine, build_session_factory, create_schema
from app.infrastructure.repositories import SqlAlchemyApiKeyRepository
from app.settings import Settings, get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

SESSION_COOKIE = "cconecta_admin"
SESSION_MAX_AGE_SECONDS = 8 * 60 * 60


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application. Tests call this with their own settings."""
    settings = settings or get_settings()

    engine = build_engine(settings)
    create_schema(engine)
    session_factory = build_session_factory(engine)

    container = Container(
        settings=settings,
        engine=engine,
        session_factory=session_factory,
        api_keys=ApiKeyService(SqlAlchemyApiKeyRepository(session_factory)),
        stream_events=StreamEventController(),
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        engine.dispose()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Receptor mínimo de eventos de streaming (LIVE / DEFERRED) enviados por QForest. "
            "Incluye panel de administración de API keys."
        ),
        lifespan=lifespan,
    )
    app.state.container = container

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        session_cookie=SESSION_COOKIE,
        max_age=SESSION_MAX_AGE_SECONDS,
        same_site="strict",
        https_only=settings.session_https_only,
    )

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)

    app.include_router(health.router)
    app.include_router(webhook.router)
    app.include_router(admin.router)

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse("/admin", status_code=307)

    return app


app = create_app()
