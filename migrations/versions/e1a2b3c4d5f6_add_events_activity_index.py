"""add composite index on events for user activity queries

Revision ID: e1a2b3c4d5f6
Revises: d9f1a2b3c4e5
Create Date: 2026-07-07 16:00:00.000000

"""
from alembic import op

revision = "e1a2b3c4d5f6"
down_revision = "d9f1a2b3c4e5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_events_org_user_created_at",
        "events",
        ["org_id", "user_id", "created_at"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_events_org_user_created_at", table_name="events")
