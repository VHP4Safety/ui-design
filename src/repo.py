"""Repository layer — all DB access returns Pydantic model instances.

Every public function is the single point of contact between raw SQLite
rows and the rest of the application.  The API, seed, and test suite all
go through here so schema changes only need updating in one place.
"""

from __future__ import annotations

import json
from typing import Optional

from src.db import get_db
from src.models.casestudy import CaseStudyCard
from src.models.cloud.method import ServiceIndexEntry  # tool rows
from src.models.cloud.tool import Method  # method rows
from src.models.platform import RegulatoryQuestion, StageExplanation


#  helpers 


def _one(conn, sql: str, params: tuple = ()) -> Optional[dict]:
    row = conn.execute(sql, params).fetchone()
    return dict(row) if row else None


def _many(conn, sql: str, params: tuple = ()) -> list[dict]:
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


# tools


def list_tools(
    stage: Optional[str] = None,
    search: Optional[str] = None,
) -> list[ServiceIndexEntry]:
    sql, params = "SELECT * FROM tools WHERE 1=1", []
    if stage:
        sql += " AND stage = ?"
        params.append(stage)
    if search:
        sql += " AND service LIKE ?"
        params.append(f"%{search}%")
    sql += " ORDER BY service"
    with get_db() as conn:
        return [ServiceIndexEntry.model_validate(r) for r in _many(conn, sql, params)]


def get_tool(tool_id: str) -> Optional[ServiceIndexEntry]:
    with get_db() as conn:
        r = _one(conn, "SELECT * FROM tools WHERE id = ?", (tool_id,))
        return ServiceIndexEntry.model_validate(r) if r else None


#  methods 


def list_methods(
    stage: Optional[str] = None,
    search: Optional[str] = None,
) -> list[Method]:
    sql, params = "SELECT * FROM methods WHERE 1=1", []
    if stage:
        sql += " AND stage LIKE ?"
        params.append(f"%{stage}%")
    if search:
        sql += " AND method LIKE ?"
        params.append(f"%{search}%")
    sql += " ORDER BY method"
    with get_db() as conn:
        return [Method.model_validate(r) for r in _many(conn, sql, params)]


def get_method(method_id: str) -> Optional[Method]:
    with get_db() as conn:
        r = _one(conn, "SELECT * FROM methods WHERE id = ?", (method_id,))
        if not r:
            return None
        if r.get("raw_json"):
            r["raw"] = json.loads(r["raw_json"])
        return Method.model_validate(r)


#  platform 


def list_regulatory_questions() -> list[RegulatoryQuestion]:
    with get_db() as conn:
        return [
            RegulatoryQuestion.model_validate(r)
            for r in _many(conn, "SELECT * FROM regulatory_questions")
        ]


def list_stages() -> list[StageExplanation]:
    with get_db() as conn:
        return [
            StageExplanation.model_validate(r)
            for r in _many(conn, "SELECT * FROM stage_explanations")
        ]


#  case studies 


def list_case_studies() -> list[CaseStudyCard]:
    with get_db() as conn:
        return [
            CaseStudyCard.model_validate(r)
            for r in _many(conn, "SELECT * FROM case_studies")
        ]


def get_case_study(slug: str) -> Optional[CaseStudyCard]:
    with get_db() as conn:
        r = _one(conn, "SELECT * FROM case_studies WHERE slug = ?", (slug,))
        return CaseStudyCard.model_validate(r) if r else None
