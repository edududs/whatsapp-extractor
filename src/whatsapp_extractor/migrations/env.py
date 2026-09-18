"""Runs every revision against the schema handed over by `migrate`, never on its own."""

from __future__ import annotations

from alembic import context

from whatsapp_extractor.adapters.sql_store import metadata

config = context.config
schema: str = config.attributes["schema"]

context.configure(
    connection=config.attributes["connection"],
    target_metadata=metadata,
    version_table_schema=schema,
)
with context.begin_transaction():
    context.run_migrations()
