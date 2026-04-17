"""Thin sqlite3 helper. No ORM — just raw SQL."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.environ.get("DATABASE_PATH", "data/vhp4safety.db")

_TABLES = [
    """CREATE TABLE IF NOT EXISTS tools (
        id TEXT PRIMARY KEY, service TEXT NOT NULL, description TEXT,
        stage TEXT, html_name TEXT, md_file_name TEXT, png_file_name TEXT,
        main_url TEXT, inst_url TEXT,
        reg_q_1a INTEGER, reg_q_1b INTEGER, reg_q_2a INTEGER,
        reg_q_2b INTEGER, reg_q_3a INTEGER, reg_q_3b INTEGER,
        login TEXT, api_type TEXT, casestudy TEXT, provider TEXT,
        provider_email TEXT, citation TEXT, version TEXT, license TEXT,
        sourcecode TEXT, docker TEXT, bio_tools TEXT, tess TEXT,
        raw_json TEXT, updated_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS methods (
        id TEXT PRIMARY KEY, method TEXT NOT NULL, issue_number INTEGER,
        description TEXT, stage TEXT, substage TEXT,
        catalog_webpage_url TEXT, case_study TEXT, regulatory_question TEXT,
        reg_q_1a INTEGER, reg_q_1b INTEGER, reg_q_2a INTEGER,
        reg_q_2b INTEGER, reg_q_3a INTEGER, reg_q_3b INTEGER,
        data_producer TEXT, sop TEXT, vendor TEXT, catalog_number TEXT,
        citation TEXT, type_iri TEXT, ontology TEXT,
        key_event_id TEXT, aop_id TEXT, raw_json TEXT, updated_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS regulatory_questions (
        key TEXT PRIMARY KEY, label TEXT NOT NULL, explanation TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS stage_explanations (
        name TEXT PRIMARY KEY, explanation TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS glossary_stage_mappings (
        glossary_url TEXT PRIMARY KEY, stage_name TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS case_studies (
        slug TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL,
        image_src TEXT, image_alt TEXT,
        config_repo TEXT DEFAULT 'VHP4Safety/ui-casestudy-config',
        default_branch TEXT DEFAULT 'main', content_json TEXT
    )""",
]


def get_conn() -> sqlite3.Connection:
    """Return a new connection with Row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db():
    """Context manager: yields a connection, auto-closes."""
    conn = get_conn()
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Create all tables (idempotent)."""
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    for ddl in _TABLES:
        conn.execute(ddl)
    conn.commit()
    conn.close()
