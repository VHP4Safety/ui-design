"""Quality checkers for API responses, used only in tests.

Each checker validates a response dict through the corresponding
Pydantic model (structural validation) and then applies domain rules
on the resulting object (content quality).

Usage:
    issues = ToolChecker.check(entry_dict)
    # returns list[tuple[field, message]]; empty means all good
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ValidationError

from src.models.casestudy import CaseStudyCard
from src.models.cloud.method import ServiceIndexEntry  # tool
from src.models.cloud.tool import Method
from src.models.platform import RegulatoryQuestion, StageExplanation

# shared constants

_STAGE_URI_PREFIX = "https://vhp4safety.github.io/glossary#"
_NO_URL = "no_url"
_FALLBACK_LOGO = "github.com/VHP4Safety/ui-design"

_PLACEHOLDER_RE = re.compile(
    r"\{\{.*?\}\}"
    r"|\[.*?(todo|tbd|laceholder|fixme|lacehholder|Input and resulting output).*?\]"
    r"|\btodo\b|\btbd\b|\bfixme\b|\blacehholder\b|\bInput and resulting output\b",
    re.IGNORECASE,
)
_HTML_RE = re.compile(r"<[a-zA-Z][^>]*>|&[a-z]+;", re.IGNORECASE)


def deep_scan(obj: Any, path: str = "") -> list[tuple[str, str]]:
    """Recursively walk any dict/list/str and return (path, issue) pairs for
    placeholder text or raw HTML found anywhere in the structure."""
    issues: list[tuple[str, str]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            child = f"{path}.{k}" if path else k
            issues += deep_scan(v, child)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            issues += deep_scan(v, f"{path}[{i}]")
    elif isinstance(obj, str) and obj:
        if _PLACEHOLDER_RE.search(obj):
            issues.append((path, "placeholder text"))
        if _HTML_RE.search(obj):
            issues.append((path, "raw HTML / entities"))
    return issues


# base helper


def _text_issues(model: BaseModel) -> list[tuple[str, str]]:
    """Scan all string fields of a validated Pydantic object for placeholder
    text and raw HTML that should never appear in production data."""
    issues = []
    for fname in model.model_fields:
        val = getattr(model, fname, None)
        if not isinstance(val, str) or not val:
            continue
        if _PLACEHOLDER_RE.search(val):
            issues.append((fname, "placeholder text"))
        if _HTML_RE.search(val):
            issues.append((fname, "raw HTML / entities"))
    return issues


def _structural_issues(model_cls: type[BaseModel], data: dict) -> list[tuple[str, str]]:
    """Run Pydantic structural validation; return (field, message) pairs."""
    try:
        model_cls.model_validate(data)
        return []
    except ValidationError as e:
        return [
            (".".join(str(line) for line in err["loc"]) or "model", err["msg"])
            for err in e.errors()
        ]


# per-entity checkers


class ToolChecker:
    model = ServiceIndexEntry

    @classmethod
    def check(cls, data: dict) -> list[tuple[str, str]]:
        issues = _structural_issues(cls.model, data)

        obj = None
        try:
            obj = cls.model.model_validate(data)
        except Exception as e:
            issues.append(("__validation__", str(e)))

        if obj:
            issues += _text_issues(obj)

            if obj.stage and not obj.stage.startswith(_STAGE_URI_PREFIX):
                issues.append(("stage", f"not a glossary URI (got {obj.stage!r})"))

            for field in ("main_url", "inst_url"):
                if getattr(obj, field) == _NO_URL:
                    issues.append((field, "URL not yet set"))

            if obj.png_file_name and _FALLBACK_LOGO in obj.png_file_name:
                issues.append(("png_file_name", "fallback logo placeholder"))
        else:
            # fallback checks on raw data
            if data.get("stage") and not str(data.get("stage")).startswith(
                _STAGE_URI_PREFIX
            ):
                issues.append(
                    ("stage", f"not a glossary URI (got {data.get('stage')!r})")
                )

            for field in ("main_url", "inst_url"):
                if data.get(field) == _NO_URL:
                    issues.append((field, "URL not yet set"))

            if data.get("png_file_name") and _FALLBACK_LOGO in str(
                data.get("png_file_name")
            ):
                issues.append(("png_file_name", "fallback logo placeholder"))

        return issues


class MethodChecker:
    model = Method

    @classmethod
    def check(cls, data: dict) -> list[tuple[str, str]]:
        issues = _structural_issues(cls.model, data)

        obj = None
        try:
            obj = cls.model.model_validate(data)
        except Exception as e:
            issues.append(("__validation__", str(e)))

        if obj:
            issues += _text_issues(obj)

            if obj.catalog_webpage_url == _NO_URL:
                issues.append(("catalog_webpage_url", "URL not yet set"))
            if not obj.https or "http" not in obj.https:
                issues.append(("https", "URL not yet set"))
            if not obj.sop:
                issues.append(("sop", "No SOP yet"))
            if not obj.regulatory_question:
                issues.append(("regulatory_question", "No regulatory question yet"))
            if not obj.ontology or "http" not in obj.ontology:
                issues.append(("ontology", "No ontology term yet set"))
        else:
            # fallback checks on raw data
            if data.get("catalog_webpage_url") == _NO_URL:
                issues.append(("catalog_webpage_url", "URL not yet set"))
            if not data.get("https") or "http" not in str(data.get("https")):
                issues.append(("https", "URL not yet set"))
            if not data.get("sop"):
                issues.append(("sop", "No SOP yet"))
            if not data.get("regulatory_question"):
                issues.append(("regulatory_question", "No regulatory question yet"))
            if not data.get("ontology") or "http" not in str(data.get("ontology")):
                issues.append(("ontology", "No ontology term yet set"))

        return issues


class RegulatoryQuestionChecker:
    model = RegulatoryQuestion

    @classmethod
    def check(cls, data: dict) -> list[tuple[str, str]]:
        issues = _structural_issues(cls.model, data)

        obj = None
        try:
            obj = cls.model.model_validate(data)
        except Exception as e:
            issues.append(("__validation__", str(e)))

        if obj:
            issues += _text_issues(obj)

        return issues


class StageExplanationChecker:
    model = StageExplanation

    @classmethod
    def check(cls, data: dict) -> list[tuple[str, str]]:
        issues = _structural_issues(cls.model, data)

        obj = None
        try:
            obj = cls.model.model_validate(data)
        except Exception as e:
            issues.append(("__validation__", str(e)))

        if obj:
            issues += _text_issues(obj)

        return issues


class CaseStudyChecker:
    model = CaseStudyCard

    @classmethod
    def check(cls, data: dict) -> list[tuple[str, str]]:
        # normalize API mismatch
        coerced = {**data, "content_json": None}
        if "name" in coerced and "slug" not in coerced:
            coerced["slug"] = coerced.pop("name")

        issues = _structural_issues(cls.model, coerced)

        obj = None
        try:
            obj = cls.model.model_validate(coerced)
        except Exception as e:
            issues.append(("__validation__", str(e)))

        if obj:
            issues += _text_issues(obj)

        return issues


class DataHitChecker:
    """Recursively scans a normalised data hit dict for null/empty fields."""

    # Fields that are genuinely optional — silence them
    _OPTIONAL = {
        "version",
        "conceptdoi",
        "conceptdoi_url",
        "funding",
        "publications",
        "files",
        "ReleaseDate",
    }

    @classmethod
    def _scan(cls, obj: Any, path: str, issues: list[tuple[str, str]]) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in cls._OPTIONAL:
                    continue
                child_path = f"{path}.{k}" if path else k
                if v is None or v == "" or v == []:
                    issues.append((child_path, "null / empty"))
                else:
                    cls._scan(v, child_path, issues)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                cls._scan(item, f"{path}[{i}]", issues)
        # scalar non-null: nothing to report

    @classmethod
    def check(cls, data: dict) -> list[tuple[str, str]]:
        issues: list[tuple[str, str]] = []
        cls._scan(data, "", issues)
        # additionally flag HTML in string fields
        for k, v in data.items():
            if isinstance(v, str) and _HTML_RE.search(v):
                issues.append((k, "raw HTML / entities"))
        return issues


# registry (used by the test runner)
# Maps API path to (checker, id_field, label_field)

ENTITY_CHECKS: dict[str, tuple[Any, str, str]] = {
    "/tools/": (ToolChecker, "id", "service"),
    "/methods/": (MethodChecker, "id", "method"),
    "/regulatory-questions/": (RegulatoryQuestionChecker, "key", "label"),
    "/stages/": (StageExplanationChecker, "name", "name"),
    "/casestudies/": (CaseStudyChecker, "name", "title"),
}
