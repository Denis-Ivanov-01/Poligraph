"""Add programs and commitments.

Revision ID: 0005_programs_commitments
Revises: 0004_statement_title_nullable
Create Date: 2026-07-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_programs_commitments"
down_revision: str | None = "0004_statement_title_nullable"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "programs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=140), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("program_type", sa.String(length=80), nullable=False),
        sa.Column("political_subject_name", sa.String(length=255), nullable=False),
        sa.Column("related_party_id", sa.Uuid(), nullable=True),
        sa.Column("related_coalition_name", sa.String(length=255), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("source_title", sa.String(length=255), nullable=True),
        sa.Column("source_description", sa.Text(), nullable=True),
        sa.Column("is_active_government_program", sa.Boolean(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["related_party_id"], ["political_parties.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_programs_is_active_government_program"), "programs", ["is_active_government_program"], unique=False)
    op.create_index(op.f("ix_programs_is_published"), "programs", ["is_published"], unique=False)
    op.create_index(op.f("ix_programs_program_type"), "programs", ["program_type"], unique=False)
    op.create_index(op.f("ix_programs_slug"), "programs", ["slug"], unique=True)
    op.create_index(
        "uq_programs_one_active_government_program",
        "programs",
        ["is_active_government_program"],
        unique=True,
        postgresql_where=sa.text("is_active_government_program = true"),
    )

    op.create_table(
        "commitments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("program_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("normalized_description", sa.Text(), nullable=True),
        sa.Column("political_subject_name", sa.String(length=255), nullable=True),
        sa.Column("related_party_id", sa.Uuid(), nullable=True),
        sa.Column("related_coalition_name", sa.String(length=255), nullable=True),
        sa.Column("topic", sa.String(length=160), nullable=True),
        sa.Column("responsible_institutions", sa.Text(), nullable=True),
        sa.Column("period", sa.String(length=160), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("measurable_criteria", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("status_group", sa.String(length=80), nullable=False),
        sa.Column("status_explanation", sa.Text(), nullable=True),
        sa.Column("confidence_level", sa.String(length=80), nullable=False),
        sa.Column("confidence_explanation", sa.Text(), nullable=True),
        sa.Column("last_status_update", sa.Date(), nullable=True),
        sa.Column("is_key_commitment", sa.Boolean(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"]),
        sa.ForeignKeyConstraint(["related_party_id"], ["political_parties.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_commitments_is_key_commitment"), "commitments", ["is_key_commitment"], unique=False)
    op.create_index(op.f("ix_commitments_is_published"), "commitments", ["is_published"], unique=False)
    op.create_index(op.f("ix_commitments_program_id"), "commitments", ["program_id"], unique=False)
    op.create_index(op.f("ix_commitments_slug"), "commitments", ["slug"], unique=True)
    op.create_index(op.f("ix_commitments_status"), "commitments", ["status"], unique=False)
    op.create_index(op.f("ix_commitments_status_group"), "commitments", ["status_group"], unique=False)
    op.create_index(op.f("ix_commitments_topic"), "commitments", ["topic"], unique=False)
    op.create_index(op.f("ix_commitments_confidence_level"), "commitments", ["confidence_level"], unique=False)

    op.create_table(
        "commitment_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("commitment_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=True),
        sa.Column("source_type", sa.String(length=100), nullable=False),
        sa.Column("publisher", sa.String(length=255), nullable=True),
        sa.Column("published_at", sa.Date(), nullable=True),
        sa.Column("quote_or_relevant_excerpt", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("supports_status", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["commitment_id"], ["commitments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_commitment_evidence_commitment_id"), "commitment_evidence", ["commitment_id"], unique=False)
    op.create_index(op.f("ix_commitment_evidence_source_type"), "commitment_evidence", ["source_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_commitment_evidence_source_type"), table_name="commitment_evidence")
    op.drop_index(op.f("ix_commitment_evidence_commitment_id"), table_name="commitment_evidence")
    op.drop_table("commitment_evidence")
    op.drop_index(op.f("ix_commitments_confidence_level"), table_name="commitments")
    op.drop_index(op.f("ix_commitments_topic"), table_name="commitments")
    op.drop_index(op.f("ix_commitments_status_group"), table_name="commitments")
    op.drop_index(op.f("ix_commitments_status"), table_name="commitments")
    op.drop_index(op.f("ix_commitments_slug"), table_name="commitments")
    op.drop_index(op.f("ix_commitments_program_id"), table_name="commitments")
    op.drop_index(op.f("ix_commitments_is_published"), table_name="commitments")
    op.drop_index(op.f("ix_commitments_is_key_commitment"), table_name="commitments")
    op.drop_table("commitments")
    op.drop_index("uq_programs_one_active_government_program", table_name="programs", postgresql_where=sa.text("is_active_government_program = true"))
    op.drop_index(op.f("ix_programs_slug"), table_name="programs")
    op.drop_index(op.f("ix_programs_program_type"), table_name="programs")
    op.drop_index(op.f("ix_programs_is_published"), table_name="programs")
    op.drop_index(op.f("ix_programs_is_active_government_program"), table_name="programs")
    op.drop_table("programs")
