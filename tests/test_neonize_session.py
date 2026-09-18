from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast

import pytest
from neonize.aioze.events import ConnectedEv
from neonize.proto.Neonize_pb2 import JID, GroupInfo, GroupName, GroupParticipant

from whatsapp_extractor.adapters.neonize_session import connected, joined_groups

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from google.protobuf.message import Message as ProtoMessage
    from neonize.aioze.client import NewAClient

type Handler = Callable[[FakeClient, ProtoMessage], Awaitable[None]]


class FakeClient:
    def __init__(self, groups: list[GroupInfo] | None = None) -> None:
        self.connection: asyncio.Future[None] = asyncio.get_running_loop().create_future()
        self.handlers: dict[type[ProtoMessage], Handler] = {}
        self.groups = groups or []
        self.stopped = False

    def event(self, event_type: type[ProtoMessage]) -> Callable[[Handler], None]:
        def register(handler: Handler) -> None:
            self.handlers[event_type] = handler

        return register

    async def connect(self) -> asyncio.Future[None]:
        self.connection.add_done_callback(lambda _: setattr(self, "stopped", True))
        return self.connection

    async def get_joined_groups(self) -> list[GroupInfo]:
        return self.groups

    async def fire(self, event_type: type[ProtoMessage], event: ProtoMessage) -> None:
        await self.handlers[event_type](self, event)


def group(jid_user: str, name: str, members: int) -> GroupInfo:
    return GroupInfo(
        JID=JID(User=jid_user, Server="g.us"),
        GroupName=GroupName(Name=name),
        Participants=[GroupParticipant(JID=JID(User=str(i), Server="s")) for i in range(members)],
    )


async def test_connected_waits_for_the_milestone_then_disconnects() -> None:
    client = FakeClient()
    inside: list[bool] = []

    async def use() -> None:
        async with connected(cast("NewAClient", client)):
            inside.append(client.stopped)

    task = asyncio.create_task(use())
    await asyncio.sleep(0)
    assert not inside  # still waiting for ConnectedEv
    await client.fire(ConnectedEv, ConnectedEv())
    await task
    assert inside == [False]
    assert client.stopped  # the connection was cancelled on exit


async def test_connected_surfaces_a_connection_that_ends_early() -> None:
    client = FakeClient()

    async def use() -> None:
        async with connected(cast("NewAClient", client)):
            pass

    task = asyncio.create_task(use())
    await asyncio.sleep(0)
    client.connection.set_exception(ConnectionError("logged out"))
    with pytest.raises(ConnectionError, match="logged out"):
        await task


async def test_joined_groups_are_mapped_by_address_name_and_size() -> None:
    client = FakeClient([group("120363000000000001", "Rota Plano", 3)])
    groups = await joined_groups(cast("NewAClient", client))
    assert [(g.jid, g.name, g.participants) for g in groups] == [
        ("120363000000000001@g.us", "Rota Plano", 3)
    ]
