from __future__ import annotations

from typing import TYPE_CHECKING

from whatsapp_extractor import (
    DomainEvent,
    EventBus,
    Jid,
    Message,
    MessageExtracted,
    Watchlist,
    extract,
)
from whatsapp_extractor.adapters.memory_store import InMemoryMessageStore
from whatsapp_extractor.testing import GROUP, make_message

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class FakeSource:
    def __init__(self, *messages: Message) -> None:
        self._messages = messages

    async def messages(self) -> AsyncIterator[Message]:
        for message in self._messages:
            yield message


class Recorder[E: DomainEvent]:
    def __init__(self) -> None:
        self.events: list[E] = []

    async def __call__(self, event: E) -> None:
        self.events.append(event)


class OtherEvent(DomainEvent):
    pass


async def test_extract_saves_then_announces_only_watched_messages() -> None:
    watched = make_message("watched")
    ignored = make_message("ignored", chat=Jid(user="999", server="g.us"))
    store = InMemoryMessageStore()
    recorder = Recorder[MessageExtracted]()
    bus = EventBus()
    bus.subscribe(MessageExtracted, recorder)

    watchlist = Watchlist(chats=frozenset({GROUP.value}))
    await extract(FakeSource(watched, ignored), watchlist.matches, store, bus)

    assert await store.load("watched") == watched
    assert await store.load("ignored") is None
    assert recorder.events == [MessageExtracted(message=watched)]


async def test_bus_dispatches_by_event_type() -> None:
    extracted = Recorder[MessageExtracted]()
    everything = Recorder[DomainEvent]()
    bus = EventBus()
    bus.subscribe(MessageExtracted, extracted)
    bus.subscribe(DomainEvent, everything)

    await bus.publish(OtherEvent())

    assert extracted.events == []
    assert everything.events == [OtherEvent()]


async def test_failing_handler_does_not_stop_the_others() -> None:
    async def boom(_: MessageExtracted) -> None:
        msg = "consumidor indisponível"
        raise RuntimeError(msg)

    after = Recorder[MessageExtracted]()
    bus = EventBus()
    bus.subscribe(MessageExtracted, boom)
    bus.subscribe(MessageExtracted, after)

    await bus.publish(MessageExtracted(message=make_message()))

    assert len(after.events) == 1
