"""Initial schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "moderators",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("username", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=500), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_moderators_username"), "moderators", ["username"], unique=True)
    op.create_table(
        "political_parties",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("short_name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_political_parties_slug"), "political_parties", ["slug"], unique=True)
    op.create_table(
        "politicians",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("biography", sa.Text(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_politicians_slug"), "politicians", ["slug"], unique=True)
    op.create_table(
        "media_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("media_type", sa.String(length=80), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_type", sa.String(length=40), nullable=False),
        sa.Column("actor_id", sa.String(length=80), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("entity_type", sa.String(length=120), nullable=False),
        sa.Column("entity_id", sa.String(length=80), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ip_address", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False)
    op.create_table(
        "party_memberships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("politician_id", sa.Uuid(), nullable=False),
        sa.Column("party_id", sa.Uuid(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["party_id"], ["political_parties.id"]),
        sa.ForeignKeyConstraint(["politician_id"], ["politicians.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "statements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("statement_date", sa.Date(), nullable=True),
        sa.Column("politician_id", sa.Uuid(), nullable=False),
        sa.Column("party_at_statement_time_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("internal_notes", sa.Text(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["party_at_statement_time_id"], ["political_parties.id"]),
        sa.ForeignKeyConstraint(["politician_id"], ["politicians.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_statements_status"), "statements", ["status"], unique=False)
    op.create_table(
        "ai_analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("statement_id", sa.Uuid(), nullable=False),
        sa.Column("model_name", sa.String(length=120), nullable=False),
        sa.Column("prompt_version", sa.String(length=80), nullable=False),
        sa.Column("schema_version", sa.String(length=80), nullable=False),
        sa.Column("analysis_date", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("factual_accuracy_score", sa.Integer(), nullable=False),
        sa.Column("logical_consistency_score", sa.Integer(), nullable=False),
        sa.Column("manipulativeness_score", sa.Integer(), nullable=False),
        sa.Column("principle_consistency_score", sa.Integer(), nullable=False),
        sa.Column("overall_score", sa.Integer(), nullable=False),
        sa.Column("factual_accuracy_explanation", sa.Text(), nullable=False),
        sa.Column("logical_consistency_explanation", sa.Text(), nullable=False),
        sa.Column("manipulativeness_explanation", sa.Text(), nullable=False),
        sa.Column("principle_consistency_explanation", sa.Text(), nullable=False),
        sa.Column("overall_explanation", sa.Text(), nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("raw_ai_response", sa.Text(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["statement_id"], ["statements.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("statement_id"),
    )
    op.create_table(
        "appeals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("statement_id", sa.Uuid(), nullable=False),
        sa.Column("submitter_name", sa.String(length=255), nullable=True),
        sa.Column("submitter_email", sa.String(length=255), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["statement_id"], ["statements.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "statement_media_assets",
        sa.Column("statement_id", sa.Uuid(), nullable=False),
        sa.Column("media_asset_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["media_asset_id"], ["media_assets.id"]),
        sa.ForeignKeyConstraint(["statement_id"], ["statements.id"]),
        sa.PrimaryKeyConstraint("statement_id", "media_asset_id"),
    )


def downgrade() -> None:
    op.drop_table("statement_media_assets")
    op.drop_table("appeals")
    op.drop_table("ai_analyses")
    op.drop_index(op.f("ix_statements_status"), table_name="statements")
    op.drop_table("statements")
    op.drop_table("party_memberships")
    op.drop_index(op.f("ix_audit_logs_action"), table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_table("media_assets")
    op.drop_index(op.f("ix_politicians_slug"), table_name="politicians")
    op.drop_table("politicians")
    op.drop_index(op.f("ix_political_parties_slug"), table_name="political_parties")
    op.drop_table("political_parties")
    op.drop_index(op.f("ix_moderators_username"), table_name="moderators")
    op.drop_table("moderators")
