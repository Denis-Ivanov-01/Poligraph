"""Remove statement principle consistency analysis fields.

Revision ID: 0017_remove_statement_principle_consistency
Revises: 0016_revert_v6_schema
Create Date: 2026-08-02
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0017_remove_principle"
down_revision: str | None = "0016_revert_v6_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE statement_ai_analyses DROP COLUMN IF EXISTS principle_consistency_score")
    op.execute("ALTER TABLE statement_ai_analyses DROP COLUMN IF EXISTS principle_consistency_explanation")


def downgrade() -> None:
    op.add_column("statement_ai_analyses", sa.Column("principle_consistency_score", sa.Integer(), nullable=True))
    op.add_column("statement_ai_analyses", sa.Column("principle_consistency_explanation", sa.Text(), nullable=True))
