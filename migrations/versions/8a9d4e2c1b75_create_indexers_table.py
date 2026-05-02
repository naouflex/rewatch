"""create indexers table

Adds the ``indexers`` table that lets a user automatically copy the latest
results of a query into another data source on a schedule.

Revision ID: 8a9d4e2c1b75
Revises: 2f5b2fcb1f3c
Create Date: 2026-05-02 14:20:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "8a9d4e2c1b75"
down_revision = "2f5b2fcb1f3c"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "indexers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("query_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("data_source_id", sa.Integer(), nullable=False),
        sa.Column("options", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("tags", postgresql.ARRAY(sa.Unicode()), nullable=True),
        sa.Column("is_archived", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["query_id"], ["queries.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["data_source_id"], ["data_sources.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_indexers_is_archived", "indexers", ["is_archived"])
    op.create_index("ix_indexers_query_id", "indexers", ["query_id"])
    op.create_index("ix_indexers_org_id", "indexers", ["org_id"])
    op.create_index("ix_indexers_user_id", "indexers", ["user_id"])


def downgrade():
    op.drop_index("ix_indexers_user_id", table_name="indexers")
    op.drop_index("ix_indexers_org_id", table_name="indexers")
    op.drop_index("ix_indexers_query_id", table_name="indexers")
    op.drop_index("ix_indexers_is_archived", table_name="indexers")
    op.drop_table("indexers")
