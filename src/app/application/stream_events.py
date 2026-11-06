from __future__ import annotations

import logging

from app.domain.entities import StreamEvent

logger = logging.getLogger(__name__)


class StreamEventController:
    """Application entry point for one received stream event.

    Phase 1 only acknowledges the event. Persistence, deduplication and fan-out
    to downstream consumers live in phase 2 (see BACKLOG.md).
    """

    def receive(self, event: StreamEvent) -> str:
        logger.info(
            "stream event received camera_device_id=%s state=%s url=%s datetime=%s spectrum=%s",
            event.camera_device_id,
            event.state,
            event.url,
            event.occurred_at.isoformat(),
            event.electromagnetic_spectrum,
        )
        return "accepted"
