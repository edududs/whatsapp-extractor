from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from .base import FrozenModel
from .jid import ChatKind, Jid


class MessageKind(StrEnum):
    TEXT = "text"
    MEDIA = "media"
    REACTION = "reaction"
    POLL = "poll"
    UNKNOWN = "unknown"

    @classmethod
    def _missing_(cls, value: object) -> MessageKind:  # noqa: ARG003 — signature set by Enum
        return cls.UNKNOWN


class MediaKind(StrEnum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    STICKER = "sticker"


class Sender(FrozenModel):
    jid: Jid
    lid: str | None = None
    phone: str | None = None
    pushname: str = ""

    @property
    def identities(self) -> frozenset[str]:
        return frozenset(filter(None, (self.jid.value, self.lid, self.phone)))


class Chat(FrozenModel):
    jid: Jid
    kind: ChatKind
    counterpart_phone: str | None = None
    """Phone of the other party. Direct chats only."""
    name: str | None = None
    """How the account owner knows this chat, e.g. the contact name of the other party."""

    @property
    def identities(self) -> frozenset[str]:
        return frozenset(filter(None, (self.jid.value, self.counterpart_phone)))


class Media(FrozenModel):
    kind: MediaKind
    mimetype: str = ""
    caption: str | None = None
    duration_seconds: int | None = None
    width: int | None = None
    height: int | None = None
    file_length: int | None = None
    file_name: str | None = None
    is_voice_note: bool | None = None


class Content(FrozenModel):
    text: str = ""
    """Plain text, extended text, or the media caption."""
    media: Media | None = None


class Message(FrozenModel):
    id: str
    timestamp: datetime
    kind: MessageKind
    from_me: bool
    chat: Chat
    sender: Sender
    recipient: Jid | None = None
    """Alternate address (phone or LID) of the counterpart on outgoing messages."""
    content: Content
    is_ephemeral: bool = False
    is_view_once: bool = False
    is_edit: bool = False

    def with_chat_name(self, name: str | None) -> Message:
        return self.model_copy(update={"chat": self.chat.model_copy(update={"name": name})})
