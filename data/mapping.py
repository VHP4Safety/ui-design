from typing import Any, Dict, List, Optional
import re

# ---------- small helpers ----------

DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)

def g(d: Dict[str, Any], *path: str, default=None):
    """Safe nested-get. Never raises KeyError."""
    cur: Any = d
    for key in path:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return cur

def first(*vals, default=None):
    """Return first non-empty (not None, not '' , not []) value."""
    for v in vals:
        if v is None:
            continue
        if v == "":
            continue
        if isinstance(v, (list, dict)) and len(v) == 0:
            continue
        return v
    return default

def find_attr(attrs: Any, name: str) -> Optional[str]:
    """Find BioStudies attribute list entry with given name."""
    if not isinstance(attrs, list):
        return None
    for a in attrs:
        if isinstance(a, dict) and a.get("name") == name:
            return a.get("value")
    return None

def extract_doi_from_text(text: Any) -> Optional[str]:
    """Extract a DOI from a string (or return None)."""
    if not isinstance(text, str) or not text:
        return None
    m = DOI_RE.search(text)
    return m.group(0) if m else None

def find_doi_anywhere(item: Dict[str, Any]) -> Optional[str]:
    """
    Best-effort DOI extractor for heterogeneous records:
    - direct fields: doi, metadata.doi
    - Zenodo related_identifiers
    - BioStudies attributes / publications / links / description
    """
    # direct keys first
    doi = first(item.get("doi"), g(item, "metadata", "doi"))
    if doi:
        # sometimes this is already "10.xxxx/...."
        return extract_doi_from_text(doi) or doi

    # Zenodo: related identifiers
    rel = g(item, "metadata", "related_identifiers", default=[]) or []
    if isinstance(rel, list):
        for r in rel:
            if not isinstance(r, dict):
                continue
            ident = r.get("identifier")
            scheme = (r.get("scheme") or "").lower()
            if scheme == "doi":
                return extract_doi_from_text(ident) or ident
            # Sometimes scheme missing but identifier contains DOI
            found = extract_doi_from_text(ident)
            if found:
                return found

    # BioStudies: attributes
    attrs = g(item, "metadata", "attributes", default=[]) or []
    for key in ("DOI", "doi", "Publication DOI", "Dataset DOI"):
        v = find_attr(attrs, key)
        found = extract_doi_from_text(v)
        if found:
            return found

    # BioStudies: publications list (if present)
    pubs = g(item, "metadata", "publications", default=[]) or []
    if isinstance(pubs, list):
        for p in pubs:
            if not isinstance(p, dict):
                continue
            for cand in (p.get("doi"), p.get("identifier"), p.get("url"), p.get("title")):
                found = extract_doi_from_text(cand)
                if found:
                    return found

    # BioStudies: links (if present)
    links = g(item, "metadata", "links", default=[]) or []
    if isinstance(links, list):
        for l in links:
            if not isinstance(l, dict):
                continue
            found = extract_doi_from_text(l.get("url"))
            if found:
                return found

    # last resort: description text
    desc = first(g(item, "metadata", "description"), item.get("description"))
    found = extract_doi_from_text(desc)
    if found:
        return found

    return None

def doi_url(doi: Optional[str]) -> Optional[str]:
    """Convert DOI to https://doi.org/..."""
    if not doi:
        return None
    d = doi.strip()
    # already a DOI URL
    if d.lower().startswith("http"):
        return d
    return f"https://doi.org/{d}"


# ---------- Zenodo normalizer ----------

def normalize_zenodo(z: Dict[str, Any]) -> Dict[str, Any]:
    creators = g(z, "metadata", "creators", default=[]) or []
    grants = g(z, "metadata", "grants", default=[]) or []
    files = z.get("files", []) or []

    doi = find_doi_anywhere(z)

    return {
        "title": first(g(z, "metadata", "title"), z.get("title")),
        "description": first(g(z, "metadata", "description")),
        "license": first(g(z, "metadata", "license", "id")),
        "authors": [
            {
                "name": c.get("name"),
                "orcid": c.get("orcid"),
                "affiliation": c.get("affiliation"),
            }
            for c in creators
            if isinstance(c, dict)
        ],
        "funding": [
            {
                "funder": g(gr, "funder", "name"),
                "funder_doi": g(gr, "funder", "doi"),
                "acronym": gr.get("acronym"),
                "title": gr.get("title"),
                "code": gr.get("code"),
                "url": gr.get("url"),
            }
            for gr in grants
            if isinstance(gr, dict)
        ],
        "ReleaseDate": first(g(z, "metadata", "publication_date"), z.get("created")),
        "id": first(z.get("id"), z.get("recid")),
        "type": first(g(z, "metadata", "resource_type", "type"), "dataset"),
        "version": first(g(z, "metadata", "version")),
        "files": [
            {
                "name": f.get("key"),
                "size": f.get("size"),
                "checksum": f.get("checksum"),
                "url": g(f, "links", "self"),
            }
            for f in files
            if isinstance(f, dict)
        ],
        "url": first(z.get("url"), g(z, "links", "self_html"), g(z, "links", "self")),

        "doi": doi,
        "doi_url": doi_url(doi),
        "conceptdoi": first(z.get("conceptdoi"), g(z, "metadata", "conceptdoi")),
        "conceptdoi_url": doi_url(first(z.get("conceptdoi"), g(z, "metadata", "conceptdoi"))),
    }


# ---------- BioStudies normalizer ----------

def normalize_biostudies(b: Dict[str, Any]) -> Dict[str, Any]:
    meta = b.get("metadata", {}) or {}
    attrs = meta.get("attributes", []) or []
    files = meta.get("files", []) or []

    author_details = meta.get("author_details", []) or []
    authors = meta.get("authors", []) or []

    if isinstance(author_details, list) and len(author_details) > 0:
        authors_norm = [
            {
                "name": a.get("name"),
                "orcid": a.get("orcid"),
                "affiliation": a.get("affiliation_name") or a.get("affiliation_ref"),
                "email": a.get("email"),
            }
            for a in author_details
            if isinstance(a, dict)
        ]
    else:
        authors_norm = [
            {"name": name, "orcid": None, "affiliation": None}
            for name in authors
            if isinstance(name, str)
        ]

    # funding best-effort
    funding = []
    subsections = g(b, "metadata", "raw_data", "section", "subsections", default=[]) or []
    if isinstance(subsections, list):
        for s in subsections:
            if isinstance(s, dict) and str(s.get("type", "")).lower() == "funding":
                entry = {}
                for a in s.get("attributes") or []:
                    if isinstance(a, dict) and a.get("name"):
                        entry[a["name"]] = a.get("value")
                if entry:
                    funding.append(entry)

    doi = find_doi_anywhere(b)

    return {
        "title": first(meta.get("title"), b.get("title")),
        "description": first(meta.get("description")),
        "license": first(find_attr(attrs, "License")),
        "authors": authors_norm,
        "funding": funding,
        "ReleaseDate": first(
            b.get("release_date"),
            find_attr(attrs, "ReleaseDate"),
            find_attr(attrs, "Release Date"),
        ),
        "id": first(meta.get("accession"), b.get("accession"), b.get("id")),
        "type": first(b.get("type"), meta.get("type"), "study"),
        "version": first(meta.get("version")),
        "files": [
            {
                "name": first(f.get("name"), f.get("path")),
                "size": f.get("size"),
                "path": f.get("path"),
            }
            for f in files
            if isinstance(f, dict)
        ],
        "url": first(b.get("url")),
        "doi": doi,
        "doi_url": doi_url(doi),
    }


# ---------- combine ----------

def normalize_all(
    bs_entries: List[Dict[str, Any]],
    zenodo_entries: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Adds 'norm_metadata' to each dict in both lists and returns a combined list of normalized dicts.
    Robust: ignores non-dicts and missing lists.
    """
    out: List[Dict[str, Any]] = []

    for z in zenodo_entries or []:
        if isinstance(z, dict):
            z["norm_metadata"] = normalize_zenodo(z)

    for b in bs_entries or []:
        if isinstance(b, dict):
            b["norm_metadata"] = normalize_biostudies(b)

    return bs_entries, zenodo_entries