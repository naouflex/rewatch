"""create assistant_threads and assistant_messages tables

Revision ID: f3a2b1c9d8e0
Revises: d6b4f3a1c8e7
Create Date: 2026-07-05 09:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

revision = "f3a2b1c9d8e0"
down_revision = "d6b4f3a1c8e7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "assistant_threads",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=80), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assistant_threads_user_id", "assistant_threads", ["user_id"])
    op.create_index("ix_assistant_threads_updated_at", "assistant_threads", ["updated_at"])

    op.create_table(
        "assistant_messages",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("thread_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["thread_id"], ["assistant_threads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assistant_messages_thread_id", "assistant_messages", ["thread_id"])


def downgrade():
    op.drop_index("ix_assistant_messages_thread_id", table_name="assistant_messages")
    op.drop_table("assistant_messages")
    op.drop_index("ix_assistant_threads_updated_at", table_name="assistant_threads")
    op.drop_index("ix_assistant_threads_user_id", table_name="assistant_threads")
    op.drop_table("assistant_threads")
