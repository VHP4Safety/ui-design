################################################################################
### Loading the required modules
import json
import os
import re

import requests
import urllib.parse
from flask import abort, jsonify, render_template, request, Response
from flask_caching import Cache
from flask_openapi3 import OpenAPI
from jinja2 import TemplateNotFound
from werkzeug.routing import BaseConverter
from src.scheduler import init_scheduler

# from wikidataintegrator import wdi_core
from wikibaseintegrator import wbi_helpers

# Data extractors (API wrappers, no DB needed)
from src.models.data.biostudies import BioStudiesExtractor
from src.models.data.zenodo import ZenodoExtractor
from src.models.data.mapping import normalize_all

# Database layer
from src.db import get_conn, init_db
from src.api import init_api

################################################################################
CACHE_TIMEOUT = 60 * 60 * 24 * 5  # 5 days -- [Ozan] I created a separate
# timeout object for the tools page because
# a 5-day caching is too long for it.
CACHE_TIMEOUT_SERVICE = 60  # Separate timeout for the tools page -- 60
# seconds.
### Configuration for BioStudies Integration
# Change these variables to switch between collections
BIOSTUDIES_COLLECTION = "VHP4Safety"  # Replace with "EU-ToxRisk" to test
BIOSTUDIES_COLLECTION_NAME = "VHP4Safety"  # Display name for the page
ZENODO_COMMUNITY = "vhp4safety"  # zenodo community
ZENODO_RECORD_TYPE = "dataset"  # only show datasets

CASESTUDIES = ["thyroid", "kidney", "parkinson"]  # List of valid case studies

###Shared explanation dictionaries for filters (used in both tools and data page)
STAGE_EXPLANATIONS = {
    "Chemical Characteristics and Hazard Identification": "A Safety Assessment Workflow Step that categorizes services that use molecular structures, chemical descriptors, and databases to predict or analyze the properties, behavior, and potential risks of chemical substances.",
    "Exposure": "A Safety Assessment Workflow Step which categorizes services that evaluate and analyze the route, duration, magnitude and frequency of exposure of an organism or (sub)population to one or multiple chemicals.",
    "Toxicokinetics": "A Safety Assessment Workflow Step which categorizes services that analyze the kinetics (absorption, distribution, metabolism and excretion) of chemicals and how these processes influence the internal dose.",
    "Toxicodynamics": "A Safety Assessment Workflow Step which categorizes services that use or extend the (quantitative) AOP framework to analyze and assess the interaction of chemicals with biological targets.",
    "Adverse Outcome": "A Safety Assessment Workflow Step which specifically refers to clinical and epidemiological effects. It categorizes services that provide information on the toxicological endpoints and adverse outcomes at a clinical or epidemiological level of chemical exposures.",
    "Other": "Other or unknown category.",
    # Legacy labels (kept for the data/methods pages until their data sources migrate)
    "ADME": "Absorption, distribution, metabolism, and excretion of a substance (toxic or not) in a living organism, following exposure to this substance.",
    "Hazard Assessment": "The process of assessing the intrinsic hazard a substance poses to human health and/or the environment",
    "Chemical Information": "Information about chemical properties and identity.",
    "General": "Not specific to a flow step.",
    "(External) exposure": "External exposure assessment.",
    "Generic": "Generic category.",
}
METHODS_URL = "https://raw.githubusercontent.com/VHP4Safety/cloud/refs/heads/main/cap/methods_index.json"
# TOOLS and SERVICES are synonymous
SERVICES_URL = "https://raw.githubusercontent.com/VHP4Safety/cloud/refs/heads/main/cap/service_index.json"

REG_QUESTIONS = {
    "reg_q_1a": {
        "label": "Kidney Case Study (a)",
        "explanation": "What is the safe cisplatin dose in cancer patients?",
    },
    "reg_q_1b": {
        "label": "Kidney Case Study (b)",
        "explanation": "What is the intrinsic hazard of tacrolimus for nephrotoxicity?",
    },
    "reg_q_2a": {
        "label": "Parkinson Case Study (a)",
        "explanation": "Can compound Dinoseb cause Parkinson's Disease?",
    },
    "reg_q_2b": {
        "label": "Parkinson Case Study (b)",
        "explanation": "What level of exposure to compound Dinoseb leads to risk for developing Parkinson's disease?",
    },
    "reg_q_3a": {
        "label": "Thyroid Case Study (a)",
        "explanation": "What information about silychristin do we need to give an advice to women in their early pregnancy to decide whether the substance can be used?",
    },
    "reg_q_3b": {
        "label": "Thyroid Case Study (b)",
        "explanation": "Does silychristin influence the thyroid-mediated brain development in the fetus resulting in cognitive impairment in children?",
    },
}

# Derived: keep the old structure available for templates expecting {label: explanation}
REG_QUESTION_EXPLANATIONS = {
    v["label"]: v["explanation"] for v in REG_QUESTIONS.values()
}


################################################################################
class RegexConverter(BaseConverter):
    """Converter for regular expression routes.

    References
    ----------
    Scholia views.py
    https://stackoverflow.com/questions/5870188

    """

    def __init__(self, url_map, *items):
        """Set up regular expression matcher."""
        super(RegexConverter, self).__init__(url_map)
        self.regex = items[0]


cache_config = {
    "CACHE_TYPE": "SimpleCache",  # Flask-Caching related configs
    "CACHE_DEFAULT_TIMEOUT": CACHE_TIMEOUT,  # 60 min chaching
    "CACHE_SERVICE_TIMEOUT": CACHE_TIMEOUT_SERVICE,
}
app = OpenAPI(
    __name__,
    info={"title": "VHP4Safety Platform API", "version": "1.0.0"},
    doc_prefix="/api/v1",
)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-insecure-key")
app.config.from_mapping(cache_config)
cache = Cache(app)

# Database init and API registration
init_db()
init_api(app)


@app.errorhandler(404)
def page_not_found(e):
    if request.path.startswith("/api/"):
        return {"error": "Not found", "path": request.path}, 404
    return render_template("404.html"), 404


@cache.memoize(timeout=CACHE_TIMEOUT)
def get_json_dict(url: str, timeout: int = 5) -> dict:
    """Fetch xxxx_index.json from the cloud repo and return as a dictionary.
    Return an empty dict on any error to avoid breaking pages that depend on it.
    """
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code != 200:
            return {}
        data = resp.json()
        if isinstance(data, dict):
            return data
        else:
            return {}
    except Exception:
        return {}


# A separate get_json_dict function for the tools page with its own timeout.
@cache.memoize(timeout=CACHE_TIMEOUT_SERVICE)
def get_json_dict_service(url: str, timeout: int = 5) -> dict:
    """Fetch xxxx_index.json from the cloud repo and return as a dictionary.
    Return an empty dict on any error to avoid breaking pages that depend on it.
    """
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code != 200:
            return {}
        data = resp.json()
        if isinstance(data, dict):
            return data
        else:
            return {}
    except Exception:
        return {}


@cache.memoize(timeout=CACHE_TIMEOUT)
def get_repository_data(
    search_query: str,
    page: int = 1,
    page_size: int = 18,
    filters: list | None = None,
    load_metadata: bool = True,
) -> tuple[dict, dict]:
    """
    Extract data from respositories
    """
    # Initialize extractor for BIOSTUDIES
    bs_extractor = BioStudiesExtractor(collection=BIOSTUDIES_COLLECTION)

    # Fetch data based on search query or list all
    if search_query:
        bs_results = bs_extractor.search_studies(
            search_query,
            page=page,
            page_size=page_size,
            filters=filters,
            load_metadata=load_metadata,
        )
    else:
        bs_results = bs_extractor.list_studies(
            page=page,
            page_size=page_size,
            include_urls=True,
            filters=filters,
            load_metadata=load_metadata,
        )

    # Initialize extractor for Zenodo
    zen_extractor = ZenodoExtractor(
        community=ZENODO_COMMUNITY, record_type=ZENODO_RECORD_TYPE
    )

    if not filters:
        # We currently do no filter Zenodo datasets.
        if search_query:
            zen_result = zen_extractor.search_records(
                search_query, page=page, size=page_size, load_metadata=load_metadata
            )
        else:
            # load metadata needed for is_rocrate filtering in template
            zen_result = zen_extractor.list_records(
                page=page,
                size=page_size,
                include_urls=True,
                load_metadata=load_metadata,
            )
    else:
        zen_result = {"hits": [], "total": 0, "error": None}

    return bs_results, zen_result


# Provide methods list to all templates for the Methods dropdown in the navbar
@app.context_processor
def inject_methods_menu():
    """Expose methods list to all templates for navbar dropdown."""
    try:
        conn = get_conn()
        rows = conn.execute("SELECT id, method FROM methods ORDER BY method").fetchall()
        conn.close()
        return {"methods_menu": [{"id": r["id"], "title": r["method"]} for r in rows]}
    except Exception:
        return {"methods_menu": []}


@app.context_processor
def inject_tools_menu():
    """Expose tools list to all templates for navbar dropdown."""
    try:
        conn = get_conn()
        rows = conn.execute("SELECT id, service FROM tools ORDER BY service").fetchall()
        conn.close()
        return {"tools_menu": [{"id": r["id"], "title": r["service"]} for r in rows]}
    except Exception:
        return {"tools_menu": []}


@app.context_processor
def inject_data_menu():
    """Fetch methods_index.json and expose a simple list of {id, title} to templates.
    Return an empty list on any error to avoid breaking pages.
    """
    bs_results, zen_results = get_repository_data(search_query="")
    hits: list = bs_results.get("hits", [])
    hits.extend(zen_results.get("hits", []))
    if hits:
        items = []
        for hit in hits:
            title = hit.get("title")
            id = hit.get("accession", "") or hit.get("doi_url", "") or hit.get("id", "")
            url = hit.get("url", "") or hit.get("doi_url")
            items.append({"id": id, "title": title, "url": url})
        # sort by title
        items = sorted(items, key=lambda x: x["title"].lower())
        return {"data_menu": items}
    else:
        return {"data_menu": []}


################################################################################
### The landing page
@app.route("/")
def home():
    conn = get_conn()
    num_tools = conn.execute("SELECT COUNT(*) FROM tools").fetchone()[0]
    num_case_studies = conn.execute("SELECT COUNT(*) FROM case_studies").fetchone()[0]
    conn.close()
    bs_res, zen_res = get_repository_data(search_query="")
    num_datasets = bs_res.get("total", 0) + zen_res.get("total", 0)
    return render_template(
        "home.html",
        num_tools=num_tools,
        num_case_studies=num_case_studies,
        num_datasets=num_datasets,
    )


################################################################################
### The sitemap.xml for search engines
@app.route("/sitemap.xml")
def sitemap():
    # Prefer generated static sitemap if present (created by src.sitemap)
    import os

    path = os.path.join(os.path.dirname(__file__), "static", "sitemap.xml")
    if os.path.exists(path):
        with open(path, "rb") as fh:
            return Response(fh.read(), mimetype="application/xml")

    # Fallback minimal sitemap
    sitemapContent = """<?xml version="1.0" encoding="utf-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://platform.vhp4safety.nl/\</loc\>
    </url>
    <url>
        <loc>https://platform.vhp4safety.nl/casestudies\</loc\>
    </url>
    <url>
        <loc>https://platform.vhp4safety.nl/tools\</loc\>
    </url>
    <url>
        <loc>https://platform.vhp4safety.nl/methods\</loc\>
    </url>
    <url>
        <loc>https://platform.vhp4safety.nl/data\</loc\>
    </url>
</urlset>
"""
    return Response(sitemapContent, mimetype="text/xml")


################################################################################
### Pages under 'Data'
@app.route("/data")
def data():
    # Get query parameters for pagination and search
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 18, type=int)
    search_query = request.args.get("query", "", type=str)

    # Get filter parameters
    filter_case_study = request.args.get("filter_case_study", "", type=str)
    filter_regulatory_question = request.args.get(
        "filter_regulatory_question", "", type=str
    )
    filter_flow_step = request.args.get("filter_flow_step", "", type=str)

    # Build filter list (only include non-empty filters)
    filters = []
    if filter_case_study:
        filters.append(("case_study", filter_case_study))
    if filter_regulatory_question:
        filters.append(("regulatory_question", filter_regulatory_question))
    if filter_flow_step:
        filters.append(("flow_step", filter_flow_step))

    bs_results, zen_results = get_repository_data(
        search_query, page, page_size, filters=filters
    )

    # Extract studies and metadata
    studies = bs_results.get("hits", [])
    bs_total = bs_results.get("total", 0)
    bs_error: str | None = bs_results.get("error", None)

    # Extract datasets and metadata from Zenodo
    datasets = zen_results.get("hits", [])
    zen_total = zen_results.get("total", 0)
    zen_error: str | None = zen_results.get("error", None)

    # enrich with normalized metadata mapping:

    # studies, datasets = normalize_all([studies],[datasets])

    # combine totals for pagination
    total = bs_total + zen_total

    # Get filtering metadata (if filters were applied)
    filters_applied = bs_results.get("filters_applied", False)
    hits_returned = bs_results.get("hits_returned", len(studies))
    pages_fetched = bs_results.get("pages_fetched", 1)
    page_size_met = bs_results.get("page_size_met", True)

    # Calculate pagination info
    has_next = (page * page_size) < total
    has_prev = page > 1

    # Pass data to template
    return render_template(
        "data/data.html",
        studies=studies,
        datasets=datasets,
        total=total,
        page=page,
        page_size=page_size,
        search_query=search_query,
        collection_name=BIOSTUDIES_COLLECTION_NAME,
        collection=BIOSTUDIES_COLLECTION,
        errors={"zenodo": zen_error, "biostudies": bs_error},
        has_next=has_next,
        has_prev=has_prev,
        filter_case_study=filter_case_study,
        filter_regulatory_question=filter_regulatory_question,
        filter_flow_step=filter_flow_step,
        filters_applied=filters_applied,
        hits_returned=hits_returned,
        pages_fetched=pages_fetched,
        page_size_met=page_size_met,
        stage_explanations=STAGE_EXPLANATIONS,
        reg_question_explanations=REG_QUESTION_EXPLANATIONS,
    )


################################################################################
### DataSet detail view


@app.template_filter("split_text_int")
def split_text_int(value: None | str) -> tuple[str, None | int]:
    """
    Splits trailing integer from a string.
    'S-VHPS21' -> ('S-VHPS', 21)
    'ABC'      -> ('ABC', None)
    'X-12A'    -> ('X-12A', None)   # only splits if digits are at the very end
    """
    # used to construct ftp file link *POTENTIALLY BRITTLE*
    if value is None:
        return ("", None)

    s = str(value)
    m = re.match(r"^(.*?)(\d+)$", s)
    if not m:
        return (s, None)

    return (m.group(1), int(m.group(2)))


@app.route("/data/<dataid>")
def data_detail(dataid):
    bs_results, zen_results = get_repository_data(dataid)

    studies = bs_results.get("hits", [])
    bs_total = bs_results.get("total", 0)
    bs_error: str | None = bs_results.get("error", None)

    # Extract datasets and metadata from Zenodo
    datasets = zen_results.get("hits", [])
    zen_total = zen_results.get("total", 0)
    zen_error: str | None = zen_results.get("error", None)

    studies, datasets = normalize_all(studies, datasets)

    if bs_error and not zen_error:
        if zen_total != 1:
            return abort(404)
    elif zen_error and not bs_error:
        if bs_total != 1:
            return abort(404)
    if studies:
        return render_template("data/data_details.html", data=studies[0])
    elif datasets:
        return render_template("data/data_details.html", data=datasets[0])
    return abort(404)


################################################################################
### Pages under 'Models'
@app.route("/models_page")
def models():
    # Get query parameters for pagination and search
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 18, type=int)
    search_query = request.args.get("query", "", type=str)

    # Get filter parameters
    filter_case_study = request.args.get("filter_case_study", "", type=str)
    filter_regulatory_question = request.args.get(
        "filter_regulatory_question", "", type=str
    )
    filter_flow_step = request.args.get("filter_flow_step", "", type=str)

    # Build filter list (only include non-empty filters)
    filters = []
    if filter_case_study:
        filters.append(("case_study", filter_case_study))
    if filter_regulatory_question:
        filters.append(("regulatory_question", filter_regulatory_question))
    if filter_flow_step:
        filters.append(("flow_step", filter_flow_step))

    # Initialize extractor
    extractor = BioStudiesExtractor(collection=BIOSTUDIES_COLLECTION)

    # Fetch data based on search query or list all
    if search_query:
        results = extractor.search_studies(
            search_query, page=page, page_size=page_size, filters=filters
        )
    else:
        results = extractor.list_studies(
            page=page, page_size=page_size, include_urls=True, filters=filters
        )

    # Extract studies and metadata
    studies = results.get("hits", [])
    total = results.get("total", 0)
    error = results.get("error", None)

    # Get filtering metadata (if filters were applied)
    filters_applied = results.get("filters_applied", False)
    hits_returned = results.get("hits_returned", len(studies))
    pages_fetched = results.get("pages_fetched", 1)
    page_size_met = results.get("page_size_met", True)

    # Calculate pagination info
    has_next = (page * page_size) < total
    has_prev = page > 1

    # Pass model data to template
    return render_template(
        "models_page.html",
        studies=studies,
        total=total,
        page=page,
        page_size=page_size,
        search_query=search_query,
        collection_name=BIOSTUDIES_COLLECTION_NAME,
        collection=BIOSTUDIES_COLLECTION,
        error=error,
        has_next=has_next,
        has_prev=has_prev,
        filter_case_study=filter_case_study,
        filter_regulatory_question=filter_regulatory_question,
        filter_flow_step=filter_flow_step,
        filters_applied=filters_applied,
        hits_returned=hits_returned,
        pages_fetched=pages_fetched,
        page_size_met=page_size_met,
        stage_explanations=STAGE_EXPLANATIONS,
        reg_question_explanations=REG_QUESTION_EXPLANATIONS,
    )


################################################################################
### Pages under 'Tools'


@app.route("/tools")
def tools():
    try:
        conn = get_conn()

        # Getting selected stages from the URL.
        selected_stages = request.args.getlist("stage")
        search_query = request.args.get("search", "").strip().lower()

        sql = "SELECT * FROM tools WHERE 1=1"
        params = []
        if selected_stages:
            placeholders = ",".join("?" * len(selected_stages))
            sql += f" AND stage IN ({placeholders})"
            params.extend(selected_stages)
        if search_query:
            sql += " AND LOWER(service) LIKE ?"
            params.append(f"%{search_query}%")
        sql += " ORDER BY service"
        rows = conn.execute(sql, params).fetchall()

        # Build reg_questions lookup from DB
        rq_rows = conn.execute("SELECT * FROM regulatory_questions").fetchall()
        reg_questions = {r["label"]: r["key"] for r in rq_rows}

        # Apply regulatory question filters
        selected_questions = request.args.getlist("reg_q")
        tools_list = []
        for row in [dict(r) for r in rows]:
            raw = json.loads(row["raw_json"]) if row.get("raw_json") else {}
            # Check reg question filters
            skip = False
            for question in selected_questions:
                field = reg_questions.get(question)
                if field and str(raw.get(field, "")).lower() != "true":
                    skip = True
                    break
            if skip:
                continue

            html_name = row["html_name"]
            png_name = row["png_file_name"]
            placeholder = (
                "https://github.com/VHP4Safety/ui-design"
                "/blob/main/static/images/logo.png"
            )

            tools_list.append(
                {
                    "id": row["id"],
                    "service": row["service"],
                    "description": row["description"],
                    "stage": row["stage"],
                    "html_name": html_name,
                    "url": f"https://cloud.vhp4safety.nl/service/{html_name}",
                    "inst_url": row["inst_url"] or "no_url",
                    "png": (
                        None
                        if png_name == placeholder
                        else f"https://raw.githubusercontent.com/VHP4Safety/cloud/main/docs/service/{png_name}"
                        if png_name and not png_name.startswith("http")
                        else png_name
                    ),
                    **raw,
                }
            )

        # Collect stages for filter sidebar
        all_stages = sorted(set(t["stage"] for t in tools_list if t.get("stage")))
        if "Other" in all_stages:
            all_stages.remove("Other")
            all_stages.append("Other")

        # Stage / reg question explanations from DB
        se_rows = conn.execute("SELECT * FROM stage_explanations").fetchall()
        stage_explanations = {s["name"]: s["explanation"] for s in se_rows}
        reg_question_explanations = {r["label"]: r["explanation"] for r in rq_rows}
        conn.close()

        return render_template(
            "tools/tools.html",
            tools=tools_list,
            stages=all_stages,
            selected_stages=selected_stages,
            reg_questions=reg_questions,
            selected_questions=selected_questions,
            stage_explanations=stage_explanations,
            reg_question_explanations=reg_question_explanations,
        )

    except Exception as e:
        return f"Error processing service data: {e}", 500


### New route to list methods (similar to the tools page)
@app.route("/methods")
@app.route("/methods/")
def methods():
    """Render methods list page from DB."""
    try:
        conn = get_conn()

        selected_stages = request.args.getlist("stage")
        search_query = request.args.get("search", "").strip().lower()

        sql = "SELECT * FROM methods WHERE 1=1"
        params = []
        if search_query:
            sql += " AND LOWER(method) LIKE ?"
            params.append(f"%{search_query}%")
        sql += " ORDER BY method"
        rows = [dict(r) for r in conn.execute(sql, params).fetchall()]

        rq_rows = conn.execute("SELECT * FROM regulatory_questions").fetchall()
        reg_questions = {r["label"]: r["key"] for r in rq_rows}
        selected_questions = request.args.getlist("reg_q")

        stages_set = set()
        methods_filtered = []
        for row in rows:
            raw = json.loads(row["raw_json"]) if row.get("raw_json") else {}
            stage_field = (row.get("stage") or "").strip()
            parts = [s.strip() for s in stage_field.split(",") if s.strip()]
            stages_set.update(parts)

            if selected_stages and not any(s in parts for s in selected_stages):
                continue

            skip = False
            for question in selected_questions:
                field = reg_questions.get(question)
                if field and str(raw.get(field, "")).lower() != "true":
                    skip = True
                    break
            if skip:
                continue

            methods_filtered.append(
                {
                    "id": row["id"],
                    "service": row["method"],
                    "description": row.get("description") or "",
                    "main_url": row.get("catalog_webpage_url") or "no_url",
                    "inst_url": "no_url",
                    "meta_data": "",
                    "png": None,
                    "raw": raw,
                }
            )

        stages = sorted(stages_set)
        if "Other" in stages:
            stages.remove("Other")
            stages.append("Other")

        se_rows = conn.execute("SELECT * FROM stage_explanations").fetchall()
        stage_explanations = {s["name"]: s["explanation"] for s in se_rows}
        reg_question_explanations = {r["label"]: r["explanation"] for r in rq_rows}
        conn.close()

        return render_template(
            "methods/methods.html",
            methods=methods_filtered,
            stages=stages,
            selected_stages=selected_stages,
            reg_questions=reg_questions,
            selected_questions=selected_questions,
            stage_explanations=stage_explanations,
            reg_question_explanations=reg_question_explanations,
        )

    except Exception as e:
        return f"Error processing methods data: {e}", 500


@app.route("/methods/<methodid>")
def method_page(methodid):
    """Render a single method detail page."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM methods WHERE id = ?", (methodid,)).fetchone()
    conn.close()
    if not row:
        abort(404)

    method_details = json.loads(row["raw_json"]) if row["raw_json"] else {}

    # Try to load full JSON from GitHub docs/methods/
    method_json = method_details
    encoded = urllib.parse.quote(methodid, safe="")
    raw_url = (
        "https://raw.githubusercontent.com/VHP4Safety/cloud"
        f"/refs/heads/main/docs/methods/{encoded}.json"
    )
    try:
        r = requests.get(raw_url, timeout=5)
        if r.status_code == 200:
            method_json = r.json()
    except Exception:
        pass

    return render_template(
        "methods/method.html",
        method=method_details,
        method_details=method_details,
        method_json=method_json,
    )


@app.route("/tools/<toolname>")
def tool_page(toolname):
    """Render a single tool detail page."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM tools WHERE id = ?", (toolname,)).fetchone()
    conn.close()
    if not row:
        abort(404)

    tool_json = json.loads(row["raw_json"]) if row["raw_json"] else {}

    # Fetch full details from cloud service JSON
    url = f"https://cloud.vhp4safety.nl/service/{toolname}.json"
    try:
        resp = requests.get(url, timeout=10)
        tool_details = resp.json() if resp.status_code == 200 else tool_json
    except Exception:
        tool_details = tool_json

    return render_template(
        "tools/tool.html",
        tool_json=tool_json,
        tool_details=tool_details,
    )


################################################################################
### Pages under 'Implementation'


# General Explore our work
@app.route("/explore_our_work")
def explore_our_work():
    return render_template("implementation/explore_our_work.html")


# General Training
@app.route("/training")
def training():
    return render_template("implementation/training.html")


# General Impact
@app.route("/impact")
def impact():
    return render_template("implementation/impact.html")


################################################################################
### Pages under 'Process Flow'


# General Safety Assessment Workflow page
@app.route("/safety_assessment_workflow")
def SafetyAssessmentWorkflow():
    return render_template("safety_assessment_workflow.html")


################################################################################
### Pages under 'Case Studies'


@app.route("/casestudies")
def workflows():
    conn = get_conn()
    cards = conn.execute("SELECT * FROM case_studies").fetchall()
    conn.close()
    return render_template(
        "case_studies/casestudies.html", cards=[dict(c) for c in cards]
    )


@app.route("/casestudies/<case>", defaults={"subpath": ""})
@app.route("/casestudies/<case>/<path:subpath>")
# additional routes are parsed client-side via JS to allow smooth animation
def casestudy(case: str, subpath: str = ""):
    conn = get_conn()
    cs = conn.execute("SELECT * FROM case_studies WHERE slug = ?", (case,)).fetchone()
    conn.close()
    if not cs:
        abort(404)

    # Load content JSON from DB and pass inline so JS skips the GitHub fetch
    raw = cs["content_json"] if cs["content_json"] else "{}"
    return render_template(
        "case_studies/casestudy.html",
        case=case,
        case_content_json=raw,
    )


@app.route("/workflow/<workflow>")
def show(workflow):
    try:
        return render_template(
            f"case_studies/parkinson/workflows/{workflow}_workflow.html"
        )
    except TemplateNotFound:
        abort(404)


################################################################################
### Pages related to chemical compounds


def is_valid_qid(qid):
    return re.fullmatch(r"Q\d+", qid) is not None


@app.route("/compound/<cwid>")
def show_compound(cwid):
    try:
        return render_template("compound.html", cwid=cwid)
    except TemplateNotFound:
        abort(404)


@app.route("/get_compound_properties/<cwid>")
def show_compounds_properties_as_json(cwid):
    if not is_valid_qid(cwid):
        return jsonify({"error": "Invalid compound identifier"}), 400
    compoundwikiEP = "https://compoundcloud.wikibase.cloud/query/sparql"
    sparqlquery = (
        "PREFIX wd: <https://compoundcloud.wikibase.cloud/entity/>\n"
        "PREFIX wdt: <https://compoundcloud.wikibase.cloud/prop/direct/>\n\n"
        "SELECT ?cmp ?cmpLabel ?formula ?mass ?inchi ?inchiKey ?SMILES WHERE {\n"
        "  VALUES ?cmp { wd:" + cwid + " }\n"
        "  ?cmp wdt:P9 ?inchi ;\n"
        "       wdt:P10 ?inchiKey .\n"
        "  OPTIONAL { ?cmp wdt:P2 ?mass }\n"
        "  OPTIONAL { ?cmp wdt:P3 ?formula }\n"
        "  OPTIONAL { ?cmp wdt:P7 ?chiralSMILES }\n"
        "  OPTIONAL { ?cmp wdt:P12 ?nonchiralSMILES }\n"
        '  BIND (COALESCE(IF(BOUND(?chiralSMILES), ?chiralSMILES, 1/0), IF(BOUND(?nonchiralSMILES), ?nonchiralSMILES, 1/0), "") AS ?SMILES)\n'
        '  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }\n'
        "}"
    )
    try:
        compound_dat = wbi_helpers.execute_sparql_query(
            sparqlquery, endpoint=compoundwikiEP
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    if not bool(compound_dat):
        return jsonify({"error": "No data found"}), 404
    compound_dat = compound_dat["results"]["bindings"][0]
    # return jsonify(compound_dat);
    compound_list = [
        {
            "wcid": compound_dat["cmp"]["value"],
            "label": compound_dat["cmpLabel"]["value"],
            "inchi": compound_dat["inchi"]["value"],
            "inchikey": compound_dat["inchiKey"]["value"],
            "SMILES": compound_dat["SMILES"]["value"],
            "formula": compound_dat["formula"]["value"],
            "mass": compound_dat["mass"]["value"],
        }
    ]
    return jsonify(compound_list), 200


@app.route("/get_compound_identifiers/<cwid>")
def show_compounds_identifiers_as_json(cwid):
    if not is_valid_qid(cwid):
        return jsonify({"error": "Invalid compound identifier"}), 400
    compoundwikiEP = "https://compoundcloud.wikibase.cloud/query/sparql"
    sparqlquery = (
        "PREFIX wd: <https://compoundcloud.wikibase.cloud/entity/>\n"
        "PREFIX wdt: <https://compoundcloud.wikibase.cloud/prop/direct/>\n\n"
        "SELECT DISTINCT ?propertyLabel ?value ?formatterURL\n"
        "WHERE {\n"
        "  VALUES ?property { wd:P13 wd:P22 wd:P23 wd:P26 wd:P27 wd:P28 wd:P36 wd:P41 wd:P43 wd:P44 wd:P45 }\n"
        "  ?property wikibase:directClaim ?valueProp .\n"
        "  OPTIONAL { wd:" + cwid + " ?valueProp ?value }\n"
        "  OPTIONAL { ?property wdt:P6 ?formatterURL }\n"
        '  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }\n'
        "}"
    )
    try:
        compound_dat = wbi_helpers.execute_sparql_query(
            sparqlquery, endpoint=compoundwikiEP
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    if len(compound_dat["results"]["bindings"]) == 0:
        return jsonify({"error": "No data found"}), 404
    compound_dat = compound_dat["results"]["bindings"]
    # return jsonify(compound_dat)

    compound_list = []
    for expProp in compound_dat:
        if "value" in expProp:
            compound_list.append(
                {
                    "propertyLabel": expProp["propertyLabel"]["value"],
                    "value": expProp["value"]["value"],
                    "formatterURL": expProp["formatterURL"]["value"],
                }
            )
        else:
            compound_list.append(
                {
                    "propertyLabel": expProp["propertyLabel"]["value"],
                    "value": "",
                    "formatterURL": "",
                }
            )
    return jsonify(compound_list), 200


@app.route("/get_compound_toxicology/<cwid>")
def show_compounds_toxicology_as_json(cwid):
    if not is_valid_qid(cwid):
        return jsonify({"error": "Invalid compound identifier"}), 400
    compoundwikiEP = "https://compoundcloud.wikibase.cloud/query/sparql"
    sparqlquery = (
        "PREFIX wd: <https://compoundcloud.wikibase.cloud/entity/>\n"
        "PREFIX wdt: <https://compoundcloud.wikibase.cloud/prop/direct/>\n\n"
        "SELECT DISTINCT ?propertyLabel ?value ?formatterURL\n"
        "WHERE {\n"
        "  VALUES ?property { wd:P17 wd:P19 wd:P4 }\n"
        "  ?property wikibase:directClaim ?valueProp .\n"
        "  OPTIONAL { wd:" + cwid + " ?valueProp ?value }\n"
        "  OPTIONAL { ?property wdt:P6 ?formatterURL }\n"
        '  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }\n'
        "}"
    )
    try:
        compound_dat = wbi_helpers.execute_sparql_query(
            sparqlquery, endpoint=compoundwikiEP
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    if len(compound_dat["results"]["bindings"]) == 0:
        return jsonify({"error": "No data found"}), 404
    compound_dat = compound_dat["results"]["bindings"]
    # return jsonify(compound_dat)

    compound_list = []
    for expProp in compound_dat:
        print(expProp)
        if "value" in expProp:
            compound_list.append(
                {
                    "propertyLabel": expProp["propertyLabel"]["value"],
                    "value": expProp["value"]["value"],
                }
            )
        else:
            compound_list.append(
                {"propertyLabel": expProp["propertyLabel"]["value"], "value": ""}
            )
    return jsonify(compound_list), 200


@app.route("/get_compound_expdata/<cwid>")
def show_compounds_expdata_as_json(cwid):
    if not is_valid_qid(cwid):
        return jsonify({"error": "Invalid compound identifier"}), 400
    compoundwikiEP = "https://compoundcloud.wikibase.cloud/query/sparql"
    sparqlquery = (
        "PREFIX wd: <https://compoundcloud.wikibase.cloud/entity/>\n"
        "PREFIX wdt: <https://compoundcloud.wikibase.cloud/prop/direct/>\n"
        "PREFIX wid: <http://www.wikidata.org/entity/>\n"
        "PREFIX widt: <http://www.wikidata.org/prop/direct/>\n"
        "PREFIX prov: <http://www.w3.org/ns/prov#>\n\n"
        "SELECT ?qid WHERE {\n"
        "  wd:P5 wikibase:directClaim ?identifierProp .\n"
        "  wd:" + cwid + " ?identifierProp ?wikidata .\n"
        '  BIND (iri(CONCAT("http://www.wikidata.org/entity/", ?wikidata)) AS ?qid)\n'
        "}"
    )
    try:
        compound_dat = wbi_helpers.execute_sparql_query(
            sparqlquery, endpoint=compoundwikiEP
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    if not bool(compound_dat):
        return jsonify({"error": "No data found"}), 404
    if len(compound_dat["results"]["bindings"]) == 0:
        return jsonify({"error": "No data found"}), 404
    compound_dat = compound_dat["results"]["bindings"][0]
    qid = compound_dat["qid"]["value"]
    # the next query may be affected by https://github.com/ad-freiburg/qlever-control/issues/187
    sparqlquery = (
        "PREFIX wd: <http://www.wikidata.org/entity/>\n"
        "PREFIX wdt: <http://www.wikidata.org/prop/direct/>\n"
        "PREFIX prov: <http://www.w3.org/ns/prov#>\n"
        "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
        "PREFIX pr: <http://www.wikidata.org/prop/reference/>\n"
        "PREFIX wikibase: <http://wikiba.se/ontology#>\n\n"
        "SELECT DISTINCT ?propEntityLabel ?value ?unitsLabel ?source ?doi ?statement\n"
        "WHERE {\n"
        "    <" + qid + "> ?propp ?statement .\n"
        "    ?statement a wikibase:BestRank ;\n"
        "      ?proppsv [ wikibase:quantityAmount ?value ; wikibase:quantityUnit ?units ] .\n"
        "    #OPTIONAL { ?statement prov:wasDerivedFrom/pr:P248 ?sourceTmp . OPTIONAL { ?sourceTmp wdt:P356 ?doiTmp . } }\n"
        "    ?property wikibase:claim ?propp ; wikibase:statementValue ?proppsv ; wdt:P1629 ?propEntity ; wdt:P31 wd:Q21077852 .\n"
        "    ?propEntity @en@rdfs:label ?propEntityLabel .\n"
        "    ?units @en@rdfs:label ?unitsLabel .\n"
        '    BIND (COALESCE(IF(BOUND(?sourceTmp), ?sourceTmp, 1/0), "") AS ?source)\n'
        '    BIND (COALESCE(IF(BOUND(?doiTmp), ?doiTmp, 1/0), "") AS ?doi)\n'
        "}"
    )
    # return sparqlquery
    try:
        sparqlqueryURL = (
            "https://qlever.cs.uni-freiburg.de/api/wikidata?format=json&query="
            + urllib.parse.quote_plus(sparqlquery)
        )
        # return sparqlqueryURL
        compound_dat = requests.get(sparqlqueryURL)
        # return json.loads(compound_dat.content)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    if not bool(compound_dat):
        return jsonify({"error": "No data found"}), 404
    compound_dat = json.loads(compound_dat.content)["results"]["bindings"]
    # return jsonify(compound_dat)
    compound_list = []
    for expProp in compound_dat:
        # return jsonify(expProp)
        compound_list.append(
            {
                "propEntityLabel": expProp["propEntityLabel"]["value"],
                "value": expProp["value"]["value"],
                "unitsLabel": expProp["unitsLabel"]["value"],
                "source": expProp["source"]["value"],
                "doi": expProp["doi"]["value"],
                "seeAlso": expProp["statement"]["value"],
            }
        )
    return jsonify(compound_list), 200


################################################################################
### Pages under 'Legal'
@app.route("/legal/terms_of_service")
def terms_of_service():
    return render_template("legal/terms_of_service.html")


@app.route("/legal/privacypolicy")
def privacy_policy():
    return render_template("legal/privacypolicy.html")


init_scheduler(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
