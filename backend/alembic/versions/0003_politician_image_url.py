"""add politician image url

Revision ID: 0003_politician_image_url
Revises: 0002_comm_sources
Create Date: 2026-07-04 13:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_politician_image_url"
down_revision = "0002_comm_sources"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("politicians", sa.Column("image_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("politicians", "image_url")
