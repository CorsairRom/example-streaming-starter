from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_container
from app.container import Container

router = APIRouter(tags=["health"])


@router.get("/health", summary="Service health and version")
def health(container: Annotated[Container, Depends(get_container)]) -> dict[str, str]:
    settings = container.settings
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "env": settings.env,
    }
