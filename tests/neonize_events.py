"""Builders of neonize wire events, shaped like the ones observed in production."""

from __future__ import annotations

from neonize.proto.Neonize_pb2 import JID, MessageInfo, MessageSource
from neonize.proto.Neonize_pb2 import Message as MessageEv
from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import Message as WaMessage

EMPTY = JID(IsEmpty=True)
ME = JID(User="100000000000001", Server="lid")
MY_PHONE = JID(User="5511900000001", Server="s.whatsapp.net")
FRIEND = JID(User="100000000000002", Server="lid")
FRIEND_PHONE = JID(User="5511900000002", Server="s.whatsapp.net")
STATUS = JID(User="status", Server="broadcast")
GROUP = JID(User="120363000000000001", Server="g.us")


def event(  # noqa: PLR0913 — mirrors the flat wire envelope
    message_id: str = "3A0000000000000000A1",
    *,
    chat: JID,
    sender: JID,
    sender_alt: JID = EMPTY,
    recipient_alt: JID = EMPTY,
    from_me: bool = False,
    kind: str = "text",
    body: WaMessage | None = None,
    pushname: str = "Owner",
    timestamp_ms: int = 1789677560000,
) -> MessageEv:
    return MessageEv(
        Info=MessageInfo(
            MessageSource=MessageSource(
                Chat=chat,
                Sender=sender,
                IsFromMe=from_me,
                SenderAlt=sender_alt,
                RecipientAlt=recipient_alt,
            ),
            ID=message_id,
            Type=kind,
            Pushname=pushname,
            Timestamp=timestamp_ms,
        ),
        Message=body or WaMessage(conversation="Oi"),
    )
