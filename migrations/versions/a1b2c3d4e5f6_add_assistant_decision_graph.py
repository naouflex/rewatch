"""add decision_graph to assistant_messages

Revision ID: a1b2c3d4e5f6
Revises: f2b3c4d5e6f7
Create Date: 2026-07-08 14:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a1b2c3d4e5f6"
down_revision = "f2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "assistant_messages",
        sa.Column("decision_graph", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade():
    op.drop_column("assistant_messages", "decision_graph")
