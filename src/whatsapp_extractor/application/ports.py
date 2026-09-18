from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Protocol

from whatsapp_extractor.domain import DomainEvent, Message

type MessageFilter = Callable[[Message], bool]
type EventHandler[E: DomainEvent] = Callable[[E], Awaitable[None]]


class MessageSource(Protocol):
    def messages(self) -> AsyncIterator[Message]:
        """Yield inbound messages until the connection ends. Connection errors propagate."""
        ...


class MessageWriter(Protocol):
    """What the extraction needs: somewhere to put each message."""

    async def save(self, message: Message) -> None:
        """Create or replace by message id. I/O errors propagate."""


class MessageStore(MessageWriter, Protocol):
    """A writer that also gives messages back, for the projects that read the archive."""

    async def load(self, message_id: str) -> Message | None:
        """Missing returns None."""


class EventPublisher(Protocol):
    async def publish(self, event: DomainEvent) -> None: ...
