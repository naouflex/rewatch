"""alert ownable and alert_events table

Adds the columns required to treat alerts as first-class "owned" objects
(``org_id`` foreign key, ``is_archived``, ``tags``), and creates the
``alert_events`` table that historizes every notification dispatched for an
alert.

Revision ID: 2f5b2fcb1f3c
Revises: db0aca1ebd32
Create Date: 2026-05-02 12:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "2f5b2fcb1f3c"
down_revision = "db0aca1ebd32"
branch_labels = None
depends_on = None


def upgrade():
    # Alerts: become "ownable"
    op.add_column(
        "alerts",
        sa.Column("org_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "alerts",
        sa.Column("is_archived", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "alerts",
        sa.Column("tags", postgresql.ARRAY(sa.Unicode()), nullable=True),
    )
    op.create_index("ix_alerts_is_archived", "alerts", ["is_archived"])

    # Backfill org_id by walking alert -> query -> data_source -> org_id.
    op.execute(
        """
        UPDATE alerts a
        SET org_id = ds.org_id
        FROM queries q
        JOIN data_sources ds ON ds.id = q.data_source_id
        WHERE a.query_id = q.id AND a.org_id IS NULL
        """
    )
    # Anything left over (alert detached from a data source) gets the first org.
    op.execute(
        """
        UPDATE alerts
        SET org_id = (SELECT id FROM organizations ORDER BY id LIMIT 1)
        WHERE org_id IS NULL
        """
    )

    op.alter_column("alerts", "org_id", nullable=False)
    op.create_foreign_key(
        "fk_alerts_org_id",
        "alerts",
        "organizations",
        ["org_id"],
        ["id"],
    )
    op.create_index("ix_alerts_org_id", "alerts", ["org_id"])

    # Alert events: a row per dispatched notification (success or error).
    op.create_table(
        "alert_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("alert_id", sa.Integer(), nullable=True),
        sa.Column("query_id", sa.Integer(), nullable=True),
        sa.Column("destination_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("alert_type", sa.String(length=255), nullable=True),
        sa.Column("state", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("additional_properties", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("is_archived", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("row_index", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["query_id"], ["queries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["destination_id"], ["notification_destinations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_events_alert_id", "alert_events", ["alert_id"])
    op.create_index("ix_alert_events_org_id", "alert_events", ["org_id"])
    op.create_index("ix_alert_events_created_at", "alert_events", ["created_at"])
    op.create_index("ix_alert_events_is_archived", "alert_events", ["is_archived"])


def downgrade():
    op.drop_index("ix_alert_events_is_archived", table_name="alert_events")
    op.drop_index("ix_alert_events_created_at", table_name="alert_events")
    op.drop_index("ix_alert_events_org_id", table_name="alert_events")
    op.drop_index("ix_alert_events_alert_id", table_name="alert_events")
    op.drop_table("alert_events")

    op.drop_index("ix_alerts_org_id", table_name="alerts")
    op.drop_constraint("fk_alerts_org_id", "alerts", type_="foreignkey")
    op.drop_index("ix_alerts_is_archived", table_name="alerts")
    op.drop_column("alerts", "tags")
    op.drop_column("alerts", "is_archived")
    op.drop_column("alerts", "org_id")
