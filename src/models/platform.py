"""Pydantic models for VHP4Safety platform configuration and domain objects."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class RegulatoryQuestion(BaseModel):
    """A regulatory question tied to a case study."""

    key: str = Field(description="Internal key, e.g. reg_q_1a")
    label: str
    explanation: str
    case_study: Optional[str] = None

    model_config = {"from_attributes": True}


class StageExplanation(BaseModel):
    """Safety-assessment workflow stage with a short explanation."""

    name: str
    explanation: str

    model_config = {"from_attributes": True}


class CompoundProperty(BaseModel):
    """Single property row returned by a SPARQL compound query."""

    property_label: str = ""
    value: str = ""
    units_label: Optional[str] = None
    formatter_url: Optional[str] = None
    source: Optional[str] = None
    doi: Optional[str] = None
    see_also: Optional[str] = None


class CompoundSummary(BaseModel):
    """Core identifiers for a compound from CompoundCloud."""

    wcid: str
    label: str
    inchi: str = ""
    inchikey: str = ""
    smiles: str = Field("", alias="SMILES")
    formula: str = ""
    mass: str = ""

    model_config = {"populate_by_name": True}


class GlossaryStageMapping(BaseModel):
    """Maps a glossary URL to a human-readable stage name."""

    glossary_url: str
    stage_name: str
