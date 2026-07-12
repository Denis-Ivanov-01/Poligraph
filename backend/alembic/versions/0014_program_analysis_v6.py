"""Add item-level program analysis batches and v6 analytical fields.

Revision ID: 0014_program_analysis_v6
Revises: 0013_contribution_method
Create Date: 2026-07-12 16:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0014_program_analysis_v6"
down_revision = "0013_contribution_method"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ai_runs", sa.Column("methodology_version", sa.String(length=80), nullable=True))
    op.add_column("ai_runs", sa.Column("parent_ai_run_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("ai_runs", sa.Column("batch_item_ref", sa.String(length=80), nullable=True))
    op.add_column("ai_runs", sa.Column("batch_position", sa.Integer(), nullable=True))
    op.add_column("ai_runs", sa.Column("expected_item_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("ai_runs", sa.Column("completed_item_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("ai_runs", sa.Column("failed_item_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("ai_runs", sa.Column("human_review_item_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("ai_runs", sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("ai_runs", sa.Column("validation_errors", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("ai_runs", sa.Column("telemetry", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("ai_runs", sa.Column("input_tokens", sa.Integer(), nullable=True))
    op.add_column("ai_runs", sa.Column("output_tokens", sa.Integer(), nullable=True))
    op.add_column("ai_runs", sa.Column("tool_call_count", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_ai_runs_parent_ai_run_id", "ai_runs", "ai_runs", ["parent_ai_run_id"], ["id"])
    op.create_index("ix_ai_runs_parent_ai_run_id", "ai_runs", ["parent_ai_run_id"])
    op.create_index("ix_ai_runs_batch_item_ref", "ai_runs", ["batch_item_ref"])

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


def downgrade() -> None:
    op.drop_column("commitment_evidence_links", "component_refs")
    op.drop_column("commitment_evidence_links", "claim_text")

    op.drop_column("commitment_status_updates", "methodology_version")
    op.drop_column("commitment_status_updates", "analysis_quality_flags")
    op.drop_column("commitment_status_updates", "human_review_reasons")
    op.drop_column("commitment_status_updates", "human_review_recommended")
    op.drop_column("commitment_status_updates", "missing_or_uncertain_evidence")
    op.drop_column("commitment_status_updates", "material_components")

    op.drop_index("ix_commitments_human_review_recommended", table_name="commitments")
    op.drop_index("ix_commitments_conclusion_basis", table_name="commitments")
    op.drop_index("ix_commitments_material_implementation_status", table_name="commitments")
    op.drop_index("ix_commitments_formal_implementation_status", table_name="commitments")
    op.drop_column("commitments", "analysis_methodology_version")
    op.drop_column("commitments", "analysis_quality_flags")
    op.drop_column("commitments", "human_review_reasons")
    op.drop_column("commitments", "human_review_recommended")
    op.drop_column("commitments", "quantitative_actual_as_of")
    op.drop_column("commitments", "contribution_applies_to_component_refs")
    op.drop_column("commitments", "contribution_counterfactual")
    op.drop_column("commitments", "missing_or_uncertain_evidence")
    op.drop_column("commitments", "conclusion_basis")
    op.drop_column("commitments", "material_implementation_status")
    op.drop_column("commitments", "formal_implementation_status")
    op.drop_column("commitments", "control_level_explanation")
    op.drop_column("commitments", "baseline_explanation")
    op.drop_column("commitments", "material_components")

    op.drop_index("ix_ai_runs_batch_item_ref", table_name="ai_runs")
    op.drop_index("ix_ai_runs_parent_ai_run_id", table_name="ai_runs")
    op.drop_constraint("fk_ai_runs_parent_ai_run_id", "ai_runs", type_="foreignkey")
    op.drop_column("ai_runs", "tool_call_count")
    op.drop_column("ai_runs", "output_tokens")
    op.drop_column("ai_runs", "input_tokens")
    op.drop_column("ai_runs", "telemetry")
    op.drop_column("ai_runs", "validation_errors")
    op.drop_column("ai_runs", "retry_count")
    op.drop_column("ai_runs", "human_review_item_count")
    op.drop_column("ai_runs", "failed_item_count")
    op.drop_column("ai_runs", "completed_item_count")
    op.drop_column("ai_runs", "expected_item_count")
    op.drop_column("ai_runs", "batch_position")
    op.drop_column("ai_runs", "batch_item_ref")
    op.drop_column("ai_runs", "parent_ai_run_id")
    op.drop_column("ai_runs", "methodology_version")
