"""Resolve case-study content from the database step hierarchy.

Case study content JSON is seeded into the ``case_studies`` table from
the VHP4Safety/ui-casestudy-config GitHub repo at seed time.
The JSON has up to 6 nesting levels:
  step1Contents  → intro + regulatory questions
  step2Contents  → dict[question_key → nav with process-flow steps]
  step3Contents  → dict[q → dict[step → node]]
  step4Contents  → dict[q → dict[step → dict[substep → node]]]
  step5Contents  → dict[q → dict[...]]
  step6Contents  → dict[q → dict[...]]

Given a URL path like /casestudies/kidney/Q1/Kinetics we resolve the
node at step3Contents["Q1"]["Kinetics"] and render it server-side.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

from src.db import get_conn


# In-memory cache keyed by slug
_content_cache: dict[str, dict] = {}


def get_content(slug: str) -> dict | None:
    """Load case-study content JSON from the database (cached)."""
    if slug in _content_cache:
        return _content_cache[slug]

    conn = get_conn()
    row = conn.execute("SELECT content_json FROM case_studies WHERE slug = ?", (slug,)).fetchone()
    conn.close()
    if not row or not row["content_json"]:
        return None

    data = json.loads(row["content_json"])
    _content_cache[slug] = data
    return data


# ── Resolved result ──────────────────────────────────────────────────────

STEP_TYPE_COLORS = {
    "workflow step": "btn-vhpdarkteal",
    "workflow-step": "btn-vhpdarkteal",
    "workflow substep": "btn-vhplightteal",
    "workflow-substep": "btn-vhplightteal",
    "process flow step": "btn-vhpdarkpurple",
    "process-flow-step": "btn-vhpdarkpurple",
    "regulatory question": "btn-vhppink-distinct",
    "regulatory-question": "btn-vhppink-distinct",
    "tool": "btn-vhpblue",
}

# Workflow header definitions
WORKFLOW_STEPS = [
    {"number": 1, "type": "regulatory-question",
     "label": "Regulatory Question"},
    {"number": 2, "type": "workflow-step",
     "label": "Safety Assessment Workflow Step"},
    {"number": 3, "type": "process-flow-step",
     "label": "Case Study Step"},
    {"number": 4, "type": "workflow-substep",
     "label": "Case Study Substep"},
    {"number": 5, "type": "tool",
     "label": "Tools, Models and Data"},
]


def btn_color(step_type: str | None) -> str:
    """Return CSS class for a step button based on its type."""
    if not step_type:
        return "btn-vhpblue"
    return STEP_TYPE_COLORS.get(step_type, "btn-vhpblue")


@dataclass
class Breadcrumb:
    label: str
    url: str
    active: bool = False


@dataclass
class StepButtonResolved:
    """A button ready to render in Jinja."""
    label: str
    description: str = ""
    css_class: str = "btn-vhpblue"
    url: str = ""
    disabled: bool = False
    is_tool_link: bool = False


@dataclass
class ResolvedStep:
    """Everything the template needs to render one case-study page."""
    case_slug: str = ""
    case_title: str = ""
    step_number: int = 1
    nav_title: str = ""
    nav_description: str = ""
    image_html: str = ""
    buttons: list[StepButtonResolved] = field(default_factory=list)
    accordion_sections: list[dict] = field(default_factory=list)
    content_html: str = ""
    breadcrumbs: list[Breadcrumb] = field(default_factory=list)
    workflow_steps: list[dict] = field(default_factory=list)
    path_parts: list[str] = field(default_factory=list)


def _slugify(value: str) -> str:
    """Convert space-separated label to URL-safe slug."""
    return value.replace(" ", "_")


def _unslugify(value: str) -> str:
    """Convert URL slug back to the key used in JSON."""
    return value.replace("_", " ")


def _make_url(case: str, parts: list[str]) -> str:
    """Build an absolute URL from case slug and path parts."""
    base = f"/casestudies/{case}"
    if parts:
        return base + "/" + "/".join(_slugify(p) for p in parts)
    return base


def _parse_content(raw: Any) -> tuple[str, list[dict]]:
    """Split content into HTML string and accordion sections list."""
    if raw is None:
        return "", []
    if isinstance(raw, str):
        return raw, []
    if isinstance(raw, list):
        sections = []
        for item in raw:
            if isinstance(item, dict):
                sections.append(item)
        return "", sections
    return str(raw), []


def resolve(
    slug: str,
    path_parts: list[str],
    branch: str = "main",
) -> Optional[ResolvedStep]:
    """Resolve a URL path to the correct step content.

    Parameters
    ----------
    slug : str
        Case study slug (kidney, parkinson, thyroid).
    path_parts : list[str]
        Path segments after /casestudies/<slug>/ — e.g.
        ["Q1", "Kinetics"] for step 3.

    Returns
    -------
    ResolvedStep or None if the path doesn't resolve.
    """
    data = get_content(slug)
    if data is None:
        return None

    step1 = data.get("step1Contents", {})
    case_title = step1.get("navTitle", slug.title() + " Case Study")

    result = ResolvedStep(
        case_slug=slug,
        case_title=case_title,
        path_parts=list(path_parts),
    )

    # Build workflow header state
    active_step = len(path_parts) + 1
    result.step_number = active_step
    for ws in WORKFLOW_STEPS:
        state = "completed" if ws["number"] < active_step \
            else "active" if ws["number"] == active_step \
            else ""
        result.workflow_steps.append({**ws, "state": state})

    # ── Step 1: no path parts ─────────────────────────────────────
    if not path_parts:
        result.nav_title = step1.get("navTitle", "")
        result.nav_description = step1.get("navDescription", "")
        html, sections = _parse_content(step1.get("content"))
        result.content_html = html
        result.accordion_sections = sections
        # Buttons = regulatory questions
        for q in step1.get("questions", []):
            result.buttons.append(StepButtonResolved(
                label=q.get("label", ""),
                description=q.get("description", ""),
                css_class=btn_color(
                    q.get("type", "regulatory-question")
                ),
                url=_make_url(slug, [q["value"]]),
                disabled=q.get("state") == "disabled",
            ))
        result.breadcrumbs = [
            Breadcrumb("Case Studies", "/casestudies"),
            Breadcrumb(case_title, "", active=True),
        ]
        return result

    # ── Step 2+: walk the nested dicts ────────────────────────────
    # path_parts[0] is the question key (e.g. "Q1")
    # path_parts[1] is the step2 choice (e.g. "Kinetics")
    # etc.
    depth = len(path_parts)
    step_key = f"step{depth + 1}Contents"

    # Navigate to the correct node
    container = data.get(step_key, {})
    node = container
    for i, part in enumerate(path_parts):
        key = _unslugify(part)
        if isinstance(node, dict) and key in node:
            node = node[key]
        else:
            # Try original (slugified) key as fallback
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return None

    if not isinstance(node, dict):
        return None

    # Extract node fields
    result.nav_title = node.get("navTitle", "")
    result.nav_description = node.get("navDescription", "")
    result.image_html = node.get("image", "")
    html, sections = _parse_content(node.get("content"))
    result.content_html = html
    result.accordion_sections = sections

    # Determine next-step buttons
    base_url_parts = list(path_parts)

    if node.get("steps"):
        for s in node["steps"]:
            val = s.get("value", s.get("label", ""))
            result.buttons.append(StepButtonResolved(
                label=s.get("label", ""),
                description=s.get("description", ""),
                css_class=btn_color(s.get("type")),
                url=_make_url(slug, base_url_parts + [val]),
                disabled=s.get("state") == "disabled",
            ))
    elif node.get("tools"):
        for t in node["tools"]:
            tool_id = t.get("id")
            route = t.get("route", "tools")
            if tool_id:
                url = f"/{route}/{tool_id}"
                is_tool = True
            else:
                url = ""
                is_tool = False
            result.buttons.append(StepButtonResolved(
                label=t.get("label", ""),
                description=t.get("description", ""),
                css_class=btn_color(t.get("type", "tool")),
                url=url,
                disabled=t.get("state") == "disabled",
                is_tool_link=is_tool,
            ))

    # Breadcrumbs
    crumbs = [Breadcrumb("Case Studies", "/casestudies")]
    crumbs.append(Breadcrumb(
        case_title, _make_url(slug, []),
    ))

    # Build intermediate crumbs
    # Step 2 label = "Regulatory Question <Q>"
    for i, part in enumerate(path_parts):
        is_last = (i == len(path_parts) - 1)
        label = _unslugify(part)
        if i == 0:
            label = f"Regulatory Question {label}"
        url = _make_url(slug, path_parts[: i + 1])
        crumbs.append(Breadcrumb(
            label, url, active=is_last,
        ))

    result.breadcrumbs = crumbs
    return result
