from __future__ import annotations

from .base import FrozenModel
from .message import Message


class DomainEvent(FrozenModel):
    """A fact in the past."""


class MessageExtracted(DomainEvent):
    """A watched message was persisted."""

    message: Message
