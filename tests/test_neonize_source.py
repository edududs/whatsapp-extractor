from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast

import pytest
from neonize.exc import ContactStoreError
from neonize.proto.Neonize_pb2 import JID, ContactInfo
from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import Message as WaMessage
from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import SenderKeyDistributionMessage
from neonize_events import FRIEND, GROUP, ME, MY_PHONE, event

from whatsapp_extractor.adapters.neonize_source import NeonizeSource

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

    from neonize.aioze.client import NewAClient
    from neonize.proto.Neonize_pb2 import Message as MessageEv

    from whatsapp_extractor import Message

type Handler = Callable[[FakeClient, MessageEv], Awaitable[None]]


class FakeContacts:
    def __init__(self) -> None:
        self.names: dict[str, str] = {}
        self.broken = False

    async def get_contact(self, jid: JID) -> ContactInfo:
        if self.broken:
            raise ContactStoreError
        name = self.names.get(jid.User)
        return ContactInfo(Found=name is not None, FullName=name or "")


class FakeClient:
    """The slice of `NewAClient` the source relies on."""

    def __init__(self) -> None:
        self.connection: asyncio.Future[None] = asyncio.get_running_loop().create_future()
        self.contact = FakeContacts()
        self._handler: Handler | None = None

    def event(self, _event_type: type[MessageEv]) -> Callable[[Handler], None]:
        def register(handler: Handler) -> None:
            self._handler = handler

        return register

    async def connect(self) -> asyncio.Future[None]:
        return self.connection

    async def receive(self, wire_event: MessageEv) -> None:
        assert self._handler is not None
        await self._handler(self, wire_event)


def from_friend(message_id: str) -> MessageEv:
    return event(message_id, chat=FRIEND, sender=FRIEND)


async def open_stream(client: FakeClient, buffer_size: int = 10) -> AsyncIterator[Message]:
    """Start the stream and let it connect: it is now waiting for the first message."""
    stream = NeonizeSource(cast("NewAClient", client), buffer_size).messages()
    first = asyncio.ensure_future(anext(stream))
    await asyncio.sleep(0)

    async def resumed() -> AsyncIterator[Message]:
        yield await first
        async for message in stream:
            yield message

    return resumed()


async def test_yields_messages_in_order_until_the_connection_ends() -> None:
    client = FakeClient()
    stream = await open_stream(client)
    await client.receive(from_friend("a"))
    await client.receive(from_friend("b"))
    client.connection.set_result(None)
    assert [message.id async for message in stream] == ["a", "b"]


async def test_connection_error_propagates() -> None:
    client = FakeClient()
    stream = await open_stream(client)
    client.connection.set_exception(ConnectionError("logged out"))
    with pytest.raises(ConnectionError, match="logged out"):
        await anext(stream)


async def test_unmappable_event_is_logged_and_skipped(caplog: pytest.LogCaptureFixture) -> None:
    client = FakeClient()
    stream = await open_stream(client)
    await client.receive(event("broken", chat=JID(), sender=FRIEND))
    await client.receive(from_friend("ok"))
    client.connection.set_result(None)
    assert [message.id async for message in stream] == ["ok"]
    assert "unmappable message broken" in caplog.text


async def test_full_buffer_drops_and_logs(caplog: pytest.LogCaptureFixture) -> None:
    client = FakeClient()
    stream = await open_stream(client, buffer_size=1)
    await client.receive(from_friend("kept"))
    await client.receive(from_friend("dropped"))
    client.connection.set_result(None)
    assert [message.id async for message in stream] == ["kept"]
    assert "dropped message dropped" in caplog.text


async def test_group_message_delivered_as_key_then_content_is_extracted_once() -> None:
    sender_key = WaMessage(
        senderKeyDistributionMessage=SenderKeyDistributionMessage(groupID=GROUP.User)
    )
    client = FakeClient()
    stream = await open_stream(client)
    await client.receive(event("same-id", chat=GROUP, sender=FRIEND, body=sender_key))
    await client.receive(event("same-id", chat=GROUP, sender=FRIEND))
    client.connection.set_result(None)
    assert [(message.id, message.content.text) async for message in stream] == [("same-id", "Oi")]


async def test_direct_chat_is_named_after_the_contact_even_when_i_am_the_sender() -> None:
    client = FakeClient()
    client.contact.names[MY_PHONE.User] = "Me (address book)"
    stream = await open_stream(client)
    await client.receive(event(chat=ME, sender=ME, recipient_alt=MY_PHONE, from_me=True))
    client.connection.set_result(None)
    assert [message.chat.name async for message in stream] == ["Me (address book)"]


async def test_contact_stored_by_chat_address_is_found_too() -> None:
    client = FakeClient()
    client.contact.names[FRIEND.User] = "Friend (address book)"
    stream = await open_stream(client)
    await client.receive(from_friend("a"))
    client.connection.set_result(None)
    assert [message.chat.name async for message in stream] == ["Friend (address book)"]


async def test_groups_are_not_looked_up_in_the_contact_store(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = FakeClient()
    client.contact.broken = True  # any lookup would log a warning
    stream = await open_stream(client)
    await client.receive(event(chat=GROUP, sender=FRIEND))
    client.connection.set_result(None)
    assert [message.chat.name async for message in stream] == [None]
    assert "contact lookup failed" not in caplog.text


async def test_failing_contact_store_never_loses_the_message(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = FakeClient()
    client.contact.broken = True
    stream = await open_stream(client)
    await client.receive(from_friend("a"))
    client.connection.set_result(None)
    assert [(message.id, message.chat.name) async for message in stream] == [("a", None)]
    assert "contact lookup failed" in caplog.text
