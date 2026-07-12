"""Redesign schema for MVP transparency workflow.

Revision ID: 0008_mvp_redesign
Revises: 0007_program_soft_delete
Create Date: 2026-07-10
"""

from collections.abc import Sequence

from alembic import op

from app.database import Base
from app import models  # noqa: F401

revision: str = "0008_mvp_redesign"
down_revision: str | None = "0007_program_soft_delete"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TABLES = (
    "statement_commitments",
    "program_media_assets",
    "case_commitments",
    "case_statements",
    "case_fact_point_evidence_links",
    "case_fact_points",
    "case_timeline_event_evidence_links",
    "case_timeline_events",
    "cases",
    "import_items",
    "imports",
    "commitment_evidence_links",
    "commitment_status_updates",
    "commitment_evidence",
    "commitments",
    "program_ai_extractions",
    "program_sections",
    "programs",
    "appeals",
    "statement_claim_evidence_links",
    "statement_claims",
    "statement_ai_analyses",
    "ai_analyses",
    "evidence_items",
    "ai_runs",
    "statement_media_assets",
    "media_assets",
    "statements",
    "party_memberships",
    "politicians",
    "political_parties",
    "entity_revisions",
    "audit_logs",
    "moderators",
    "users",
)


def upgrade() -> None:
    bind = op.get_bind()
    for table in TABLES:
        op.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')
    Base.metadata.create_all(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind, checkfirst=True)
