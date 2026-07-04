"""Rename communication score and add analysis source URLs.

Revision ID: 0002_comm_sources
Revises: 0001_initial
Create Date: 2026-07-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_comm_sources"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("ai_analyses", "manipulativeness_score", new_column_name="communicational_integrity_score")
    op.alter_column("ai_analyses", "manipulativeness_explanation", new_column_name="communicational_integrity_explanation")
    op.add_column("ai_analyses", sa.Column("source_urls", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("ai_analyses", "source_urls")
    op.alter_column("ai_analyses", "communicational_integrity_explanation", new_column_name="manipulativeness_explanation")
    op.alter_column("ai_analyses", "communicational_integrity_score", new_column_name="manipulativeness_score")
