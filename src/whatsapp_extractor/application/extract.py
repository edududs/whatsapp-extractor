from __future__ import annotations

from typing import TYPE_CHECKING

from whatsapp_extractor.domain import MessageExtracted

if TYPE_CHECKING:
    from .ports import EventPublisher, MessageFilter, MessageSource, MessageWriter


async def extract(
    source: MessageSource,
    accepts: MessageFilter,
    writer: MessageWriter,
    publisher: EventPublisher,
) -> None:
    """Persist every accepted message, then announce it. Store errors stop the extraction."""
    async for message in source.messages():
        if not accepts(message):
            continue
        await writer.save(message)
        await publisher.publish(MessageExtracted(message=message))
