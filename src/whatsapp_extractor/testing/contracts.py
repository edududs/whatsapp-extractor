"""Properties every implementation of a port must hold. Inherit, implement, done."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from hypothesis import HealthCheck, assume, given, settings

from .strategies import message_ids, messages

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from contextlib import AbstractAsyncContextManager

    from whatsapp_extractor.application import MessageStore
    from whatsapp_extractor.domain import Message

# Each example opens a fresh store, often on disk: no deadline, and fewer but real examples.
# The same property runs once per implementing class, which is what differing_executors
# would otherwise flag.
_contract = settings(
    deadline=None,
    max_examples=25,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.differing_executors],
)


class MessageStoreContract:
    """Subclass it as `TestMyStore` in a test module and implement `open_store`.

    Every example gets a fresh, empty store from `open_store`; close it on exit.
    """

    def open_store(self) -> AbstractAsyncContextManager[MessageStore]:
        raise NotImplementedError

    @_contract
    @given(message_id=message_ids())
    def test_never_saved_id_loads_as_none(self, message_id: str) -> None:
        async def check(store: MessageStore) -> None:
            assert await store.load(message_id) is None

        self._run(check)

    @_contract
    @given(message=messages())
    def test_saved_message_loads_back_equal(self, message: Message) -> None:
        async def check(store: MessageStore) -> None:
            await store.save(message)
            assert await store.load(message.id) == message

        self._run(check)

    @_contract
    @given(first=messages(), second=messages())
    def test_last_save_of_an_id_wins(self, first: Message, second: Message) -> None:
        second = second.model_copy(update={"id": first.id})

        async def check(store: MessageStore) -> None:
            await store.save(first)
            await store.save(second)
            assert await store.load(first.id) == second

        self._run(check)

    @_contract
    @given(one=messages(), other=messages())
    def test_saving_another_id_does_not_touch_the_first(self, one: Message, other: Message) -> None:
        assume(one.id != other.id)

        async def check(store: MessageStore) -> None:
            await store.save(one)
            await store.save(other)
            assert await store.load(one.id) == one

        self._run(check)

    def _run(self, check: Callable[[MessageStore], Coroutine[None, None, None]]) -> None:
        async def with_store() -> None:
            async with self.open_store() as store:
                await check(store)

        asyncio.run(with_store())
