"""Short-lived connections: connect, wait for a milestone event, do something, disconnect."""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING

from google.protobuf.message import Message as ProtoMessage
from neonize.aioze.events import ConnectedEv
from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from neonize.aioze.client import NewAClient


@contextlib.asynccontextmanager
async def connected[E: ProtoMessage](
    client: NewAClient, *, until: type[E] = ConnectedEv
) -> AsyncGenerator[None]:
    """Yield once `until` has arrived; leaving tells neonize to stop its worker thread.

    A connection that ends before the milestone surfaces its error here.
    """
    reached = asyncio.Event()

    async def on_event(_: NewAClient, __: E) -> None:
        reached.set()

    client.event(until)(on_event)
    connection = await client.connect()
    waiter = asyncio.ensure_future(reached.wait())
    try:
        await asyncio.wait({waiter, connection}, return_when=asyncio.FIRST_COMPLETED)
        if connection.done():
            connection.result()
        yield
    finally:
        waiter.cancel()
        connection.cancel()


class Group(BaseModel):
    model_config = ConfigDict(frozen=True)

    jid: str
    name: str
    participants: int


async def joined_groups(client: NewAClient) -> list[Group]:
    """The groups the connected account is a member of, as WhatsApp reports them."""
    return [
        Group(
            jid=f"{info.JID.User}@{info.JID.Server}",
            name=info.GroupName.Name,
            participants=len(info.Participants),
        )
        for info in await client.get_joined_groups()
    ]
