#!/usr/bin/env python3
"""API quality check — Pydantic-first.

For every entity type, fetches the API response and validates each
entry through its Pydantic model (structural) + domain rules (content).
Reports counts, field completeness, content warnings, and route health.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone

from .quality_models import ENTITY_CHECKS, DataHitChecker, deep_scan


# resolve BASE URL


def _port_from_dockerfile(path: str) -> str:
    try:
        with open(path) as f:
            for line in f:
                m = re.match(r"^\s*EXPOSE\s+(\d+)", line)
                if m:
                    return m.group(1)
    except OSError:
        pass
    return "5050"


def _container_ip(name: str) -> str | None:
    try:
        out = subprocess.check_output(
            [
                "docker",
                "inspect",
                "--format",
                "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
                name,
            ],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return out or None
    except Exception:
        return None


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = _port_from_dockerfile(os.path.join(REPO_ROOT, "Dockerfile"))

if "VHP_BASE_URL" in os.environ:
    BASE = os.environ["VHP_BASE_URL"].rstrip("/")
else:
    ip = _container_ip(os.environ.get("VHP_CONTAINER", "vhp4safety"))
    BASE = f"http://{ip}:{PORT}/api" if ip else f"http://localhost:{PORT}/api"

print(f"# Using BASE: {BASE}", file=sys.stderr)


# HTTP helper


def get(path: str) -> tuple[int, object]:
    try:
        with urllib.request.urlopen(
            urllib.request.Request(f"{BASE}{path}"), timeout=200  # TODO fix slow API call
        ) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return 0, None


# run checks

errors: list[str] = []
warnings: list[str] = []

# 1. Entity counts + content quality
counts: dict[str, int | None] = {}
quality_issues: list[tuple[str, str, str, str, str]] = []
# shape: (entity, entry_id, entry_label, field, issue)

for path, (checker, id_field, label_field) in ENTITY_CHECKS.items():
    entity = path.strip("/").split("/")[0]
    status, data = get(path)
    if status != 200 or not isinstance(data, list):
        counts[entity] = None
        errors.append(f"GET {path} -> {status}")
        continue

    counts[entity] = len(data)

    for entry in data:
        entry_id = str(entry.get(id_field, "?"))
        entry_label = str(entry.get(label_field) or entry_id)
        for field, msg in checker.check(entry):
            quality_issues.append((entity, entry_id, entry_label, field, msg))
            warnings.append(f"[{entity}] {entry_label!r} / {field}: {msg}")

# 1b. Case study detail scan — content_json is only in the detail endpoint
_cs_status, _cs_list = get("/casestudies/")
if isinstance(_cs_list, list):
    for cs in _cs_list:
        cs_name = cs.get("name") or cs.get("slug", "?")
        cs_title = cs.get("title") or cs_name
        detail_status, detail = get(f"/casestudies/{cs_name}")
        if detail_status != 200 or not isinstance(detail, dict):
            continue
        content = detail.get("content_json")
        if not content:
            continue
        # deduplicate by (path, issue) — content_json can repeat the same template
        seen: set[tuple[str, str]] = set()
        for field, msg in deep_scan(content, "content_json"):
            key = (field, msg)
            if key in seen:
                continue
            seen.add(key)
            quality_issues.append(("casestudies", cs_name, cs_title, field, msg))
            warnings.append(f"[casestudies] {cs_title!r} / {field}: {msg}")

# 2. Validation completeness (from /validation/ endpoint)
_, validation = get("/validation/")

# 3. Route health
ROUTES = [
    ("/tools/", False),
    ("/tools/cdkdepict", False),
    ("/methods/", False),
    ("/methods/5_cfda_assay_to_determine_cytotoxicity", False),
    ("/regulatory-questions/", False),
    ("/stages/", False),
    ("/casestudies/", False),
    ("/casestudies/kidney", False),
    ("/compounds/Q2270", True),  # proxies Virtuoso
    ("/compounds/Q2270/properties", False),
    ("/compounds/Q2270/identifiers", False),
    ("/compounds/Q2270/toxicology", False),
    ("/compounds/Q2270/experimental-data", True),  # proxies BridgeDB
    ("/data/", True),  # proxies external sources
    ("/validation/", False),
    ("/validation/tools", False),
]

health: list[tuple[str, int, bool, bool]] = []
for path, external in ROUTES:
    status, _ = get(path)
    OK = 200 <= status < 300
    health.append((path, status, OK, external))
    if not OK and not external:
        errors.append(f"GET {path} -> {status}")

# 4. /data/ source stats (external: warnings only)
_DATA_KEY_FIELDS = ("title", "description", "authors", "doi", "license")
data_source_stats: list[dict] = []
data_hit_details: dict[str, list[dict]] = {}  # source -> list of per-hit dicts
_, data_resp = get("/data/")
if isinstance(data_resp, dict):
    for source in ("biostudies", "zenodo"):
        block = data_resp.get(source, {})
        hits = block.get("hits", [])
        error = block.get("error")
        field_stats = {
            f: sum(
                1 for h in hits if not h.get(f) or (isinstance(h[f], list) and not h[f])
            )
            for f in _DATA_KEY_FIELDS
        }
        data_source_stats.append(
            {
                "source": source,
                "total": block.get("total", 0),
                "returned": len(hits),
                "error": error,
                "field_stats": field_stats,
            }
        )
        if error:
            warnings.append(f"[data/{source}] error: {error}")

        # per-hit detail: id + which key fields are present
        hit_rows = []
        for h in hits:
            rec_id = h.get("id") or h.get("accession") or h.get("recid") or "?"
            present = {
                f: bool(h.get(f) and not (isinstance(h[f], list) and not h[f]))
                for f in _DATA_KEY_FIELDS
            }
            hit_rows.append({"id": rec_id, "present": present})
        data_hit_details[source] = hit_rows

        # quality-check each hit (HTML, placeholders, missing fields)
        entity_label = f"data/{source}"
        for h in hits:
            rec_id = h.get("id") or h.get("accession") or h.get("recid") or "?"
            rec_label = h.get("title") or rec_id
            for field, msg in DataHitChecker.check(h):
                quality_issues.append((entity_label, rec_id, rec_label, field, msg))
                warnings.append(f"[{entity_label}] {rec_label!r} / {field}: {msg}")


# build report

now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
lines = [f"## API check {now}", ""]

# counts (DB entities)
lines += ["### Entity counts", "", "| Entity | Count |", "|--------|------:|"]
for entity, n in counts.items():
    lines.append(f"| {entity} | {n if n is not None else 'ERR'} |")
# add data source totals
for s in data_source_stats:
    lines.append(f"| data/{s['source']} | {s['total']} |")
lines.append("")

# validation completeness
if validation and "entities" in validation:
    lines += [
        "### Validation (field completeness)",
        "",
        "| Entity | Entries | Avg complete | Full |",
        "|--------|--------:|-------------:|-----:|",
    ]
    for e in validation["entities"]:
        lines.append(
            f"| {e['entity']} | {e['total_entries']}"
            f" | {e['avg_completeness_pct']}%"
            f" | {e['fully_complete']}/{e['total_entries']} |"
        )
    lines.append("")

# content quality
lines += ["### Content quality TODOs", ""]

if quality_issues:
    lines += ["<details>"]
    lines += ["<summary>Show issues</summary>", ""]

    for entity, id, label, field, issue in quality_issues:
        safe_label = label.replace("|", "&#124;")
        display_entity = entity
        if entity == "tools":
            display_entity = "service"
        if entity.startswith("data/"):
            link = f"[{id}]({BASE}/data/{id})"
        else:
            link = f"[{id}](https://github.com/VHP4Safety/cloud/blob/main/docs/{display_entity}/{id}.json)"
        field_display = str(field)
        if "content_json" in field_display:
            field_display = field_display.split("content_json.")[1]
        lines.append(
            f"- [ ] **{entity}** {safe_label}: fix `{field_display}`: {issue} (_source: {link}_)"
        )

    lines += ["", "</details>"]
else:
    lines.append("_No content quality issues detected._")

lines.append("")

# data sources — aggregate + per-record breakdown
lines += ["### Data sources (BioStudies + Zenodo)", ""]
if data_source_stats:
    for s in data_source_stats:
        header = f"**{s['source']}**, {s['returned']} of {s['total']} returned"
        if s["error"]:
            header += f"  WARN `{s['error']}`"
        lines += [
            header,
            "",
            "| Field | Missing | Present |",
            "|-------|--------:|--------:|",
        ]
        ret = s["returned"]
        for f, missing in s["field_stats"].items():
            present = ret - missing
            flag = " WARN" if missing > 0 else ""
            lines.append(f"| `{f}` | {missing}{flag} | {present}/{ret} |")
        lines.append("")

        # per-record detail
        hit_rows = data_hit_details.get(s["source"], [])
        if hit_rows:
            col_headers = " | ".join(f"`{f}`" for f in _DATA_KEY_FIELDS)
            col_seps = " | ".join("---" for _ in _DATA_KEY_FIELDS)
            lines += [
                f"_Per-record ({s['source']}):_",
                "",
                f"| ID | {col_headers} |",
                f"|----|{col_seps}|",
            ]
            for row in hit_rows:
                cells = " | ".join(
                    "OK" if row["present"][f] else "FAIL" for f in _DATA_KEY_FIELDS
                )
                lines.append(f"| `{row['id']}` | {cells} |")
            lines.append("")
else:
    lines += ["_/data/ endpoint unavailable._", ""]

# route health
lines += ["### Route health", "", "| Route | Status |", "|-------|-------:|"]
for path, status, OK, external in health:
    if OK:
        mark = "OK"
    elif external:
        mark = f"WARN ({status}) external"
    else:
        mark = f"FAIL ({status})"
    lines.append(f"| `{path}` | {mark} |")
lines.append("")

# result
WARN_count = len(warnings)
result = "PASS" if not errors else "FAIL"
if WARN_count:
    result += f" ({WARN_count} content warning{'s' if WARN_count != 1 else ''})"
lines.append(f"**Result: {result}**")

print("\n".join(lines))
if errors:
    sys.exit(1)
