"""LLM provider abstraction (spec §47).

Supports three providers behind one interface:
  - ``mock``   : deterministic, offline, rule-based responses (default —
                 keeps the whole platform runnable without any API key)
  - ``openai`` : any OpenAI-compatible Chat Completions endpoint
  - ``ollama`` : local Ollama instance

Business logic never talks to a provider directly — it uses ``LLMClient``.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from ai.models.config import LLMConfig

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
    pass


class LLMClient:
    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig.from_env()

    # ------------------------------------------------------------------
    @property
    def provider(self) -> str:
        return self.config.provider

    def complete(
        self,
        system: str,
        user: str,
        *,
        json_mode: bool = True,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Run one completion and return the raw text (JSON when json_mode)."""
        if self.config.provider == "mock":
            return self._mock_complete(system, user, json_mode)
        if self.config.provider == "ollama":
            return self._ollama_complete(system, user, json_mode, temperature, max_tokens)
        if self.config.provider == "openai":
            return self._openai_complete(system, user, json_mode, temperature, max_tokens)
        raise LLMError(f"Unknown LLM provider: {self.config.provider}")

    def complete_json(self, system: str, user: str, **kw: Any) -> dict:
        """Completion parsed as JSON; raises LLMError on parse failure."""
        raw = self.complete(system, user, json_mode=True, **kw)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LLMError(f"LLM returned non-JSON output: {raw[:200]}") from exc
        if not isinstance(data, dict):
            raise LLMError(f"LLM returned non-object JSON: {type(data).__name__}")
        return data

    def health(self) -> dict:
        if self.config.provider == "mock":
            return {"ok": True, "provider": "mock", "detail": "offline rule-based mode"}
        try:
            if self.config.provider == "ollama":
                r = httpx.get(f"{self.config.base_url}/api/tags", timeout=5)
            else:
                r = httpx.get(f"{self.config.base_url}/models", timeout=5,
                              headers=self.config.headers)
            return {"ok": r.status_code < 500, "provider": self.config.provider,
                    "status_code": r.status_code}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "provider": self.config.provider, "error": str(exc)}

    # ------------------------------------------------------------------
    def _openai_complete(self, system, user, json_mode, temperature, max_tokens) -> str:
        url = f"{self.config.base_url}/chat/completions"
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature if temperature is not None else self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        try:
            r = httpx.post(url, json=payload, headers=self.config.headers,
                           timeout=self.config.timeout)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError) as exc:
            raise LLMError(f"OpenAI-compatible request failed: {exc}") from exc

    def _ollama_complete(self, system, user, json_mode, temperature, max_tokens) -> str:
        url = f"{self.config.base_url}/api/chat"
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {
                "temperature": temperature if temperature is not None else self.config.temperature,
                "num_predict": max_tokens or self.config.max_tokens,
            },
        }
        if json_mode:
            payload["format"] = "json"
        try:
            r = httpx.post(url, json=payload, timeout=self.config.timeout)
            r.raise_for_status()
            return r.json()["message"]["content"]
        except (httpx.HTTPError, KeyError) as exc:
            raise LLMError(f"Ollama request failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Deterministic mock — mirrors the JSON contracts of the real agents
    # ------------------------------------------------------------------
    def _mock_complete(self, system: str, user: str, json_mode: bool) -> str:
        if json_mode:
            return json.dumps(self._mock_respond(system, user), ensure_ascii=False)
        return self._mock_respond(system, user).get("text", "")

    def _mock_respond(self, system: str, user: str) -> dict:
        # Agent identity marker (see ai/agents/*_agent.py) — explicit dispatch
        if "AGENT: triage" in user:
            return self._mock_triage(user)
        if "AGENT: threat" in user:
            return self._mock_threat(user)
        if "AGENT: vuln" in user:
            return self._mock_vuln(user)
        if "AGENT: report" in user:
            return self._mock_report(user)
        return {"classification": "unknown", "reasoning_summary": "mock provider: no specialized handler"}

    def _mock_triage(self, user: str) -> dict:
        low_user = user.lower()
        has_ioc = '"threat_intel": [{"' in user and "confidence" in user
        severities = [s for s in ("critical", "high", "medium", "low", "info") if f'"severity": "{s}"' in user]
        sev = severities[0] if severities else "medium"
        high_risk = sev in ("critical", "high")
        classification = "true_positive" if (high_risk or has_ioc) else "likely_false_positive"
        confidence = 0.9 if (high_risk and has_ioc) else (0.75 if high_risk or has_ioc else 0.5)
        techniques: list[str] = []
        for t in ("T1059.001", "T1190", "T1078", "T1021", "T1566", "T1133"):
            if t in user:
                techniques.append(t)
        if not techniques:
            techniques = ["T1059.001"] if "execution" in user or "powershell" in low_user.lower() else []
        evidence_ids = []
        for eid in ("E001", "E002", "E003", "E004", "E005"):
            if eid in user:
                evidence_ids.append(eid)
        return {
            "classification": classification,
            "severity": sev,
            "confidence": confidence,
            "attack_stage": "execution" if techniques else None,
            "mitre_techniques": techniques,
            "evidence_ids": evidence_ids,
            "reasoning_summary": (
                f"Mock triage: severity={sev}, ioc_hit={has_ioc}; "
                "rule-based classification (configure LLM_PROVIDER for LLM analysis)."
            ),
            "recommendations": [
                "collect_process_tree",
                "review_related_events",
                "block_src_ip" if has_ioc else "monitor_src_ip",
            ],
        }

    def _mock_threat(self, user: str) -> dict:
        malicious = "malicious" in user.lower() or "ioc" in user.lower()
        return {
            "malicious": malicious,
            "confidence": 0.89 if malicious else 0.3,
            "tags": ["mock"] if malicious else [],
            "related_entities": [],
            "evidence_ids": [],
        }

    def _mock_vuln(self, user: str) -> dict:
        return {
            "authenticity": "confirmed",
            "remediation_priority": "high" if "high" in user else "medium",
            "impact_scope": ["affected_asset"],
            "exploit_risk": 0.6,
            "evidence_ids": [],
            "reasoning_summary": "Mock vulnerability assessment (rule-based).",
        }

    def _mock_report(self, user: str) -> dict:
        return {
            "summary": "Mock 报告摘要：事件已完成 AI 研判，详见风险与建议章节。",
            "timeline_narrative": "事件由关联引擎自动生成，时间线见报告第 2 节。",
            "recommendations": ["按处置建议执行", "复查证据链完整性"],
            "evidence_ids": [],
        }
