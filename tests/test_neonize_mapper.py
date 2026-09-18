from __future__ import annotations

from datetime import UTC, datetime

import pytest
from hypothesis import given
from hypothesis import strategies as st
from neonize.proto.Neonize_pb2 import JID
from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import (
    AudioMessage,
    ExtendedTextMessage,
    ImageMessage,
    SenderKeyDistributionMessage,
    VideoMessage,
)
from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import Message as WaMessage
from neonize_events import EMPTY, FRIEND, FRIEND_PHONE, ME, MY_PHONE, STATUS, event
from pydantic import ValidationError

from whatsapp_extractor import ChatKind, Jid, MediaKind, MessageKind
from whatsapp_extractor.adapters.neonize_mapper import is_key_exchange_only, to_message
from whatsapp_extractor.testing import lid_jids, phone_jids, texts

# --- examples: the shapes seen in production, readable as a spec ---------------------------------


def test_outgoing_direct_message_takes_the_counterpart_from_the_recipient() -> None:
    message = to_message(
        event(
            chat=ME,
            sender=ME,
            recipient_alt=MY_PHONE,
            from_me=True,
            body=WaMessage(extendedTextMessage=ExtendedTextMessage(text="Oi")),
        )
    )
    assert message.kind is MessageKind.TEXT
    assert message.timestamp == datetime.fromtimestamp(1789677560, tz=UTC)
    assert message.chat.kind is ChatKind.DIRECT
    assert message.chat.counterpart_phone == MY_PHONE.User
    assert message.sender.lid == ME.User
    assert message.sender.phone is None  # the recipient phone is never the sender phone
    assert message.recipient is not None
    assert message.recipient.phone == MY_PHONE.User
    assert message.content.text == "Oi"
    assert message.content.media is None


def test_incoming_direct_message_takes_the_counterpart_from_the_sender() -> None:
    message = to_message(event(chat=FRIEND, sender=FRIEND, sender_alt=FRIEND_PHONE))
    assert message.chat.counterpart_phone == FRIEND_PHONE.User
    assert message.sender.phone == FRIEND_PHONE.User
    assert message.sender.lid == FRIEND.User
    assert message.recipient is None


def test_status_video_has_media_and_no_counterpart() -> None:
    video = VideoMessage(
        mimetype="video/mp4",
        caption="simbora",
        seconds=5,
        height=720,
        width=1280,
        fileLength=1327198,
    )
    message = to_message(
        event(chat=STATUS, sender=FRIEND, kind="media", body=WaMessage(videoMessage=video))
    )
    assert message.kind is MessageKind.MEDIA
    assert message.chat.kind is ChatKind.STATUS
    assert message.chat.counterpart_phone is None
    assert message.content.text == "simbora"
    media = message.content.media
    assert media is not None
    assert media.kind is MediaKind.VIDEO
    assert (media.duration_seconds, media.width, media.height) == (5, 1280, 720)


def test_voice_note_is_flagged() -> None:
    audio = AudioMessage(mimetype="audio/ogg", PTT=True, seconds=3)
    message = to_message(event(chat=FRIEND, sender=FRIEND, body=WaMessage(audioMessage=audio)))
    assert message.content.media is not None
    assert message.content.media.is_voice_note is True


def test_event_without_chat_is_rejected() -> None:
    with pytest.raises(ValidationError):
        to_message(event(chat=JID(), sender=FRIEND))


# --- properties: rules that hold for every wire event -----------------------------------------


def wire(jid: Jid) -> JID:
    return JID(User=jid.user, Server=jid.server)


@given(sender=lid_jids(), sender_alt=st.none() | phone_jids(), recipient_alt=phone_jids())
def test_sender_phone_comes_from_the_sender_or_its_alt_never_from_the_recipient(
    sender: Jid, sender_alt: Jid | None, recipient_alt: Jid
) -> None:
    message = to_message(
        event(
            chat=wire(sender),
            sender=wire(sender),
            sender_alt=wire(sender_alt) if sender_alt else EMPTY,
            recipient_alt=wire(recipient_alt),
            from_me=True,
        )
    )
    assert message.sender.phone == (sender_alt.phone if sender_alt else None)
    assert message.chat.counterpart_phone == recipient_alt.phone


@given(chat=lid_jids(), sender=st.one_of(lid_jids(), phone_jids()), from_me=st.booleans())
def test_direct_chat_without_any_phone_has_no_counterpart_phone(
    chat: Jid, sender: Jid, *, from_me: bool
) -> None:
    message = to_message(event(chat=wire(chat), sender=wire(sender), from_me=from_me))
    expected = None if from_me else sender.phone
    assert message.chat.counterpart_phone == expected


@given(
    caption=texts(max_size=50),
    width=st.integers(min_value=0, max_value=10_000),
    height=st.integers(min_value=0, max_value=10_000),
    size=st.integers(min_value=0, max_value=2**31),
)
def test_proto_zero_values_mean_absent(caption: str, width: int, height: int, size: int) -> None:
    image = ImageMessage(mimetype="image/jpeg", caption=caption, width=width, height=height)
    image.fileLength = size
    message = to_message(event(chat=FRIEND, sender=FRIEND, body=WaMessage(imageMessage=image)))
    media = message.content.media
    assert media is not None
    assert (media.caption, media.width, media.height, media.file_length) == (
        caption or None,
        width or None,
        height or None,
        size or None,
    )


@given(text=texts(max_size=50))
def test_only_a_bare_sender_key_counts_as_key_exchange(text: str) -> None:
    key_only = WaMessage(senderKeyDistributionMessage=SenderKeyDistributionMessage(groupID="g"))
    with_content = WaMessage(
        conversation=text or "x",
        senderKeyDistributionMessage=SenderKeyDistributionMessage(groupID="g"),
    )
    assert is_key_exchange_only(event(chat=FRIEND, sender=FRIEND, body=key_only))
    assert not is_key_exchange_only(event(chat=FRIEND, sender=FRIEND, body=with_content))
