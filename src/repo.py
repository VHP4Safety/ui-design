"""Repository layer — all DB access returns Pydantic model instances.

ORM instances are validated directly via ``model_validate(orm_obj)``
thanks to ``from_attributes = True`` on every Pydantic schema.
"""

from __future__ import annotations

import json
from typing import Optional

from src.db import (
    CaseStudy as CaseStudyORM,
    Method as MethodORM,
    RegulatoryQuestion as RegulatoryQuestionORM,
    StageExplanation as StageExplanationORM,
    Tool as ToolORM,
    db,
)
from src.models.casestudy import CaseStudyCard
from src.models.cloud.method import ServiceIndexEntry  # tool rows
from src.models.cloud.tool import Method  # method rows
from src.models.platform import RegulatoryQuestion, StageExplanation


# ── tools ──────────────────────────────────────────────────────────────


def list_tools(
    stage: Optional[str] = None,
    search: Optional[str] = None,
) -> list[ServiceIndexEntry]:
    q = ToolORM.query
    if stage:
        q = q.filter(ToolORM.stage == stage)
    if search:
        q = q.filter(ToolORM.service.ilike(f"%{search}%"))
    return [ServiceIndexEntry.model_validate(r) for r in q.order_by(ToolORM.service)]


def get_tool(tool_id: str) -> Optional[ServiceIndexEntry]:
    r = db.session.get(ToolORM, tool_id)
    return ServiceIndexEntry.model_validate(r) if r else None


# ── methods ────────────────────────────────────────────────────────────


def list_methods(
    stage: Optional[str] = None,
    search: Optional[str] = None,
) -> list[Method]:
    q = MethodORM.query
    if stage:
        q = q.filter(MethodORM.stage.ilike(f"%{stage}%"))
    if search:
        q = q.filter(MethodORM.method.ilike(f"%{search}%"))
    return [Method.model_validate(r) for r in q.order_by(MethodORM.method)]


def get_method(method_id: str) -> Optional[Method]:
    r = db.session.get(MethodORM, method_id)
    if not r:
        return None
    m = Method.model_validate(r)
    if r.raw_json:
        m.model_extra["raw"] = json.loads(r.raw_json)  # type: ignore[index]
    return m


# ── platform ───────────────────────────────────────────────────────────


def list_regulatory_questions() -> list[RegulatoryQuestion]:
    return [RegulatoryQuestion.model_validate(r) for r in RegulatoryQuestionORM.query]


def list_stages() -> list[StageExplanation]:
    return [StageExplanation.model_validate(r) for r in StageExplanationORM.query]


# ── case studies ───────────────────────────────────────────────────────


def list_case_studies() -> list[CaseStudyCard]:
    return [CaseStudyCard.model_validate(r) for r in CaseStudyORM.query]


def get_case_study(slug: str) -> Optional[CaseStudyCard]:
    r = db.session.get(CaseStudyORM, slug)
    return CaseStudyCard.model_validate(r) if r else None
