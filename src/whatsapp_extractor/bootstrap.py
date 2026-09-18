"""Composition root: the only module that knows every concrete piece."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING

from neonize.aioze.client import NewAClient

from .adapters.jsonl_store import JsonlMessageStore
from .adapters.log_handler import log_message_extracted
from .adapters.memory_store import InMemoryMessageStore
from .adapters.neonize_source import NeonizeSource
from .adapters.sql_store import SqlMessageStore, engine_for
from .application import (
    EventBus,
    EventHandler,
    MessageFilter,
    MessageSource,
    MessageWriter,
    extract,
)
from .domain import MessageExtracted
from .settings import Settings, StoreKind, ViewKind

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

log = logging.getLogger(__name__)


async def run(
    settings: Settings,
    *handlers: EventHandler[MessageExtracted],
    source: MessageSource | None = None,
    accepts: MessageFilter | None = None,
    writer: MessageWriter | None = None,
) -> None:
    """Extract with the bundled pieces, or with yours. Handlers run after the view."""
    bus = EventBus()
    for handler in (message_view(settings.view), *handlers):
        bus.subscribe(MessageExtracted, handler)
    source = source or NeonizeSource(NewAClient(settings.database), settings.buffer_size)
    accepts = accepts or settings.watchlist.matches
    async with open_writer(settings, writer) as target:
        await extract(source, accepts, target, bus)


@contextlib.asynccontextmanager
async def open_writer(
    settings: Settings, given: MessageWriter | None
) -> AsyncGenerator[MessageWriter]:
    if given is not None:
        yield given
        return
    match settings.store:
        case StoreKind.MEMORY:
            yield InMemoryMessageStore()
        case StoreKind.JSONL:
            yield JsonlMessageStore(settings.jsonl_path)
        case StoreKind.SQL:
            engine = engine_for(settings.database)
            try:
                store = SqlMessageStore(engine)
                await store.create_schema()
                yield store
            finally:
                await engine.dispose()


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


def main() -> None:
    configure_logging()
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(run(Settings()))
