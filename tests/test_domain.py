from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from whatsapp_extractor import ChatKind, Jid, Message, MessageKind, Watchlist
from whatsapp_extractor.domain.jid import LID_SERVER, PHONE_SERVER
from whatsapp_extractor.testing import (
    jids,
    lid_jids,
    make_message,
    messages,
    phone_jids,
    texts,
    watchlists,
)


def test_jid_rejects_empty() -> None:
    with pytest.raises(ValidationError):
        Jid(user="", server="")


@given(jid=jids())
def test_jid_value_is_user_at_server(jid: Jid) -> None:
    assert jid.value == (f"{jid.user}@{jid.server}" if jid.user else jid.server)


@given(jid=jids())
def test_phone_and_lid_are_the_user_of_their_server_and_nothing_else(jid: Jid) -> None:
    assert jid.phone == (jid.user if jid.server == PHONE_SERVER else None)
    assert jid.lid == (jid.user if jid.server == LID_SERVER else None)


@given(jid=st.one_of(phone_jids(), lid_jids()))
def test_people_have_direct_chats(jid: Jid) -> None:
    assert ChatKind.of(jid) is ChatKind.DIRECT


@given(jid=jids())
def test_status_is_the_only_broadcast_that_is_not_a_broadcast(jid: Jid) -> None:
    kind = ChatKind.of(jid)
    assert (kind is ChatKind.STATUS) == (jid.value == "status@broadcast")
    assert (kind is ChatKind.BROADCAST) == (jid.server == "broadcast" and jid.user != "status")


@given(value=texts(max_size=20))
def test_unknown_message_kinds_do_not_reject_the_message(value: str) -> None:
    known = {kind.value for kind in MessageKind}
    assert (MessageKind(value) is MessageKind.UNKNOWN) == (value not in known)


@given(message=messages())
def test_message_has_a_single_shape_that_round_trips_through_json(message: Message) -> None:
    assert Message.model_validate_json(message.model_dump_json()) == message


@given(message=messages())
def test_empty_watchlist_watches_everything(message: Message) -> None:
    assert Watchlist().matches(message)


@given(message=messages(), watchlist=watchlists())
def test_watchlist_matches_iff_it_names_the_chat_or_the_sender(
    message: Message, watchlist: Watchlist
) -> None:
    names_chat = not watchlist.chats.isdisjoint(message.chat.identities)
    names_sender = not watchlist.senders.isdisjoint(message.sender.identities)
    empty = not watchlist.chats and not watchlist.senders
    assert watchlist.matches(message) == (empty or names_chat or names_sender)


@given(message=messages(), data=st.data())
def test_any_identity_of_the_chat_or_sender_is_enough(
    message: Message, data: st.DataObject
) -> None:
    chat_identity = data.draw(st.sampled_from(sorted(message.chat.identities)))
    sender_identity = data.draw(st.sampled_from(sorted(message.sender.identities)))
    assert Watchlist(chats=frozenset({chat_identity})).matches(message)
    assert Watchlist(senders=frozenset({sender_identity})).matches(message)


def test_the_example_message_is_a_group_message_from_alice() -> None:
    message = make_message()
    assert message.chat.kind is ChatKind.GROUP
    assert message.sender.pushname == "Alice"
