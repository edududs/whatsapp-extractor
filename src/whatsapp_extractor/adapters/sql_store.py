"""Messages in the database neonize already uses, isolated per account.

Each account owns a schema named `wa_<phone>`. On PostgreSQL that is a real schema next to
the `whatsmeow_*` tables; on SQLite, where schemas do not exist, it is a separate file
`wa_<phone>.db` attached to every connection, so the same table definitions and the same
migrations serve both.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    MetaData,
    String,
    Table,
    delete,
    event,
    insert,
    select,
    text,
)
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from whatsapp_extractor.domain import Message

if TYPE_CHECKING:
    from alembic.config import Config
    from sqlalchemy.engine import Connection

_PHONE = re.compile(r"^[0-9]{5,15}$")
_MIGRATIONS = Path(__file__).resolve().parent.parent / "migrations"

metadata = MetaData()

# `payload` is the source of truth; the other columns are projections of it for querying.
messages = Table(
    "messages",
    metadata,
    Column("id", String, primary_key=True),
    Column("chat_jid", String, nullable=False, index=True),
    Column("timestamp", DateTime(timezone=True), nullable=False, index=True),
    Column("payload", JSON, nullable=False),
)


def schema_for(account: str) -> str:
    """The schema that holds one account's messages. The phone becomes part of an identifier."""
    if not _PHONE.match(account):
        msg = f"account must be a phone number, got {account!r}"
        raise ValueError(msg)
    return f"wa_{account}"


def is_postgres(database: str) -> bool:
    return database.startswith(("postgres://", "postgresql://"))


def engine_for(database: str, schema: str) -> AsyncEngine:
    """An async engine on the neonize database whose unqualified tables resolve to `schema`."""
    translate: dict[str | None, str | None] = {None: schema}
    if is_postgres(database):
        url = "postgresql+asyncpg://" + database.split("://", 1)[1]
        return create_async_engine(url, execution_options={"schema_translate_map": translate})
    # neonize writes to the same file: wait for its lock instead of failing at once.
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{database}",
        connect_args={"timeout": 30},
        execution_options={"schema_translate_map": translate},
    )
    attached = Path(database).resolve().parent / f"{schema}.db"

    @event.listens_for(engine.sync_engine, "connect")
    def attach(dbapi_connection: Any, _: object) -> None:  # noqa: ANN401 — DBAPI connection, untyped by SQLAlchemy
        cursor = dbapi_connection.cursor()
        cursor.execute(f"ATTACH DATABASE ? AS {schema}", (str(attached),))
        cursor.close()

    return engine


async def migrate(engine: AsyncEngine, schema: str) -> None:
    """Bring `schema` to the latest revision, creating it when needed."""
    from alembic.config import Config  # noqa: PLC0415 — alembic logs at import; load it only here

    config = Config()
    config.set_main_option("script_location", str(_MIGRATIONS))
    config.attributes["schema"] = schema
    async with engine.begin() as connection:
        if engine.dialect.name == "postgresql":
            await connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
        await connection.run_sync(_upgrade, config)


def _upgrade(connection: Connection, config: Config) -> None:
    from alembic import command  # noqa: PLC0415 — see `migrate`

    config.attributes["connection"] = connection
    command.upgrade(config, "head")


class SqlMessageStore:
    """Any database with an async SQLAlchemy driver; build the engine with `engine_for`."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def save(self, message: Message) -> None:
        # Delete + insert in one transaction: a portable upsert, no dialect-specific SQL.
        async with self._engine.begin() as connection:
            await connection.execute(delete(messages).where(messages.c.id == message.id))
            await connection.execute(
                insert(messages).values(
                    id=message.id,
                    chat_jid=message.chat.jid.value,
                    timestamp=message.timestamp,
                    payload=message.model_dump(mode="json"),
                )
            )

    async def load(self, message_id: str) -> Message | None:
        async with self._engine.connect() as connection:
            payload = await connection.scalar(
                select(messages.c.payload).where(messages.c.id == message_id)
            )
        return None if payload is None else Message.model_validate(payload)
