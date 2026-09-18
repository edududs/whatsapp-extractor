from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Column, DateTime, MetaData, String, Table, delete, insert, select
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from whatsapp_extractor.domain import Message

if TYPE_CHECKING:
    from pathlib import Path

_metadata = MetaData()

# `payload` is the source of truth; the other columns are projections of it for querying.
_messages = Table(
    "messages",
    _metadata,
    Column("id", String, primary_key=True),
    Column("chat_jid", String, nullable=False, index=True),
    Column("timestamp", DateTime(timezone=True), nullable=False, index=True),
    Column("payload", JSON, nullable=False),
)


def engine_for(database: str | Path) -> AsyncEngine:
    """The database neonize keeps the session in, as an async SQLAlchemy engine.

    neonize takes a SQLite file path or a `postgres://` DSN; the extractor puts its
    `messages` table in that same database, next to the `whatsmeow_*` tables.
    """
    database = str(database)
    if database.startswith(("postgres://", "postgresql://")):
        return create_async_engine("postgresql+asyncpg://" + database.split("://", 1)[1])
    # neonize writes to the same file: wait for its lock instead of failing at once.
    return create_async_engine(f"sqlite+aiosqlite:///{database}", connect_args={"timeout": 30})


class SqlMessageStore:
    """Any database with an async SQLAlchemy driver; see `engine_for`."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def create_schema(self) -> None:
        async with self._engine.begin() as connection:
            await connection.run_sync(_metadata.create_all)

    async def save(self, message: Message) -> None:
        # Delete + insert in one transaction: a portable upsert, no dialect-specific SQL.
        async with self._engine.begin() as connection:
            await connection.execute(delete(_messages).where(_messages.c.id == message.id))
            await connection.execute(
                insert(_messages).values(
                    id=message.id,
                    chat_jid=message.chat.jid.value,
                    timestamp=message.timestamp,
                    payload=message.model_dump(mode="json"),
                )
            )

    async def load(self, message_id: str) -> Message | None:
        async with self._engine.connect() as connection:
            payload = await connection.scalar(
                select(_messages.c.payload).where(_messages.c.id == message_id)
            )
        return None if payload is None else Message.model_validate(payload)
