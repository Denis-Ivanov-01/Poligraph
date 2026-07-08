"""Add editable AI artifacts for statements and programs.

Revision ID: 0006_editable_ai_artifacts
Revises: 0005_programs_commitments
Create Date: 2026-07-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_editable_ai_artifacts"
down_revision: str | None = "0005_programs_commitments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("statements", sa.Column("generated_prompt_text", sa.Text(), nullable=True))
    op.add_column("programs", sa.Column("generated_prompt_text", sa.Text(), nullable=True))
    op.add_column("programs", sa.Column("raw_ai_response", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("programs", "raw_ai_response")
    op.drop_column("programs", "generated_prompt_text")
    op.drop_column("statements", "generated_prompt_text")
