"""Every bundled store honours the port contract, and the SQL one shares the neonize database."""

from __future__ import annotations

import contextlib
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from hypothesis import given
from hypothesis import strategies as st

from whatsapp_extractor.adapters.jsonl_store import JsonlMessageStore
from whatsapp_extractor.adapters.memory_store import InMemoryMessageStore
from whatsapp_extractor.adapters.sql_store import SqlMessageStore, engine_for
from whatsapp_extractor.testing import MessageStoreContract

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from whatsapp_extractor import MessageStore


class TestInMemoryMessageStore(MessageStoreContract):
    @contextlib.asynccontextmanager
    async def open_store(self) -> AsyncGenerator[MessageStore]:
        yield InMemoryMessageStore()


class TestJsonlMessageStore(MessageStoreContract):
    @contextlib.asynccontextmanager
    async def open_store(self) -> AsyncGenerator[MessageStore]:
        with tempfile.TemporaryDirectory() as folder:
            yield JsonlMessageStore(Path(folder) / "nested" / "messages.jsonl")


class TestSqlMessageStore(MessageStoreContract):
    @contextlib.asynccontextmanager
    async def open_store(self) -> AsyncGenerator[MessageStore]:
        with tempfile.TemporaryDirectory() as folder:
            engine = engine_for(Path(folder) / "session.db")
            store = SqlMessageStore(engine)
            await store.create_schema()
            try:
                yield store
            finally:
                await engine.dispose()


@given(path=st.from_regex(r"\A[A-Za-z0-9_./-]{1,40}\.db\Z"))
def test_a_file_path_is_a_sqlite_database(path: str) -> None:
    url = engine_for(path).url
    assert url.drivername == "sqlite+aiosqlite"
    assert url.database == path


@given(
    scheme=st.sampled_from(["postgres", "postgresql"]),
    rest=st.from_regex(r"\A[a-z]+:[a-z0-9]+@[a-z.]+:[1-9][0-9]{1,4}/[a-z_]+\Z"),
)
def test_a_postgres_dsn_keeps_its_credentials_and_swaps_the_driver(scheme: str, rest: str) -> None:
    url = engine_for(f"{scheme}://{rest}").url
    assert url.drivername == "postgresql+asyncpg"
    assert url.render_as_string(hide_password=False) == f"postgresql+asyncpg://{rest}"
