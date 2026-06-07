"""make destinations and query snippets ownable and private

Destinations and query snippets are now scoped to their owning user (and
organization) rather than being shared org-wide. To allow each user to keep
their own private copies, the uniqueness constraints move from being global /
org-wide to being per ``(org_id, user_id, ...)``:

* ``notification_destinations``: name is unique per (org, user) instead of
  per (org).
* ``query_snippets``: trigger is unique per (org, user) instead of globally.

Indexes on ``user_id`` are added to keep the per-user lookups cheap.

Revision ID: b3f7c1a9d4e2
Revises: 9c33fa1bd2c0
Create Date: 2026-06-07 21:20:00.000000

"""
from alembic import op

revision = "b3f7c1a9d4e2"
down_revision = "9c33fa1bd2c0"
branch_labels = None
depends_on = None


def upgrade():
    # notification_destinations: name unique per (org, user)
    op.execute("DROP INDEX IF EXISTS notification_destinations_org_id_name")
    op.create_index(
        "notification_destinations_org_id_user_id_name",
        "notification_destinations",
        ["org_id", "user_id", "name"],
        unique=True,
    )
    op.create_index(
        "ix_notification_destinations_user_id",
        "notification_destinations",
        ["user_id"],
    )

    # query_snippets: trigger unique per (org, user) rather than globally.
    # The legacy global-unique constraint may exist either as a constraint or an
    # index depending on how the table was created, so drop both defensively.
    op.execute("ALTER TABLE query_snippets DROP CONSTRAINT IF EXISTS query_snippets_trigger_key")
    op.execute("DROP INDEX IF EXISTS query_snippets_trigger_key")
    op.create_index(
        "query_snippets_org_id_user_id_trigger",
        "query_snippets",
        ["org_id", "user_id", "trigger"],
        unique=True,
    )
    op.create_index("ix_query_snippets_user_id", "query_snippets", ["user_id"])


def downgrade():
    op.drop_index("ix_query_snippets_user_id", table_name="query_snippets")
    op.drop_index("query_snippets_org_id_user_id_trigger", table_name="query_snippets")
    op.create_unique_constraint("query_snippets_trigger_key", "query_snippets", ["trigger"])

    op.drop_index(
        "ix_notification_destinations_user_id", table_name="notification_destinations"
    )
    op.drop_index(
        "notification_destinations_org_id_user_id_name", table_name="notification_destinations"
    )
    op.create_index(
        "notification_destinations_org_id_name",
        "notification_destinations",
        ["org_id", "name"],
        unique=True,
    )
