from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from whatsapp_extractor.domain import Message


class InMemoryMessageStore:
    def __init__(self) -> None:
        self._messages: dict[str, Message] = {}

    async def save(self, message: Message) -> None:
        self._messages[message.id] = message

    async def load(self, message_id: str) -> Message | None:
        return self._messages.get(message_id)
