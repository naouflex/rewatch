"""create forum_posts table and seed sample community posts

Revision ID: d9f1a2b3c4e5
Revises: c8e4f2a1b7d3
Create Date: 2026-07-07 15:30:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision = "d9f1a2b3c4e5"
down_revision = "c8e4f2a1b7d3"
branch_labels = None
depends_on = None

NEW_PERMISSIONS = [
    "list_community_posts",
    "view_community_post",
    "create_community_post",
    "edit_community_post",
]

DUMMY_POSTS = [
    {
        "title": "Welcome to the Rewatch community!",
        "category": "general",
        "body": (
            "Hi everyone — this is a space to share queries, dashboards, alerts, and tips with your team.\n\n"
            "A few ideas for your first post:\n"
            "- Share a query pattern that saved you time\n"
            "- Ask for feedback on a dashboard layout\n"
            "- Compare alert destination setups\n\n"
            "Be kind, stay on topic, and link to resources when you can."
        ),
    },
    {
        "title": "Reusable cohort chart for weekly active users",
        "category": "queries",
        "body": (
            "I've been using a simple cohort query to track weekly active users by signup week. "
            "The trick is to bucket users in a CTE first, then join activity on `date_trunc('week', event_at)`.\n\n"
            "Happy to share the full SQL if anyone wants it — works well on Postgres and BigQuery "
            "with minor syntax tweaks."
        ),
    },
    {
        "title": "Dashboard layout: KPI row + drill-down table",
        "category": "dashboards",
        "body": (
            "For exec-facing boards I keep a single row of counter widgets (revenue, signups, churn) "
            "and one wide table visualization underneath for drill-down.\n\n"
            "Using text widgets for context notes between sections helps new viewers understand "
            "what they're looking at without opening each query."
        ),
    },
    {
        "title": "Slack alert templates that actually get read",
        "category": "alerts",
        "body": (
            "Short subject lines and a link back to the query work best for us. "
            "We mute alerts during deploy windows and use rearm=3600 on noisy checks.\n\n"
            "Anyone using webhook destinations with custom JSON payloads? "
            "Would love to compare structures."
        ),
    },
    {
        "title": "Parameterized queries: defaults vs required params",
        "category": "queries",
        "body": (
            "We standardize on required date range parameters for anything customer-facing, "
            "but use defaults for internal exploratory queries.\n\n"
            "Tip: document expected param types in the query description so dashboard "
            "editors know what to pass through."
        ),
    },
    {
        "title": "Dark mode friendly chart colors",
        "category": "dashboards",
        "body": (
            "If your charts look washed out in dark theme, try higher-contrast series colors "
            "and avoid light gray gridlines.\n\n"
            "Counter widgets with subtle background tints also read better than flat white boxes "
            "when the whole org uses dark mode."
        ),
    },
    {
        "title": "Custom data source icons — quick win for onboarding",
        "category": "tips",
        "body": (
            "Uploading brand icons on data sources makes the query editor and home recents "
            "much easier to scan for new teammates.\n\n"
            "Takes a minute per source and saves a lot of 'which database is this?' questions."
        ),
    },
    {
        "title": "When to index query results vs schedule refreshes",
        "category": "tips",
        "body": (
            "We use indexers when downstream tools need a stable table; "
            "for dashboards we usually rely on scheduled query refreshes instead.\n\n"
            "Rule of thumb: indexer if multiple consumers need the same snapshot, "
            "schedule if it's mostly for one dashboard."
        ),
    },
]


def _seed_posts(conn):
    count = conn.execute(text("SELECT COUNT(*) FROM forum_posts")).scalar()
    if count:
        return

    org_row = conn.execute(text("SELECT id FROM organizations ORDER BY id LIMIT 1")).fetchone()
    if not org_row:
        return

    org_id = org_row[0]
    user_row = conn.execute(
        text("SELECT id FROM users WHERE org_id = :org_id ORDER BY id LIMIT 1"),
        {"org_id": org_id},
    ).fetchone()
    if not user_row:
        return

    user_id = user_row[0]
    insert = text(
        "INSERT INTO forum_posts "
        "(updated_at, created_at, org_id, user_id, title, body, category) "
        "VALUES (NOW(), NOW(), :org_id, :user_id, :title, :body, :category)"
    )
    for post in DUMMY_POSTS:
        conn.execute(insert, {"org_id": org_id, "user_id": user_id, **post})


def upgrade():
    op.create_table(
        "forum_posts",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_forum_posts_org_id", "forum_posts", ["org_id"])
    op.create_index("ix_forum_posts_user_id", "forum_posts", ["user_id"])
    op.create_index("ix_forum_posts_category", "forum_posts", ["category"])
    op.create_index("ix_forum_posts_updated_at", "forum_posts", ["updated_at"])

    conn = op.get_bind()
    stmt = text(
        "UPDATE groups SET permissions = array_append(permissions, :perm) "
        "WHERE NOT (:perm = ANY(permissions))"
    )
    for permission in NEW_PERMISSIONS:
        conn.execute(stmt, {"perm": permission})

    _seed_posts(conn)


def downgrade():
    conn = op.get_bind()
    stmt = text(
        "UPDATE groups SET permissions = array_remove(permissions, :perm) "
        "WHERE :perm = ANY(permissions)"
    )
    for permission in NEW_PERMISSIONS:
        conn.execute(stmt, {"perm": permission})

    op.drop_index("ix_forum_posts_updated_at", table_name="forum_posts")
    op.drop_index("ix_forum_posts_category", table_name="forum_posts")
    op.drop_index("ix_forum_posts_user_id", table_name="forum_posts")
    op.drop_index("ix_forum_posts_org_id", table_name="forum_posts")
    op.drop_table("forum_posts")
