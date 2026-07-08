"""Add soft delete flag to programs.

Revision ID: 0007_program_soft_delete
Revises: 0006_editable_ai_artifacts
Create Date: 2026-07-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_program_soft_delete"
down_revision: str | None = "0006_editable_ai_artifacts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("programs", sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index(op.f("ix_programs_is_deleted"), "programs", ["is_deleted"], unique=False)
    op.alter_column("programs", "is_deleted", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_programs_is_deleted"), table_name="programs")
    op.drop_column("programs", "is_deleted")
