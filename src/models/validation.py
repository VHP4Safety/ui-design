"""Pydantic models for the data completeness validation report.

These are the response shapes for /api/validation/
and /api/validation/<entity>.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class FieldCompleteness(BaseModel):
    """Completeness information for a single field of one entry."""

    field: str
    present: bool
    value_preview: str | None = None


class EntryValidation(BaseModel):
    """Completeness report for a single DB row."""

    id: str
    label: str
    fields_total: int
    fields_filled: int
    completeness_pct: float
    missing: list[str] = Field(default_factory=list)
    details: list[FieldCompleteness] = Field(default_factory=list)


class EntitySummary(BaseModel):
    """Aggregate completeness stats for one entity type."""

    entity: str
    total_entries: int
    schema_fields: list[str] = Field(default_factory=list)
    avg_completeness_pct: float
    fully_complete: int
    entries: list[EntryValidation] = Field(default_factory=list)


class ValidationReport(BaseModel):
    """Full cross-entity completeness report."""

    generated_at: str
    entities: list[EntitySummary] = Field(default_factory=list)
