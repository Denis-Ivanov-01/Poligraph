"""program contribution methodology

Revision ID: 0013_contribution_method
Revises: 0012_section_commitment_idx
Create Date: 2026-07-12 11:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0013_contribution_method"
down_revision = "0012_section_commitment_idx"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("commitments", sa.Column("commitment_type", sa.String(length=80), nullable=True))
    op.add_column("commitments", sa.Column("promised_item_type", sa.String(length=80), nullable=True))
    op.add_column("commitments", sa.Column("baseline_mode", sa.String(length=80), nullable=True))
    op.add_column("commitments", sa.Column("required_external_actors", sa.Text(), nullable=True))
    op.add_column("commitments", sa.Column("control_level", sa.String(length=80), nullable=True))
    op.add_column("commitments", sa.Column("evaluation_basis", sa.Text(), nullable=True))
    op.add_column("commitments", sa.Column("contribution_types_text", sa.Text(), nullable=True))
    op.add_column("commitments", sa.Column("official_program_change_note", sa.Text(), nullable=True))
    op.add_column("commitments", sa.Column("source_version_note", sa.Text(), nullable=True))
    op.add_column("commitments", sa.Column("quantitative_target", sa.Text(), nullable=True))
    op.add_column("commitments", sa.Column("quantitative_actual", sa.Text(), nullable=True))
    op.add_column("commitments", sa.Column("measure_validity_status", sa.String(length=80), nullable=True))
    op.add_column("commitments", sa.Column("contribution_level", sa.String(length=80), nullable=False, server_default="indeterminate"))
    op.add_column("commitments", sa.Column("contribution_explanation", sa.Text(), nullable=True))
    op.add_column("commitments", sa.Column("contribution_confidence", sa.String(length=80), nullable=True))
    op.add_column("commitments", sa.Column("importance_level", sa.String(length=40), nullable=False, server_default="standard"))
    op.add_column("commitments", sa.Column("importance_weight", sa.Integer(), nullable=False, server_default="2"))
    op.create_index("ix_commitments_commitment_type", "commitments", ["commitment_type"])
    op.create_index("ix_commitments_promised_item_type", "commitments", ["promised_item_type"])
    op.create_index("ix_commitments_baseline_mode", "commitments", ["baseline_mode"])
    op.create_index("ix_commitments_control_level", "commitments", ["control_level"])
    op.create_index("ix_commitments_measure_validity_status", "commitments", ["measure_validity_status"])
    op.create_index("ix_commitments_contribution_level", "commitments", ["contribution_level"])
    op.create_index("ix_commitments_contribution_confidence", "commitments", ["contribution_confidence"])
    op.create_index("ix_commitments_importance_level", "commitments", ["importance_level"])

    op.add_column("commitment_status_updates", sa.Column("previous_contribution_level", sa.String(length=80), nullable=True))
    op.add_column("commitment_status_updates", sa.Column("new_contribution_level", sa.String(length=80), nullable=True))
    op.add_column("commitment_status_updates", sa.Column("contribution_explanation", sa.Text(), nullable=True))
    op.add_column("commitment_status_updates", sa.Column("contribution_confidence", sa.String(length=40), nullable=True))

    op.add_column("commitment_evidence_links", sa.Column("evidence_role", sa.String(length=80), nullable=True))
    op.add_column("commitment_evidence_links", sa.Column("evidence_strength", sa.String(length=40), nullable=True))
    op.add_column("commitment_evidence_links", sa.Column("is_self_reported", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("commitment_evidence_links", sa.Column("is_independent_confirmation", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("commitment_evidence_links", sa.Column("is_contradictory", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("commitment_evidence_links", sa.Column("is_disproven", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("commitment_evidence_links", sa.Column("limitations", sa.Text(), nullable=True))
    op.create_index("ix_commitment_evidence_links_evidence_role", "commitment_evidence_links", ["evidence_role"])
    op.create_index("ix_commitment_evidence_links_evidence_strength", "commitment_evidence_links", ["evidence_strength"])
    op.create_index("ix_commitment_evidence_links_is_self_reported", "commitment_evidence_links", ["is_self_reported"])
    op.create_index(
        "ix_commitment_evidence_links_is_independent_confirmation",
        "commitment_evidence_links",
        ["is_independent_confirmation"],
    )
    op.create_index("ix_commitment_evidence_links_is_contradictory", "commitment_evidence_links", ["is_contradictory"])
    op.create_index("ix_commitment_evidence_links_is_disproven", "commitment_evidence_links", ["is_disproven"])


def downgrade() -> None:
    op.drop_index("ix_commitment_evidence_links_is_disproven", table_name="commitment_evidence_links")
    op.drop_index("ix_commitment_evidence_links_is_contradictory", table_name="commitment_evidence_links")
    op.drop_index("ix_commitment_evidence_links_is_independent_confirmation", table_name="commitment_evidence_links")
    op.drop_index("ix_commitment_evidence_links_is_self_reported", table_name="commitment_evidence_links")
    op.drop_index("ix_commitment_evidence_links_evidence_strength", table_name="commitment_evidence_links")
    op.drop_index("ix_commitment_evidence_links_evidence_role", table_name="commitment_evidence_links")
    op.drop_column("commitment_evidence_links", "limitations")
    op.drop_column("commitment_evidence_links", "is_disproven")
    op.drop_column("commitment_evidence_links", "is_contradictory")
    op.drop_column("commitment_evidence_links", "is_independent_confirmation")
    op.drop_column("commitment_evidence_links", "is_self_reported")
    op.drop_column("commitment_evidence_links", "evidence_strength")
    op.drop_column("commitment_evidence_links", "evidence_role")

    op.drop_column("commitment_status_updates", "contribution_confidence")
    op.drop_column("commitment_status_updates", "contribution_explanation")
    op.drop_column("commitment_status_updates", "new_contribution_level")
    op.drop_column("commitment_status_updates", "previous_contribution_level")

    op.drop_index("ix_commitments_importance_level", table_name="commitments")
    op.drop_index("ix_commitments_contribution_confidence", table_name="commitments")
    op.drop_index("ix_commitments_contribution_level", table_name="commitments")
    op.drop_index("ix_commitments_measure_validity_status", table_name="commitments")
    op.drop_index("ix_commitments_control_level", table_name="commitments")
    op.drop_index("ix_commitments_baseline_mode", table_name="commitments")
    op.drop_index("ix_commitments_promised_item_type", table_name="commitments")
    op.drop_index("ix_commitments_commitment_type", table_name="commitments")
    op.drop_column("commitments", "importance_weight")
    op.drop_column("commitments", "importance_level")
    op.drop_column("commitments", "contribution_confidence")
    op.drop_column("commitments", "contribution_explanation")
    op.drop_column("commitments", "contribution_level")
    op.drop_column("commitments", "measure_validity_status")
    op.drop_column("commitments", "quantitative_actual")
    op.drop_column("commitments", "quantitative_target")
    op.drop_column("commitments", "source_version_note")
    op.drop_column("commitments", "official_program_change_note")
    op.drop_column("commitments", "contribution_types_text")
    op.drop_column("commitments", "evaluation_basis")
    op.drop_column("commitments", "control_level")
    op.drop_column("commitments", "required_external_actors")
    op.drop_column("commitments", "baseline_mode")
    op.drop_column("commitments", "promised_item_type")
    op.drop_column("commitments", "commitment_type")
