"""Seed the database from upstream GitHub JSON indexes.

Run: python -m src.seed
Idempotent — uses SQLAlchemy session.merge() (equivalent to INSERT OR REPLACE).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import requests

from src.db import (
    db,
    CaseStudy,
    GlossaryStageMappings,
    Method,
    RegulatoryQuestion,
    StageExplanation,
    Tool,
    init_db,
)

SERVICES_URL = os.environ.get(
    "SERVICES_URL",
    "https://raw.githubusercontent.com/VHP4Safety/cloud"
    "/refs/heads/main/cap/service_index.json",
)
METHODS_URL = os.environ.get(
    "METHODS_URL",
    "https://raw.githubusercontent.com/VHP4Safety/cloud"
    "/refs/heads/main/cap/methods_index.json",
)

# ── Static reference data ────────────────────────────────────────────────

REG_QUESTIONS = {
    "reg_q_1a": {
        "label": "Kidney Case Study (a)",
        "explanation": "What is the safe cisplatin dose in cancer patients?",
    },
    "reg_q_1b": {
        "label": "Kidney Case Study (b)",
        "explanation": (
            "What is the intrinsic hazard of tacrolimus for nephrotoxicity?"
        ),
    },
    "reg_q_2a": {
        "label": "Parkinson Case Study (a)",
        "explanation": "Can compound Dinoseb cause Parkinson's Disease?",
    },
    "reg_q_2b": {
        "label": "Parkinson Case Study (b)",
        "explanation": (
            "What level of exposure to compound Dinoseb leads to "
            "risk for developing Parkinson's disease?"
        ),
    },
    "reg_q_3a": {
        "label": "Thyroid Case Study (a)",
        "explanation": (
            "What information about silychristin do we need to give "
            "an advice to women in their early pregnancy to decide "
            "whether the substance can be used?"
        ),
    },
    "reg_q_3b": {
        "label": "Thyroid Case Study (b)",
        "explanation": (
            "Does silychristin influence the thyroid-mediated brain "
            "development in the fetus resulting in cognitive "
            "impairment in children?"
        ),
    },
}

STAGE_EXPLANATIONS = {
    "ADME": (
        "Absorption, distribution, metabolism, and excretion of a "
        "substance in a living organism, following exposure."
    ),
    "Hazard Assessment": (
        "The process of assessing the intrinsic hazard a substance "
        "poses to human health and/or the environment."
    ),
    "Chemical Information": ("Information about chemical properties and identity."),
    "General": "Not specific to a flow step.",
    "(External) exposure": "External exposure assessment.",
    "Generic": "Generic category.",
    "Other": "Other or unknown category.",
}

GLOSSARY_STAGE_MAPPINGS = {
    "https://vhp4safety.github.io/glossary#VHP0000056": "ADME",
    "https://vhp4safety.github.io/glossary#VHP0000102": "Hazard Assessment",
    "https://vhp4safety.github.io/glossary#VHP0000148": "Chemical Information",
    "https://vhp4safety.github.io/glossary#VHP0000149": "General",
}

CASE_STUDIES = [
    {
        "slug": "kidney",
        "title": "Kidney case study",
        "description": "To study kidney disease and pharmacovigilance.",
        "image_src": "/static/images/image43_hexagon.svg",
        "image_alt": "Kidney case study",
    },
    {
        "slug": "parkinson",
        "title": "Parkinson case study",
        "description": (
            "To study life course pesticide exposure and neurodegenerative disease."
        ),
        "image_src": "/static/images/image45_hexagon.svg",
        "image_alt": "Parkinson case study",
    },
    {
        "slug": "thyroid",
        "title": "Thyroid case study",
        "description": (
            "To study health effects discriminated by age and sex on "
            "thyroid-mediated neurodevelopment."
        ),
        "image_src": "/static/images/image47_hexagon.svg",
        "image_alt": "Thyroid case study",
    },
]

CASESTUDY_CONTENT_URL = (
    "https://raw.githubusercontent.com/"
    "VHP4Safety/ui-casestudy-config/main/{slug}_content.json"
)


def _bool_flag(val):
    if val is None or val == "":
        return None
    return 1 if str(val).strip().lower() == "true" else 0


def _now():
    return datetime.now(timezone.utc).isoformat()


def seed_reference_data() -> None:
    for key, data in REG_QUESTIONS.items():
        db.session.merge(
            RegulatoryQuestion(
                key=key, label=data["label"], explanation=data["explanation"]
            )
        )
    for name, explanation in STAGE_EXPLANATIONS.items():
        db.session.merge(StageExplanation(name=name, explanation=explanation))
    for url, stage in GLOSSARY_STAGE_MAPPINGS.items():
        db.session.merge(GlossaryStageMappings(glossary_url=url, stage_name=stage))
    for cs in CASE_STUDIES:
        content_json = None
        try:
            url = CASESTUDY_CONTENT_URL.format(slug=cs["slug"])
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            content_json = resp.text
            print(f"  ok fetched {cs['slug']}_content.json")
        except Exception as exc:
            print(f"  x could not fetch {cs['slug']}: {exc}")
        db.session.merge(
            CaseStudy(
                slug=cs["slug"],
                title=cs["title"],
                description=cs["description"],
                image_src=cs.get("image_src"),
                image_alt=cs.get("image_alt"),
                content_json=content_json,
            )
        )
    db.session.commit()
    print("ok reference data seeded")


def seed_tools() -> None:
    resp = requests.get(SERVICES_URL, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    # Build glossary lookup
    glossary = {g.glossary_url: g.stage_name for g in GlossaryStageMappings.query.all()}

    now = _now()
    for tool_id, raw in data.items():
        stage = raw.get("stage", "")
        stage = glossary.get(stage, stage)
        if stage in ("NA", "Unknown"):
            stage = "Other"

        db.session.merge(
            Tool(
                id=tool_id,
                service=raw.get("service", tool_id),
                description=raw.get("description"),
                stage=stage,
                html_name=raw.get("html_name"),
                md_file_name=raw.get("md_file_name"),
                png_file_name=raw.get("png_file_name"),
                main_url=raw.get("main_url"),
                inst_url=raw.get("inst_url") or None,
                reg_q_1a=_bool_flag(raw.get("reg_q_1a")),
                reg_q_1b=_bool_flag(raw.get("reg_q_1b")),
                reg_q_2a=_bool_flag(raw.get("reg_q_2a")),
                reg_q_2b=_bool_flag(raw.get("reg_q_2b")),
                reg_q_3a=_bool_flag(raw.get("reg_q_3a")),
                reg_q_3b=_bool_flag(raw.get("reg_q_3b")),
                login=raw.get("login"),
                api_type=raw.get("api"),
                casestudy=raw.get("casestudy"),
                provider=raw.get("provider"),
                provider_email=raw.get("provider-email"),
                citation=raw.get("citation"),
                version=raw.get("version"),
                license=raw.get("license"),
                sourcecode=raw.get("sourcecode"),
                docker=raw.get("docker"),
                bio_tools=raw.get("bioTools"),
                tess=raw.get("tess"),
                raw_json=json.dumps(raw),
                updated_at=now,
            )
        )
    db.session.commit()
    print(f"ok {len(data)} tools seeded")


def seed_methods() -> None:
    resp = requests.get(METHODS_URL, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    now = _now()
    for method_id, raw in data.items():
        db.session.merge(
            Method(
                id=method_id,
                method=raw.get("method") or raw.get("method_name_content", method_id),
                issue_number=raw.get("issue_number"),
                description=raw.get("method_description_content"),
                stage=raw.get("vhp4safety_workflow_stage_content"),
                substage=raw.get("workflow_substage_content"),
                catalog_webpage_url=raw.get("catalog_webpage_url"),
                case_study=raw.get("case_study_content"),
                regulatory_question=raw.get("regulatory_question_content"),
                reg_q_1a=_bool_flag(raw.get("reg_q_1a")),
                reg_q_1b=_bool_flag(raw.get("reg_q_1b")),
                reg_q_2a=_bool_flag(raw.get("reg_q_2a")),
                reg_q_2b=_bool_flag(raw.get("reg_q_2b")),
                reg_q_3a=_bool_flag(raw.get("reg_q_3a")),
                reg_q_3b=_bool_flag(raw.get("reg_q_3b")),
                data_producer=raw.get("data_producer_content"),
                sop=raw.get("available_sop_or_protocol_content"),
                vendor=raw.get("vendor_content"),
                catalog_number=raw.get("catalog_number_content"),
                citation=raw.get("citation_content"),
                type_iri=raw.get("ontology_term_content"),
                ontology=raw.get("type_content"),
                key_event_id=raw.get(
                    "relevant_aop_wiki_key_event(s)_to_the_assay_content"
                ),
                aop_id=raw.get(
                    "relevant_aop_wiki_adverse_outcome_pathway(s)_to_the_assay_content"
                ),
                raw_json=json.dumps(raw),
                updated_at=now,
            )
        )
    db.session.commit()
    print(f"ok {len(data)} methods seeded")


def seed_all(app=None) -> None:
    """Seed all tables.  Pass a Flask app instance when called outside a
    request context (e.g. from the CLI or a background thread).
    """
    if app is not None:
        ctx = app.app_context()
        ctx.push()
    else:
        ctx = None

    try:
        init_db(app) if app is not None else None
        seed_reference_data()
        seed_tools()
        seed_methods()
        print("ok seeding complete")
    finally:
        if ctx is not None:
            ctx.pop()


if __name__ == "__main__":
    # CLI entry point: create a minimal Flask app to provide the app context
    from flask import Flask as _Flask

    _app = _Flask(__name__)
    seed_all(_app)
