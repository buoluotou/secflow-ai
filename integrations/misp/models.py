"""MISP API models — the subset of MISP objects SecFlow consumes."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MISPAttribute(BaseModel):
    id: str = ""
    uuid: str = ""
    type: str = ""  # ip-src | ip-dst | domain | url | md5 | sha1 | sha256 | email ...
    value: str = ""
    category: str = ""
    comment: str = ""
    to_ids: bool = False
    timestamp: str = ""
    event_id: str = ""


class MISPEvent(BaseModel):
    id: str = ""
    uuid: str = ""
    info: str = ""
    threat_level_id: str = "2"
    analysis: str = "0"
    timestamp: str = ""
    published: bool = False
    tags: list[dict[str, Any]] = Field(default_factory=list)
    Attribute: list[MISPAttribute] = Field(default_factory=list)


class MISPResponse(BaseModel):
    response: list[dict[str, Any]] = Field(default_factory=list)
