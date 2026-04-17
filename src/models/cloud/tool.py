"""Pydantic models for VHP4Safety Cloud tool JSON schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Method(BaseModel):
    """A single method entry (docs/methods/*.json).

    Field names match the ORM columns in tables.py.
    Aliases map to the raw JSON keys from the cloud repo.
    """

    id: str
    method: str = Field(description="Method title (from issue title)")
    issue_number: Optional[int] = None
    description: Optional[str] = Field(
        None, alias="method_description_content"
    )

    # Upstream issue-template fields (new-tool-method-entry.yml)
    data_producer: Optional[str] = Field(
        None, alias="data_producer_content"
    )
    sop: Optional[str] = Field(
        None, alias="available_sop_or_protocol_content"
    )
    vendor: Optional[str] = Field(
        None, alias="vendor_content"
    )
    catalog_number: Optional[str] = Field(
        None, alias="catalog_number_content"
    )
    catalog_webpage_url: Optional[str] = None
    citation: Optional[str] = Field(
        None, alias="citation_content"
    )
    stage: Optional[str] = Field(
        None, alias="vhp4safety_workflow_stage_content"
    )
    substage: Optional[str] = Field(
        None, alias="workflow_substage_content"
    )
    case_study: Optional[str] = Field(
        None, alias="case_study_content"
    )
    regulatory_question: Optional[str] = Field(
        None, alias="regulatory_question_content"
    )
    type_iri: Optional[str] = Field(
        None, alias="ontology_term_content"
    )
    ontology: Optional[str] = Field(
        None, alias="type_content"
    )
    key_event_id: Optional[str] = Field(
        None,
        alias="relevant_aop_wiki_key_event(s)_to_the_assay_content",
    )
    aop_id: Optional[str] = Field(
        None,
        alias="relevant_aop_wiki_adverse_outcome_pathway(s)"
        "_to_the_assay_content",
    )

    # Regulatory question flags
    reg_q_1a: Optional[str] = None
    reg_q_1b: Optional[str] = None
    reg_q_2a: Optional[str] = None
    reg_q_2b: Optional[str] = None
    reg_q_3a: Optional[str] = None
    reg_q_3b: Optional[str] = None

    timestamp: Optional[datetime] = None
    https: Optional[str] = Field(
        None, description="Broken URL fragment in some files"
    )

    model_config = {"populate_by_name": True, "extra": "allow"}


class MethodIndex(BaseModel):
    """The full methods index (cap/methods_index.json).

    A mapping of method id → Method.
    """

    root: dict[str, Method] = Field(default_factory=dict)

    model_config = {"extra": "allow"}

    @classmethod
    def from_dict(cls, data: dict) -> MethodIndex:
        return cls(root={k: Method.model_validate(v) for k, v in data.items()})
