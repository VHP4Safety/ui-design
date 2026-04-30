"""Generate a static sitemap.xml file from DB contents and Flask routes."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional, Tuple
import os
from xml.etree import ElementTree as ET

from sqlalchemy import select

from src.db import db, Tool, Method, CaseStudy, init_db
from src.api import init_api
from flask_openapi3.openapi import OpenAPI
from flask_openapi3.models.info import Info

BASE_URL = os.environ.get("BASE_URL", "http://localhost:5050")

OUT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "static", "sitemap.xml")
)


def _add_url(
    root,
    loc: str,
    lastmod: Optional[str] = None,
    changefreq: str = "monthly",
    priority: str = "0.5",
) -> None:
    url = ET.SubElement(root, "url")
    ET.SubElement(url, "loc").text = loc

    if lastmod:
        ET.SubElement(url, "lastmod").text = lastmod

    ET.SubElement(url, "changefreq").text = changefreq
    ET.SubElement(url, "priority").text = priority


def gather_static_routes(app) -> Iterable[Tuple[str, None]]:
    for rule in app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue

        if "GET" not in rule.methods:
            continue

        if rule.arguments:
            continue

        yield (f"{BASE_URL}{rule.rule}", None)


def gather_db_urls() -> Iterable[Tuple[str, Optional[str]]]:
    yield (f"{BASE_URL}/", datetime.utcnow().isoformat())

    for t in db.session.execute(select(Tool.id, Tool.updated_at)):
        if t.id:
            yield (f"{BASE_URL}/tools/{t.id}", t.updated_at)

    for m in db.session.execute(select(Method.id, Method.updated_at)):
        if m.id:
            yield (f"{BASE_URL}/methods/{m.id}", m.updated_at)

    for cs in db.session.execute(select(CaseStudy.slug)):
        if cs.slug:
            yield (f"{BASE_URL}/casestudies/{cs.slug}", None)


def build_sitemap(app, out_path: str = OUT_PATH) -> str:
    root = ET.Element(
        "urlset",
        xmlns="http://www.sitemaps.org/schemas/sitemap/0.9",
    )

    for loc, last in gather_static_routes(app):
        _add_url(root, loc, lastmod=last)

    for loc, last in gather_db_urls():
        _add_url(root, loc, lastmod=last)
    for loc in {
        "/explore_our_work",
        "/tools",
        "/methods",
        "/data",
        "/casestudies",
        "/impact",
        "/training",
        "/safety_assessment_workflow",
    }:
        loc_f = BASE_URL + loc
        _add_url(root, loc_f, lastmod=None)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    ET.ElementTree(root).write(
        out_path,
        encoding="utf-8",
        xml_declaration=True,
    )

    return out_path


def main() -> None:
    app = OpenAPI(
        __name__,
        info=Info(title="VHP4Safety Platform API", version="1.0.0"),
        doc_prefix="/api/v1",
    )

    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-insecure-key")

    init_api(app)
    init_db(app)

    with app.app_context():
        path = build_sitemap(app)

    print(f"Wrote sitemap to: {path}")


if __name__ == "__main__":
    main()
