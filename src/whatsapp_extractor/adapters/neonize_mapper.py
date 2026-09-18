"""Anti-corruption layer: every neonize/protobuf wire detail stops here."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from neonize.utils.jid import build_jid
from neonize.utils.message import extract_text

from whatsapp_extractor.domain import (
    Chat,
    ChatKind,
    Content,
    Jid,
    Media,
    MediaKind,
    Message,
    MessageKind,
    Sender,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from neonize.proto.Neonize_pb2 import JID, ContactInfo
    from neonize.proto.Neonize_pb2 import Message as MessageEv
    from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import Message as WaMessage

_KEY_EXCHANGE_FIELDS = {"senderKeyDistributionMessage", "messageContextInfo"}


def is_key_exchange_only(event: MessageEv) -> bool:
    """Whether the event carries no message, only encryption plumbing.

    whatsmeow dispatches one event per encrypted node of a stanza. In groups and status a
    stanza may bring two: the sender key, then the content. Same id, twice.
    """
    return {field.name for field, _ in _body(event).ListFields()} <= _KEY_EXCHANGE_FIELDS


def to_message(event: MessageEv) -> Message:
    """Raise `pydantic.ValidationError` when the event cannot become a valid message."""
    info = event.Info
    source = info.MessageSource
    chat = _jid(source.Chat)
    sender = _jid(source.Sender)
    sender_alt = _optional_jid(source.SenderAlt)
    recipient_alt = _optional_jid(source.RecipientAlt)
    kind = ChatKind.of(chat)
    body = _body(event)
    # Outgoing: the counterpart is the recipient. Incoming: it is the sender.
    counterparts = (recipient_alt, chat) if source.IsFromMe else (sender_alt, sender, chat)
    return Message(
        id=info.ID,
        timestamp=datetime.fromtimestamp(info.Timestamp / 1000, tz=UTC),
        kind=MessageKind(info.Type),
        from_me=source.IsFromMe,
        chat=Chat(
            jid=chat,
            kind=kind,
            counterpart_phone=_first(_phones(counterparts)) if kind is ChatKind.DIRECT else None,
        ),
        sender=Sender(
            jid=sender,
            lid=_first(jid.lid for jid in (sender, sender_alt) if jid),
            phone=_first(_phones((sender, sender_alt))),
            pushname=info.Pushname,
        ),
        recipient=recipient_alt,
        content=Content(text=extract_text(body), media=_media(body)),
        is_ephemeral=event.IsEphemeral,
        is_view_once=event.IsViewOnce or event.IsViewOnceV2 or event.IsViewOnceV2Extension,
        is_edit=event.IsEdit,
    )


def contact_jids(chat: Chat) -> list[JID]:
    """Where the contact of a direct chat may be stored: by phone first, then by chat address."""
    phone = [build_jid(chat.counterpart_phone)] if chat.counterpart_phone else []
    return [*phone, build_jid(chat.jid.user, chat.jid.server)]


def contact_name(contact: ContactInfo) -> str | None:
    """The address book name wins over the names people give themselves."""
    return contact.FullName or contact.BusinessName or contact.PushName or None


def _body(event: MessageEv) -> WaMessage:
    # The neonize stubs import `waE2E` by a path that does not resolve, hiding this type.
    return cast("WaMessage", event.Message)  # pyright: ignore[reportUnknownMemberType]


def _jid(raw: JID) -> Jid:
    return Jid(user=raw.User, server=raw.Server)


def _optional_jid(raw: JID) -> Jid | None:
    if raw.IsEmpty or not (raw.User or raw.Server):
        return None
    return _jid(raw)


def _phones(jids: Iterable[Jid | None]) -> Iterable[str | None]:
    return (jid.phone for jid in jids if jid)


def _first(values: Iterable[str | None]) -> str | None:
    return next(filter(None, values), None)


def _media(message: WaMessage) -> Media | None:
    """Proto3 zero values ("" and 0) mean absent, hence the `or None`."""
    if message.HasField("imageMessage"):
        image = message.imageMessage
        return Media(
            kind=MediaKind.IMAGE,
            mimetype=image.mimetype,
            caption=image.caption or None,
            width=image.width or None,
            height=image.height or None,
            file_length=image.fileLength or None,
        )
    if message.HasField("videoMessage"):
        video = message.videoMessage
        return Media(
            kind=MediaKind.VIDEO,
            mimetype=video.mimetype,
            caption=video.caption or None,
            duration_seconds=video.seconds or None,
            width=video.width or None,
            height=video.height or None,
            file_length=video.fileLength or None,
        )
    if message.HasField("audioMessage"):
        audio = message.audioMessage
        return Media(
            kind=MediaKind.AUDIO,
            mimetype=audio.mimetype,
            duration_seconds=audio.seconds or None,
            file_length=audio.fileLength or None,
            is_voice_note=audio.PTT,
        )
    if message.HasField("documentMessage"):
        document = message.documentMessage
        return Media(
            kind=MediaKind.DOCUMENT,
            mimetype=document.mimetype,
            caption=document.caption or None,
            file_length=document.fileLength or None,
            file_name=document.fileName or document.title or None,
        )
    if message.HasField("stickerMessage"):
        sticker = message.stickerMessage
        return Media(
            kind=MediaKind.STICKER,
            mimetype=sticker.mimetype,
            width=sticker.width or None,
            height=sticker.height or None,
            file_length=sticker.fileLength or None,
        )
    return None
