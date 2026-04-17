"""RESTful API with auto-generated OpenAPI documentation.

Uses flask-smorest (marshmallow + OpenAPI 3) so Swagger UI is
served automatically at /api/v1/docs.
"""

from __future__ import annotations

import json

from flask import Flask
from flask_smorest import Api, Blueprint, abort
from marshmallow import Schema, fields

from src.db import get_conn
from src.models.data.biostudies import BioStudiesExtractor
from src.models.data.zenodo import ZenodoExtractor
from src.models.data.mapping import normalize_all
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


# -- Marshmallow Schemas ---------------------------------------------------

class ToolSchema(Schema):
    id = fields.Str(metadata={"example": "cdkdepict"})
    service = fields.Str(metadata={
        "example": "CDK Depict",
        "description": "Human-readable tool name"})
    description = fields.Str(metadata={
        "example": "A webservice for generating chemical "
        "structure images from SMILES inputs."})
    stage = fields.Str(metadata={
        "example": "Other",
        "description": "Safety-assessment workflow stage"})
    main_url = fields.Str(metadata={
        "example": "https://www.simolecule.com/cdkdepict/depict.html"})
    inst_url = fields.Str(metadata={
        "example": "https://cdkdepict.cloud.vhp4safety.nl/"})
    html_name = fields.Str(metadata={"example": "cdkdepict.html"})
    png_file_name = fields.Str(metadata={"example": "cdkdepict.png"})


class MethodSchema(Schema):
    id = fields.Str(metadata={
        "example": "5_cfda_assay_to_determine_cytotoxicity"})
    method = fields.Str(metadata={
        "example": "5-CFDA assay to determine cytotoxicity",
        "description": "Human-readable method name"})
    description = fields.Str(metadata={
        "example": "Fluorescence-based determination "
        "of cell membrane damage"})
    stage = fields.Str(metadata={"example": "Adverse Outcome"})
    substage = fields.Str(metadata={
        "example": "Cell death, Adverse outcome"})
    catalog_webpage_url = fields.Str(metadata={
        "example": "https://www.thermofisher.com/order/"
        "catalog/product/C1354"})
    raw = fields.Dict(load_default=None, metadata={
        "description": "Full upstream YAML fields "
        "from the methods catalog"})


class RegulatoryQuestionSchema(Schema):
    key = fields.Str(metadata={"example": "reg_q_1a"})
    label = fields.Str(metadata={
        "example": "Kidney Case Study (a)"})
    explanation = fields.Str(metadata={
        "example": "What is the safe cisplatin dose "
        "in cancer patients?"})


class StageExplanationSchema(Schema):
    name = fields.Str(metadata={"example": "ADME"})
    explanation = fields.Str(metadata={
        "example": "Absorption, distribution, metabolism, "
        "and excretion of a substance in a living organism, "
        "following exposure."})


class CaseStudySchema(Schema):
    name = fields.Str(
        attribute="slug",
        metadata={"description": "Short identifier used in URLs",
                  "example": "kidney"})
    title = fields.Str(metadata={
        "example": "Kidney case study"})
    description = fields.Str(metadata={
        "example": "To study kidney disease "
        "and pharmacovigilance."})
    image_src = fields.Str(metadata={
        "example": "/static/images/image43_hexagon.svg"})
    config_repo = fields.Str(metadata={
        "example": "VHP4Safety/ui-casestudy-config"})
    default_branch = fields.Str(metadata={
        "example": "main"})


class CaseStudyDetailSchema(CaseStudySchema):
    content_json = fields.Raw(
        load_default=None,
        metadata={
            "description":
            "Full nested JSON driving the case-study UI "
            "(intro text, regulatory questions, "
            "process-flow steps)"})


class CompoundSummarySchema(Schema):
    wcid = fields.Str()
    label = fields.Str()
    inchi = fields.Str()
    inchikey = fields.Str()
    smiles = fields.Str(data_key="SMILES")
    formula = fields.Str()
    mass = fields.Str()


class CompoundIdentifierSchema(Schema):
    property_label = fields.Str(data_key="propertyLabel")
    value = fields.Str()
    formatter_url = fields.Str(data_key="formatterURL")


class CompoundToxicologySchema(Schema):
    property_label = fields.Str(data_key="propertyLabel")
    value = fields.Str()


class CompoundExpDataSchema(Schema):
    property_label = fields.Str(data_key="propEntityLabel")
    value = fields.Str()
    units_label = fields.Str(data_key="unitsLabel")
    source = fields.Str()
    doi = fields.Str()
    see_also = fields.Str(data_key="seeAlso")


class CompoundDetailSchema(Schema):
    summary = fields.Nested(CompoundSummarySchema)
    identifiers = fields.List(fields.Nested(CompoundIdentifierSchema))
    toxicology = fields.List(fields.Nested(CompoundToxicologySchema))
    experimental_data = fields.List(fields.Nested(CompoundExpDataSchema))


class DataSearchQuerySchema(Schema):
    query = fields.Str(
        load_default="",
        metadata={"example": "kidney"})
    page = fields.Int(load_default=1)
    size = fields.Int(load_default=18)


class DataSourceResultSchema(Schema):
    total = fields.Int()
    hits = fields.List(fields.Dict())
    error = fields.Str(allow_none=True)


class DataResultSchema(Schema):
    biostudies = fields.Nested(DataSourceResultSchema)
    zenodo = fields.Nested(DataSourceResultSchema)


class SearchQuerySchema(Schema):
    stage = fields.Str(
        load_default=None,
        metadata={"example": "Other"})
    search = fields.Str(
        load_default="",
        metadata={"example": ""})


# -- Blueprints ------------------------------------------------------------

tools_bp = Blueprint("tools", __name__, url_prefix="/api/tools",
                     description="Tool / service endpoints")
methods_bp = Blueprint("methods", __name__, url_prefix="/api/methods",
                       description="Method endpoints")
reg_q_bp = Blueprint("regulatory_questions", __name__,
                     url_prefix="/api/regulatory-questions",
                     description="Regulatory questions")
stages_bp = Blueprint("stages", __name__, url_prefix="/api/stages",
                      description="Safety-assessment workflow stages")
casestudies_bp = Blueprint("casestudies", __name__,
                           url_prefix="/api/casestudies",
                           description="Case study endpoints")
compounds_bp = Blueprint("compounds", __name__, url_prefix="/api/compounds",
                         description="Compound data (SPARQL-backed)")
data_bp = Blueprint("data", __name__, url_prefix="/api/data",
                    description="Dataset search (BioStudies + Zenodo)")


# -- Tools -----------------------------------------------------------------

@tools_bp.route("/")
@tools_bp.arguments(SearchQuerySchema, location="query")
@tools_bp.response(200, ToolSchema(many=True))
def list_tools(args):
    """List all tools, with optional stage/search filters.

    Returns every tool (service) registered on the platform.
    Filter by workflow stage or free-text search on the tool name.
    """
    conn = get_conn()
    sql = "SELECT * FROM tools WHERE 1=1"
    params = []
    if args.get("stage"):
        sql += " AND stage = ?"
        params.append(args["stage"])
    if args.get("search"):
        sql += " AND service LIKE ?"
        params.append(f"%{args['search']}%")
    sql += " ORDER BY service"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@tools_bp.route("/<tool_id>")
@tools_bp.doc(parameters=[{
    "name": "tool_id", "in": "path",
    "example": "cdkdepict"}])
@tools_bp.response(200, ToolSchema)
def get_tool(tool_id):
    """Get a single tool by its ID."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM tools WHERE id = ?", (tool_id,)).fetchone()
    conn.close()
    if not row:
        abort(404, message="Tool not found")
    return dict(row)


# -- Methods ---------------------------------------------------------------

@methods_bp.route("/")
@methods_bp.arguments(SearchQuerySchema, location="query")
@methods_bp.response(200, MethodSchema(many=True))
def list_methods(args):
    """List all methods, with optional stage/search filters.

    Methods describe experimental or computational procedures
    used in safety-assessment workflows.
    """
    conn = get_conn()
    sql = "SELECT * FROM methods WHERE 1=1"
    params = []
    if args.get("stage"):
        sql += " AND stage LIKE ?"
        params.append(f"%{args['stage']}%")
    if args.get("search"):
        sql += " AND method LIKE ?"
        params.append(f"%{args['search']}%")
    sql += " ORDER BY method"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@methods_bp.route("/<method_id>")
@methods_bp.doc(parameters=[{
    "name": "method_id", "in": "path",
    "example": "5_cfda_assay_to_determine_cytotoxicity"}])
@methods_bp.response(200, MethodSchema)
def get_method(method_id):
    """Get a single method by ID, including full upstream fields.

    The ``raw`` field contains every field from the upstream
    methods catalog YAML (AOP references, key events, etc.).
    """
    conn = get_conn()
    row = conn.execute("SELECT * FROM methods WHERE id = ?", (method_id,)).fetchone()
    conn.close()
    if not row:
        abort(404, message="Method not found")
    d = dict(row)
    if d.get("raw_json"):
        d["raw"] = json.loads(d["raw_json"])
    return d


# -- Regulatory Questions --------------------------------------------------

@reg_q_bp.route("/")
@reg_q_bp.response(200, RegulatoryQuestionSchema(many=True))
def list_regulatory_questions():
    """List the six regulatory questions that link tools to case studies.

    Each question is tied to a case study pair (a/b).
    For example, ``reg_q_1a`` = *"Kidney Case Study (a)"*.
    """
    conn = get_conn()
    rows = conn.execute("SELECT * FROM regulatory_questions").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# -- Stages ----------------------------------------------------------------

@stages_bp.route("/")
@stages_bp.response(200, StageExplanationSchema(many=True))
def list_stages():
    """List all safety-assessment workflow stages.

    Stages are the high-level phases of the VHP4Safety
    process flow: ADME, Hazard Assessment, etc.
    """
    conn = get_conn()
    rows = conn.execute("SELECT * FROM stage_explanations").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# -- Case Studies ----------------------------------------------------------

@casestudies_bp.route("/")
@casestudies_bp.response(200, CaseStudySchema(many=True))
def list_case_studies():
    """List the three VHP4Safety case studies (summary only).

    Returns name, title, description, and image for each.
    Use the detail endpoint for the full content JSON.

    Available names: ``kidney``, ``parkinson``, ``thyroid``.
    """
    conn = get_conn()
    rows = conn.execute("SELECT * FROM case_studies").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@casestudies_bp.route("/<name>")
@casestudies_bp.doc(parameters=[{
    "name": "name", "in": "path",
    "example": "kidney"}])
@casestudies_bp.response(200, CaseStudyDetailSchema)
def get_case_study(name):
    """Get a case study by name, including its full content JSON.

    The content JSON contains the intro text, regulatory questions,
    and process-flow workflow steps that drive the case-study UI.
    """
    conn = get_conn()
    row = conn.execute("SELECT * FROM case_studies WHERE slug = ?", (name,)).fetchone()
    conn.close()
    if not row:
        abort(404, message="Case study not found")
    d = dict(row)
    if d.get("content_json"):
        d["content_json"] = json.loads(d["content_json"])
    return d


# -- Compounds (SPARQL-backed) ---------------------------------------------

@compounds_bp.route("/<cwid>")
@compounds_bp.doc(parameters=[{
    "name": "cwid", "in": "path",
    "description": "Wikidata compound ID",
    "example": "Q2270"}])
@compounds_bp.response(200, CompoundDetailSchema)
def get_compound(cwid):
    """Get full compound data from Wikidata via SPARQL.

    Returns summary properties, external identifiers,
    toxicology data, and experimental measurements.
    """
    if not is_valid_qid(cwid):
        abort(400, message="Invalid compound identifier")
    try:
        return get_full_compound(cwid).model_dump()
    except Exception as e:
        abort(502, message=str(e))


@compounds_bp.route("/<cwid>/properties")
@compounds_bp.doc(parameters=[{
    "name": "cwid", "in": "path", "example": "Q2270"}])
@compounds_bp.response(200, CompoundSummarySchema)
def get_compound_properties(cwid):
    """Get core compound properties (formula, mass, InChI, SMILES)."""
    if not is_valid_qid(cwid):
        abort(400, message="Invalid compound identifier")
    try:
        summary = get_properties(cwid)
        if not summary:
            abort(404, message="No data found")
        return summary.model_dump()
    except Exception as e:
        abort(502, message=str(e))


@compounds_bp.route("/<cwid>/identifiers")
@compounds_bp.doc(parameters=[{
    "name": "cwid", "in": "path", "example": "Q2270"}])
@compounds_bp.response(200, CompoundIdentifierSchema(many=True))
def get_compound_identifiers(cwid):
    """Get external database identifiers (CAS, PubChem, ChEBI, etc.)."""
    if not is_valid_qid(cwid):
        abort(400, message="Invalid compound identifier")
    try:
        return [i.model_dump() for i in get_identifiers(cwid)]
    except Exception as e:
        abort(502, message=str(e))


@compounds_bp.route("/<cwid>/toxicology")
@compounds_bp.doc(parameters=[{
    "name": "cwid", "in": "path", "example": "Q2270"}])
@compounds_bp.response(200, CompoundToxicologySchema(many=True))
def get_compound_toxicology(cwid):
    """Get toxicology data (LD50, LC50, etc.)."""
    if not is_valid_qid(cwid):
        abort(400, message="Invalid compound identifier")
    try:
        return [t.model_dump() for t in get_toxicology(cwid)]
    except Exception as e:
        abort(502, message=str(e))


@compounds_bp.route("/<cwid>/experimental-data")
@compounds_bp.doc(parameters=[{
    "name": "cwid", "in": "path", "example": "Q2270"}])
@compounds_bp.response(200, CompoundExpDataSchema(many=True))
def get_compound_exp_data(cwid):
    """Get experimental measurements (EC50, IC50, etc.)."""
    if not is_valid_qid(cwid):
        abort(400, message="Invalid compound identifier")
    try:
        return [d.model_dump() for d in get_experimental_data(cwid)]
    except Exception as e:
        abort(502, message=str(e))


# -- Data (BioStudies + Zenodo passthrough) --------------------------------

@data_bp.route("/")
@data_bp.arguments(DataSearchQuerySchema, location="query")
@data_bp.response(200, DataResultSchema)
def list_data(args):
    """Search datasets across BioStudies and Zenodo repositories.

    Returns paginated results from both sources with normalised metadata.
    """
    query = args.get("query", "")
    page = args.get("page", 1)
    size = args.get("size", 18)

    bs = BioStudiesExtractor(collection=BIOSTUDIES_COLLECTION)
    zen = ZenodoExtractor(community=ZENODO_COMMUNITY, record_type=ZENODO_RECORD_TYPE)

    if query:
        bs_res = bs.search_studies(query, page=page, page_size=size)
        zen_res = zen.search_records(query, page=page, size=size)
    else:
        bs_res = bs.list_studies(page=page, page_size=size, include_urls=True)
        zen_res = zen.list_records(page=page, size=size, include_urls=True)

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


@data_bp.route("/<data_id>")
@data_bp.doc(parameters=[{
    "name": "data_id", "in": "path", "example": "S-BSST1503"}])
@data_bp.response(200)
def get_data_detail(data_id):
    """Get normalised metadata for a single dataset by its accession ID.

    Searches both BioStudies and Zenodo for the given identifier.
    """
    bs = BioStudiesExtractor(collection=BIOSTUDIES_COLLECTION)
    zen = ZenodoExtractor(community=ZENODO_COMMUNITY, record_type=ZENODO_RECORD_TYPE)
    bs_res = bs.search_studies(data_id, page=1, page_size=1)
    zen_res = zen.search_records(data_id, page=1, size=1)
    studies = bs_res.get("hits", [])
    datasets = zen_res.get("hits", [])
    studies, datasets = normalize_all(studies, datasets)
    if studies:
        return studies[0].get("norm_metadata", studies[0])
    if datasets:
        return datasets[0].get("norm_metadata", datasets[0])
    abort(404, message="Dataset not found")


# -- Validation blueprint --------------------------------------------------

validation_bp = Blueprint("validation", __name__, url_prefix="/api/validation",
                          description="Data completeness validation")

from src.models.cloud.method import ServiceIndexEntry as ToolModel
from src.models.cloud.tool import Method as MethodModel
from src.models.platform import (
    RegulatoryQuestion as RQModel,
    StageExplanation as SEModel,
)
from src.models.casestudy import CaseStudyCard as CSModel

_ENTITY_REGISTRY = {
    "tools":                  ("tools",                  ToolModel,   "id",   "service"),
    "methods":                ("methods",                MethodModel, "id",   "method"),
    "case_studies":           ("case_studies",           CSModel,     "slug", "title"),
    "regulatory_questions":   ("regulatory_questions",   RQModel,     "key",  "label"),
    "stage_explanations":     ("stage_explanations",     SEModel,     "name", "name"),
}

_SKIP_FIELDS = {
    "raw_json", "updated_at", "model_config",
    "timestamp", "https",
    "reg_q_1a", "reg_q_1b", "reg_q_2a",
    "reg_q_2b", "reg_q_3a", "reg_q_3b",
}


class FieldCompleteness(Schema):
    field = fields.Str()
    present = fields.Bool()
    value_preview = fields.Str(allow_none=True)


class EntryValidation(Schema):
    id = fields.Str()
    label = fields.Str()
    fields_total = fields.Int()
    fields_filled = fields.Int()
    completeness_pct = fields.Float()
    missing = fields.List(fields.Str())
    details = fields.List(fields.Nested(FieldCompleteness))


class EntitySummary(Schema):
    entity = fields.Str()
    total_entries = fields.Int()
    schema_fields = fields.List(fields.Str())
    avg_completeness_pct = fields.Float()
    fully_complete = fields.Int()
    entries = fields.List(fields.Nested(EntryValidation))


class ValidationReport(Schema):
    generated_at = fields.Str()
    entities = fields.List(fields.Nested(EntitySummary))


def _is_filled(val):
    if val is None:
        return False
    if isinstance(val, str) and val.strip() == "":
        return False
    return True


def _preview(val, max_len=80):
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
        details = []
        filled = 0
        missing = []
        for f in check_fields:
            val = d.get(f)
            ok = _is_filled(val)
            if ok:
                filled += 1
            else:
                missing.append(f)
            details.append({"field": f, "present": ok, "value_preview": _preview(val)})

        total = len(check_fields)
        pct = round(filled / total * 100, 1) if total else 100.0
        entries.append({
            "id": str(d.get(id_attr, "?")),
            "label": str(d.get(label_attr) or d.get(id_attr, "?")),
            "fields_total": total,
            "fields_filled": filled,
            "completeness_pct": pct,
            "missing": missing,
            "details": details,
        })

    avg = round(sum(e["completeness_pct"] for e in entries) / len(entries), 1) if entries else 0.0
    fully = sum(1 for e in entries if e["completeness_pct"] == 100.0)
    return {
        "entity": entity_name,
        "total_entries": len(entries),
        "schema_fields": check_fields,
        "avg_completeness_pct": avg,
        "fully_complete": fully,
        "entries": entries,
    }


@validation_bp.route("/")
@validation_bp.response(200, ValidationReport)
def validate_all():
    """Full data completeness report across all entity types.

    Checks every row in tools, methods, case_studies,
    regulatory_questions, and stage_explanations for missing fields.

    """
    from datetime import datetime, timezone
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "entities": [
            _validate_entity(name, tbl, model, id_a, lbl_a)
            for name, (tbl, model, id_a, lbl_a) in _ENTITY_REGISTRY.items()
        ],
    }


@validation_bp.route("/<entity>")
@validation_bp.doc(parameters=[{
    "name": "entity", "in": "path", "example": "tools"}])
@validation_bp.response(200, EntitySummary)
def validate_entity(entity):
    """Data completeness report for a single entity type.

    Valid entity names: ``tools``, ``methods``, ``case_studies``,
    ``regulatory_questions``, ``stage_explanations``.
    """
    if entity not in _ENTITY_REGISTRY:
        abort(404, message=f"Unknown entity '{entity}'. Valid: {', '.join(_ENTITY_REGISTRY)}")
    tbl, model, id_a, lbl_a = _ENTITY_REGISTRY[entity]
    return _validate_entity(entity, tbl, model, id_a, lbl_a)


# -- Registration helper ---------------------------------------------------

def init_api(app: Flask) -> Api:
    """Configure flask-smorest and register all API blueprints."""
    app.config.update({
        "API_TITLE": "VHP4Safety Platform API",
        "API_VERSION": "v1",
        "OPENAPI_VERSION": "3.0.3",
        "OPENAPI_URL_PREFIX": "/api/v1",
        "OPENAPI_SWAGGER_UI_PATH": "/docs",
        "OPENAPI_SWAGGER_UI_URL": "https://cdn.jsdelivr.net/npm/swagger-ui-dist/",
        "OPENAPI_REDOC_PATH": "/redoc",
        "OPENAPI_REDOC_URL": "https://cdn.jsdelivr.net/npm/redoc@latest/bundles/redoc.standalone.js",
    })
    smorest_api = Api(app)
    for bp in (tools_bp, methods_bp, reg_q_bp, stages_bp,
               casestudies_bp, compounds_bp, data_bp, validation_bp):
        smorest_api.register_blueprint(bp)
    return smorest_api
