"""Every bundled store honours the port contract; the SQL one isolates accounts by schema."""

from __future__ import annotations

import asyncio
import contextlib
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from whatsapp_extractor.adapters.jsonl_store import JsonlMessageStore
from whatsapp_extractor.adapters.memory_store import InMemoryMessageStore
from whatsapp_extractor.adapters.sql_store import (
    SqlMessageStore,
    engine_for,
    migrate,
    schema_for,
)
from whatsapp_extractor.testing import MessageStoreContract, messages, phones

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from whatsapp_extractor import Message, MessageStore


class TestInMemoryMessageStore(MessageStoreContract):
    @contextlib.asynccontextmanager
    async def open_store(self) -> AsyncGenerator[MessageStore]:
        yield InMemoryMessageStore()


class TestJsonlMessageStore(MessageStoreContract):
    @contextlib.asynccontextmanager
    async def open_store(self) -> AsyncGenerator[MessageStore]:
        with tempfile.TemporaryDirectory() as folder:
            yield JsonlMessageStore(Path(folder) / "nested" / "messages.jsonl")


@contextlib.asynccontextmanager
async def sql_store(folder: Path, account: str) -> AsyncGenerator[SqlMessageStore]:
    schema = schema_for(account)
    engine = engine_for(str(folder / "session.db"), schema)
    try:
        await migrate(engine, schema)
        yield SqlMessageStore(engine)
    finally:
        await engine.dispose()


class TestSqlMessageStore(MessageStoreContract):
    @contextlib.asynccontextmanager
    async def open_store(self) -> AsyncGenerator[MessageStore]:
        with tempfile.TemporaryDirectory() as folder:
            async with sql_store(Path(folder), "5511900000001") as store:
                yield store


@settings(deadline=None, max_examples=15, suppress_health_check=[HealthCheck.too_slow])
@given(one=phones(), other=phones(), message=messages())
def test_accounts_never_see_each_other_even_with_the_same_message_id(
    one: str, other: str, message: Message
) -> None:
    async def check() -> None:
        with tempfile.TemporaryDirectory() as folder:
            async with (
                sql_store(Path(folder), one) as first,
                sql_store(Path(folder), other) as second,
            ):
                await first.save(message)
                assert await first.load(message.id) == message
                assert (await second.load(message.id)) == (message if one == other else None)

    asyncio.run(check())


def test_migrating_twice_is_harmless(tmp_path: Path) -> None:
    async def check() -> None:
        async with sql_store(tmp_path, "5511900000001"):
            pass
        async with sql_store(tmp_path, "5511900000001") as store:
            assert await store.load("nope") is None

    asyncio.run(check())


def test_sqlite_keeps_each_account_in_its_own_file_next_to_the_session(tmp_path: Path) -> None:
    async def check() -> None:
        async with sql_store(tmp_path, "5511900000001"):
            pass

    asyncio.run(check())
    assert (tmp_path / "wa_5511900000001.db").exists()


@given(phone=phones())
def test_schema_name_is_a_safe_identifier(phone: str) -> None:
    assert schema_for(phone) == f"wa_{phone}"


@given(account=st.text(max_size=20).filter(lambda s: not s.isdigit() or not 5 <= len(s) <= 15))
def test_anything_but_a_phone_is_rejected_as_schema(account: str) -> None:
    with pytest.raises(ValueError, match="phone"):
        schema_for(account)


@given(path=st.from_regex(r"\A[A-Za-z0-9_./-]{1,40}\.db\Z"))
def test_a_file_path_is_a_sqlite_database(path: str) -> None:
    url = engine_for(path, "wa_1").url
    assert url.drivername == "sqlite+aiosqlite"
    assert url.database == path


@settings(deadline=None)  # the first engine loads the asyncpg driver
@given(
    scheme=st.sampled_from(["postgres", "postgresql"]),
    rest=st.from_regex(r"\A[a-z]+:[a-z0-9]+@[a-z.]+:[1-9][0-9]{1,4}/[a-z_]+\Z"),
)
def test_a_postgres_dsn_keeps_its_credentials_and_swaps_the_driver(scheme: str, rest: str) -> None:
    url = engine_for(f"{scheme}://{rest}", "wa_1").url
    assert url.drivername == "postgresql+asyncpg"
    assert url.render_as_string(hide_password=False) == f"postgresql+asyncpg://{rest}"
