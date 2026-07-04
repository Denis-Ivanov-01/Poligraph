"""make statement title nullable

Revision ID: 0004_statement_title_nullable
Revises: 0003_politician_image_url
Create Date: 2026-07-04 13:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_statement_title_nullable"
down_revision = "0003_politician_image_url"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("statements", "title", existing_type=sa.String(length=255), nullable=True)


def downgrade() -> None:
    op.alter_column("statements", "title", existing_type=sa.String(length=255), nullable=False)
