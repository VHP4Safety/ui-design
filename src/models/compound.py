"""Pydantic models for compound data from CompoundCloud SPARQL.

These are not stored in the database — they model the responses from
the CompoundCloud Wikibase SPARQL endpoint and from Wikidata QLever
for experimental data.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CompoundSummary(BaseModel):
    """Core compound identifiers from CompoundCloud."""

    wcid: str = Field(description="CompoundCloud entity URI")
    label: str = Field(description="Human-readable compound name")
    inchi: str = ""
    inchikey: str = ""
    smiles: str = Field("", alias="SMILES")
    formula: str = ""
    mass: str = ""

    model_config = {"populate_by_name": True}


class CompoundIdentifier(BaseModel):
    """A single external identifier for a compound."""

    property_label: str = Field(
        "", description="Name of the identifier property"
    )
    value: str = ""
    formatter_url: str = Field(
        "", description="URL template for the identifier"
    )


class CompoundToxicology(BaseModel):
    """A toxicology property row."""

    property_label: str = ""
    value: str = ""


class CompoundExperimentalDatum(BaseModel):
    """A single experimental measurement from Wikidata."""

    property_label: str = Field(
        "", description="Measured property name"
    )
    value: str = ""
    units_label: str = ""
    source: str = ""
    doi: str = ""
    see_also: str = Field(
        "", description="Link to the Wikidata statement"
    )


class CompoundDetail(BaseModel):
    """Full compound view combining all SPARQL query results."""

    summary: Optional[CompoundSummary] = None
    identifiers: list[CompoundIdentifier] = Field(
        default_factory=list
    )
    toxicology: list[CompoundToxicology] = Field(
        default_factory=list
    )
    experimental_data: list[CompoundExperimentalDatum] = Field(
        default_factory=list
    )
