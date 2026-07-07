"""add forum comments and likes

Revision ID: f2b3c4d5e6f7
Revises: e1a2b3c4d5f6
Create Date: 2026-07-07 16:30:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision = "f2b3c4d5e6f7"
down_revision = "e1a2b3c4d5f6"
branch_labels = None
depends_on = None


def _seed_replies(conn):
    posts = conn.execute(text("SELECT id, org_id, user_id FROM forum_posts ORDER BY id LIMIT 3")).fetchall()
    if not posts:
        return

    existing = conn.execute(text("SELECT COUNT(*) FROM forum_comments")).scalar()
    if existing:
        return

    samples = [
        "Thanks for sharing — we use the same cohort pattern on our retention dashboard.",
        "Good tip. We also add a default date range param so embed viewers cannot pull unbounded data.",
        "Has anyone tried wiring this alert to Slack with a custom webhook payload?",
    ]

    insert = text(
        "INSERT INTO forum_comments "
        "(updated_at, created_at, org_id, post_id, user_id, parent_id, body) "
        "VALUES (NOW(), NOW(), :org_id, :post_id, :user_id, NULL, :body)"
    )
    for post, body in zip(posts, samples):
        conn.execute(
            insert,
            {"org_id": post[1], "post_id": post[0], "user_id": post[2], "body": body},
        )


def upgrade():
    op.create_table(
        "forum_comments",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["post_id"], ["forum_posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["parent_id"], ["forum_comments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_forum_comments_post_id", "forum_comments", ["post_id"])
    op.create_index("ix_forum_comments_user_id", "forum_comments", ["user_id"])
    op.create_index("ix_forum_comments_parent_id", "forum_comments", ["parent_id"])

    op.create_table(
        "forum_likes",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("target_type", sa.String(length=16), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "target_type", "target_id", name="unique_forum_like"),
    )
    op.create_index("ix_forum_likes_target", "forum_likes", ["target_type", "target_id"])
    op.create_index("ix_forum_likes_user_id", "forum_likes", ["user_id"])

    _seed_replies(op.get_bind())


def downgrade():
    op.drop_index("ix_forum_likes_user_id", table_name="forum_likes")
    op.drop_index("ix_forum_likes_target", table_name="forum_likes")
    op.drop_table("forum_likes")
    op.drop_index("ix_forum_comments_parent_id", table_name="forum_comments")
    op.drop_index("ix_forum_comments_user_id", table_name="forum_comments")
    op.drop_index("ix_forum_comments_post_id", table_name="forum_comments")
    op.drop_table("forum_comments")
