"""tool role + tool call columns on messages

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Postgres allows ADD VALUE inside a transaction as long as the new value
    # isn't used in the same transaction (we don't).
    op.execute("ALTER TYPE message_role ADD VALUE IF NOT EXISTS 'tool'")
    op.add_column(
        "messages",
        sa.Column("tool_calls", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column("messages", sa.Column("tool_call_id", sa.String(length=32), nullable=True))
    op.add_column("messages", sa.Column("tool_name", sa.String(length=200), nullable=True))
    op.add_column("messages", sa.Column("tool_is_error", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("messages", "tool_is_error")
    op.drop_column("messages", "tool_name")
    op.drop_column("messages", "tool_call_id")
    op.drop_column("messages", "tool_calls")
    # Removing an enum value needs a type rebuild; drop tool rows first.
    op.execute("DELETE FROM messages WHERE role = 'tool'")
    op.execute("ALTER TYPE message_role RENAME TO message_role_old")
    op.execute("CREATE TYPE message_role AS ENUM ('user', 'assistant')")
    op.execute(
        "ALTER TABLE messages ALTER COLUMN role TYPE message_role USING role::text::message_role"
    )
    op.execute("DROP TYPE message_role_old")
