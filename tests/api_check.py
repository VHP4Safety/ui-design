#!/usr/bin/env python3
"""API check: counts, validation summary, and route health."""

import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone


def _port_from_dockerfile(dockerfile_path: str) -> str:
    """Read the first EXPOSE port from the Dockerfile next to this repo."""
    try:
        with open(dockerfile_path) as f:
            for line in f:
                m = re.match(r"^\s*EXPOSE\s+(\d+)", line)
                if m:
                    return m.group(1)
    except OSError:
        pass
    return "5050"


def _container_ip(container_name: str) -> str | None:
    """Return the bridge IP of a running container, or None."""
    try:
        out = subprocess.check_output(
            [
                "docker", "inspect",
                "--format", "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
                container_name,
            ],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return out if out else None
    except Exception:
        return None


# ── resolve BASE URL ─────────────────────────────────────────────
# Priority:
#   1. VHP_BASE_URL env var (set manually or by CI)
#   2. Docker-inspect the container named in VHP_CONTAINER env var
#   3. localhost + port from Dockerfile EXPOSE

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCKERFILE = os.path.join(REPO_ROOT, "Dockerfile")
PORT = _port_from_dockerfile(DOCKERFILE)

if "VHP_BASE_URL" in os.environ:
    BASE = os.environ["VHP_BASE_URL"].rstrip("/")
else:
    container_name = os.environ.get("VHP_CONTAINER", "vhp4safety")
    ip = _container_ip(container_name)
    if ip:
        BASE = f"http://{ip}:{PORT}/api"
    else:
        BASE = f"http://localhost:{PORT}/api"

print(f"# Using BASE: {BASE}", file=sys.stderr)


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
# Routes marked external=True depend on outside services (Virtuoso, BridgeDB, etc.)
# and are reported as warnings only — they never affect PASS/FAIL.
ROUTES = [
    ("GET", "/tools/",                                          False),
    ("GET", "/tools/cdkdepict",                                 False),
    ("GET", "/methods/",                                        False),
    ("GET", "/methods/5_cfda_assay_to_determine_cytotoxicity",  False),
    ("GET", "/regulatory-questions/",                           False),
    ("GET", "/stages/",                                         False),
    ("GET", "/casestudies/",                                    False),
    ("GET", "/casestudies/kidney",                              False),
    ("GET", "/compounds/Q2270",                                 True),   # proxies external source
    ("GET", "/compounds/Q2270/properties",                      False),
    ("GET", "/compounds/Q2270/identifiers",                     False),
    ("GET", "/compounds/Q2270/toxicology",                      False),
    ("GET", "/compounds/Q2270/experimental-data",               True),   # proxies external source
    ("GET", "/data/",                                           True),   # proxies external sources
    ("GET", "/validation/",                                     False),
    ("GET", "/validation/tools",                                False),
]

health = []
for method, path, external in ROUTES:
    status, _ = get(path)
    ok = 200 <= status < 300
    health.append((method, path, status, ok, external))
    if not ok and not external:
        errors.append(f"{method} {path} -> {status}")

# build report
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
for method, path, status, ok, external in health:
    if ok:
        mark = "ok"
    elif external:
        mark = f"warn ({status}) ⚠️ external service"
    else:
        mark = f"FAIL ({status})"
    lines.append(f"| {method} | `{path}` | {mark} |")
lines.append("")

# result
all_ok = not errors
lines.append(f"**Result: {'PASS' if all_ok else 'FAIL'}**")

print("\n".join(lines))
if not all_ok:
    sys.exit(1)
