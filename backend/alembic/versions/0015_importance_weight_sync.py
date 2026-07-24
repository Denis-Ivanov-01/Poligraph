"""Derive commitment importance weight from editorial importance level.

Revision ID: 0015_importance_weight_sync
Revises: 0014_program_analysis_v6
Create Date: 2026-07-12 17:00:00.000000
"""

from alembic import op


revision = "0015_importance_weight_sync"
down_revision = "0014_program_analysis_v6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE commitments
        SET importance_level = CASE
            WHEN importance_level IN ('key', 'standard', 'technical') THEN importance_level
            ELSE 'standard'
        END
        """
    )
    op.execute(
        """
        UPDATE commitments
        SET importance_weight = CASE importance_level
            WHEN 'key' THEN 3
            WHEN 'technical' THEN 1
            ELSE 2
        END
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'ck_commitments_importance_level_weight'
            ) THEN
                ALTER TABLE commitments
                ADD CONSTRAINT ck_commitments_importance_level_weight
                CHECK (
                    (importance_level = 'key' AND importance_weight = 3)
                    OR (importance_level = 'standard' AND importance_weight = 2)
                    OR (importance_level = 'technical' AND importance_weight = 1)
                );
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE commitments DROP CONSTRAINT IF EXISTS ck_commitments_importance_level_weight")
