"""Risk Engine (spec §39).

The LLM never assigns a final risk level directly. Risk is *computed* from
independent, auditable factors:

    risk_score = technical_severity
               × asset_criticality
               × exposure
               × threat_intelligence
               × exploit_evidence
               × confidence

Levels:  0–5 Low, 5–10 Medium, 10–20 High, 20+ Critical.

Calibration: factors are configurable in `risk/calibration.py` and must be
tuned against `datasets/evaluation/` — never hard-coded into business logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from risk.calibration import (
    ASSET_CRITICALITY_FACTORS,
    CONFIDENCE_WEIGHT,
    EXPOSURE_FACTORS,
    EXPLOIT_FACTOR,
    SEVERITY_FACTORS,
    THREAT_INTEL_FACTOR,
    RISK_LEVELS,
)


@dataclass
class RiskFactors:
    technical_severity: float = 0.0
    asset_criticality: float = 1.0
    exposure: float = 1.0
    threat_intel: float = 1.0
    exploit: float = 1.0
    confidence: float = 0.5
    detail: dict = field(default_factory=dict)


class RiskEngine:
    """Deterministic multiplicative risk scoring."""

    def __init__(self, calibration: dict | None = None):
        self.cal = calibration or {}

    # ------------------------------------------------------------------
    def from_incident_context(self, ctx: dict) -> RiskFactors:
        """Build factors from the Context Engine envelope + AI triage output.

        ctx: result of `ContextEngine.for_incident()` plus optional
             `ctx["ai_triage"]` with keys {severity, confidence,
             exploit_evidence, malicious}.
        """
        severity = "low"
        confidence = 0.5
        exploit = False
        malicious = False

        triage = ctx.get("ai_triage") or {}
        if triage.get("severity"):
            severity = triage["severity"]
        if triage.get("confidence") is not None:
            confidence = float(triage["confidence"])
        if triage.get("exploit_evidence"):
            exploit = True
        if triage.get("malicious") or triage.get("threat_intel_malicious"):
            malicious = True

        # worst severity across current events / findings
        for ev in ctx.get("current_event", []):
            if ev.get("severity"):
                severity = self._worse(severity, ev["severity"])
        for f in ctx.get("findings", []):
            if f.get("severity"):
                severity = self._worse(severity, f["severity"])

        asset_criticality = 1
        for a in ctx.get("asset", []):
            asset_criticality = max(asset_criticality, int(a.get("criticality") or 1))
        exposure_key = "production"
        for a in ctx.get("asset", []):
            if a.get("environment"):
                exposure_key = a["environment"]

        ti_factor = THREAT_INTEL_FACTOR if malicious else 1.0

        return RiskFactors(
            technical_severity=self._severity_factor(severity),
            asset_criticality=self._criticality_factor(asset_criticality),
            exposure=self._exposure_factor(exposure_key),
            threat_intel=ti_factor,
            exploit=EXPLOIT_FACTOR if exploit else 1.0,
            confidence=self._confidence_weight(confidence),
            detail={
                "severity": severity,
                "asset_criticality_raw": asset_criticality,
                "environment": exposure_key,
                "malicious": malicious,
                "exploit_evidence": exploit,
                "confidence_raw": confidence,
            },
        )

    def score(self, factors: RiskFactors) -> tuple[float, str]:
        score = (
            factors.technical_severity
            * factors.asset_criticality
            * factors.exposure
            * factors.threat_intel
            * factors.exploit
            * factors.confidence
        )
        return round(score, 2), self.level(score)

    def level(self, score: float) -> str:
        for level, lo, hi in RISK_LEVELS:
            if lo <= score < hi:
                return level
        return "critical"

    # ------------------------------------------------------------------
    @staticmethod
    def _severity_factor(severity: str) -> float:
        return SEVERITY_FACTORS.get(severity, SEVERITY_FACTORS["medium"])

    @staticmethod
    def _criticality_factor(criticality: int) -> float:
        return ASSET_CRITICALITY_FACTORS.get(criticality, 1.0)

    @staticmethod
    def _exposure_factor(env: str) -> float:
        return EXPOSURE_FACTORS.get(env, 1.0)

    @staticmethod
    def _confidence_weight(confidence: float) -> float:
        """Map confidence 0..1 → 0.5..1.0 so doubt never zeroes the score."""
        c = max(0.0, min(1.0, confidence))
        return CONFIDENCE_WEIGHT[0] + c * (CONFIDENCE_WEIGHT[1] - CONFIDENCE_WEIGHT[0])

    @staticmethod
    def _worse(a: str, b: str) -> str:
        order = ["info", "low", "medium", "high", "critical"]
        return a if order.index(a) >= order.index(b) else b
