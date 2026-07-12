"""Add immutable program AI run inputs and source coverage metadata.

Revision ID: 0011_program_ai_run_integrity
Revises: 0010_legacy_commitment_defaults
Create Date: 2026-07-11
"""

from collections.abc import Sequence

from alembic import op


revision: str = "0011_program_ai_run_integrity"
down_revision: str | None = "0010_legacy_commitment_defaults"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE programs ADD COLUMN IF NOT EXISTS source_acquisition_method VARCHAR(80)")
    op.execute("ALTER TABLE programs ADD COLUMN IF NOT EXISTS source_coverage_status VARCHAR(40)")
    op.execute("ALTER TABLE programs ADD COLUMN IF NOT EXISTS source_acquisition_note TEXT")
    op.execute("ALTER TABLE programs ADD COLUMN IF NOT EXISTS source_document_complete BOOLEAN")
    op.execute("ALTER TABLE programs ADD COLUMN IF NOT EXISTS supplementary_source_urls JSONB")
    op.execute("CREATE INDEX IF NOT EXISTS ix_programs_source_acquisition_method ON programs (source_acquisition_method)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_programs_source_coverage_status ON programs (source_coverage_status)")

    op.execute("ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS import_error TEXT")
    op.execute("ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS input_snapshot JSONB")
    op.execute("ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS local_ref_map JSONB")
    op.execute("ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS input_fingerprint VARCHAR(64)")
    op.execute("ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS analysis_date DATE")
    op.execute("ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS validated_at TIMESTAMP WITH TIME ZONE")
    op.execute("ALTER TABLE ai_runs ADD COLUMN IF NOT EXISTS imported_at TIMESTAMP WITH TIME ZONE")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_runs_input_fingerprint ON ai_runs (input_fingerprint)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_runs_imported_at ON ai_runs (imported_at)")

    op.execute(
        """
        DELETE FROM commitment_evidence_links newer
        USING commitment_evidence_links older
        WHERE newer.id > older.id
          AND newer.status_update_id IS NOT NULL
          AND newer.status_update_id = older.status_update_id
          AND newer.evidence_item_id = older.evidence_item_id
          AND newer.relation_type = older.relation_type
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_commitment_evidence_link_update_evidence_relation'
            ) THEN
                ALTER TABLE commitment_evidence_links
                ADD CONSTRAINT uq_commitment_evidence_link_update_evidence_relation
                UNIQUE (status_update_id, evidence_item_id, relation_type);
            END IF;
        END $$;
        """
    )

    op.execute("DROP INDEX IF EXISTS ix_commitments_status")
    op.execute("DROP INDEX IF EXISTS ix_commitments_confidence_level")
    op.execute("ALTER TABLE commitments DROP COLUMN IF EXISTS status")
    op.execute("ALTER TABLE commitments DROP COLUMN IF EXISTS confidence_level")
    op.execute("ALTER TABLE commitments DROP COLUMN IF EXISTS period")
    op.execute("ALTER TABLE commitment_status_updates DROP COLUMN IF EXISTS update_date")
    op.execute("ALTER TABLE commitment_status_updates DROP COLUMN IF EXISTS confidence_level")


def downgrade() -> None:
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS period VARCHAR(160)")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS status VARCHAR(80)")
    op.execute("UPDATE commitments SET status = current_status WHERE status IS NULL")
    op.execute("ALTER TABLE commitments ALTER COLUMN status SET DEFAULT 'not_analyzed'")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS confidence_level VARCHAR(80)")
    op.execute("UPDATE commitments SET confidence_level = confidence WHERE confidence_level IS NULL")
    op.execute("ALTER TABLE commitments ALTER COLUMN confidence_level SET DEFAULT 'medium'")
    op.execute("CREATE INDEX IF NOT EXISTS ix_commitments_status ON commitments (status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_commitments_confidence_level ON commitments (confidence_level)")
    op.execute("ALTER TABLE commitment_status_updates ADD COLUMN IF NOT EXISTS update_date DATE")
    op.execute("UPDATE commitment_status_updates SET update_date = effective_date WHERE update_date IS NULL")
    op.execute("ALTER TABLE commitment_status_updates ADD COLUMN IF NOT EXISTS confidence_level VARCHAR(80)")
    op.execute("UPDATE commitment_status_updates SET confidence_level = confidence WHERE confidence_level IS NULL")

    op.execute("ALTER TABLE commitment_evidence_links DROP CONSTRAINT IF EXISTS uq_commitment_evidence_link_update_evidence_relation")
    op.execute("DROP INDEX IF EXISTS ix_ai_runs_imported_at")
    op.execute("DROP INDEX IF EXISTS ix_ai_runs_input_fingerprint")
    op.execute("ALTER TABLE ai_runs DROP COLUMN IF EXISTS imported_at")
    op.execute("ALTER TABLE ai_runs DROP COLUMN IF EXISTS validated_at")
    op.execute("ALTER TABLE ai_runs DROP COLUMN IF EXISTS analysis_date")
    op.execute("ALTER TABLE ai_runs DROP COLUMN IF EXISTS input_fingerprint")
    op.execute("ALTER TABLE ai_runs DROP COLUMN IF EXISTS local_ref_map")
    op.execute("ALTER TABLE ai_runs DROP COLUMN IF EXISTS input_snapshot")
    op.execute("ALTER TABLE ai_runs DROP COLUMN IF EXISTS import_error")

    op.execute("DROP INDEX IF EXISTS ix_programs_source_coverage_status")
    op.execute("DROP INDEX IF EXISTS ix_programs_source_acquisition_method")
    op.execute("ALTER TABLE programs DROP COLUMN IF EXISTS supplementary_source_urls")
    op.execute("ALTER TABLE programs DROP COLUMN IF EXISTS source_document_complete")
    op.execute("ALTER TABLE programs DROP COLUMN IF EXISTS source_acquisition_note")
    op.execute("ALTER TABLE programs DROP COLUMN IF EXISTS source_coverage_status")
    op.execute("ALTER TABLE programs DROP COLUMN IF EXISTS source_acquisition_method")
