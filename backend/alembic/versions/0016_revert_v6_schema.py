"""Revert v6 prompt-only analytical schema fields.

Revision ID: 0016_revert_v6_schema
Revises: 0015_importance_weight_sync
Create Date: 2026-07-12
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0016_revert_v6_schema"
down_revision: str | None = "0015_importance_weight_sync"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE commitment_evidence_links DROP COLUMN IF EXISTS component_refs")
    op.execute("ALTER TABLE commitment_evidence_links DROP COLUMN IF EXISTS claim_text")

    op.execute("ALTER TABLE commitment_status_updates DROP COLUMN IF EXISTS methodology_version")
    op.execute("ALTER TABLE commitment_status_updates DROP COLUMN IF EXISTS analysis_quality_flags")
    op.execute("ALTER TABLE commitment_status_updates DROP COLUMN IF EXISTS human_review_reasons")
    op.execute("ALTER TABLE commitment_status_updates DROP COLUMN IF EXISTS human_review_recommended")
    op.execute("ALTER TABLE commitment_status_updates DROP COLUMN IF EXISTS missing_or_uncertain_evidence")
    op.execute("ALTER TABLE commitment_status_updates DROP COLUMN IF EXISTS material_components")

    op.execute("DROP INDEX IF EXISTS ix_commitments_human_review_recommended")
    op.execute("DROP INDEX IF EXISTS ix_commitments_conclusion_basis")
    op.execute("DROP INDEX IF EXISTS ix_commitments_material_implementation_status")
    op.execute("DROP INDEX IF EXISTS ix_commitments_formal_implementation_status")
    op.execute("ALTER TABLE commitments DROP COLUMN IF EXISTS analysis_methodology_version")
    op.execute("ALTER TABLE commitments DROP COLUMN IF EXISTS analysis_quality_flags")
    op.execute("ALTER TABLE commitments DROP COLUMN IF EXISTS human_review_reasons")
    op.execute("ALTER TABLE commitments DROP COLUMN IF EXISTS human_review_recommended")
    op.execute("ALTER TABLE commitments DROP COLUMN IF EXISTS quantitative_actual_as_of")
    op.execute("ALTER TABLE commitments DROP COLUMN IF EXISTS contribution_applies_to_component_refs")
    op.execute("ALTER TABLE commitments DROP COLUMN IF EXISTS contribution_counterfactual")
    op.execute("ALTER TABLE commitments DROP COLUMN IF EXISTS missing_or_uncertain_evidence")
    op.execute("ALTER TABLE commitments DROP COLUMN IF EXISTS conclusion_basis")
    op.execute("ALTER TABLE commitments DROP COLUMN IF EXISTS material_implementation_status")
    op.execute("ALTER TABLE commitments DROP COLUMN IF EXISTS formal_implementation_status")
    op.execute("ALTER TABLE commitments DROP COLUMN IF EXISTS control_level_explanation")
    op.execute("ALTER TABLE commitments DROP COLUMN IF EXISTS baseline_explanation")
    op.execute("ALTER TABLE commitments DROP COLUMN IF EXISTS material_components")


def downgrade() -> None:
    op.add_column("commitments", sa.Column("material_components", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("commitments", sa.Column("baseline_explanation", sa.Text(), nullable=True))
    op.add_column("commitments", sa.Column("control_level_explanation", sa.Text(), nullable=True))
    op.add_column("commitments", sa.Column("formal_implementation_status", sa.String(length=40), nullable=True))
    op.add_column("commitments", sa.Column("material_implementation_status", sa.String(length=40), nullable=True))
    op.add_column("commitments", sa.Column("conclusion_basis", sa.String(length=40), nullable=True))
    op.add_column("commitments", sa.Column("missing_or_uncertain_evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("commitments", sa.Column("contribution_counterfactual", sa.Text(), nullable=True))
    op.add_column("commitments", sa.Column("contribution_applies_to_component_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("commitments", sa.Column("quantitative_actual_as_of", sa.Date(), nullable=True))
    op.add_column("commitments", sa.Column("human_review_recommended", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("commitments", sa.Column("human_review_reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("commitments", sa.Column("analysis_quality_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("commitments", sa.Column("analysis_methodology_version", sa.String(length=80), nullable=True))
    op.create_index("ix_commitments_formal_implementation_status", "commitments", ["formal_implementation_status"])
    op.create_index("ix_commitments_material_implementation_status", "commitments", ["material_implementation_status"])
    op.create_index("ix_commitments_conclusion_basis", "commitments", ["conclusion_basis"])
    op.create_index("ix_commitments_human_review_recommended", "commitments", ["human_review_recommended"])

    op.add_column("commitment_status_updates", sa.Column("material_components", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("commitment_status_updates", sa.Column("missing_or_uncertain_evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("commitment_status_updates", sa.Column("human_review_recommended", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("commitment_status_updates", sa.Column("human_review_reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("commitment_status_updates", sa.Column("analysis_quality_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("commitment_status_updates", sa.Column("methodology_version", sa.String(length=80), nullable=True))

    op.add_column("commitment_evidence_links", sa.Column("claim_text", sa.Text(), nullable=True))
    op.add_column("commitment_evidence_links", sa.Column("component_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
