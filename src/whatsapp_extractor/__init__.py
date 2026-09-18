"""Reusable piece: extract watched WhatsApp messages into a store and announce them.

Compose it per project: a `MessageSource`, a `MessageFilter` (e.g. `Watchlist.matches`),
a `MessageStore` and an `EventBus` with the project's handlers. Adapters are imported
from their concrete modules under `whatsapp_extractor.adapters`.
"""

from .application import (
    EventBus,
    EventHandler,
    EventPublisher,
    MessageFilter,
    MessageSource,
    MessageStore,
    MessageWriter,
    extract,
)
from .domain import (
    Chat,
    ChatKind,
    Content,
    DomainEvent,
    Jid,
    Media,
    MediaKind,
    Message,
    MessageExtracted,
    MessageKind,
    Sender,
    Watchlist,
)

__all__ = [
    "Chat",
    "ChatKind",
    "Content",
    "DomainEvent",
    "EventBus",
    "EventHandler",
    "EventPublisher",
    "Jid",
    "Media",
    "MediaKind",
    "Message",
    "MessageExtracted",
    "MessageFilter",
    "MessageKind",
    "MessageSource",
    "MessageStore",
    "MessageWriter",
    "Sender",
    "Watchlist",
    "extract",
]
