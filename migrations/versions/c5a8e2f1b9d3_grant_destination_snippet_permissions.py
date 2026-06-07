"""grant destination and query snippet permissions to existing groups

Destinations and query snippets are now gated behind dedicated role
permissions (``list/create/edit/view_destination`` and the query snippet
equivalents). These were added to ``Group.DEFAULT_PERMISSIONS`` so new groups
get them automatically, but groups that already exist in the database keep
their old permission list and would therefore hide the create/list UI.

This migration appends the new permissions to every existing group that does
not already have them, so regular users (and admins) regain access to the
destinations and query snippets pages without manual edits.

Revision ID: c5a8e2f1b9d3
Revises: b3f7c1a9d4e2
Create Date: 2026-06-07 21:33:00.000000

"""
from alembic import op
from sqlalchemy import text

revision = "c5a8e2f1b9d3"
down_revision = "b3f7c1a9d4e2"
branch_labels = None
depends_on = None

NEW_PERMISSIONS = [
    "list_destinations",
    "create_destination",
    "edit_destination",
    "view_destination",
    "list_query_snippets",
    "create_query_snippet",
    "edit_query_snippet",
    "view_query_snippet",
]


def upgrade():
    conn = op.get_bind()
    stmt = text(
        "UPDATE groups SET permissions = array_append(permissions, :perm) "
        "WHERE NOT (:perm = ANY(permissions))"
    )
    for permission in NEW_PERMISSIONS:
        conn.execute(stmt, {"perm": permission})


def downgrade():
    conn = op.get_bind()
    stmt = text(
        "UPDATE groups SET permissions = array_remove(permissions, :perm) "
        "WHERE :perm = ANY(permissions)"
    )
    for permission in NEW_PERMISSIONS:
        conn.execute(stmt, {"perm": permission})
