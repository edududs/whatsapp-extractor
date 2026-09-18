"""Example-based builders: one valid message, readable at a glance."""

from __future__ import annotations

from datetime import UTC, datetime

from whatsapp_extractor.domain import (
    Chat,
    ChatKind,
    Content,
    Jid,
    Message,
    MessageKind,
    Sender,
)

GROUP = Jid(user="120363000000000001", server="g.us")
ALICE = Jid(user="5511900000001", server="s.whatsapp.net")


def make_message(
    message_id: str = "msg-1",
    *,
    chat: Jid = GROUP,
    sender: Jid = ALICE,
    text: str = "Oi",
) -> Message:
    return Message(
        id=message_id,
        timestamp=datetime(2026, 9, 17, 18, 0, tzinfo=UTC),
        kind=MessageKind.TEXT,
        from_me=False,
        chat=Chat(jid=chat, kind=ChatKind.of(chat)),
        sender=Sender(jid=sender, phone=sender.phone, lid=sender.lid, pushname="Alice"),
        content=Content(text=text),
    )
