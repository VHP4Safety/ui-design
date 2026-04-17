#!/usr/bin/env python3
"""API check: counts, validation summary, and route health."""

import json
import sys
import urllib.request
from datetime import datetime, timezone

BASE = "http://localhost:5050/api"


def get(path):
    url = f"{BASE}{path}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return 0, None


errors = []

# 1. Entity counts
ENTITIES = {
    "Tools":                "/tools/",
    "Methods":              "/methods/",
    "Case studies":         "/casestudies/",
    "Regulatory questions": "/regulatory-questions/",
    "Stage explanations":   "/stages/",
}

counts = {}
for label, path in ENTITIES.items():
    status, data = get(path)
    if status == 200 and isinstance(data, list):
        counts[label] = len(data)
    else:
        counts[label] = None
        errors.append(f"GET {path} -> {status}")

# 2. Validation summary
status, validation = get("/validation/")
if status != 200:
    errors.append(f"GET /validation/ -> {status}")
    validation = None

# 3. Health check every route
ROUTES = [
    ("GET", "/tools/"),
    ("GET", "/tools/cdkdepict"),
    ("GET", "/methods/"),
    ("GET", "/methods/5_cfda_assay_to_determine_cytotoxicity"),
    ("GET", "/regulatory-questions/"),
    ("GET", "/stages/"),
    ("GET", "/casestudies/"),
    ("GET", "/casestudies/kidney"),
    ("GET", "/compounds/Q2270"),
    ("GET", "/compounds/Q2270/properties"),
    ("GET", "/compounds/Q2270/identifiers"),
    ("GET", "/compounds/Q2270/toxicology"),
    ("GET", "/compounds/Q2270/experimental-data"),
    ("GET", "/data/"),
    ("GET", "/validation/"),
    ("GET", "/validation/tools"),
]

health = []
for method, path in ROUTES:
    status, _ = get(path)
    ok = 200 <= status < 300
    health.append((method, path, status, ok))
    if not ok:
        errors.append(f"{method} {path} -> {status}")

# ── build report ──────────────────────────────────────────────────

now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
lines = [f"## API check -- {now}", ""]

# counts
lines.append("### Entity counts")
lines.append("")
lines.append("| Entity | Count |")
lines.append("|--------|------:|")
for label, n in counts.items():
    lines.append(f"| {label} | {n if n is not None else 'ERR'} |")
lines.append("")

# validation
if validation and "entities" in validation:
    lines.append("### Validation (field completeness)")
    lines.append("")
    lines.append("| Entity | Entries | Avg complete | Full |")
    lines.append("|--------|--------:|-------------:|-----:|")
    for e in validation["entities"]:
        lines.append(
            f"| {e['entity']} | {e['total_entries']}"
            f" | {e['avg_completeness_pct']}%"
            f" | {e['fully_complete']}/{e['total_entries']} |"
        )
    lines.append("")

# health
lines.append("### Route health")
lines.append("")
lines.append("| Method | Route | Status |")
lines.append("|--------|-------|-------:|")
for method, path, status, ok in health:
    mark = "ok" if ok else f"FAIL ({status})"
    lines.append(f"| {method} | `{path}` | {mark} |")
lines.append("")

# result
all_ok = not errors
lines.append(f"**Result: {'PASS' if all_ok else 'FAIL'}**")

print("\n".join(lines))
if not all_ok:
    sys.exit(1)
