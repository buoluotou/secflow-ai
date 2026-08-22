"""Nuclei output models (JSONL line shape of `nuclei -jsonl`)."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class NucleiInfo(BaseModel):
    name: str = ""
    author: list[str] = []
    severity: str = "medium"
    description: str = ""
    classification: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = []
    remediation: str = ""


class NucleiMatcher(BaseModel):
    name: str = ""
    status: bool = False
    matched: str = ""


class NucleiResult(BaseModel):
    template_id: str = ""
    info: NucleiInfo = Field(default_factory=NucleiInfo)
    matched_at: str = ""
    type: str = "http"
    host: str = ""
    ip: str = ""
    port: str = ""
    scheme: str = ""
    request: str = ""
    response: str = ""
    matcher_status: bool = False
    extracted_results: list[str] = []
    timestamp: str = ""
    curl_command: str = ""

    @property
    def cwe(self) -> str | None:
        return (self.info.classification or {}).get("cwe-id", [""])[0] if self.info.classification.get("cwe-id") else None

    @property
    def cvss(self) -> float | None:
        try:
            val = (self.info.classification or {}).get("cvss-metrics") or {}
            return float((self.info.classification or {}).get("cvss-score", 0) or 0) or None
        except (TypeError, ValueError):
            return None
