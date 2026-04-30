"""Data models & extractors for BioStudies and Zenodo datasets."""

from src.models.data.biostudies import BioStudiesExtractor
from src.models.data.zenodo import ZenodoExtractor
from src.models.data.mapping import normalize_all
from src.models.data.schemas import (
    Author,
    Attribute,
    AuthorDetail,
    BiologicalContext,
    BioStudiesParsedMetadata,
    DataFile,
    ExperimentalDesign,
    FileEntry,
    Funding,
    LinkEntry,
    NormalizedMetadata,
    ProtocolEntry,
    Publication,
    TechnicalDetails,
    UrlExistsResult,
    ZenodoFileEntry,
    ZenodoParsedMetadata,
)

__all__ = [
    # Extractors
    "BioStudiesExtractor",
    "ZenodoExtractor",
    # Normalizer
    "normalize_all",
    # Pydantic models
    "Author",
    "Attribute",
    "AuthorDetail",
    "BiologicalContext",
    "BioStudiesParsedMetadata",
    "DataFile",
    "ExperimentalDesign",
    "FileEntry",
    "Funding",
    "LinkEntry",
    "NormalizedMetadata",
    "ProtocolEntry",
    "Publication",
    "TechnicalDetails",
    "UrlExistsResult",
    "ZenodoFileEntry",
    "ZenodoParsedMetadata",
]
