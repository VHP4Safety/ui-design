"""Pydantic models for VHP4Safety Cloud method JSON schemas."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ServiceContact(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None


class ServiceProvider(BaseModel):
    contact: Optional[ServiceContact] = None
    url: Optional[str] = None
    name: Optional[str] = None


class ServiceInstance(BaseModel):
    type: Optional[str] = None
    url: Optional[str] = None
    license: Optional[str] = None
    version: Optional[str] = None
    source: Optional[str] = None
    vhp_platform: Optional[str] = Field(None, alias="vhp-platform")

    model_config = {"populate_by_name": True, "extra": "allow"}


class ServiceAccess(BaseModel):
    API: Optional[str] = None
    login: Optional[str] = None

    model_config = {"extra": "allow"}


class ServiceIntro(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None


class RegulatoryQuestion(BaseModel):
    q1a: Optional[str] = Field(None, alias="1a")
    q1b: Optional[str] = Field(None, alias="1b")
    q2a: Optional[str] = Field(None, alias="2a")
    q2b: Optional[str] = Field(None, alias="2b")
    q3a: Optional[str] = Field(None, alias="3a")
    q3b: Optional[str] = Field(None, alias="3b")

    model_config = {"populate_by_name": True}


class Service(BaseModel):
    """A single service entry (docs/service/*.json)."""

    id: str
    service: str = Field(description="Service display name")
    description: Optional[str] = None

    stage: Optional[str] = None
    substage: Optional[str] = None
    screenshot: Optional[str] = None
    url: Optional[str] = None

    instance: Optional[ServiceInstance] = None
    intro: Optional[ServiceIntro] = None
    provider: Optional[ServiceProvider] = None
    access: Optional[ServiceAccess] = None
    regulatory_question: Optional[RegulatoryQuestion] = Field(
        None, alias="regulatory-question"
    )
    ELIXIR: Optional[dict] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class ServiceIndexEntry(BaseModel):
    """A service as represented in the index (cap/service_index.json)."""

    id: str
    service: str
    description: Optional[str] = None

    html_name: Optional[str] = None
    md_file_name: Optional[str] = None
    png_file_name: Optional[str] = None
    stage: Optional[str] = None
    main_url: Optional[str] = None
    inst_url: Optional[str] = None

    # Regulatory question flags (stored as 0/1 in DB)
    reg_q_1a: Optional[bool] = None
    reg_q_1b: Optional[bool] = None
    reg_q_2a: Optional[bool] = None
    reg_q_2b: Optional[bool] = None
    reg_q_3a: Optional[bool] = None
    reg_q_3b: Optional[bool] = None

    # Upstream issue-template fields (new-tool-service-entry.yml)
    login: Optional[str] = None
    api_type: Optional[str] = Field(None, alias="api")
    casestudy: Optional[str] = None
    provider: Optional[str] = None
    provider_email: Optional[str] = Field(None, alias="provider-email")
    citation: Optional[str] = None
    version: Optional[str] = None
    license: Optional[str] = None
    sourcecode: Optional[str] = None
    docker: Optional[str] = None
    bio_tools: Optional[str] = Field(None, alias="bioTools")
    tess: Optional[str] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class ServiceIndex(BaseModel):
    """The full service index (cap/service_index.json).

    A mapping of service id → ServiceIndexEntry.
    """

    root: dict[str, ServiceIndexEntry] = Field(default_factory=dict)

    model_config = {"extra": "allow"}

    @classmethod
    def from_dict(cls, data: dict) -> ServiceIndex:
        return cls(
            root={k: ServiceIndexEntry.model_validate(v) for k, v in data.items()}
        )
