"""Bring existing program workflow tables up to the multistage model.

Revision ID: 0009_program_multistage_workflow
Revises: 0008_mvp_redesign
Create Date: 2026-07-10
"""

from collections.abc import Sequence

from alembic import op


revision: str = "0009_program_multistage_workflow"
down_revision: str | None = "0008_mvp_redesign"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _add_fk_if_missing(name: str, table: str, column: str, target_table: str, target_column: str = "id") -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = '{name}') THEN
                ALTER TABLE {table}
                ADD CONSTRAINT {name}
                FOREIGN KEY ({column}) REFERENCES {target_table}({target_column});
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    op.execute("ALTER TABLE programs ADD COLUMN IF NOT EXISTS short_description TEXT")
    op.execute("ALTER TABLE programs ADD COLUMN IF NOT EXISTS internal_notes TEXT")
    op.execute("ALTER TABLE programs ADD COLUMN IF NOT EXISTS period_text VARCHAR(160)")
    op.execute("ALTER TABLE programs ADD COLUMN IF NOT EXISTS publication_date DATE")
    op.execute("ALTER TABLE programs ADD COLUMN IF NOT EXISTS status VARCHAR(60) NOT NULL DEFAULT 'draft'")
    op.execute("ALTER TABLE programs ADD COLUMN IF NOT EXISTS structural_review_status VARCHAR(40) NOT NULL DEFAULT 'not_reviewed'")
    op.execute("ALTER TABLE programs ADD COLUMN IF NOT EXISTS structural_review_note TEXT")
    op.execute("ALTER TABLE programs ADD COLUMN IF NOT EXISTS factual_review_status VARCHAR(40) NOT NULL DEFAULT 'not_reviewed'")
    op.execute("ALTER TABLE programs ADD COLUMN IF NOT EXISTS factual_review_note TEXT")
    op.execute("ALTER TABLE programs ADD COLUMN IF NOT EXISTS published_at TIMESTAMP WITH TIME ZONE")
    op.execute("CREATE INDEX IF NOT EXISTS ix_programs_status ON programs (status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_programs_structural_review_status ON programs (structural_review_status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_programs_factual_review_status ON programs (factual_review_status)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS program_media_assets (
            program_id UUID NOT NULL REFERENCES programs(id),
            media_asset_id UUID NOT NULL REFERENCES media_assets(id),
            document_role VARCHAR(80) NOT NULL DEFAULT 'source_document',
            display_order INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            PRIMARY KEY (program_id, media_asset_id)
        )
        """
    )

    op.execute("ALTER TABLE program_sections ADD COLUMN IF NOT EXISTS parent_section_id UUID")
    op.execute("ALTER TABLE program_sections ADD COLUMN IF NOT EXISTS section_code VARCHAR(80)")
    op.execute("ALTER TABLE program_sections ADD COLUMN IF NOT EXISTS original_heading VARCHAR(255)")
    op.execute("ALTER TABLE program_sections ADD COLUMN IF NOT EXISTS problem_description TEXT")
    op.execute("ALTER TABLE program_sections ADD COLUMN IF NOT EXISTS aggregate_status_summary TEXT")
    op.execute("ALTER TABLE program_sections ADD COLUMN IF NOT EXISTS key_findings JSONB")
    op.execute("ALTER TABLE program_sections ADD COLUMN IF NOT EXISTS policy_area VARCHAR(160)")
    op.execute("ALTER TABLE program_sections ADD COLUMN IF NOT EXISTS source_origin VARCHAR(40) NOT NULL DEFAULT 'manual'")
    op.execute("ALTER TABLE program_sections ADD COLUMN IF NOT EXISTS import_ref VARCHAR(80)")
    op.execute("ALTER TABLE program_sections ADD COLUMN IF NOT EXISTS structural_status VARCHAR(40) NOT NULL DEFAULT 'draft'")
    op.execute("ALTER TABLE program_sections ADD COLUMN IF NOT EXISTS factual_review_status VARCHAR(40) NOT NULL DEFAULT 'not_reviewed'")
    _add_fk_if_missing("fk_program_sections_parent_section_id", "program_sections", "parent_section_id", "program_sections")
    op.execute("CREATE INDEX IF NOT EXISTS ix_program_sections_parent_section_id ON program_sections (parent_section_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_program_sections_policy_area ON program_sections (policy_area)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_program_sections_source_origin ON program_sections (source_origin)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_program_sections_import_ref ON program_sections (import_ref)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_program_sections_structural_status ON program_sections (structural_status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_program_sections_factual_review_status ON program_sections (factual_review_status)")

    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS parent_commitment_id UUID")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS import_ref VARCHAR(80)")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS display_code VARCHAR(80)")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS period_text VARCHAR(160)")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'commitments' AND column_name = 'period'
            ) THEN
                UPDATE commitments SET period_text = period WHERE period_text IS NULL;
            END IF;
        END $$;
        """
    )
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS current_status VARCHAR(80) NOT NULL DEFAULT 'not_started'")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'commitments' AND column_name = 'status'
            ) THEN
                UPDATE commitments
                SET current_status = CASE status
                    WHEN 'broken' THEN 'violated'
                    WHEN 'blocked' THEN 'unclear'
                    WHEN 'insufficient_data' THEN 'unclear'
                    ELSE status
                END;
            END IF;
        END $$;
        """
    )
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS confidence VARCHAR(80) NOT NULL DEFAULT 'medium'")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'commitments' AND column_name = 'confidence_level'
            ) THEN
                UPDATE commitments
                SET confidence = CASE confidence_level
                    WHEN 'insufficient_data' THEN 'low'
                    ELSE confidence_level
                END;
            END IF;
        END $$;
        """
    )
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS materiality_reason TEXT")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS source_origin VARCHAR(40) NOT NULL DEFAULT 'manual'")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS structural_status VARCHAR(40) NOT NULL DEFAULT 'draft'")
    op.execute("ALTER TABLE commitments ADD COLUMN IF NOT EXISTS factual_review_status VARCHAR(40) NOT NULL DEFAULT 'not_reviewed'")
    _add_fk_if_missing("fk_commitments_parent_commitment_id", "commitments", "parent_commitment_id", "commitments")
    op.execute("CREATE INDEX IF NOT EXISTS ix_commitments_parent_commitment_id ON commitments (parent_commitment_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_commitments_import_ref ON commitments (import_ref)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_commitments_current_status ON commitments (current_status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_commitments_confidence ON commitments (confidence)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_commitments_source_origin ON commitments (source_origin)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_commitments_structural_status ON commitments (structural_status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_commitments_factual_review_status ON commitments (factual_review_status)")

    op.execute("ALTER TABLE commitment_status_updates ADD COLUMN IF NOT EXISTS effective_date DATE")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'commitment_status_updates' AND column_name = 'update_date'
            ) THEN
                UPDATE commitment_status_updates SET effective_date = update_date WHERE effective_date IS NULL;
            END IF;
        END $$;
        """
    )
    op.execute("ALTER TABLE commitment_status_updates ADD COLUMN IF NOT EXISTS confidence VARCHAR(40) NOT NULL DEFAULT 'medium'")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'commitment_status_updates' AND column_name = 'confidence_level'
            ) THEN
                UPDATE commitment_status_updates SET confidence = confidence_level;
            END IF;
        END $$;
        """
    )
    op.execute("ALTER TABLE commitment_status_updates ADD COLUMN IF NOT EXISTS update_reason TEXT")
    op.execute("ALTER TABLE commitment_status_updates ADD COLUMN IF NOT EXISTS source_origin VARCHAR(40) NOT NULL DEFAULT 'manual'")
    op.execute("ALTER TABLE commitment_status_updates ADD COLUMN IF NOT EXISTS structural_status VARCHAR(40) NOT NULL DEFAULT 'parsed'")
    op.execute("ALTER TABLE commitment_status_updates ADD COLUMN IF NOT EXISTS factual_review_status VARCHAR(40) NOT NULL DEFAULT 'not_reviewed'")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS program_media_assets")
    op.execute("ALTER TABLE commitment_status_updates DROP COLUMN IF EXISTS factual_review_status")
    op.execute("ALTER TABLE commitment_status_updates DROP COLUMN IF EXISTS structural_status")
    op.execute("ALTER TABLE commitment_status_updates DROP COLUMN IF EXISTS source_origin")
    op.execute("ALTER TABLE commitment_status_updates DROP COLUMN IF EXISTS update_reason")
    op.execute("ALTER TABLE commitment_status_updates DROP COLUMN IF EXISTS confidence")
    op.execute("ALTER TABLE commitment_status_updates DROP COLUMN IF EXISTS effective_date")
    op.execute("ALTER TABLE commitments DROP COLUMN IF EXISTS factual_review_status")
    op.execute("ALTER TABLE commitments DROP COLUMN IF EXISTS structural_status")
    op.execute("ALTER TABLE commitments DROP COLUMN IF EXISTS source_origin")
    op.execute("ALTER TABLE commitments DROP COLUMN IF EXISTS materiality_reason")
    op.execute("ALTER TABLE commitments DROP COLUMN IF EXISTS confidence")
    op.execute("ALTER TABLE commitments DROP COLUMN IF EXISTS current_status")
    op.execute("ALTER TABLE commitments DROP COLUMN IF EXISTS period_text")
    op.execute("ALTER TABLE commitments DROP COLUMN IF EXISTS display_code")
    op.execute("ALTER TABLE commitments DROP COLUMN IF EXISTS import_ref")
    op.execute("ALTER TABLE commitments DROP COLUMN IF EXISTS parent_commitment_id")
    op.execute("ALTER TABLE program_sections DROP COLUMN IF EXISTS factual_review_status")
    op.execute("ALTER TABLE program_sections DROP COLUMN IF EXISTS structural_status")
    op.execute("ALTER TABLE program_sections DROP COLUMN IF EXISTS import_ref")
    op.execute("ALTER TABLE program_sections DROP COLUMN IF EXISTS source_origin")
    op.execute("ALTER TABLE program_sections DROP COLUMN IF EXISTS policy_area")
    op.execute("ALTER TABLE program_sections DROP COLUMN IF EXISTS key_findings")
    op.execute("ALTER TABLE program_sections DROP COLUMN IF EXISTS aggregate_status_summary")
    op.execute("ALTER TABLE program_sections DROP COLUMN IF EXISTS problem_description")
    op.execute("ALTER TABLE program_sections DROP COLUMN IF EXISTS original_heading")
    op.execute("ALTER TABLE program_sections DROP COLUMN IF EXISTS section_code")
    op.execute("ALTER TABLE program_sections DROP COLUMN IF EXISTS parent_section_id")
    op.execute("ALTER TABLE programs DROP COLUMN IF EXISTS published_at")
    op.execute("ALTER TABLE programs DROP COLUMN IF EXISTS factual_review_note")
    op.execute("ALTER TABLE programs DROP COLUMN IF EXISTS factual_review_status")
    op.execute("ALTER TABLE programs DROP COLUMN IF EXISTS structural_review_note")
    op.execute("ALTER TABLE programs DROP COLUMN IF EXISTS structural_review_status")
    op.execute("ALTER TABLE programs DROP COLUMN IF EXISTS status")
    op.execute("ALTER TABLE programs DROP COLUMN IF EXISTS publication_date")
    op.execute("ALTER TABLE programs DROP COLUMN IF EXISTS period_text")
    op.execute("ALTER TABLE programs DROP COLUMN IF EXISTS internal_notes")
    op.execute("ALTER TABLE programs DROP COLUMN IF EXISTS short_description")
