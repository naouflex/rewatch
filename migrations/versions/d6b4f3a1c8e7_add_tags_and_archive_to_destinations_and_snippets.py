"""add tags and is_archived to destinations and query snippets

Brings destinations and query snippets to parity with alerts/indexers by adding
tagging and archiving:

* ``tags``        – optional array of labels for filtering.
* ``is_archived`` – hides the resource from the default listings (kept for
  reference / un-archiving) without deleting it.

Revision ID: d6b4f3a1c8e7
Revises: c5a8e2f1b9d3
Create Date: 2026-06-07 21:40:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "d6b4f3a1c8e7"
down_revision = "c5a8e2f1b9d3"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("notification_destinations", "query_snippets"):
        op.add_column(table, sa.Column("tags", postgresql.ARRAY(sa.Unicode()), nullable=True))
        op.add_column(
            table,
            sa.Column("is_archived", sa.Boolean(), server_default=sa.false(), nullable=False),
        )
        op.create_index("ix_{}_is_archived".format(table), table, ["is_archived"])


def downgrade():
    for table in ("notification_destinations", "query_snippets"):
        op.drop_index("ix_{}_is_archived".format(table), table_name=table)
        op.drop_column(table, "is_archived")
        op.drop_column(table, "tags")
