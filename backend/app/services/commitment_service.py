import json
import re
from datetime import date
from typing import Any

from sqlalchemy import case, desc, exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.commitment import Commitment, CommitmentEvidence, CommitmentEvidenceLink, CommitmentStatusUpdate
from app.models.program import Program, ProgramSection

PROGRAM_TYPES = {
    "government_program": "Управленска програма",
    "coalition_agreement": "Коалиционно споразумение",
    "party_program": "Партийна програма",
    "election_program": "Предизборна програма",
    "policy_platform": "Политическа платформа",
    "government_action_plan": "План за действие на правителството",
    "sector_strategy": "Секторна стратегия",
    "municipal_program": "Общинска програма",
    "legislative_agenda": "Законодателна програма",
    "other": "Друго",
}

COMMITMENT_STATUSES = {
    "not_analyzed": {
        "label": "Не е анализирано",
        "group": "pending",
        "description": "Ангажиментът е извлечен като кандидат, но още няма анализ на изпълнението.",
    },
    "not_started": {
        "label": "Не започнато",
        "group": "pending",
        "description": "След преглед на периода и наличните доказателства няма потвърдени действия по изпълнение.",
    },
    "in_progress": {
        "label": "В процес",
        "group": "active",
        "description": "Има реални действия, но няма завършен резултат.",
    },
    "kept_to_date": {
        "label": "Спазва се към момента",
        "group": "active",
        "description": "Продължаващо отрицателно или поддържащо обещание не е нарушено към датата на анализа.",
    },
    "condition_not_met": {
        "label": "Условието не е настъпило",
        "group": "pending",
        "description": "Ангажиментът е условен и изрично поставеното условие още не е изпълнено.",
    },
    "not_due": {
        "label": "Още не е дължим",
        "group": "pending",
        "description": "Срокът или релевантният период още не е настъпил и няма основание за крайна оценка.",
    },
    "delayed": {
        "label": "Отложено",
        "group": "active",
        "description": "Има официално отлагане или забавяне спрямо обещания срок, без окончателно изоставяне.",
    },
    "partially_fulfilled": {
        "label": "Частично изпълнено",
        "group": "active",
        "description": "Има постигнат резултат, но той не покрива изцяло обещанието.",
    },
    "fulfilled": {
        "label": "Изпълнено",
        "group": "completed",
        "description": "Обещаното е постигнато по същество.",
    },
    "violated": {
        "label": "Нарушено",
        "group": "failed",
        "description": "Направено е обратното на заявения ангажимент.",
    },
    "abandoned": {
        "label": "Изоставено",
        "group": "failed",
        "description": "Ангажиментът вече не се преследва или е публично изоставен.",
    },
    "not_applicable": {
        "label": "Неприложимо",
        "group": "unclear",
        "description": "Ангажиментът не може коректно да бъде оценен, защото предметът му е отпаднал или е официално променен.",
    },
    "unclear": {
        "label": "Неясен след анализ",
        "group": "unclear",
        "description": "Извършен е анализ, но доказателствата са недостатъчни, противоречиви или недостъпни за стабилен извод.",
    },
}

STATUS_GROUPS = {
    "pending": "Предстоящи",
    "active": "Активни",
    "completed": "Завършени",
    "failed": "Неизпълнени",
    "unclear": "Неясни",
}

CONFIDENCE_LEVELS = {
    "high": "Висока увереност",
    "medium": "Средна увереност",
    "low": "Ниска увереност",
}

EVIDENCE_SOURCE_TYPES = {
    "bill": "Законопроект",
    "vote": "Гласуване",
    "council_of_ministers_decision": "Решение на Министерски съвет",
    "national_assembly_decision": "Решение на Народното събрание",
    "budget_change": "Бюджетна промяна",
    "public_procurement": "Обществена поръчка",
    "contract": "Договор",
    "report": "Доклад",
    "strategy": "Стратегия",
    "action_plan": "План за действие",
    "parliamentary_question": "Парламентарен въпрос",
    "transcript": "Стенограма",
    "official_press_release": "Официално прессъобщение",
    "court_act": "Съдебен акт",
    "regulatory_decision": "Регулаторно решение",
    "public_statement": "Публично изказване",
    "media_publication": "Медийна публикация",
    "government_document": "Правителствен документ",
    "legislation": "Законодателство",
    "parliamentary_document": "Парламентарен документ",
    "court_document": "Съдебен документ",
    "official_register": "Официален регистър",
    "budget_document": "Бюджетен документ",
    "procurement_record": "Обществена поръчка",
    "institutional_statement": "Институционално съобщение",
    "statistical_dataset": "Статистически данни",
    "audit_or_report": "Одит или доклад",
    "media_report": "Медийна публикация",
    "other": "Друго",
}

COMMITMENT_TYPES = {
    "action": "Обещано действие",
    "legislative_action": "Законодателно действие",
    "legislative_result": "Законодателен резултат",
    "operational_result": "Оперативен резултат",
    "public_outcome": "Обществен резултат",
    "maintenance": "Запазване на съществуваща политика",
    "negative_commitment": "Обещание за невъвеждане или непрекратяване",
    "conditional": "Условен ангажимент",
    "other": "Друго",
}

BASELINE_MODES = {
    "new_policy": "Нова политика",
    "continuation": "Продължаване на съществуваща политика",
    "inherited_implementation": "Наследено изпълнение",
    "automatic_legal_process": "Автоматичен законов процес",
    "adopted_not_implemented": "Приет, но неприложен нормативен акт",
    "pre_secured_funding": "Предварително осигурено финансиране",
    "pre_signed_contract": "Предварително подписан договор",
    "expansion": "Разширяване на съществуваща политика",
    "acceleration": "Ускоряване на съществуваща политика",
    "status_quo": "Запазване на статуквото",
    "reversal": "Отмяна или обръщане на предходна политика",
    "unclear": "Неясна изходна ситуация",
}

CONTROL_LEVELS = {
    "direct": "Пряк контрол",
    "high_shared": "Висок споделен контрол",
    "limited_shared": "Ограничен споделен контрол",
    "external": "Външен контрол",
    "not_relevant": "Не е релевантно",
    "unclear": "Неясно",
}

CONTRIBUTION_LEVELS = {
    "none": {"label": "Няма установим допълнителен принос", "coefficient": 0.0},
    "limited": {"label": "Ограничен или процедурен принос", "coefficient": 1 / 3},
    "shared": {"label": "Съществен споделен принос", "coefficient": 2 / 3},
    "decisive": {"label": "Решаващ принос", "coefficient": 1.0},
    "indeterminate": {"label": "Не може да се определи", "coefficient": None},
}

CONTRIBUTION_TYPES = {
    "initiative": "Инициатива",
    "legislative_preparation": "Законодателна подготовка",
    "funding": "Финансиране",
    "administrative_execution": "Административно изпълнение",
    "coordination": "Координация",
    "acceleration": "Ускоряване",
    "expansion": "Разширяване",
    "preventing_termination": "Предотвратяване на прекратяване",
    "maintenance": "Поддържане",
    "formalization": "Формализиране",
    "procedural_participation": "Процедурно участие",
    "inherited_implementation": "Наследено изпълнение",
    "shared_implementation": "Споделено изпълнение",
}

IMPORTANCE_LEVELS = {
    "key": {"label": "Ключов", "weight": 3},
    "standard": {"label": "Стандартен", "weight": 2},
    "technical": {"label": "Технически или поддържащ", "weight": 1},
}

MATERIALITY_LEVELS = {
    "low": "Ниска",
    "medium": "Средна",
    "high": "Висока",
}

MEASURE_VALIDITY_STATUSES = {
    "active": "Мярката действа",
    "expired": "Мярката е с изтекъл срок",
    "repealed": "Мярката е отменена",
    "not_in_force": "Не е влязла в сила",
    "not_relevant": "Не е релевантно",
    "unclear": "Неясно",
}

EVIDENCE_ROLES = {
    "supports_fulfillment": "Подкрепя изпълнението",
    "contradicts_fulfillment": "Противоречи на изпълнението",
    "supports_contribution": "Подкрепя приноса",
    "contradicts_contribution": "Противоречи на приноса",
    "baseline": "Изходна ситуация",
    "official_change": "Официална промяна",
    "validity": "Валидност на мярката",
    "context": "Контекст",
}

EVIDENCE_STRENGTHS = {
    "strong": "Силно доказателство",
    "medium": "Средно доказателство",
    "weak": "Слабо доказателство",
    "contradictory": "Противоречиво",
}

COMMITMENT_EVIDENCE_RELATION_TYPES = {
    "supports_status": "Подкрепя статуса",
    "contradicts_status": "Противоречи на статуса",
    "contextualizes": "Дава контекст",
    "proves_completion": "Доказва завършване",
    "proves_delay": "Доказва забавяне",
    "proves_violation": "Доказва нарушение",
    "supports_contribution": "Подкрепя приноса",
    "contradicts_contribution": "Противоречи на приноса",
    "background": "Фонова информация",
}

FULFILLMENT_SCORE_VALUES = {
    "fulfilled": 1.0,
    "partially_fulfilled": 0.5,
    "in_progress": 0.25,
    "kept_to_date": 0.5,
    "not_started": 0.0,
    "violated": 0.0,
    "abandoned": 0.0,
    "delayed": 0.0,
}

def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9а-яА-Я]+", "-", value.strip().lower()).strip("-")
    return normalized or "item"


def ensure_unique_slug(db: Session, model: type[Program] | type[ProgramSection] | type[Commitment], base: str, current_id: Any | None = None) -> str:
    base_slug = slugify(base)
    slug = base_slug
    counter = 2
    while True:
        query = select(model).where(model.slug == slug)
        if current_id:
            query = query.where(model.id != current_id)
        if not db.scalar(query):
            return slug
        slug = f"{base_slug}-{counter}"
        counter += 1


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Expected a string or null.")
    stripped = value.strip()
    return stripped or None


def status_group(status: str) -> str:
    return COMMITMENT_STATUSES.get(status, COMMITMENT_STATUSES["not_started"])["group"]


def zero_status_counts() -> dict[str, int]:
    return {key: 0 for key in COMMITMENT_STATUSES}


def public_effective_status_expr():
    has_analysis = exists(select(CommitmentStatusUpdate.id).where(CommitmentStatusUpdate.commitment_id == Commitment.id))
    return case((has_analysis, Commitment.current_status), else_="not_analyzed")


def public_confidence_expr():
    has_analysis = exists(select(CommitmentStatusUpdate.id).where(CommitmentStatusUpdate.commitment_id == Commitment.id))
    return case((has_analysis, Commitment.confidence), else_=None)


def merge_status_counts(target: dict[str, int], source: dict[str, int]) -> None:
    for key, value in source.items():
        target[key] = target.get(key, 0) + value


def status_label(status: str) -> str:
    return COMMITMENT_STATUSES.get(status, COMMITMENT_STATUSES["not_analyzed"])["label"]


def confidence_label(confidence: str | None) -> str | None:
    return CONFIDENCE_LEVELS.get(confidence) if confidence else None


def contribution_label(contribution_level: str | None) -> str | None:
    if not contribution_level:
        return None
    meta = CONTRIBUTION_LEVELS.get(contribution_level)
    return meta["label"] if meta else contribution_level


def commitment_type_label(commitment_type: str | None) -> str | None:
    return COMMITMENT_TYPES.get(commitment_type, commitment_type) if commitment_type else None


def baseline_mode_label(baseline_mode: str | None) -> str | None:
    return BASELINE_MODES.get(baseline_mode, baseline_mode) if baseline_mode else None


def control_level_label(control_level: str | None) -> str | None:
    return CONTROL_LEVELS.get(control_level, control_level) if control_level else None


def importance_label(importance_level: str | None) -> str | None:
    if not importance_level:
        return None
    meta = IMPORTANCE_LEVELS.get(importance_level)
    return meta["label"] if meta else importance_level


def measure_validity_label(measure_validity_status: str | None) -> str | None:
    return MEASURE_VALIDITY_STATUSES.get(measure_validity_status, measure_validity_status) if measure_validity_status else None


def evidence_role_label(evidence_role: str | None) -> str | None:
    return EVIDENCE_ROLES.get(evidence_role, evidence_role) if evidence_role else None


def evidence_strength_label(evidence_strength: str | None) -> str | None:
    return EVIDENCE_STRENGTHS.get(evidence_strength, evidence_strength) if evidence_strength else None


def commitment_importance_weight(commitment: Commitment) -> int:
    importance_level = getattr(commitment, "importance_level", None)
    if importance_level in IMPORTANCE_LEVELS:
        return IMPORTANCE_LEVELS[importance_level]["weight"]
    return IMPORTANCE_LEVELS["standard"]["weight"]


def commitment_fulfillment_value(status: str | None) -> float | None:
    if not status:
        return None
    return FULFILLMENT_SCORE_VALUES.get(status)


def commitment_contribution_coefficient(contribution_level: str | None) -> float | None:
    if not contribution_level:
        return None
    meta = CONTRIBUTION_LEVELS.get(contribution_level)
    return meta["coefficient"] if meta else None


def program_score_summary(commitments: list[Commitment]) -> dict[str, Any]:
    total_weight = 0
    due_weight = 0
    analyzed_weight = 0
    contribution_weight = 0
    fulfillment_points = 0.0
    contribution_adjusted_points = 0.0
    analyzed_count = 0
    due_count = 0
    unclear_count = 0
    not_analyzed_count = 0
    indeterminate_contribution_count = 0
    violated_count = 0
    abandoned_count = 0
    contribution_counts = {key: 0 for key in CONTRIBUTION_LEVELS}

    for commitment in commitments:
        weight = commitment_importance_weight(commitment)
        total_weight += weight
        has_analysis = bool(getattr(commitment, "status_updates", None))
        status = commitment.current_status if has_analysis else "not_analyzed"
        contribution = commitment.contribution_level or "indeterminate"
        contribution_counts[contribution] = contribution_counts.get(contribution, 0) + 1
        if status == "not_analyzed":
            not_analyzed_count += 1
            continue
        if status in {"not_due", "condition_not_met", "not_applicable"}:
            continue
        due_count += 1
        due_weight += weight
        if status == "unclear":
            unclear_count += 1
            continue
        fulfillment_value = commitment_fulfillment_value(status)
        if fulfillment_value is None:
            unclear_count += 1
            continue
        analyzed_count += 1
        analyzed_weight += weight
        fulfillment_points += weight * fulfillment_value
        if status == "violated":
            violated_count += 1
        if status == "abandoned":
            abandoned_count += 1
        coefficient = commitment_contribution_coefficient(contribution)
        if coefficient is None:
            indeterminate_contribution_count += 1
            continue
        contribution_weight += weight
        contribution_adjusted_points += weight * fulfillment_value * coefficient

    return {
        "fulfillment_score": round(100 * fulfillment_points / analyzed_weight, 1) if analyzed_weight else None,
        "overall_score": round(100 * contribution_adjusted_points / contribution_weight, 1) if contribution_weight else None,
        "coverage": round(analyzed_weight / due_weight, 3) if due_weight else None,
        "contribution_coverage": round(contribution_weight / due_weight, 3) if due_weight else None,
        "total_commitments": len(commitments),
        "due_commitments": due_count,
        "analyzed_commitments": analyzed_count,
        "total_weight": total_weight,
        "due_weight": due_weight,
        "analyzed_weight": analyzed_weight,
        "unclear_count": unclear_count,
        "not_analyzed_count": not_analyzed_count,
        "indeterminate_contribution_count": indeterminate_contribution_count,
        "violated_count": violated_count,
        "abandoned_count": abandoned_count,
        "contribution_counts": contribution_counts,
    }


def unset_other_active_programs(db: Session, program: Program | None = None) -> None:
    query = select(Program).where(Program.is_active_government_program.is_(True), Program.is_deleted.is_(False))
    if program and program.id:
        query = query.where(Program.id != program.id)
    for item in db.scalars(query):
        item.is_active_government_program = False


def program_payload(program: Program) -> dict[str, Any]:
    return {
        "id": program.id,
        "title": program.title,
        "slug": program.slug,
        "description": program.description,
        "short_description": program.short_description,
        "program_type": program.program_type,
        "program_type_label": PROGRAM_TYPES.get(program.program_type, program.program_type),
        "political_subject_name": program.political_subject_name,
        "related_party": {
            "id": program.related_party.id,
            "slug": program.related_party.slug,
            "full_name": program.related_party.full_name,
            "short_name": program.related_party.short_name,
        }
        if program.related_party
        else None,
        "related_coalition_name": program.related_coalition_name,
        "period_text": program.period_text,
        "period_start": program.period_start,
        "period_end": program.period_end,
        "publication_date": program.publication_date,
        "source_url": program.source_url,
        "source_title": program.source_title,
        "source_description": program.source_description,
        "source_acquisition_method": program.source_acquisition_method,
        "source_coverage_status": program.source_coverage_status,
        "source_acquisition_note": program.source_acquisition_note,
        "source_document_complete": program.source_document_complete,
        "supplementary_source_urls": program.supplementary_source_urls or [],
        "is_active_government_program": program.is_active_government_program,
    }


def direct_commitment_status_counts(db: Session, program_id) -> dict[Any, dict[str, int]]:
    status_expr = public_effective_status_expr().label("effective_status")
    rows = db.execute(
        select(Commitment.program_section_id, status_expr, func.count(Commitment.id))
        .where(Commitment.program_id == program_id, Commitment.is_published.is_(True))
        .group_by(Commitment.program_section_id, status_expr)
    ).all()
    counts_by_section: dict[Any, dict[str, int]] = {}
    for section_id, status, count in rows:
        counts = counts_by_section.setdefault(section_id, zero_status_counts())
        counts[status] = int(count)
    return counts_by_section


def direct_commitment_counts(db: Session, program_id) -> dict[Any, int]:
    rows = db.execute(
        select(Commitment.program_section_id, func.count(Commitment.id))
        .where(Commitment.program_id == program_id, Commitment.is_published.is_(True))
        .group_by(Commitment.program_section_id)
    ).all()
    return {section_id: int(count) for section_id, count in rows}


def rollup_section_status_counts(sections: list[ProgramSection], direct_counts: dict[Any, dict[str, int]]) -> dict[Any, dict[str, int]]:
    children_by_parent: dict[Any, list[ProgramSection]] = {}
    by_id = {section.id: section for section in sections}
    for section in sections:
        children_by_parent.setdefault(section.parent_section_id, []).append(section)

    rolled: dict[Any, dict[str, int]] = {}

    def visit(section: ProgramSection) -> dict[str, int]:
        counts = dict(direct_counts.get(section.id, zero_status_counts()))
        for child in children_by_parent.get(section.id, []):
            merge_status_counts(counts, visit(child))
        rolled[section.id] = counts
        return counts

    for section in sections:
        if section.parent_section_id not in by_id:
            visit(section)
    return rolled


def program_sections_for_summary(db: Session, program_id) -> list[ProgramSection]:
    return list(
        db.scalars(
            select(ProgramSection)
            .where(ProgramSection.program_id == program_id)
            .order_by(ProgramSection.display_order, ProgramSection.created_at)
        )
    )


def section_summary_payload(
    section: ProgramSection,
    *,
    status_counts: dict[str, int],
    direct_commitment_count: int,
    child_section_count: int,
) -> dict[str, Any]:
    total_commitments = sum(status_counts.values())
    return {
        "id": section.id,
        "section_code": section.section_code,
        "title": section.title,
        "summary": section.summary,
        "policy_area": section.policy_area,
        "display_order": section.display_order,
        "status_counts": status_counts,
        "commitment_count": total_commitments,
        "direct_commitment_count": direct_commitment_count,
        "child_section_count": child_section_count,
        "has_subsections": child_section_count > 0,
        "has_commitments": direct_commitment_count > 0,
    }


def program_section_summaries(db: Session, program_id, parent_section_id=None) -> list[dict[str, Any]]:
    sections = program_sections_for_summary(db, program_id)
    direct_counts = direct_commitment_status_counts(db, program_id)
    direct_totals = direct_commitment_counts(db, program_id)
    rolled_counts = rollup_section_status_counts(sections, direct_counts)
    children_by_parent: dict[Any, list[ProgramSection]] = {}
    for section in sections:
        children_by_parent.setdefault(section.parent_section_id, []).append(section)

    items = children_by_parent.get(parent_section_id, [])
    return [
        section_summary_payload(
            section,
            status_counts=rolled_counts.get(section.id, zero_status_counts()),
            direct_commitment_count=direct_totals.get(section.id, 0),
            child_section_count=len(children_by_parent.get(section.id, [])),
        )
        for section in sorted(items, key=lambda item: (item.display_order, item.created_at))
    ]


def program_status_counts(db: Session, program_id) -> dict[str, int]:
    status_expr = public_effective_status_expr().label("effective_status")
    rows = db.execute(
        select(status_expr, func.count(Commitment.id))
        .join(Program)
        .where(
            Commitment.program_id == program_id,
            Commitment.is_published.is_(True),
            Program.is_published.is_(True),
            Program.is_deleted.is_(False),
        )
        .group_by(status_expr)
    ).all()
    counts = zero_status_counts()
    for status, count in rows:
        counts[status] = int(count)
    return counts


def program_last_commitment_update(db: Session, program_id):
    return db.scalar(
        select(func.max(Commitment.last_status_update)).where(Commitment.program_id == program_id, Commitment.is_published.is_(True))
    )


def public_commitment_row_payload(row: Any, program: Program) -> dict[str, Any]:
    status = row.status
    confidence = row.confidence_level
    contribution_level = getattr(row, "contribution_level", None)
    contribution_confidence = getattr(row, "contribution_confidence", None)
    importance_level_value = getattr(row, "importance_level", None)
    importance_weight_value = getattr(row, "importance_weight", None)
    return {
        "id": row.id,
        "display_code": row.display_code,
        "title": row.title,
        "slug": row.slug,
        "normalized_description": row.normalized_description,
        "status": status,
        "status_label": status_label(status),
        "status_group": status_group(status),
        "status_group_label": STATUS_GROUPS.get(status_group(status), status_group(status)),
        "confidence_level": confidence,
        "confidence_label": confidence_label(confidence),
        "contribution_level": contribution_level,
        "contribution_label": contribution_label(contribution_level),
        "contribution_confidence": contribution_confidence,
        "contribution_confidence_label": confidence_label(contribution_confidence),
        "importance_level": importance_level_value,
        "importance_label": importance_label(importance_level_value),
        "importance_weight": importance_weight_value,
        "last_status_update": row.last_status_update,
        "display_order": row.display_order,
        "program_section_id": row.program_section_id,
        "program": program_payload(program),
        "evidence_count": int(row.evidence_count or 0),
    }


def apply_public_commitment_filters(query, *, program_id, section_id=None, q=None, status=None, confidence=None):
    has_analysis = exists(select(CommitmentStatusUpdate.id).where(CommitmentStatusUpdate.commitment_id == Commitment.id))
    query = query.where(Commitment.program_id == program_id, Commitment.is_published.is_(True))
    if section_id:
        query = query.where(Commitment.program_section_id == section_id)
    if q:
        pattern = f"%{q.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(Commitment.title).like(pattern),
                func.lower(Commitment.normalized_description).like(pattern),
                func.lower(Commitment.original_text).like(pattern),
            )
        )
    if status:
        if status == "not_analyzed":
            query = query.where(~has_analysis)
        elif status in COMMITMENT_STATUSES:
            query = query.where(has_analysis, Commitment.current_status == status)
    if confidence:
        if confidence in CONFIDENCE_LEVELS:
            query = query.where(has_analysis, Commitment.confidence == confidence)
    return query


def commitment_rows_page(
    db: Session,
    program: Program,
    *,
    section_id=None,
    q: str | None = None,
    status: str | None = None,
    confidence: str | None = None,
    sort: str = "order",
    limit: int = 25,
    offset: int = 0,
) -> dict[str, Any]:
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)
    evidence_count = (
        select(func.count(CommitmentEvidenceLink.id))
        .where(CommitmentEvidenceLink.commitment_id == Commitment.id)
        .correlate(Commitment)
        .scalar_subquery()
    )
    status_expr = public_effective_status_expr().label("status")
    confidence_expr = public_confidence_expr().label("confidence_level")
    base = select(Commitment.id)
    base = apply_public_commitment_filters(
        base,
        program_id=program.id,
        section_id=section_id,
        q=q,
        status=status,
        confidence=confidence,
    )
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0

    query = select(
        Commitment.id,
        Commitment.program_section_id,
        Commitment.display_code,
        Commitment.title,
        Commitment.slug,
        Commitment.normalized_description,
        Commitment.display_order,
        Commitment.last_status_update,
        Commitment.contribution_level,
        Commitment.contribution_confidence,
        Commitment.importance_level,
        Commitment.importance_weight,
        status_expr,
        confidence_expr,
        evidence_count.label("evidence_count"),
    )
    query = apply_public_commitment_filters(
        query,
        program_id=program.id,
        section_id=section_id,
        q=q,
        status=status,
        confidence=confidence,
    )
    if sort == "updated":
        query = query.order_by(desc(Commitment.last_status_update).nullslast(), Commitment.display_order, Commitment.created_at)
    elif sort == "title":
        query = query.order_by(Commitment.title, Commitment.display_order, Commitment.created_at)
    elif sort == "status":
        query = query.order_by(status_expr, Commitment.display_order, Commitment.created_at)
    else:
        query = query.order_by(Commitment.display_order, Commitment.created_at)
    rows = db.execute(query.offset(offset).limit(limit)).all()
    next_offset = offset + limit
    return {
        "items": [public_commitment_row_payload(row, program) for row in rows],
        "total_count": int(total),
        "limit": limit,
        "offset": offset,
        "next_offset": next_offset if next_offset < total else None,
        "has_more": next_offset < total,
    }


def section_status_counts(section: Any) -> dict[str, int]:
    counts = {key: 0 for key in COMMITMENT_STATUSES}
    for commitment in section.commitments:
        if not commitment.is_published:
            continue
        effective_status = commitment.status if commitment.status_updates else "not_analyzed"
        counts[effective_status] = counts.get(effective_status, 0) + 1
    for child in section.child_sections:
        child_counts = section_status_counts(child)
        for key, value in child_counts.items():
            counts[key] = counts.get(key, 0) + value
    return counts


def section_payload(section: Any) -> dict[str, Any]:
    return {
        "id": section.id,
        "section_code": section.section_code,
        "title": section.title,
        "summary": section.summary,
        "problem_description": section.problem_description,
        "aggregate_status_summary": section.aggregate_status_summary,
        "key_findings": section.key_findings or [],
        "policy_area": section.policy_area,
        "display_order": section.display_order,
        "status_counts": section_status_counts(section),
        "commitments": [
            commitment_payload(item)
            for item in sorted(section.commitments, key=lambda item: (item.display_order, item.created_at))
            if item.is_published
        ],
        "children": [section_payload(item) for item in sorted(section.child_sections, key=lambda item: (item.display_order, item.created_at))],
    }


def evidence_payload(evidence: CommitmentEvidence) -> dict[str, Any]:
    return {
        "id": evidence.id,
        "title": evidence.title,
        "url": evidence.url,
        "source_type": evidence.source_type,
        "source_type_label": EVIDENCE_SOURCE_TYPES.get(evidence.source_type, evidence.source_type),
        "evidence_role": evidence.evidence_role,
        "evidence_role_label": evidence_role_label(evidence.evidence_role),
        "evidence_strength": evidence.evidence_strength,
        "evidence_strength_label": evidence_strength_label(evidence.evidence_strength),
        "is_self_reported": evidence.is_self_reported,
        "is_independent_confirmation": evidence.is_independent_confirmation,
        "is_contradictory": evidence.is_contradictory,
        "is_disproven": evidence.is_disproven,
        "limitations": evidence.limitations,
        "claim": evidence.note,
        "component_refs": [],
        "publisher": evidence.publisher,
        "published_at": evidence.published_at,
        "accessed_at": evidence.evidence_item.accessed_at if evidence.evidence_item else None,
        "quote_or_relevant_excerpt": evidence.quote_or_relevant_excerpt,
        "description": evidence.description,
        "supports_status": evidence.supports_status,
        "relation_type": evidence.relation_type,
        "factual_review_status": evidence.factual_review_status,
    }


def ai_run_public_metadata(ai_run: Any | None) -> dict[str, Any] | None:
    if not ai_run:
        return None
    return {
        "model_name": ai_run.model_name,
        "prompt_version": ai_run.prompt_version,
        "schema_version": ai_run.schema_version,
        "methodology_version": ai_run.methodology_version,
        "analysis_date": ai_run.analysis_date,
        "task_type": ai_run.task_type,
        "status": ai_run.status,
    }


def commitment_payload(commitment: Commitment, include_evidence: bool = False) -> dict[str, Any]:
    updates = sorted(commitment.status_updates, key=lambda item: item.created_at, reverse=True)
    has_analysis = bool(updates)
    latest_update = updates[0] if updates else None
    current_status = commitment.status if has_analysis else "not_analyzed"
    current_group = status_group(current_status)
    payload = {
        "id": commitment.id,
        "display_code": commitment.display_code,
        "title": commitment.title,
        "slug": commitment.slug,
        "original_text": commitment.original_text if include_evidence else None,
        "normalized_description": commitment.normalized_description,
        "topic": commitment.topic,
        "responsible_institutions": commitment.responsible_institutions,
        "period": commitment.period,
        "deadline": commitment.deadline,
        "measurable_criteria": commitment.measurable_criteria,
        "commitment_type": commitment.commitment_type,
        "commitment_type_label": commitment_type_label(commitment.commitment_type),
        "promised_item_type": commitment.promised_item_type,
        "baseline_mode": commitment.baseline_mode,
        "baseline_mode_label": baseline_mode_label(commitment.baseline_mode),
        "required_external_actors": commitment.required_external_actors,
        "control_level": commitment.control_level,
        "control_level_label": control_level_label(commitment.control_level),
        "evaluation_basis": commitment.evaluation_basis,
        "contribution_types": commitment.contribution_types_text,
        "official_program_change_note": commitment.official_program_change_note,
        "source_version_note": commitment.source_version_note,
        "quantitative_target": commitment.quantitative_target,
        "quantitative_actual": commitment.quantitative_actual,
        "measure_validity_status": commitment.measure_validity_status,
        "measure_validity_label": measure_validity_label(commitment.measure_validity_status),
        "status": current_status,
        "status_label": COMMITMENT_STATUSES[current_status]["label"],
        "status_group": current_group,
        "status_group_label": STATUS_GROUPS.get(current_group, current_group),
        "status_explanation": commitment.status_explanation if has_analysis else None,
        "confidence_level": commitment.confidence_level if has_analysis else None,
        "confidence_label": CONFIDENCE_LEVELS.get(commitment.confidence_level) if has_analysis else None,
        "confidence_explanation": commitment.confidence_explanation if has_analysis else None,
        "contribution_level": commitment.contribution_level if has_analysis else None,
        "contribution_label": contribution_label(commitment.contribution_level) if has_analysis else None,
        "contribution_explanation": commitment.contribution_explanation if has_analysis else None,
        "contribution_confidence": commitment.contribution_confidence if has_analysis else None,
        "contribution_confidence_label": confidence_label(commitment.contribution_confidence) if has_analysis else None,
        "last_status_update": commitment.last_status_update if has_analysis else None,
        "importance_level": commitment.importance_level,
        "importance_label": importance_label(commitment.importance_level),
        "importance_weight": commitment_importance_weight(commitment),
        "is_key_commitment": commitment.is_key_commitment,
        "display_order": commitment.display_order,
        "program": program_payload(commitment.program),
        "evidence_count": len(commitment.evidence),
        "analysis_metadata": ai_run_public_metadata(getattr(latest_update, "ai_run", None) if latest_update else None),
    }
    if include_evidence:
        payload["evidence"] = [evidence_payload(item) for item in commitment.evidence]
        payload["status_history"] = [
            {
                "previous_status": item.previous_status,
                "new_status": item.new_status,
                "new_status_group": item.new_status_group,
                "status_explanation": item.status_explanation,
                "confidence": item.confidence,
                "contribution_level": item.new_contribution_level,
                "contribution_label": contribution_label(item.new_contribution_level),
                "contribution_explanation": item.contribution_explanation,
                "contribution_confidence": item.contribution_confidence,
                "effective_date": item.effective_date,
                "factual_review_status": item.factual_review_status,
                "created_at": item.created_at,
                "ai_run": ai_run_public_metadata(getattr(item, "ai_run", None)),
            }
            for item in updates
        ]
    return payload


def commitment_query():
    return select(Commitment).options(
        selectinload(Commitment.program).selectinload(Program.related_party),
        selectinload(Commitment.related_party),
        selectinload(Commitment.evidence_links).selectinload(CommitmentEvidence.evidence_item),
        selectinload(Commitment.status_updates).selectinload(CommitmentStatusUpdate.ai_run),
    )


def active_government_program_summary(db: Session) -> dict[str, Any] | None:
    program = db.scalar(
        select(Program)
        .where(Program.is_active_government_program.is_(True), Program.is_published.is_(True), Program.is_deleted.is_(False))
        .options(selectinload(Program.related_party))
    )
    if not program:
        return None
    commitments = list(
        db.scalars(
            commitment_query()
            .where(Commitment.program_id == program.id, Commitment.is_published.is_(True))
            .order_by(Commitment.display_order, Commitment.created_at)
        )
    )
    counts = {key: 0 for key in COMMITMENT_STATUSES}
    for commitment in commitments:
        effective_status = commitment.status if commitment.status_updates else "not_analyzed"
        counts[effective_status] = counts.get(effective_status, 0) + 1
    key_commitments = [item for item in commitments if item.is_key_commitment][:5]
    return {
        "program": program_payload(program),
        "total_commitments": len(commitments),
        "status_counts": counts,
        "score_summary": program_score_summary(commitments),
        "key_commitments": [commitment_payload(item) for item in key_commitments],
    }


def topic_options(db: Session) -> list[str]:
    return [
        item
        for item in db.scalars(
            select(Commitment.topic)
            .join(Program)
            .where(Commitment.topic.is_not(None), Commitment.is_published.is_(True), Program.is_deleted.is_(False))
            .group_by(Commitment.topic)
            .order_by(Commitment.topic)
        )
        if item
    ]


def validate_import_json(raw_json: str) -> dict[str, Any]:
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ValueError("Top-level JSON must be an object.")
    program = data.get("program")
    commitments = data.get("commitments")
    if not isinstance(program, dict):
        raise ValueError("Missing program object.")
    if not isinstance(commitments, list) or not commitments:
        raise ValueError("Missing commitments array.")
    if not optional_text(program.get("title")):
        raise ValueError("program.title is required.")
    if program.get("program_type") not in PROGRAM_TYPES:
        raise ValueError("program.program_type is invalid.")
    for index, commitment in enumerate(commitments, start=1):
        if not isinstance(commitment, dict):
            raise ValueError(f"commitments[{index}] must be an object.")
        if not optional_text(commitment.get("title")):
            raise ValueError(f"commitments[{index}].title is required.")
        if not optional_text(commitment.get("original_text")):
            raise ValueError(f"commitments[{index}].original_text is required.")
        if commitment.get("initial_status", "not_started") not in COMMITMENT_STATUSES:
            raise ValueError(f"commitments[{index}].initial_status is invalid.")
        if commitment.get("confidence_level", "medium") not in CONFIDENCE_LEVELS:
            raise ValueError(f"commitments[{index}].confidence_level is invalid.")
    return data


