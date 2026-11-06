from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, Request

from app.application.api_keys import ApiKeyService
from app.container import Container
from app.domain.entities import ApiKeyRecord


def get_container(request: Request) -> Container:
    """Return the composition root built when the app started."""
    return request.app.state.container


def get_api_key_service(
    container: Annotated[Container, Depends(get_container)],
) -> ApiKeyService:
    return container.api_keys


def require_api_key(
    service: Annotated[ApiKeyService, Depends(get_api_key_service)],
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> ApiKeyRecord:
    """Validate the `X-API-Key` header. Raises 401 through `AppError`."""
    return service.authenticate(x_api_key)
