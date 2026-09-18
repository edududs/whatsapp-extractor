from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from neonize.aioze.events import MessageEv
from neonize.exc import ContactStoreError
from pydantic import ValidationError

from whatsapp_extractor.domain import ChatKind

from .neonize_mapper import contact_jids, contact_name, is_key_exchange_only, to_message

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from neonize.aioze.client import NewAClient

    from whatsapp_extractor.domain import Chat, Message

log = logging.getLogger(__name__)


class NeonizeSource:
    """WhatsApp via the asyncio client of neonize.

    neonize dispatches events fire-and-forget, so it cannot be slowed down: when the
    consumer lags more than `buffer_size` messages behind, new ones are dropped and logged.
    """

    def __init__(self, client: NewAClient, buffer_size: int) -> None:
        self._client = client
        self._buffer_size = buffer_size

    async def messages(self) -> AsyncIterator[Message]:
        buffer: asyncio.Queue[Message] = asyncio.Queue(self._buffer_size)

        # Never awaits: neonize runs one task per event, and awaiting here would reorder them.
        async def on_message(_: NewAClient, event: MessageEv) -> None:
            if is_key_exchange_only(event):
                log.debug("skipped key exchange of message %s", event.Info.ID)
                return
            try:
                buffer.put_nowait(to_message(event))
            except ValidationError:
                log.exception("unmappable message %s", event.Info.ID)
            except (asyncio.QueueFull, asyncio.QueueShutDown):
                log.error("dropped message %s: buffer full or stream closed", event.Info.ID)  # noqa: TRY400 — a traceback adds nothing here

        self._client.event(MessageEv)(on_message)
        connection = await self._client.connect()
        connection.add_done_callback(lambda _: buffer.shutdown())
        try:
            while True:
                yield await self._with_chat_name(await buffer.get())
        except asyncio.QueueShutDown:
            await connection  # surfaces the connection error, if any
        finally:
            connection.cancel()  # tells neonize to stop its worker thread

    async def _with_chat_name(self, message: Message) -> Message:
        if message.chat.kind is not ChatKind.DIRECT:
            return message
        return message.with_chat_name(await self._contact_name(message.chat))

    async def _contact_name(self, chat: Chat) -> str | None:
        """Read from the contact store neonize keeps in the session file. Cosmetic: never fails."""
        try:
            for jid in contact_jids(chat):
                if name := contact_name(await self._client.contact.get_contact(jid)):
                    return name
        except ContactStoreError:
            log.warning("contact lookup failed for chat %s", chat.jid.value, exc_info=True)
        return None
