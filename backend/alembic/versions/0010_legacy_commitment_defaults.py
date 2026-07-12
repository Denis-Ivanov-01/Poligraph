"""Relax legacy commitment columns kept for compatibility.

Revision ID: 0010_legacy_commitment_defaults
Revises: 0009_program_multistage_workflow
Create Date: 2026-07-10
"""

from collections.abc import Sequence

from alembic import op


revision: str = "0010_legacy_commitment_defaults"
down_revision: str | None = "0009_program_multistage_workflow"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'commitments' AND column_name = 'status'
            ) THEN
                UPDATE commitments
                SET status = current_status
                WHERE status IS NULL AND current_status IS NOT NULL;

                ALTER TABLE commitments
                ALTER COLUMN status SET DEFAULT 'not_analyzed';

                ALTER TABLE commitments
                ALTER COLUMN status DROP NOT NULL;
            END IF;

            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'commitments' AND column_name = 'confidence_level'
            ) THEN
                UPDATE commitments
                SET confidence_level = confidence
                WHERE confidence_level IS NULL AND confidence IS NOT NULL;

                ALTER TABLE commitments
                ALTER COLUMN confidence_level SET DEFAULT 'medium';

                ALTER TABLE commitments
                ALTER COLUMN confidence_level DROP NOT NULL;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'commitments' AND column_name = 'status'
            ) THEN
                UPDATE commitments
                SET status = COALESCE(status, current_status, 'not_started');

                ALTER TABLE commitments
                ALTER COLUMN status SET DEFAULT 'not_started';

                ALTER TABLE commitments
                ALTER COLUMN status SET NOT NULL;
            END IF;

            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'commitments' AND column_name = 'confidence_level'
            ) THEN
                UPDATE commitments
                SET confidence_level = COALESCE(confidence_level, confidence, 'medium');

                ALTER TABLE commitments
                ALTER COLUMN confidence_level SET DEFAULT 'medium';

                ALTER TABLE commitments
                ALTER COLUMN confidence_level SET NOT NULL;
            END IF;
        END $$;
        """
    )
