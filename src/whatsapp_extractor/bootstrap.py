"""Composition root: the only module that knows every concrete piece."""

from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING
from uuid import uuid4

from neonize.aioze.client import NewAClient
from neonize.aioze.events import OfflineSyncCompletedEv

from .adapters.jsonl_store import JsonlMessageStore
from .adapters.log_handler import log_message_extracted
from .adapters.memory_store import InMemoryMessageStore
from .adapters.neonize_accounts import Account, account_of, find_account
from .adapters.neonize_session import Group, connected, joined_groups
from .adapters.neonize_source import NeonizeSource
from .adapters.sql_store import SqlMessageStore, engine_for, migrate, schema_for
from .application import (
    EventBus,
    EventHandler,
    MessageFilter,
    MessageSource,
    MessageWriter,
    extract,
)
from .domain import MessageExtracted, Watchlist
from .settings import Settings, StoreKind, ViewKind

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

log = logging.getLogger(__name__)


class AccountRequiredError(ValueError):
    """`run` extracts for exactly one account; `Settings.account` must say which."""


class AccountNotPairedError(LookupError):
    def __init__(self, phone: str) -> None:
        super().__init__(f"account {phone} is not paired in this database; run `pair`")
        self.phone = phone


async def run(
    settings: Settings,
    *handlers: EventHandler[MessageExtracted],
    source: MessageSource | None = None,
    accepts: MessageFilter | None = None,
    writer: MessageWriter | None = None,
) -> None:
    """Extract one account with the bundled pieces, or with yours. Handlers run after the view."""
    if settings.account is None:
        raise AccountRequiredError
    bus = EventBus()
    for handler in (message_view(settings.view), *handlers):
        bus.subscribe(MessageExtracted, handler)
    source = source or neonize_source(settings, settings.account)
    if accepts is None:
        watchlist = settings.watchlist_for(settings.account)
        accepts = watchlist.matches
        log.info("account %s: %s", settings.account, describe(watchlist))
    async with open_writer(settings, settings.account, writer) as target:
        await extract(source, accepts, target, bus)


def describe(watchlist: Watchlist) -> str:
    """What the run will let through, so an empty screen is never a mystery."""
    if not watchlist.chats and not watchlist.senders:
        return "watching every chat and sender"
    return (
        f"watching {len(watchlist.chats)} chat(s) {sorted(watchlist.chats)} "
        f"and {len(watchlist.senders)} sender(s) {sorted(watchlist.senders)}"
    )


def neonize_client(settings: Settings, phone: str) -> NewAClient:
    account = find_account(settings.database, phone)
    if account is None:
        raise AccountNotPairedError(phone)
    return NewAClient(settings.database, jid=account.device)


def neonize_source(settings: Settings, phone: str) -> NeonizeSource:
    return NeonizeSource(neonize_client(settings, phone), settings.buffer_size)


async def groups_of(settings: Settings, phone: str) -> list[Group]:
    """Connect briefly as the account and list the groups it belongs to."""
    client = neonize_client(settings, phone)
    async with connected(client):
        return await joined_groups(client)


@contextlib.asynccontextmanager
async def open_writer(
    settings: Settings, account: str, given: MessageWriter | None
) -> AsyncGenerator[MessageWriter]:
    """The account's own store: a schema, a file, or nothing shared."""
    if given is not None:
        yield given
        return
    match settings.store:
        case StoreKind.MEMORY:
            yield InMemoryMessageStore()
        case StoreKind.JSONL:
            yield JsonlMessageStore(settings.jsonl_path_for(account))
        case StoreKind.SQL:
            schema = schema_for(account)
            engine = engine_for(settings.message_database, schema)
            try:
                await migrate(engine, schema)
                yield SqlMessageStore(engine)
            finally:
                await engine.dispose()


async def migrate_account(settings: Settings, account: str) -> None:
    schema = schema_for(account)
    engine = engine_for(settings.message_database, schema)
    try:
        await migrate(engine, schema)
    finally:
        await engine.dispose()


class Pairing:
    """Pair one more phone into the database. neonize prints the QR code on the terminal.

    `run` returns when the initial sync completes; `account` is known as soon as the phone
    is linked, so a Ctrl+C after that still leaves a usable account.
    """

    def __init__(self, settings: Settings) -> None:
        self._client = NewAClient(settings.database, uuid=f"pairing-{uuid4().hex}")

    @property
    def account(self) -> Account | None:
        me = self._client.me
        return account_of(me) if me is not None else None

    async def run(self) -> None:
        async with connected(self._client, until=OfflineSyncCompletedEv):
            pass


def message_view(view: ViewKind) -> EventHandler[MessageExtracted]:
    if view is ViewKind.LOG:
        return log_message_extracted
    try:
        from rich import get_console  # noqa: PLC0415 — optional extra `rich`

        from .adapters import rich_view  # noqa: PLC0415 — imports rich
    except ImportError:
        log.warning("view `%s` needs the `rich` extra: falling back to `log`", view.value)
        return log_message_extracted
    render = rich_view.render_json if view is ViewKind.JSON else rich_view.render_panel
    return rich_view.message_view(get_console(), render)


def configure_logging() -> None:
    """Only the executable configures logging; as a library this piece just emits records."""
    try:
        from rich.logging import RichHandler  # noqa: PLC0415 — optional extra `rich`
    except ImportError:
        handler, log_format = logging.StreamHandler(), logging.BASIC_FORMAT
    else:
        handler, log_format = RichHandler(), "%(message)s"
    # force: neonize calls basicConfig on import, which would turn this one into a no-op.
    logging.basicConfig(level=logging.INFO, format=log_format, handlers=[handler], force=True)
    logging.getLogger("alembic").setLevel(logging.WARNING)
