"""Generate a static sitemap.xml file from DB contents."""
from __future__ import annotations

from datetime import datetime
from typing import Iterable
import os
from xml.etree import ElementTree as ET

from src.db import get_conn

BASE_URL = os.environ.get("BASE_URL", "http://localhost:5050")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "static", "sitemap.xml")


def _add_url(root, loc, lastmod=None, changefreq="monthly", priority="0.5"):
    url = ET.SubElement(root, "url")
    ET.SubElement(url, "loc").text = loc
    if lastmod:
        ET.SubElement(url, "lastmod").text = lastmod
    ET.SubElement(url, "changefreq").text = changefreq
    ET.SubElement(url, "priority").text = priority


def gather_urls() -> Iterable[tuple[str, str | None]]:
    conn = get_conn()
    try:
        yield (f"{BASE_URL}/", datetime.utcnow().isoformat())
        for path in ("/tools", "/methods", "/data", "/casestudies", "/api/v1/docs"):
            yield (f"{BASE_URL}{path}", None)
        for t in conn.execute("SELECT id, updated_at FROM tools").fetchall():
            if t["id"]:
                yield (f"{BASE_URL}/tools/{t['id']}", t["updated_at"])
        for m in conn.execute("SELECT id, updated_at FROM methods").fetchall():
            if m["id"]:
                yield (f"{BASE_URL}/methods/{m['id']}", m["updated_at"])
        for cs in conn.execute("SELECT slug FROM case_studies").fetchall():
            if cs["slug"]:
                yield (f"{BASE_URL}/casestudies/{cs['slug']}", None)
    finally:
        conn.close()


def build_sitemap(out_path: str = OUT_PATH) -> str:
    root = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for loc, last in gather_urls():
        _add_url(root, loc, lastmod=last)
    tree = ET.ElementTree(root)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    tree.write(out_path, encoding="utf-8", xml_declaration=True)
    return out_path


def main() -> None:
    path = build_sitemap()
    print(f"Wrote sitemap to: {path}")


if __name__ == "__main__":
    main()
