"""Pydantic models for VHP4Safety case-study content JSON schemas.

The JSON files originate from a separate GitHub repo
(VHP4Safety/ui-casestudy-config) and are fetched once during database
seeding (``python -m src.seed``).  The full JSON blob is stored in
the ``case_studies.content_json`` column and resolved server-side
by ``src.casestudy_resolver`` into rendered Jinja templates.

These models formalise the structure so it can be validated
server-side, used in tests, and consumed by type-aware code.

Hierarchy (up to 6 levels deep):
  CaseStudyContent          ← root of one *_content.json file
    └ Step1Contents          ← intro + regulatory-question buttons
    └ step2Contents          ← dict[question_key → ProcessFlowNav]
    └ step3Contents          ← dict[question_key → dict[step_label → WorkflowStepNode]]
    └ step4–6Contents        ← additional nesting (same WorkflowStepNode shape)

Every "node" at step ≥ 2 follows the same recursive pattern captured
by ``WorkflowStepNode``.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# Enums


class StepType(str, Enum):
    """Button colour / role categories used by the JS renderer."""

    WORKFLOW_STEP = "workflow step"
    WORKFLOW_SUBSTEP = "workflow substep"
    PROCESS_FLOW_STEP = "process flow step"
    REGULATORY_QUESTION = "regulatory question"
    TOOL = "tool"


class CaseStudySlug(str, Enum):
    """Known case-study URL slugs."""

    KIDNEY = "kidney"
    PARKINSON = "parkinson"
    THYROID = "thyroid"


# Leaf / reusable pieces


class StepButton(BaseModel):
    """A single clickable button shown in a step panel.

    Appears in ``questions``, ``steps``, and ``tools`` arrays.
    """

    label: str
    value: Optional[str] = None
    description: Optional[str] = None
    type: Optional[StepType] = None
    state: Optional[str] = None  # e.g. "disabled"

    # tool-specific fields
    id: Optional[str] = None
    route: Optional[str] = None  # e.g. "tools" or "methods"

    model_config = {"extra": "allow"}


class AccordionSection(BaseModel):
    """One collapsible section inside ``content`` when it is an array."""

    section: Optional[str] = None
    description: Optional[str] = None

    model_config = {"extra": "allow"}


# Content can be a raw HTML string **or** a list of accordion sections.
# We keep it as ``Any`` so both shapes validate; downstream code already
# branches on ``Array.isArray(content)`` in JS.
ContentBlock = str | list[AccordionSection] | None


# Step 1 (intro + regulatory questions)


class Step1Contents(BaseModel):
    """Top-level intro panel for a case study.

    Shown on first load; contains the two regulatory-question buttons.
    """

    navTitle: str
    navDescription: str = ""
    questions: list[StepButton] = Field(default_factory=list)
    content: Any = None  # HTML string or accordion list

    model_config = {"extra": "allow"}


# Generic workflow node (steps 2–6)


class WorkflowStepNode(BaseModel):
    """A single node at any depth in the step hierarchy.

    Depending on what keys are present the JS renderer shows:
    * ``steps``  → navigable sub-step buttons (goes deeper)
    * ``tools``  → tool buttons (leaf, may link to /tools/<id>)
    * neither    → plain content panel

    Nodes may contain ``content`` as HTML **or** accordion JSON.
    ``image`` is an optional raw HTML string (e.g. an <img> tag).
    """

    navTitle: Optional[str] = None
    navDescription: Optional[str] = None
    steps: Optional[list[StepButton]] = None
    tools: Optional[list[StepButton]] = None
    content: Any = None
    image: Optional[str] = None

    # Some step-3 entries carry a flag to signal step-4 exists
    step4content: Optional[str] = None

    model_config = {"extra": "allow"}


class ProcessFlowNav(BaseModel):
    """Step-2 panel: safety-assessment workflow steps for one question.

    Keys ``steps`` list the process-flow buttons; ``content`` is the
    intro HTML.
    """

    navTitle: str = ""
    navDescription: str = ""
    steps: list[StepButton] = Field(default_factory=list)
    content: Any = None
    image: Optional[str] = None

    model_config = {"extra": "allow"}


# Root document

# Steps 3-6 are nested dicts whose keys are dynamic (question key,
# step label, sub-step label …).  We type them as deeply as
# practical; the innermost values are always WorkflowStepNode.

Step3Map = dict[str, dict[str, WorkflowStepNode]]
Step4Map = dict[str, dict[str, dict[str, WorkflowStepNode]]]
Step5Map = dict[str, dict[str, dict[str, dict[str, WorkflowStepNode]]]]
Step6Map = dict[str, dict[str, dict[str, dict[str, dict[str, WorkflowStepNode]]]]]


class CaseStudyContent(BaseModel):
    """Root schema for a ``<case>_content.json`` file.

    Mirrors exactly the shape consumed by ``casestudies.js``.
    """

    step1Contents: Step1Contents
    step2Contents: dict[str, ProcessFlowNav] = Field(default_factory=dict)
    step3Contents: Optional[Step3Map] = None
    step4Contents: Optional[Step4Map] = None
    step5Contents: Optional[Step5Map] = None
    step6Contents: Optional[Step6Map] = None

    model_config = {"extra": "allow"}


# Case study card (listing page)


class CaseStudyCard(BaseModel):
    """Metadata for one card on the /casestudies listing page."""

    slug: CaseStudySlug
    title: str
    description: str
    image_src: str = ""
    image_alt: str = ""
    url: str = ""
    config_repo: Optional[str] = None
    content_json: Optional[str] = None


# Convenience: full registry


class CaseStudyRegistry(BaseModel):
    """All known case studies with their summary cards and loaded content."""

    cards: list[CaseStudyCard] = Field(default_factory=list)
    content: dict[CaseStudySlug, CaseStudyContent] = Field(
        default_factory=dict,
    )

    model_config = {"extra": "allow"}
