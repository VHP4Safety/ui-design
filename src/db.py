"""SQLAlchemy ORM database layer."""

from __future__ import annotations

import os

from flask_sqlalchemy import SQLAlchemy

DB_PATH = os.environ.get("DATABASE_PATH", "data/vhp4safety.db")

db = SQLAlchemy()


#  ORM models


class Tool(db.Model):
    __tablename__ = "tools"

    id = db.Column(db.String, primary_key=True)
    service = db.Column(db.String, nullable=False)
    description = db.Column(db.Text)
    stage = db.Column(db.String)
    html_name = db.Column(db.String)
    md_file_name = db.Column(db.String)
    png_file_name = db.Column(db.String)
    main_url = db.Column(db.String)
    inst_url = db.Column(db.String)
    reg_q_1a = db.Column(db.Integer)
    reg_q_1b = db.Column(db.Integer)
    reg_q_2a = db.Column(db.Integer)
    reg_q_2b = db.Column(db.Integer)
    reg_q_3a = db.Column(db.Integer)
    reg_q_3b = db.Column(db.Integer)
    login = db.Column(db.String)
    api_type = db.Column(db.String)
    casestudy = db.Column(db.String)
    provider = db.Column(db.String)
    provider_email = db.Column(db.String)
    citation = db.Column(db.Text)
    version = db.Column(db.String)
    license = db.Column(db.String)
    sourcecode = db.Column(db.String)
    docker = db.Column(db.String)
    bio_tools = db.Column(db.String)
    tess = db.Column(db.String)
    raw_json = db.Column(db.Text)
    updated_at = db.Column(db.String)


class Method(db.Model):
    __tablename__ = "methods"

    id = db.Column(db.String, primary_key=True)
    method = db.Column(db.String, nullable=False)
    issue_number = db.Column(db.Integer)
    description = db.Column(db.Text)
    stage = db.Column(db.String)
    substage = db.Column(db.String)
    catalog_webpage_url = db.Column(db.String)
    case_study = db.Column(db.String)
    regulatory_question = db.Column(db.String)
    reg_q_1a = db.Column(db.Integer)
    reg_q_1b = db.Column(db.Integer)
    reg_q_2a = db.Column(db.Integer)
    reg_q_2b = db.Column(db.Integer)
    reg_q_3a = db.Column(db.Integer)
    reg_q_3b = db.Column(db.Integer)
    data_producer = db.Column(db.String)
    sop = db.Column(db.Text)
    vendor = db.Column(db.String)
    catalog_number = db.Column(db.String)
    citation = db.Column(db.Text)
    type_iri = db.Column(db.String)
    ontology = db.Column(db.String)
    key_event_id = db.Column(db.String)
    aop_id = db.Column(db.String)
    raw_json = db.Column(db.Text)
    updated_at = db.Column(db.String)


class RegulatoryQuestion(db.Model):
    __tablename__ = "regulatory_questions"

    key = db.Column(db.String, primary_key=True)
    label = db.Column(db.String, nullable=False)
    explanation = db.Column(db.Text, nullable=False)


class StageExplanation(db.Model):
    __tablename__ = "stage_explanations"

    name = db.Column(db.String, primary_key=True)
    explanation = db.Column(db.Text, nullable=False)


class GlossaryStageMappings(db.Model):
    __tablename__ = "glossary_stage_mappings"

    glossary_url = db.Column(db.String, primary_key=True)
    stage_name = db.Column(db.String, nullable=False)


class CaseStudy(db.Model):
    __tablename__ = "case_studies"

    slug = db.Column(db.String, primary_key=True)
    title = db.Column(db.String, nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_src = db.Column(db.String)
    image_alt = db.Column(db.String)
    config_repo = db.Column(db.String, default="VHP4Safety/ui-casestudy-config")
    default_branch = db.Column(db.String, default="main")
    content_json = db.Column(db.Text)


#  Helpers


def row_to_dict(obj) -> dict:
    """Convert an ORM model instance to a plain dict."""
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


#  App factory


def init_db(app) -> None:
    """Configure Flask-SQLAlchemy and create all tables."""

    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    db_path = os.environ.get("DATABASE_PATH")
    if not db_path:
        db_path = os.path.join(BASE_DIR, "data", "vhp4safety.db")

    db_path = os.path.abspath(db_path)

    # ensure directory exists
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    # hard fail early if not writable
    try:
        with open(db_path, "a"):
            pass
    except OSError as e:
        raise RuntimeError(f"Database path not writable: {db_path}") from e

    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    with app.app_context():
        db.create_all()
