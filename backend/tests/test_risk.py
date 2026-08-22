"""Risk Engine tests (spec §39) — deterministic multiplicative scoring."""
from risk.engine import RiskEngine


def test_level_thresholds():
    engine = RiskEngine()
    assert engine.level(2.0) == "low"
    assert engine.level(5.0) == "medium"
    assert engine.level(10.0) == "high"
    assert engine.level(20.0) == "critical"
    assert engine.level(99) == "critical"


def test_high_risk_scenario():
    ctx = {
        "current_event": [{"severity": "critical", "confidence": 0.95}],
        "findings": [{"severity": "critical", "cvss": 9.8}],
        "asset": [{"criticality": 5, "environment": "production"}],
        "ai_triage": {"severity": "critical", "confidence": 0.92, "malicious": True, "exploit_evidence": True},
    }
    factors = RiskEngine().from_incident_context(ctx)
    score, level = RiskEngine().score(factors)
    assert level == "critical"
    assert score >= 20


def test_low_risk_scenario():
    ctx = {
        "current_event": [{"severity": "low"}],
        "findings": [],
        "asset": [{"criticality": 1, "environment": "development"}],
        "ai_triage": {"severity": "low", "confidence": 0.3},
    }
    factors = RiskEngine().from_incident_context(ctx)
    score, level = RiskEngine().score(factors)
    assert level in ("low", "medium")
    assert score < 5


def test_factors_are_auditable():
    ctx = {
        "current_event": [{"severity": "high"}],
        "asset": [{"criticality": 4, "environment": "dmz"}],
        "ai_triage": {"severity": "high", "confidence": 0.8},
    }
    factors = RiskEngine().from_incident_context(ctx)
    assert factors.detail["severity"] == "high"
    assert factors.detail["asset_criticality_raw"] == 4
    assert factors.detail["environment"] == "dmz"
