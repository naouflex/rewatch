"""add icon_url to data_sources

Revision ID: c8e4f2a1b7d3
Revises: f3a2b1c9d8e0
Create Date: 2026-07-07 13:20:00.000000

"""
import sqlalchemy as sa
from alembic import op

revision = "c8e4f2a1b7d3"
down_revision = "f3a2b1c9d8e0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("data_sources", sa.Column("icon_url", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("data_sources", "icon_url")
