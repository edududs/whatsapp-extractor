"""messages table

Revision ID: 0001
Revises:
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "messages",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("chat_jid", sa.String(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
    )
    op.create_index("ix_messages_chat_jid", "messages", ["chat_jid"])
    op.create_index("ix_messages_timestamp", "messages", ["timestamp"])


def downgrade() -> None:
    op.drop_index("ix_messages_timestamp", table_name="messages")
    op.drop_index("ix_messages_chat_jid", table_name="messages")
    op.drop_table("messages")
