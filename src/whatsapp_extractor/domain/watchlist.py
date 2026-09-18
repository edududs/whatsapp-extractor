from __future__ import annotations

from typing import TYPE_CHECKING

from .base import FrozenModel

if TYPE_CHECKING:
    from .message import Message


class Watchlist(FrozenModel):
    """Which messages to extract: any watched chat OR any watched sender. Empty watches all."""

    chats: frozenset[str] = frozenset()
    """Chat JIDs (`123@g.us`) or, for direct chats, the counterpart phone."""
    senders: frozenset[str] = frozenset()
    """Sender JIDs, phones or LIDs."""

    def matches(self, message: Message) -> bool:
        if not self.chats and not self.senders:
            return True
        return not (
            self.chats.isdisjoint(message.chat.identities)
            and self.senders.isdisjoint(message.sender.identities)
        )
