"""Add index for public program section commitment browsing.

Revision ID: 0012_section_commitment_idx
Revises: 0011_program_ai_run_integrity
Create Date: 2026-07-11
"""

from collections.abc import Sequence

from alembic import op


revision: str = "0012_section_commitment_idx"
down_revision: str | None = "0011_program_ai_run_integrity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE INDEX IF NOT EXISTS ix_commitments_program_section_id ON commitments (program_section_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_commitments_program_section_id")
