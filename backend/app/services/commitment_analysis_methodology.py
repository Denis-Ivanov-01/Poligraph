from typing import Any

from app.models.commitment import Commitment, CommitmentEvidenceLink
from app.models.evidence import EvidenceItem
from app.services.commitment_service import (
    BASELINE_MODES,
    COMMITMENT_EVIDENCE_RELATION_TYPES,
    COMMITMENT_STATUSES,
    COMMITMENT_TYPES,
    CONFIDENCE_LEVELS,
    CONTRIBUTION_LEVELS,
    CONTRIBUTION_TYPES,
    CONTROL_LEVELS,
    EVIDENCE_ROLES,
    EVIDENCE_SOURCE_TYPES,
    EVIDENCE_STRENGTHS,
    MEASURE_VALIDITY_STATUSES,
)
from app.services.prompt_schema_builder import db_fields_contract, enum_contract, enum_list_contract


COMMITMENT_ANALYSIS_METHODOLOGY_VERSION = "2026-07-12.1"
DEFAULT_BATCH_TRANCHE_SIZE = 50

MATERIAL_COMPONENT_STATUSES = {
    "complete",
    "in_progress",
    "absent",
    "not_due",
    "unclear",
    "not_applicable",
}
IMPLEMENTATION_DIMENSION_STATUSES = {"complete", "partial", "incomplete", "not_due", "not_applicable", "unclear"}
CONCLUSION_BASES = {"positive_evidence", "contradictory_evidence", "mixed", "procedural_timing", "absence_of_evidence"}
EVIDENCE_GAP_KINDS = {"missing", "inaccessible", "ambiguous", "outdated", "contradictory"}
DEADLINE_TYPES = {"explicit_date", "explicit_period", "end_of_term", "recurring", "conditional", "none", "unclear"}


CANONICAL_COMMITMENT_ANALYSIS_METHODOLOGY = """Stable commitment-analysis methodology:
1. Start from the original promise and identify every materially distinct component before assigning an overall status. Separate tools, actions, operational results, and public outcomes. For every component state what is complete, in progress, absent, not due, not applicable, or unclear, and link the finding to evidence.
2. Determine promise type, promised item type, deadlines and periods, measurable criteria, responsible authority, required external actors, and cabinet control. Evaluate the promise at the level at which it was made. A tool or interface does not prove an operational result or a wider public outcome.
3. Establish the baseline from evidence. Test whether the promise is genuinely new, a continuation, expansion, acceleration, inherited implementation, implementation of an adopted measure, supported by pre-secured funding or a pre-signed contract, an automatic legal process, maintenance of the status quo, or a reversal. A new interface over existing data or infrastructure is not automatically a new policy. Use unclear when the baseline is not supportable.
4. Keep fulfillment and cabinet contribution independent. For contribution, compare the evidenced baseline with the counterfactual without cabinet action; identify discretionary cabinet acts, automatic or contractual developments, inherited work, pre-existing data and infrastructure, and the roles of Parliament, courts, regulators, municipalities, independent authorities, EU institutions, contractors, and other actors. Apply contribution only to the components actually completed. A decisive rating requires a concrete counterfactual explanation.
5. Prefer primary official evidence: legislation and official gazettes, government decisions, parliamentary records, methodologies and technical documentation, public registers, budgets and execution reports, procurement and contracts, audits, court and regulator decisions, official statistics, and official product documentation. Institutional announcements prove only what they directly document and do not by themselves prove effectiveness, full functionality, impact, or causation.
6. Search actively for limiting and contradictory material: methodologies, version notes, future roadmaps, repeals or expiry, audit findings, contrary official records, and independent confirmation where material. For dynamic systems, registers, dashboards, and statistics use the newest state available as of the analysis date and record the relevant source or observation date.
7. Distinguish announcement from adoption, procedure from result, funding from implementation, a proposed bill from law in force, and formal completion from material operation. Distinguish inherited or automatic implementation from discretionary contribution.
8. Calibrate confidence only to confidence in the selected implementation status. Uncertainty about broader impact does not by itself lower confidence in a well-supported partial status. Absence of an easily found source is not proof of non-implementation; after serious but inconclusive research use unclear rather than an unsupported hard negative.
9. Preserve missing, inaccessible, ambiguous, outdated, and contradictory evidence explicitly. Every source relationship must name the claim it supports or limits, its role, its strength, the affected material components, and any limitation.
10. For parliamentary commitments, account for whether the cabinet had a stable majority. Drafting, timely submission, public defense, support-seeking, and reasonable negotiation may satisfy the controllable part even when the final legislative result does not occur.
11. Deadline analysis must come only from the promise or directly relevant evidence. The analysis date is not a deadline. Use deadline_type explicit_date for a concrete date, explicit_period for a named period, end_of_term for term-bound promises, recurring for repeated obligations, conditional for explicit triggers, none when no deadline exists, and unclear when timing cannot be supported. For conditional promises, name the trigger; for recurring promises, describe the recurrence; for promises without measurable criteria, return an empty measurable_criteria array.
12. Status meanings: not_started means no substantiated action after considering the period; in_progress means concrete material action without the promised result; kept_to_date means an ongoing maintenance/negative promise remains preserved; condition_not_met means the explicit condition has not occurred; not_due means the deadline or due period has not arrived; delayed means officially postponed or materially delayed; partially_fulfilled means separable material parts are complete; fulfilled means all material elements are achieved; violated means a material contrary action; abandoned means reliably dropped/reversed/lapsed; not_applicable means the object of evaluation no longer applies; unclear means serious review did not support a stable conclusion.
13. Consistency rules: fulfilled cannot be returned when material_implementation_status is partial or incomplete and requires every material component to be complete or not applicable; partially_fulfilled must correspond to partial material implementation or a material mixture of completed and incomplete, unclear, absent, delayed, or not-due components; not_started cannot coexist with complete material components or material_implementation_status complete; in_progress requires verified material action, not only an announcement or intention; violated requires evidence of conduct directly contrary to the commitment, not mere inaction; delayed requires evidence of postponement or a missed applicable timing expectation, and the explanation must distinguish the original timing from any new timing; kept_to_date applies only to continuing maintenance or negative commitments, not ordinary positive reform promises; not_due requires a future deadline, period, stage, or other timing basis; condition_not_met requires an explicit untriggered condition; not_applicable requires an objective reason why the commitment no longer applies and must not be used merely because implementation is difficult; measure_validity_status describes the current validity of an implemented measure and must not silently overwrite the historical implementation finding; component findings, current_status, material components, formal/material dimensions, explanations, evidence links, confidence, contribution, timing fields, and measure validity must tell one coherent analytical story.
14. All public-facing explanations must be in Bulgarian. Do not invent sources, URLs, quotations, dates, institutions, functions, impact, causation, deadlines, conditions, criteria, or cabinet adoption. The model is never a source."""


def commitment_analysis_output_schema(commitment_ref: str) -> dict[str, Any]:
    """Return the individual commitment-analysis object shared by standalone and batch status prompts."""
    commitment_fields = db_fields_contract(
        Commitment,
        [
            "deadline",
            "period_text",
            "commitment_type",
            "promised_item_type",
            "baseline_mode",
            "control_level",
            "evaluation_basis",
            "current_status",
            "status_explanation",
            "confidence",
            "confidence_explanation",
            "contribution_level",
            "contribution_explanation",
            "contribution_confidence",
            "official_program_change_note",
            "source_version_note",
            "quantitative_target",
            "quantitative_actual",
            "measure_validity_status",
        ],
        enum_fields={
            "commitment_type": COMMITMENT_TYPES,
            "promised_item_type": COMMITMENT_TYPES,
            "baseline_mode": BASELINE_MODES,
            "control_level": CONTROL_LEVELS,
            "current_status": {key: "" for key in COMMITMENT_STATUSES if key != "not_analyzed"},
            "confidence": CONFIDENCE_LEVELS,
            "contribution_level": CONTRIBUTION_LEVELS,
            "contribution_confidence": CONFIDENCE_LEVELS,
            "measure_validity_status": MEASURE_VALIDITY_STATUSES,
        },
        nullable_overrides={
            "commitment_type": False,
            "promised_item_type": False,
            "baseline_mode": False,
            "control_level": False,
            "current_status": False,
            "confidence": False,
            "contribution_level": False,
            "contribution_confidence": False,
            "measure_validity_status": False,
        },
    )
    source_fields = db_fields_contract(
        EvidenceItem,
        [
            "title",
            "url",
            "source_type",
            "publisher",
            "published_at",
            "accessed_at",
            "quote_or_relevant_excerpt",
            "description",
            "reliability_level",
        ],
        enum_fields={"source_type": EVIDENCE_SOURCE_TYPES, "reliability_level": CONFIDENCE_LEVELS},
        nullable_overrides={
            "url": True,
            "source_type": False,
            "accessed_at": False,
            "reliability_level": False,
        },
    )
    evidence_link_fields = db_fields_contract(
        CommitmentEvidenceLink,
        [
            "relation_type",
            "evidence_role",
            "evidence_strength",
            "is_self_reported",
            "is_independent_confirmation",
            "is_contradictory",
            "is_disproven",
            "limitations",
        ],
        enum_fields={
            "relation_type": COMMITMENT_EVIDENCE_RELATION_TYPES,
            "evidence_role": EVIDENCE_ROLES,
            "evidence_strength": EVIDENCE_STRENGTHS,
        },
        nullable_overrides={"relation_type": False, "evidence_role": False, "evidence_strength": False},
    )
    return {
        "commitment_analysis": {
            "commitment_ref": commitment_ref,
            "deadline": commitment_fields["deadline"],
            "deadline_type": enum_contract(DEADLINE_TYPES),
            "period": commitment_fields["period_text"],
            "conditional_trigger": "string or null",
            "measurable_criteria": ["string"],
            "commitment_type": commitment_fields["commitment_type"],
            "promised_item_type": commitment_fields["promised_item_type"],
            "material_components": [
                {
                    "component_ref": "C1",
                    "description": "string",
                    "promised_item_type": enum_contract(COMMITMENT_TYPES),
                    "status": enum_contract(MATERIAL_COMPONENT_STATUSES),
                    "finding": "string",
                    "evidence_refs": ["E1"],
                }
            ],
            "baseline_mode": commitment_fields["baseline_mode"],
            "baseline_explanation": "string",
            "responsible_authority": "string or null",
            "required_external_actors": ["string"],
            "control_level": commitment_fields["control_level"],
            "control_level_explanation": "string",
            "evaluation_basis": commitment_fields["evaluation_basis"],
            "formal_implementation_status": enum_contract(IMPLEMENTATION_DIMENSION_STATUSES),
            "material_implementation_status": enum_contract(IMPLEMENTATION_DIMENSION_STATUSES),
            "current_status": commitment_fields["current_status"],
            "status_explanation": commitment_fields["status_explanation"],
            "conclusion_basis": enum_contract(CONCLUSION_BASES),
            "confidence": commitment_fields["confidence"],
            "confidence_explanation": commitment_fields["confidence_explanation"],
            "missing_or_uncertain_evidence": [
                {
                    "kind": enum_contract(EVIDENCE_GAP_KINDS),
                    "description": "string",
                    "impact_on_conclusion": "string",
                }
            ],
            "contribution_level": commitment_fields["contribution_level"],
            "contribution_explanation": commitment_fields["contribution_explanation"],
            "contribution_counterfactual": "string",
            "contribution_confidence": commitment_fields["contribution_confidence"],
            "contribution_types": enum_list_contract(CONTRIBUTION_TYPES),
            "contribution_applies_to_component_refs": ["C1"],
            "official_program_change_note": commitment_fields["official_program_change_note"],
            "source_version_note": commitment_fields["source_version_note"],
            "quantitative_target": commitment_fields["quantitative_target"],
            "quantitative_actual": commitment_fields["quantitative_actual"],
            "quantitative_actual_as_of": "YYYY-MM-DD or null",
            "measure_validity_status": commitment_fields["measure_validity_status"],
            "evidence_links": [
                {
                    "source_ref": "E1",
                    "relation_type": evidence_link_fields["relation_type"],
                    "evidence_role": evidence_link_fields["evidence_role"],
                    "evidence_strength": evidence_link_fields["evidence_strength"],
                    "claim": "string",
                    "component_refs": ["C1"],
                    "is_self_reported": evidence_link_fields["is_self_reported"],
                    "is_independent_confirmation": evidence_link_fields["is_independent_confirmation"],
                    "is_contradictory": evidence_link_fields["is_contradictory"],
                    "is_disproven": evidence_link_fields["is_disproven"],
                    "limitations": evidence_link_fields["limitations"],
                }
            ],
        },
        "sources": [
            {
                "source_ref": "E1",
                **source_fields,
            }
        ],
    }
