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
    op.execute("ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS methodology_version VARCHAR(80)")
    op.execute("ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS parent_ai_run_id UUID")
    op.execute("ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS batch_item_ref VARCHAR(80)")
    op.execute("ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS batch_position INTEGER")
    op.execute("ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS expected_item_count INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS completed_item_count INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS failed_item_count INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS human_review_item_count INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS retry_count INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS validation_errors JSONB")
    op.execute("ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS telemetry JSONB")
    op.execute("ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS input_tokens INTEGER")
    op.execute("ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS output_tokens INTEGER")
    op.execute("ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS tool_call_count INTEGER")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conrelid = 'ai_runs'::regclass
                  AND contype = 'f'
                  AND conkey = ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid = 'ai_runs'::regclass AND attname = 'parent_ai_run_id')]
            ) THEN
                ALTER TABLE ai_runs
                ADD CONSTRAINT fk_ai_runs_parent_ai_run_id
                FOREIGN KEY (parent_ai_run_id) REFERENCES ai_runs(id);
            END IF;
        END $$;
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_runs_parent_ai_run_id ON ai_runs (parent_ai_run_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_runs_batch_item_ref ON ai_runs (batch_item_ref)")

    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS material_components JSONB")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS baseline_explanation TEXT")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS control_level_explanation TEXT")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS formal_implementation_status VARCHAR(40)")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS material_implementation_status VARCHAR(40)")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS conclusion_basis VARCHAR(40)")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS missing_or_uncertain_evidence JSONB")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS contribution_counterfactual TEXT")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS contribution_applies_to_component_refs JSONB")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS quantitative_actual_as_of DATE")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS human_review_recommended BOOLEAN NOT NULL DEFAULT false")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS human_review_reasons JSONB")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS analysis_quality_flags JSONB")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS analysis_methodology_version VARCHAR(80)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_commitments_formal_implementation_status ON commitments (formal_implementation_status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_commitments_material_implementation_status ON commitments (material_implementation_status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_commitments_conclusion_basis ON commitments (conclusion_basis)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_commitments_human_review_recommended ON commitments (human_review_recommended)")

    op.execute("ALTER TABLE commitment_status_updates ADD COLUMN IF NOT EXISTS material_components JSONB")
    op.execute("ALTER TABLE commitment_status_updates ADD COLUMN IF NOT EXISTS missing_or_uncertain_evidence JSONB")
    op.execute("ALTER TABLE commitment_status_updates ADD COLUMN IF NOT EXISTS human_review_recommended BOOLEAN NOT NULL DEFAULT false")
    op.execute("ALTER TABLE commitment_status_updates ADD COLUMN IF NOT EXISTS human_review_reasons JSONB")
    op.execute("ALTER TABLE commitment_status_updates ADD COLUMN IF NOT EXISTS analysis_quality_flags JSONB")
    op.execute("ALTER TABLE commitment_status_updates ADD COLUMN IF NOT EXISTS methodology_version VARCHAR(80)")

    op.execute("ALTER TABLE commitment_evidence_links ADD COLUMN IF NOT EXISTS claim_text TEXT")
    op.execute("ALTER TABLE commitment_evidence_links ADD COLUMN IF NOT EXISTS component_refs JSONB")


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
