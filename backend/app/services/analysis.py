"""Analysis service — orchestrates the AI pipeline (spec §34–§40).

Pipeline for one incident:
    Context Engine → Triage Agent → Threat Agent → Risk Engine → AIAnalysis row
                      ↘ Vulnerability Agent (when findings exist)
                      ↘ Report Agent (for report narratives)

Every agent output is JSON-schema validated and evidence-bound.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from ai.agents import AGENTS, create_agent
from ai.models.llm import LLMClient
from ai.reasoning.context import validate_context
from ai.reasoning.evidence import enrich_output_with_evidence, validate_evidence_binding
from app.models.analysis import AIAnalysis, RiskAssessment
from app.models.incident import AttackTechnique, Incident
from app.services.audit import log_audit
from app.services.context import ContextEngine
from risk.engine import RiskEngine

logger = logging.getLogger(__name__)


class AnalysisService:
    def __init__(self, db: Session):
        self.db = db
        self.llm = LLMClient()

    # ------------------------------------------------------------------
    def analyze_incident(self, incident: Incident, agents: list[str] | None = None,
                         force: bool = False) -> dict[str, Any]:
        ctx = validate_context(ContextEngine(self.db).for_incident(incident))
        requested = agents or list(AGENTS)
        results: dict[str, Any] = {}

        # Existing analyses (unless forced)
        existing = {
            a.agent_type: a
            for a in self.db.query(AIAnalysis).filter(
                AIAnalysis.incident_id == incident.id, AIAnalysis.status == "completed"
            )
        }

        triage_out = self._run_agent(existing, ctx, incident, "triage", force)
        if triage_out:
            results["triage"] = triage_out
            incident.ai_decision = triage_out.get("classification")
            incident.attack_stage = triage_out.get("attack_stage") or incident.attack_stage
            self._sync_techniques(incident, triage_out.get("mitre_techniques", []))

        if "threat" in requested:
            threat_out = self._run_agent(existing, ctx, incident, "threat", force)
            if threat_out:
                results["threat"] = threat_out
                ctx["ai_triage"] = {
                    **(ctx.get("ai_triage") or {}),
                    "threat_intel_malicious": threat_out.get("malicious", False),
                }

        if ctx.get("findings") and "vuln" in requested:
            vuln_out = self._run_agent(existing, ctx, incident, "vuln", force)
            if vuln_out:
                results["vuln"] = vuln_out
                ctx["ai_triage"] = {
                    **(ctx.get("ai_triage") or {}),
                    "exploit_evidence": vuln_out.get("exploit_risk", 0) >= 0.6,
                }

        if "report" in requested and incident.status in ("approved", "resolved", "closed"):
            report_out = self._run_agent(existing, ctx, incident, "report", force)
            if report_out:
                results["report"] = report_out

        # --- Risk Engine: AI analyses, deterministic score (spec §39) ---
        if triage_out:
            ctx["ai_triage"] = {
                **(ctx.get("ai_triage") or {}),
                "severity": triage_out.get("severity"),
                "confidence": triage_out.get("confidence"),
                "malicious": (results.get("threat") or {}).get("malicious", False),
                "exploit_evidence": (results.get("vuln") or {}).get("exploit_risk", 0) >= 0.6,
            }
            factors = RiskEngine().from_incident_context(ctx)
            score, level = RiskEngine().score(factors)
            assessment = RiskAssessment(
                incident_id=incident.id,
                risk_score=score,
                risk_level=level,
                factors={**factors.detail, "factors": {
                    "technical_severity": factors.technical_severity,
                    "asset_criticality": factors.asset_criticality,
                    "exposure": factors.exposure,
                    "threat_intel": factors.threat_intel,
                    "exploit": factors.exploit,
                    "confidence": factors.confidence,
                }},
            )
            self.db.add(assessment)
            self.db.flush()
            results["risk"] = {
                "risk_score": score,
                "risk_level": level,
                "factors": assessment.factors,
            }
            incident.severity = triage_out.get("severity", incident.severity)

        incident.confidence = float(
            (triage_out or {}).get("confidence", incident.confidence or 0.5)
        )
        if incident.status == "new":
            incident.status = "triaging"
        self.db.flush()
        log_audit(self.db, "ai.analyze", "incident", incident.id,
                  detail={"agents": list(results.keys())})
        return results

    # ------------------------------------------------------------------
    def _run_agent(self, existing: dict, ctx: dict, incident: Incident,
                   agent_type: str, force: bool) -> dict | None:
        if not force and agent_type in existing:
            return existing[agent_type].output
        agent = create_agent(agent_type, llm=self.llm)
        try:
            output = agent.run(ctx)
            validate_evidence_binding(output, ctx)
            output = enrich_output_with_evidence(output, ctx)
        except Exception as exc:  # noqa: BLE001
            logger.warning("agent %s failed: %s", agent_type, exc)
            self.db.add(
                AIAnalysis(
                    incident_id=incident.id,
                    agent_type=agent_type,
                    input=ctx,
                    output={},
                    status="failed",
                    model=self.llm.config.model,
                    prompt_version=agent.prompt_version,
                    error=str(exc)[:2000],
                )
            )
            self.db.flush()
            return None
        self.db.add(
            AIAnalysis(
                incident_id=incident.id,
                agent_type=agent_type,
                input=ctx,
                output=output,
                status="completed",
                model=self.llm.config.model,
                prompt_version=agent.prompt_version,
            )
        )
        self.db.flush()
        return output

    # ------------------------------------------------------------------
    @staticmethod
    def _sync_techniques(incident: Incident, techniques: list[str]) -> None:
        existing = {t.technique_id for t in incident.techniques}
        for tid in techniques:
            if tid and tid not in existing:
                incident.techniques.append(
                    AttackTechnique(incident_id=incident.id, technique_id=tid, source="ai")
                )
