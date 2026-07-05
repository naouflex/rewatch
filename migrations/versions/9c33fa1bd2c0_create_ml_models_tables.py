"""create ml_models tables

Adds the four tables that back the MLModels feature:

- ``ml_models``                 - one row per ML model (estimator + metadata)
- ``ml_model_versions``         - immutable training snapshots used for revert/fork
- ``prediction_results``        - inference outputs
- ``ml_model_subscriptions``    - notification destinations per model

The schema mirrors the inverse-watch port but drops the Keras-specific
``autoencoder_model_blob`` / ``encoder_model_blob`` columns since the rewatch
implementation is sklearn-only.

Revision ID: 9c33fa1bd2c0
Revises: 8a9d4e2c1b75
Create Date: 2026-05-02 17:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "9c33fa1bd2c0"
down_revision = "8a9d4e2c1b75"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ml_models",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1024), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("query_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.Unicode()), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rearm", sa.Integer(), nullable=True),
        sa.Column("state", sa.String(length=255), nullable=True, server_default="unknown"),
        sa.Column("state_train", sa.String(length=255), nullable=True, server_default="unknown"),
        sa.Column("state_predict", sa.String(length=255), nullable=True, server_default="unknown"),
        sa.Column("options", postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default="{}"),
        sa.Column("input_data", sa.Text(), nullable=True, server_default=""),
        sa.Column("model_blob", postgresql.BYTEA(), nullable=False, server_default=sa.text("''::bytea")),
        sa.Column("metrics", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("train_data_hash", sa.String(length=64), nullable=True),
        sa.Column("test_data_hash", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["query_id"], ["queries.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ml_models_org_id_name", "ml_models", ["org_id", "name"])
    op.create_index("ix_ml_models_is_archived", "ml_models", ["is_archived"])

    op.create_table(
        "ml_model_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("description", sa.String(length=1024), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("org_id", sa.Integer(), nullable=True),
        sa.Column("query_id", sa.Integer(), nullable=True),
        sa.Column("changes", sa.String(length=255), nullable=True),
        sa.Column("model_blob", postgresql.BYTEA(), nullable=False, server_default=sa.text("''::bytea")),
        sa.Column("metrics", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("options", postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default="{}"),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("tags", postgresql.ARRAY(sa.Unicode()), nullable=True),
        sa.Column("rearm", sa.Integer(), nullable=True),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("state", sa.String(length=255), nullable=True, server_default="unknown"),
        sa.Column("state_train", sa.String(length=255), nullable=True, server_default="unknown"),
        sa.Column("state_predict", sa.String(length=255), nullable=True, server_default="unknown"),
        sa.Column("input_data", sa.Text(), nullable=True, server_default=""),
        sa.ForeignKeyConstraint(["model_id"], ["ml_models.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["query_id"], ["queries.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_id", "version", name="unique_model_version"),
    )
    op.create_index("ix_ml_model_versions_is_archived", "ml_model_versions", ["is_archived"])

    op.create_table(
        "prediction_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("model_id", sa.Integer(), nullable=True),
        sa.Column("query_id", sa.Integer(), nullable=True),
        sa.Column("destination_id", sa.Integer(), nullable=True),
        sa.Column("additional_properties", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="{}"),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("tags", postgresql.ARRAY(sa.Unicode()), nullable=True),
        sa.Column("model_version", sa.Integer(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("input_data", sa.Text(), nullable=True, server_default=""),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["model_id"], ["ml_models.id"]),
        sa.ForeignKeyConstraint(["query_id"], ["queries.id"]),
        sa.ForeignKeyConstraint(["destination_id"], ["notification_destinations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prediction_results_is_archived", "prediction_results", ["is_archived"])

    op.create_table(
        "ml_model_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("destination_id", sa.Integer(), nullable=True),
        sa.Column("model_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["destination_id"], ["notification_destinations.id"]),
        sa.ForeignKeyConstraint(["model_id"], ["ml_models.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ml_model_subscriptions_destination_id_model_id",
        "ml_model_subscriptions",
        ["destination_id", "model_id"],
        unique=True,
    )


def downgrade():
    op.drop_index("ml_model_subscriptions_destination_id_model_id", table_name="ml_model_subscriptions")
    op.drop_table("ml_model_subscriptions")

    op.drop_index("ix_prediction_results_is_archived", table_name="prediction_results")
    op.drop_table("prediction_results")

    op.drop_index("ix_ml_model_versions_is_archived", table_name="ml_model_versions")
    op.drop_table("ml_model_versions")

    op.drop_index("ix_ml_models_is_archived", table_name="ml_models")
    op.drop_index("ml_models_org_id_name", table_name="ml_models")
    op.drop_table("ml_models")
