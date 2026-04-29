"""RESTful API — Pydantic -> OpenAPI 3.1 auto-generated.

Uses flask-openapi3 so that the OpenAPI spec is derived directly from
the Pydantic models in src/models/.

Swagger UI: /api/v1/
OpenAPI JSON:/api/v1/openapi.json
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from flask import abort
from flask_openapi3 import APIBlueprint, OpenAPI, Tag
from pydantic import BaseModel, ConfigDict, Field, RootModel

from src import repo
from src.db import get_conn
from src.models.casestudy import CaseStudyCard as CSModel
from src.models.cloud.method import ServiceIndexEntry as ToolModel
from src.models.cloud.tool import Method as MethodModel
from src.models.compound import (
    CompoundDetail,
    CompoundExperimentalDatum,
    CompoundIdentifier,
    CompoundSummary,
    CompoundToxicology,
)
from src.models.data.biostudies import BioStudiesExtractor
from src.models.data.mapping import normalize_all
from src.models.data.zenodo import ZenodoExtractor
from src.models.platform import (
    RegulatoryQuestion as RQModel,
    StageExplanation as SEModel,
)
from src.services.compound import (
    get_experimental_data,
    get_full_compound,
    get_identifiers,
    get_properties,
    get_toxicology,
    is_valid_qid,
)

BIOSTUDIES_COLLECTION = "VHP4Safety"
ZENODO_COMMUNITY = "vhp4safety"
ZENODO_RECORD_TYPE = "dataset"

#  Tags
tag_tools = Tag(name="tools", description="Tool / service endpoints")
tag_methods = Tag(name="methods", description="Method endpoints")
tag_reg_q = Tag(name="regulatory_questions", description="Regulatory questions")
tag_stages = Tag(name="stages", description="Safety-assessment workflow stages")
tag_casestudies = Tag(name="casestudies", description="Case study endpoints")
tag_compounds = Tag(name="compounds", description="Compound data (SPARQL-backed)")
tag_data = Tag(name="data", description="Dataset search (BioStudies + Zenodo)")
tag_validation = Tag(name="validation", description="Data completeness validation")

#  Query / path parameter models


class FilterQuery(BaseModel):
    stage: Optional[str] = Field(None, description="Workflow stage filter")
    search: Optional[str] = Field("", description="Free-text search")


class DataSearchQuery(BaseModel):
    query: str = Field("", description="Search term")
    page: int = Field(1, description="Page number (1-based)")
    size: int = Field(18, description="Results per page")


class ToolPath(BaseModel):
    tool_id: str = Field(..., description="Tool identifier, e.g. cdkdepict")


class MethodPath(BaseModel):
    method_id: str = Field(
        ...,
        description="Method identifier, e.g. 5_cfda_assay_to_determine_cytotoxicity",
    )


class CaseStudyPath(BaseModel):
    name: str = Field(..., description="Case study name: kidney, parkinson or thyroid")


class CompoundPath(BaseModel):
    cwid: str = Field(..., description="Compound Wiki compound QID, e.g. Q2270")


class DataDetailPath(BaseModel):
    data_id: str = Field(..., description="Data entry identifier (e.g. 19665244) ")


class EntityPath(BaseModel):
    entity: str = Field(
        ...,
        description="Entity type: tools, methods, case_studies, regulatory_questions or stage_explanations",
    )


#  Response schemas


class ToolResponse(BaseModel):
    """A platform tool / service."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "cdkdepict",
                "service": "CDK Depict",
                "description": "A webservice for generating chemical structure images from SMILES inputs.",
                "stage": "Chemical Characteristics and Hazard Identification",
                "main_url": "https://www.simolecule.com/cdkdepict/depict.html",
                "inst_url": "https://cdkdepict.cloud.vhp4safety.nl/",
                "html_name": "cdkdepict.html",
                "png_file_name": "cdkdepict.png",
                "reg_q_1a": True,
                "reg_q_1b": False,
                "reg_q_2a": False,
                "reg_q_2b": False,
                "reg_q_3a": False,
                "reg_q_3b": False,
            }
        }
    )

    id: str = Field(description="URL-safe identifier")
    service: str = Field(description="Human-readable tool name")
    description: Optional[str] = None
    stage: Optional[str] = Field(None, description="Safety-assessment workflow stage")
    main_url: Optional[str] = Field(None, description="Upstream / canonical URL")
    inst_url: Optional[str] = Field(None, description="VHP4Safety instance URL")
    html_name: Optional[str] = None
    png_file_name: Optional[str] = None
    reg_q_1a: Optional[bool] = Field(
        None, description="Relevant to Kidney case study (a)"
    )
    reg_q_1b: Optional[bool] = Field(
        None, description="Relevant to Kidney case study (b)"
    )
    reg_q_2a: Optional[bool] = Field(
        None, description="Relevant to Parkinson case study (a)"
    )
    reg_q_2b: Optional[bool] = Field(
        None, description="Relevant to Parkinson case study (b)"
    )
    reg_q_3a: Optional[bool] = Field(
        None, description="Relevant to Thyroid case study (a)"
    )
    reg_q_3b: Optional[bool] = Field(
        None, description="Relevant to Thyroid case study (b)"
    )
    login: Optional[str] = None
    provider: Optional[str] = None
    citation: Optional[str] = None
    license: Optional[str] = None
    sourcecode: Optional[str] = None


class MethodResponse(BaseModel):
    """A safety-assessment method / assay."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "5_cfda_assay_to_determine_cytotoxicity",
                "method": "5-CFDA assay to determine cytotoxicity",
                "description": "Fluorescence-based determination of cell membrane damage.",
                "stage": "Adverse Outcome",
                "substage": "Cell death, Adverse outcome",
                "catalog_webpage_url": "https://www.thermofisher.com/order/catalog/product/C1354",
            }
        }
    )

    id: str
    method: str = Field(description="Human-readable method name")
    description: Optional[str] = None
    stage: Optional[str] = None
    substage: Optional[str] = None
    catalog_webpage_url: Optional[str] = None
    vendor: Optional[str] = None
    catalog_number: Optional[str] = None
    citation: Optional[str] = None
    case_study: Optional[str] = None
    regulatory_question: Optional[str] = None
    type_iri: Optional[str] = None
    ontology: Optional[str] = None
    key_event_id: Optional[str] = None
    aop_id: Optional[str] = None


class RegulatoryQuestionResponse(BaseModel):
    """One of the six regulatory questions that frame the case studies."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "key": "reg_q_1a",
                "label": "Kidney Case Study (a)",
                "explanation": "What is the safe cisplatin dose in cancer patients?",
            }
        }
    )

    key: str = Field(description="Internal key, e.g. reg_q_1a")
    label: str
    explanation: str
    case_study: Optional[str] = None


class StageResponse(BaseModel):
    """A safety-assessment workflow stage."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Toxicokinetics",
                "explanation": "Analysis of kinetics (ADME) and how they influence internal dose.",
            }
        }
    )

    name: str
    explanation: str


class CaseStudyResponse(BaseModel):
    """Summary card for a VHP4Safety case study."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "kidney",
                "title": "Kidney case study",
                "description": "To study kidney disease and pharmacovigilance.",
                "image_src": "/static/images/image43_hexagon.svg",
                "config_repo": "VHP4Safety/ui-casestudy-config",
            }
        }
    )

    name: str = Field(description="Case study, e.g. kidney")
    title: str
    description: str
    image_src: Optional[str] = None
    image_alt: Optional[str] = None
    url: Optional[str] = None
    config_repo: Optional[str] = None


class CaseStudyDetailResponse(CaseStudyResponse):
    """Case study with full UI content JSON."""

    content_json: Optional[Any] = Field(
        None,
        description="Full nested JSON driving the case-study UI (intro, process-flow, etc.)",
    )


class DataSourceResult(BaseModel):
    """Paginated results from one data source."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total": 8,
                "hits": [
                    {"title": "VHP4Safety kidney dataset", "doi": "10.1234/example"}
                ],
                "error": None,
            }
        }
    )

    total: int = 0
    hits: list[dict] = Field(default_factory=list)
    error: Optional[str] = None


class DataResult(BaseModel):
    """Combined dataset search results from BioStudies and Zenodo."""

    biostudies: DataSourceResult = Field(default_factory=DataSourceResult)
    zenodo: DataSourceResult = Field(default_factory=DataSourceResult)


class NormalisedDataset(BaseModel):
    """Normalised metadata for a single dataset record."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "VHP4Safety kidney cisplatin dataset",
                "description": "In vitro and in vivo datasets for nephrotoxicity modelling.",
                "doi": "10.1234/example",
                "doi_url": "https://doi.org/10.1234/example",
                "license": "CC-BY-4.0",
                "authors": [{"name": "Smith J"}],
                "files": [],
                "publications": [],
            }
        }
    )

    title: Optional[str] = None
    description: Optional[str] = None
    doi: Optional[str] = None
    doi_url: Optional[str] = None
    license: Optional[str] = None
    authors: list[dict] = Field(default_factory=list)
    files: list[dict] = Field(default_factory=list)
    publications: list[dict] = Field(default_factory=list)


# Validation response schemas (re-exported from src.models.validation for OpenAPI)


class FieldDetail(BaseModel):
    field: str
    present: bool
    value_preview: Optional[str] = None


class EntryValidation(BaseModel):
    id: str
    label: str
    fields_total: int
    fields_filled: int
    completeness_pct: float
    missing: list[str]
    details: list[FieldDetail]


class EntitySummaryResponse(BaseModel):
    """Completeness report for one entity type."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "entity": "tools",
                "total_entries": 50,
                "schema_fields": ["service", "description", "stage", "main_url"],
                "avg_completeness_pct": 42.9,
                "fully_complete": 0,
                "entries": [],
            }
        }
    )

    entity: str
    total_entries: int
    schema_fields: list[str]
    avg_completeness_pct: float
    fully_complete: int
    entries: list[EntryValidation]


class ValidationReportResponse(BaseModel):
    """Full data completeness report across all entity types."""

    generated_at: str
    entities: list[EntitySummaryResponse]


#  List response wrappers (flask-openapi3 requires a concrete BaseModel)


class ToolList(RootModel[list[ToolResponse]]):
    pass


class MethodList(RootModel[list[MethodResponse]]):
    pass


class RegulatoryQuestionList(RootModel[list[RegulatoryQuestionResponse]]):
    pass


class StageList(RootModel[list[StageResponse]]):
    pass


class CaseStudyList(RootModel[list[CaseStudyResponse]]):
    pass


class CompoundIdentifierList(RootModel[list[CompoundIdentifier]]):
    pass


class CompoundToxicologyList(RootModel[list[CompoundToxicology]]):
    pass


class CompoundExperimentalDatumList(RootModel[list[CompoundExperimentalDatum]]):
    pass


#  Blueprints

tools_bp = APIBlueprint(
    "tools", __name__, url_prefix="/api/tools", abp_tags=[tag_tools]
)
methods_bp = APIBlueprint(
    "methods", __name__, url_prefix="/api/methods", abp_tags=[tag_methods]
)
reg_q_bp = APIBlueprint(
    "regulatory_questions",
    __name__,
    url_prefix="/api/regulatory-questions",
    abp_tags=[tag_reg_q],
)
stages_bp = APIBlueprint(
    "stages", __name__, url_prefix="/api/stages", abp_tags=[tag_stages]
)
casestudies_bp = APIBlueprint(
    "casestudies", __name__, url_prefix="/api/casestudies", abp_tags=[tag_casestudies]
)
compounds_bp = APIBlueprint(
    "compounds", __name__, url_prefix="/api/compounds", abp_tags=[tag_compounds]
)
data_bp = APIBlueprint("data", __name__, url_prefix="/api/data", abp_tags=[tag_data])
validation_bp = APIBlueprint(
    "validation", __name__, url_prefix="/api/validation", abp_tags=[tag_validation]
)

#  Tools


@tools_bp.get("/", responses={200: ToolList})
def list_tools(query: FilterQuery):
    """List all tools, with optional stage/search filters."""
    return [
        t.model_dump() for t in repo.list_tools(stage=query.stage, search=query.search)
    ]


@tools_bp.get("/<tool_id>", responses={200: ToolResponse})
def get_tool(path: ToolPath):
    """Get a single tool by its ID."""
    tool = repo.get_tool(path.tool_id)
    if not tool:
        abort(404)
    return tool.model_dump()


#  Methods


@methods_bp.get("/", responses={200: MethodList})
def list_methods(query: FilterQuery):
    """List all methods, with optional stage/search filters."""
    return [
        m.model_dump()
        for m in repo.list_methods(stage=query.stage, search=query.search)
    ]


@methods_bp.get("/<method_id>", responses={200: MethodResponse})
def get_method(path: MethodPath):
    """Get a single method by ID, including full upstream fields."""
    method = repo.get_method(path.method_id)
    if not method:
        abort(404)
    return method.model_dump()


#  Regulatory Questions


@reg_q_bp.get("/", responses={200: RegulatoryQuestionList})
def list_regulatory_questions():
    """List the six regulatory questions that link tools to case studies."""
    return [q.model_dump() for q in repo.list_regulatory_questions()]


#  Stages


@stages_bp.get("/", responses={200: StageList})
def list_stages():
    """List all safety-assessment workflow stages."""
    return [s.model_dump() for s in repo.list_stages()]


#  Case Studies


@casestudies_bp.get("/", responses={200: CaseStudyList})
def list_case_studies():
    """List the VHP4Safety case studies (summary only)."""
    out = []
    for c in repo.list_case_studies():
        d = c.model_dump()
        d["name"] = d.pop("slug", d.get("name"))
        out.append(d)
    return out


@casestudies_bp.get("/<name>", responses={200: CaseStudyDetailResponse})
def get_case_study(path: CaseStudyPath):
    """Get a case study by name, including its full content JSON."""
    case = repo.get_case_study(path.name)
    if not case:
        abort(404)
    d = case.model_dump()
    d["name"] = d.pop("slug", d.get("name"))
    if isinstance(d.get("content_json"), str):
        d["content_json"] = json.loads(d["content_json"])
    return d


#  Compounds


@compounds_bp.get("/<cwid>", responses={200: CompoundDetail})
def get_compound(path: CompoundPath):
    """Get full compound data from Compound Wiki via SPARQL."""
    if not is_valid_qid(path.cwid):
        abort(400)
    try:
        return get_full_compound(path.cwid).model_dump()
    except Exception:
        abort(502)


@compounds_bp.get("/<cwid>/properties", responses={200: CompoundSummary})
def get_compound_properties(path: CompoundPath):
    """Get core compound properties (formula, mass, InChI, SMILES)."""
    if not is_valid_qid(path.cwid):
        abort(400)
    try:
        summary = get_properties(path.cwid)
        if not summary:
            abort(404)
        return summary.model_dump()
    except Exception:
        abort(502)


@compounds_bp.get("/<cwid>/identifiers", responses={200: CompoundIdentifierList})
def get_compound_identifiers(path: CompoundPath):
    """Get external database identifiers (CAS, PubChem, ChEBI, etc.)."""
    if not is_valid_qid(path.cwid):
        abort(400)
    try:
        return [i.model_dump() for i in get_identifiers(path.cwid)]
    except Exception:
        abort(502)


@compounds_bp.get("/<cwid>/toxicology", responses={200: CompoundToxicologyList})
def get_compound_toxicology(path: CompoundPath):
    """Get toxicology data (LD50, LC50, etc.)."""
    if not is_valid_qid(path.cwid):
        abort(400)
    try:
        return [t.model_dump() for t in get_toxicology(path.cwid)]
    except Exception:
        abort(502)


@compounds_bp.get(
    "/<cwid>/experimental-data", responses={200: CompoundExperimentalDatumList}
)
def get_compound_exp_data(path: CompoundPath):
    """Get experimental measurements (EC50, IC50, etc.)."""
    if not is_valid_qid(path.cwid):
        abort(400)
    try:
        return [d.model_dump() for d in get_experimental_data(path.cwid)]
    except Exception:
        abort(502)


#  Data (BioStudies + Zenodo)


@data_bp.get("/", responses={200: DataResult})
def list_data(query: DataSearchQuery):
    """Search datasets across BioStudies and Zenodo repositories."""
    bs = BioStudiesExtractor(collection=BIOSTUDIES_COLLECTION)
    zen = ZenodoExtractor(community=ZENODO_COMMUNITY, record_type=ZENODO_RECORD_TYPE)
    if query.query:
        bs_res = bs.search_studies(
            query.query, page=query.page, page_size=query.size, load_metadata=True
        )
        zen_res = zen.search_records(
            query.query, page=query.page, size=query.size, load_metadata=True
        )
    else:
        bs_res = bs.list_studies(
            page=query.page, page_size=query.size, include_urls=True, load_metadata=True
        )
        zen_res = zen.list_records(
            page=query.page, size=query.size, include_urls=True, load_metadata=True
        )

    studies = bs_res.get("hits", [])
    datasets = zen_res.get("hits", [])
    studies, datasets = normalize_all(studies, datasets)

    return {
        "biostudies": {
            "total": bs_res.get("total", 0),
            "hits": [h.get("norm_metadata", h) for h in studies],
            "error": bs_res.get("error"),
        },
        "zenodo": {
            "total": zen_res.get("total", 0),
            "hits": [h.get("norm_metadata", h) for h in datasets],
            "error": zen_res.get("error"),
        },
    }


@data_bp.get("/<data_id>", responses={200: NormalisedDataset})
def get_data_detail(path: DataDetailPath):
    """Get normalised metadata for a single dataset by its accession ID."""
    bs = BioStudiesExtractor(collection=BIOSTUDIES_COLLECTION)
    zen = ZenodoExtractor(community=ZENODO_COMMUNITY, record_type=ZENODO_RECORD_TYPE)
    bs_res = bs.search_studies(path.data_id, page=1, page_size=1, load_metadata=True)
    zen_res = zen.search_records(path.data_id, page=1, size=1, load_metadata=True)
    studies = bs_res.get("hits", [])
    datasets = zen_res.get("hits", [])
    studies, datasets = normalize_all(studies, datasets)
    if studies:
        return studies[0].get("norm_metadata", studies[0])
    if datasets:
        return datasets[0].get("norm_metadata", datasets[0])



#  Validation

_SKIP_FIELDS = {
    "raw_json",
    "updated_at",
    "model_config",
    "timestamp",
    "https",
    "reg_q_1a",
    "reg_q_1b",
    "reg_q_2a",
    "reg_q_2b",
    "reg_q_3a",
    "reg_q_3b",
}

_ENTITY_REGISTRY = {
    "tools": ("tools", ToolModel, "id", "service"),
    "methods": ("methods", MethodModel, "id", "method"),
    "case_studies": ("case_studies", CSModel, "slug", "title"),
    "regulatory_questions": ("regulatory_questions", RQModel, "key", "label"),
    "stage_explanations": ("stage_explanations", SEModel, "name", "name"),
}


def _is_filled(val) -> bool:
    if val is None:
        return False
    if isinstance(val, str) and val.strip() == "":
        return False
    return True


def _preview(val, max_len: int = 80):
    if val is None:
        return None
    s = str(val)
    return s[:max_len] + ("..." if len(s) > max_len else "")


def _validate_entity(entity_name, table, pydantic_model, id_attr, label_attr):
    check_fields = [f for f in pydantic_model.model_fields if f not in _SKIP_FIELDS]
    conn = get_conn()
    rows = conn.execute(f"SELECT * FROM {table}").fetchall()
    conn.close()

    entries = []
    for row in rows:
        d = dict(row)
        details, filled, missing = [], 0, []
        for f in check_fields:
            val = d.get(f)
            ok = _is_filled(val)
            filled += ok
            if not ok:
                missing.append(f)
            details.append({"field": f, "present": ok, "value_preview": _preview(val)})

        total = len(check_fields)
        pct = round(filled / total * 100, 1) if total else 100.0
        entries.append(
            {
                "id": str(d.get(id_attr, "?")),
                "label": str(d.get(label_attr) or d.get(id_attr, "?")),
                "fields_total": total,
                "fields_filled": filled,
                "completeness_pct": pct,
                "missing": missing,
                "details": details,
            }
        )

    avg = (
        round(sum(e["completeness_pct"] for e in entries) / len(entries), 1)
        if entries
        else 0.0
    )
    return {
        "entity": entity_name,
        "total_entries": len(entries),
        "schema_fields": check_fields,
        "avg_completeness_pct": avg,
        "fully_complete": sum(1 for e in entries if e["completeness_pct"] == 100.0),
        "entries": entries,
    }


@validation_bp.get("/", responses={200: ValidationReportResponse})
def validate_all():
    """Full data completeness report across all entity types."""
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "entities": [
            _validate_entity(name, tbl, model, id_a, lbl_a)
            for name, (tbl, model, id_a, lbl_a) in _ENTITY_REGISTRY.items()
        ],
    }


@validation_bp.get("/<entity>", responses={200: EntitySummaryResponse})
def validate_entity(path: EntityPath):
    """Data completeness report for a single entity type."""
    if path.entity not in _ENTITY_REGISTRY:
        abort(404)
    tbl, model, id_a, lbl_a = _ENTITY_REGISTRY[path.entity]
    return _validate_entity(path.entity, tbl, model, id_a, lbl_a)


#  App factory


def init_api(app: OpenAPI) -> None:
    """Register all API blueprints on the OpenAPI app."""
    for bp in (
        tools_bp,
        methods_bp,
        reg_q_bp,
        stages_bp,
        casestudies_bp,
        compounds_bp,
        data_bp,
        validation_bp,
    ):
        app.register_api(bp)
