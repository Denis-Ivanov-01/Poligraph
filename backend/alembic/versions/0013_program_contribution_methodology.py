"""program contribution methodology

Revision ID: 0013_contribution_method
Revises: 0012_section_commitment_idx
Create Date: 2026-07-12 11:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0013_contribution_method"
down_revision = "0012_section_commitment_idx"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS commitment_type VARCHAR(80)")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS promised_item_type VARCHAR(80)")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS baseline_mode VARCHAR(80)")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS required_external_actors TEXT")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS control_level VARCHAR(80)")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS evaluation_basis TEXT")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS contribution_types_text TEXT")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS official_program_change_note TEXT")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS source_version_note TEXT")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS quantitative_target TEXT")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS quantitative_actual TEXT")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS measure_validity_status VARCHAR(80)")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS contribution_level VARCHAR(80) NOT NULL DEFAULT 'indeterminate'")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS contribution_explanation TEXT")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS contribution_confidence VARCHAR(80)")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS importance_level VARCHAR(40) NOT NULL DEFAULT 'standard'")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS importance_weight INTEGER NOT NULL DEFAULT 2")
    op.execute("CREATE INDEX IF NOT EXISTS ix_commitments_commitment_type ON commitments (commitment_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_commitments_promised_item_type ON commitments (promised_item_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_commitments_baseline_mode ON commitments (baseline_mode)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_commitments_control_level ON commitments (control_level)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_commitments_measure_validity_status ON commitments (measure_validity_status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_commitments_contribution_level ON commitments (contribution_level)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_commitments_contribution_confidence ON commitments (contribution_confidence)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_commitments_importance_level ON commitments (importance_level)")

    op.execute("ALTER TABLE commitment_status_updates ADD COLUMN IF NOT EXISTS previous_contribution_level VARCHAR(80)")
    op.execute("ALTER TABLE commitment_status_updates ADD COLUMN IF NOT EXISTS new_contribution_level VARCHAR(80)")
    op.execute("ALTER TABLE commitment_status_updates ADD COLUMN IF NOT EXISTS contribution_explanation TEXT")
    op.execute("ALTER TABLE commitment_status_updates ADD COLUMN IF NOT EXISTS contribution_confidence VARCHAR(40)")

    op.execute("ALTER TABLE commitment_evidence_links ADD COLUMN IF NOT EXISTS evidence_role VARCHAR(80)")
    op.execute("ALTER TABLE commitment_evidence_links ADD COLUMN IF NOT EXISTS evidence_strength VARCHAR(40)")
    op.execute("ALTER TABLE commitment_evidence_links ADD COLUMN IF NOT EXISTS is_self_reported BOOLEAN NOT NULL DEFAULT false")
    op.execute("ALTER TABLE commitment_evidence_links ADD COLUMN IF NOT EXISTS is_independent_confirmation BOOLEAN NOT NULL DEFAULT false")
    op.execute("ALTER TABLE commitment_evidence_links ADD COLUMN IF NOT EXISTS is_contradictory BOOLEAN NOT NULL DEFAULT false")
    op.execute("ALTER TABLE commitment_evidence_links ADD COLUMN IF NOT EXISTS is_disproven BOOLEAN NOT NULL DEFAULT false")
    op.execute("ALTER TABLE commitment_evidence_links ADD COLUMN IF NOT EXISTS limitations TEXT")
    op.execute("CREATE INDEX IF NOT EXISTS ix_commitment_evidence_links_evidence_role ON commitment_evidence_links (evidence_role)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_commitment_evidence_links_evidence_strength ON commitment_evidence_links (evidence_strength)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_commitment_evidence_links_is_self_reported ON commitment_evidence_links (is_self_reported)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_commitment_evidence_links_is_independent_confirmation "
        "ON commitment_evidence_links (is_independent_confirmation)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_commitment_evidence_links_is_contradictory ON commitment_evidence_links (is_contradictory)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_commitment_evidence_links_is_disproven ON commitment_evidence_links (is_disproven)")


def downgrade() -> None:
    op.drop_index("ix_commitment_evidence_links_is_disproven", table_name="commitment_evidence_links")
    op.drop_index("ix_commitment_evidence_links_is_contradictory", table_name="commitment_evidence_links")
    op.drop_index("ix_commitment_evidence_links_is_independent_confirmation", table_name="commitment_evidence_links")
    op.drop_index("ix_commitment_evidence_links_is_self_reported", table_name="commitment_evidence_links")
    op.drop_index("ix_commitment_evidence_links_evidence_strength", table_name="commitment_evidence_links")
    op.drop_index("ix_commitment_evidence_links_evidence_role", table_name="commitment_evidence_links")
    op.drop_column("commitment_evidence_links", "limitations")
    op.drop_column("commitment_evidence_links", "is_disproven")
    op.drop_column("commitment_evidence_links", "is_contradictory")
    op.drop_column("commitment_evidence_links", "is_independent_confirmation")
    op.drop_column("commitment_evidence_links", "is_self_reported")
    op.drop_column("commitment_evidence_links", "evidence_strength")
    op.drop_column("commitment_evidence_links", "evidence_role")

    op.drop_column("commitment_status_updates", "contribution_confidence")
    op.drop_column("commitment_status_updates", "contribution_explanation")
    op.drop_column("commitment_status_updates", "new_contribution_level")
    op.drop_column("commitment_status_updates", "previous_contribution_level")

    op.drop_index("ix_commitments_importance_level", table_name="commitments")
    op.drop_index("ix_commitments_contribution_confidence", table_name="commitments")
    op.drop_index("ix_commitments_contribution_level", table_name="commitments")
    op.drop_index("ix_commitments_measure_validity_status", table_name="commitments")
    op.drop_index("ix_commitments_control_level", table_name="commitments")
    op.drop_index("ix_commitments_baseline_mode", table_name="commitments")
    op.drop_index("ix_commitments_promised_item_type", table_name="commitments")
    op.drop_index("ix_commitments_commitment_type", table_name="commitments")
    op.drop_column("commitments", "importance_weight")
    op.drop_column("commitments", "importance_level")
    op.drop_column("commitments", "contribution_confidence")
    op.drop_column("commitments", "contribution_explanation")
    op.drop_column("commitments", "contribution_level")
    op.drop_column("commitments", "measure_validity_status")
    op.drop_column("commitments", "quantitative_actual")
    op.drop_column("commitments", "quantitative_target")
    op.drop_column("commitments", "source_version_note")
    op.drop_column("commitments", "official_program_change_note")
    op.drop_column("commitments", "contribution_types_text")
    op.drop_column("commitments", "evaluation_basis")
    op.drop_column("commitments", "control_level")
    op.drop_column("commitments", "required_external_actors")
    op.drop_column("commitments", "baseline_mode")
    op.drop_column("commitments", "promised_item_type")
    op.drop_column("commitments", "commitment_type")
