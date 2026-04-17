"""Seed the database from upstream GitHub JSON indexes.

Run: python -m src.seed
Idempotent — uses INSERT OR REPLACE (upsert).
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

import requests

from src.db import get_conn, init_db

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
            "What is the intrinsic hazard of tacrolimus "
            "for nephrotoxicity?"
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
    "Chemical Information": (
        "Information about chemical properties and identity."
    ),
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
            "To study life course pesticide exposure and "
            "neurodegenerative disease."
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


def seed_reference_data(conn) -> None:
    for key, data in REG_QUESTIONS.items():
        conn.execute(
            "INSERT OR REPLACE INTO regulatory_questions (key, label, explanation) VALUES (?, ?, ?)",
            (key, data["label"], data["explanation"]),
        )
    for name, explanation in STAGE_EXPLANATIONS.items():
        conn.execute(
            "INSERT OR REPLACE INTO stage_explanations (name, explanation) VALUES (?, ?)",
            (name, explanation),
        )
    for url, stage in GLOSSARY_STAGE_MAPPINGS.items():
        conn.execute(
            "INSERT OR REPLACE INTO glossary_stage_mappings (glossary_url, stage_name) VALUES (?, ?)",
            (url, stage),
        )
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
        conn.execute(
            """INSERT OR REPLACE INTO case_studies
               (slug, title, description, image_src, image_alt, content_json)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (cs["slug"], cs["title"], cs["description"],
             cs.get("image_src"), cs.get("image_alt"), content_json),
        )
    conn.commit()
    print("ok reference data seeded")


def seed_tools(conn) -> None:
    resp = requests.get(SERVICES_URL, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    # Build glossary lookup
    cur = conn.execute("SELECT glossary_url, stage_name FROM glossary_stage_mappings")
    glossary = {r["glossary_url"]: r["stage_name"] for r in cur}

    now = _now()
    for tool_id, raw in data.items():
        stage = raw.get("stage", "")
        stage = glossary.get(stage, stage)
        if stage in ("NA", "Unknown"):
            stage = "Other"

        conn.execute(
            """INSERT OR REPLACE INTO tools
               (id, service, description, stage, html_name, md_file_name,
                png_file_name, main_url, inst_url,
                reg_q_1a, reg_q_1b, reg_q_2a, reg_q_2b, reg_q_3a, reg_q_3b,
                login, api_type, casestudy, provider, provider_email,
                citation, version, license, sourcecode, docker,
                bio_tools, tess, raw_json, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (tool_id, raw.get("service", tool_id), raw.get("description"),
             stage, raw.get("html_name"), raw.get("md_file_name"),
             raw.get("png_file_name"), raw.get("main_url"),
             raw.get("inst_url") or None,
             _bool_flag(raw.get("reg_q_1a")), _bool_flag(raw.get("reg_q_1b")),
             _bool_flag(raw.get("reg_q_2a")), _bool_flag(raw.get("reg_q_2b")),
             _bool_flag(raw.get("reg_q_3a")), _bool_flag(raw.get("reg_q_3b")),
             raw.get("login"), raw.get("api"), raw.get("casestudy"),
             raw.get("provider"), raw.get("provider-email"),
             raw.get("citation"), raw.get("version"), raw.get("license"),
             raw.get("sourcecode"), raw.get("docker"),
             raw.get("bioTools"), raw.get("tess"),
             json.dumps(raw), now),
        )
    conn.commit()
    print(f"ok {len(data)} tools seeded")


def seed_methods(conn) -> None:
    resp = requests.get(METHODS_URL, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    now = _now()
    for method_id, raw in data.items():
        conn.execute(
            """INSERT OR REPLACE INTO methods
               (id, method, issue_number, description, stage, substage,
                catalog_webpage_url, case_study, regulatory_question,
                reg_q_1a, reg_q_1b, reg_q_2a, reg_q_2b, reg_q_3a, reg_q_3b,
                data_producer, sop, vendor, catalog_number, citation,
                type_iri, ontology, key_event_id, aop_id,
                raw_json, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (method_id,
             raw.get("method") or raw.get("method_name_content", method_id),
             raw.get("issue_number"),
             raw.get("method_description_content"),
             raw.get("vhp4safety_workflow_stage_content"),
             raw.get("workflow_substage_content"),
             raw.get("catalog_webpage_url"),
             raw.get("case_study_content"),
             raw.get("regulatory_question_content"),
             _bool_flag(raw.get("reg_q_1a")), _bool_flag(raw.get("reg_q_1b")),
             _bool_flag(raw.get("reg_q_2a")), _bool_flag(raw.get("reg_q_2b")),
             _bool_flag(raw.get("reg_q_3a")), _bool_flag(raw.get("reg_q_3b")),
             raw.get("data_producer_content"),
             raw.get("available_sop_or_protocol_content"),
             raw.get("vendor_content"),
             raw.get("catalog_number_content"),
             raw.get("citation_content"),
             raw.get("ontology_term_content"),
             raw.get("type_content"),
             raw.get("relevant_aop_wiki_key_event(s)_to_the_assay_content"),
             raw.get("relevant_aop_wiki_adverse_outcome_pathway(s)_to_the_assay_content"),
             json.dumps(raw), now),
        )
    conn.commit()
    print(f"ok {len(data)} methods seeded")


def seed_all() -> None:
    init_db()
    conn = get_conn()
    try:
        seed_reference_data(conn)
        seed_tools(conn)
        seed_methods(conn)
        print("ok seeding complete")
    finally:
        conn.close()


if __name__ == "__main__":
    seed_all()
