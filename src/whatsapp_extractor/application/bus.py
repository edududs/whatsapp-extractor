from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from whatsapp_extractor.domain import DomainEvent

if TYPE_CHECKING:
    from .ports import EventHandler

log = logging.getLogger(__name__)


class EventBus:
    """In-process and ordered. Handlers are isolated: a failure is logged, never propagated."""

    def __init__(self) -> None:
        self._dispatchers: list[EventHandler[DomainEvent]] = []

    def subscribe[E: DomainEvent](self, event_type: type[E], handler: EventHandler[E]) -> None:
        """Subscribing to a base type also receives its subtypes."""

        async def dispatch(event: DomainEvent) -> None:
            if not isinstance(event, event_type):
                return
            try:
                await handler(event)
            except Exception:
                log.exception("handler %r failed on %s", handler, type(event).__name__)

        self._dispatchers.append(dispatch)

    async def publish(self, event: DomainEvent) -> None:
        for dispatch in self._dispatchers:
            await dispatch(event)
