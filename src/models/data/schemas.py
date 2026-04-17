"""Pydantic models for normalized dataset metadata (BioStudies & Zenodo)."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Shared / reusable sub-models ──────────────────────────────────────────


class Author(BaseModel):
    """Normalised author/creator."""

    name: Optional[str] = None
    orcid: Optional[str] = None
    affiliation: Optional[str] = None
    email: Optional[str] = None


class Funding(BaseModel):
    """Normalised funding entry."""

    funder: Optional[str] = None
    funder_doi: Optional[str] = None
    acronym: Optional[str] = None
    title: Optional[str] = None
    code: Optional[str] = None
    url: Optional[str] = None
    raw: Optional[dict[str, Any]] = None
    source: Optional[str] = None


class DataFile(BaseModel):
    """Normalised file entry (common to both sources)."""

    name: Optional[str] = None
    path: Optional[str] = None
    size: Optional[int] = None
    checksum: Optional[str] = None
    url: Optional[str] = None
    exists: Optional[bool] = None
    content_length: Optional[str] = None

    model_config = {"extra": "allow"}


class Publication(BaseModel):
    """Linked publication extracted from a dataset record."""

    title: Optional[str] = None
    doi: Optional[str] = None
    doi_url: Optional[str] = None
    url: Optional[str] = None
    pmid: Optional[str] = None
    year: Optional[str] = None
    authors: Optional[str] = None
    journal: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    type: Optional[str] = None
    issn: Optional[str] = None
    relation: Optional[str] = None
    resource_type: Optional[str] = None
    source: Optional[str] = None


# ── Top-level normalised metadata ─────────────────────────────────────────


class NormalizedMetadata(BaseModel):
    """Unified normalised metadata for any dataset (Zenodo or BioStudies)."""

    title: Optional[str] = None
    description: Optional[str] = None
    license: Optional[str] = None
    authors: list[Author] = Field(default_factory=list)
    funding: list[Funding] = Field(default_factory=list)
    ReleaseDate: Optional[str] = Field(None, alias="ReleaseDate")
    id: Optional[str | int] = None
    type: Optional[str] = None
    version: Optional[str] = None
    files: list[DataFile] = Field(default_factory=list)
    url: Optional[str] = None
    doi: Optional[str] = None
    doi_url: Optional[str] = None
    publications: list[Publication] = Field(default_factory=list)

    # Zenodo-specific
    conceptdoi: Optional[str] = None
    conceptdoi_url: Optional[str] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


# ── BioStudies raw-metadata models ────────────────────────────────────────


class Attribute(BaseModel):
    name: str = ""
    value: str = ""


class BiologicalContext(BaseModel):
    model_config = {"extra": "allow"}


class TechnicalDetails(BaseModel):
    model_config = {"extra": "allow"}


class ExperimentalDesign(BaseModel):
    factors: list[dict[str, Any]] = Field(default_factory=list)

    model_config = {"extra": "allow"}


class ProtocolEntry(BaseModel):
    type: str = ""
    description: str = ""
    attributes: list[Attribute] = Field(default_factory=list)


class LinkEntry(BaseModel):
    url: str = ""
    type: str = ""
    description: str = ""
    attributes: list[dict[str, Any]] = Field(default_factory=list)


class FileEntry(BaseModel):
    """Rich file entry from BioStudies parse_metadata."""

    name: str = ""
    path: str = ""
    size: Optional[int] = None
    type: Optional[str] = None
    description: str = ""
    file_kind: str = ""
    attributes: list[dict[str, Any]] = Field(default_factory=list)
    url: Optional[str] = None
    exists_check: Optional[dict[str, Any]] = None
    raw: Optional[dict[str, Any]] = None


class AuthorDetail(BaseModel):
    name: str = ""
    email: str = ""
    orcid: Optional[str] = None
    affiliation_ref: Optional[str] = None
    affiliation_name: str = ""


class BioStudiesParsedMetadata(BaseModel):
    """Full structured metadata returned by BioStudiesExtractor.parse_metadata."""

    accession: str = "N/A"
    title: str = "N/A"
    description: str = "N/A"
    release_date: str = "N/A"
    modification_date: str = "N/A"
    type: str = "N/A"

    # VHP4Safety filterable fields
    case_study: str = ""
    regulatory_question: str = ""
    flow_step: str = ""
    collection: str = ""

    attributes: list[Attribute] = Field(default_factory=list)
    authors: list[str] = Field(default_factory=list)
    author_details: list[AuthorDetail] = Field(default_factory=list)
    files: list[FileEntry] = Field(default_factory=list)
    links: list[LinkEntry] = Field(default_factory=list)
    protocols: list[ProtocolEntry] = Field(default_factory=list)
    publications: list[LinkEntry] = Field(default_factory=list)
    organizations: list[dict[str, Any]] = Field(default_factory=list)

    biological_context: BiologicalContext = Field(default_factory=BiologicalContext)
    technical_details: TechnicalDetails = Field(default_factory=TechnicalDetails)
    experimental_design: ExperimentalDesign = Field(default_factory=ExperimentalDesign)

    rocrate_file: Optional[dict[str, Any]] = None
    rocrate_url: Optional[str] = None

    url: str = ""
    raw_data: Optional[dict[str, Any]] = None

    model_config = {"extra": "allow"}


# ── Zenodo parsed-metadata model ──────────────────────────────────────────


class ZenodoFileEntry(BaseModel):
    id: Optional[str] = None
    key: Optional[str] = None
    size: Optional[int] = None
    checksum: Optional[str] = None
    links: dict[str, Any] = Field(default_factory=dict)


class ZenodoParsedMetadata(BaseModel):
    """Full structured metadata returned by ZenodoExtractor.parse_metadata."""

    id: Optional[int | str] = None
    recid: Optional[int | str] = None
    doi: Optional[str] = None
    doi_url: Optional[str] = None
    title: str = "N/A"
    description: str = "N/A"
    publication_date: str = "N/A"
    access_right: Optional[str] = None
    creators: list[dict[str, Any]] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    resource_type: dict[str, Any] = Field(default_factory=dict)
    license: dict[str, Any] = Field(default_factory=dict)
    grants: list[dict[str, Any]] = Field(default_factory=list)
    communities: list[dict[str, Any]] = Field(default_factory=list)
    related_identifiers: list[dict[str, Any]] = Field(default_factory=list)
    files: list[ZenodoFileEntry] = Field(default_factory=list)
    links: dict[str, Any] = Field(default_factory=dict)
    stats: dict[str, Any] = Field(default_factory=dict)
    is_rocrate: bool = False

    url: str = ""
    raw: Optional[dict[str, Any]] = None

    model_config = {"extra": "allow"}


# ── URL-existence check result ────────────────────────────────────────────


class UrlExistsResult(BaseModel):
    """Result of a HEAD / Range probe to check file existence."""

    url: Optional[str] = None
    exists: bool = False
    status_code: Optional[int] = None
    content_length: Optional[str] = None
    final_url: Optional[str] = None
    error: Optional[str] = None
    method: Optional[str] = None
