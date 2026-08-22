"""AI agents tests — mock provider, schema validation, evidence binding."""
from ai.agents import create_agent
from ai.reasoning.evidence import EvidenceViolation, validate_evidence_binding

CONTEXT = {
    "incident": {"id": "INC-1", "title": "t", "status": "new", "severity": "high"},
    "current_event": [
        {"id": "EVT-1", "severity": "high", "src_ip": "203.0.113.66",
         "event_type": "execution", "techniques": ["T1059.001"]}
    ],
    "asset": [{"criticality": 5, "environment": "production"}],
    "history": [],
    "findings": [],
    "threat_intel": [{"id": "IOC-1", "type": "ip", "value": "203.0.113.66", "confidence": 0.9}],
    "evidence": [
        {"id": "E001", "type": "wazuh_alert", "source": "wazuh", "title": "exec"},
        {"id": "E002", "type": "misp_ioc", "source": "misp", "title": "ioc"},
    ],
    "attack_context": {"techniques": ["T1059.001"], "stage": "execution"},
}


def test_triage_mock_validates_schema():
    agent = create_agent("triage")
    out = agent.run(CONTEXT)
    assert out["classification"] in (
        "true_positive", "false_positive", "likely_true_positive", "likely_false_positive"
    )
    assert 0.0 <= out["confidence"] <= 1.0
    assert isinstance(out["mitre_techniques"], list)
    assert isinstance(out["evidence_ids"], list)
    assert out["_provider"] == "mock"


def test_triage_mock_flags_high_risk_with_ioc():
    agent = create_agent("triage")
    out = agent.run(CONTEXT)
    assert out["classification"] == "true_positive"
    assert out["severity"] in ("high", "critical")


def test_threat_and_vuln_agents():
    threat = create_agent("threat").run(CONTEXT)
    assert "malicious" in threat and 0.0 <= threat["confidence"] <= 1.0

    vuln_ctx = {**CONTEXT, "findings": [{"id": "F1", "severity": "high", "cvss": 9.0}]}
    vuln = create_agent("vuln").run(vuln_ctx)
    assert vuln["authenticity"] in ("confirmed", "unconfirmed", "false_positive")


def test_evidence_binding_enforced():
    out = {"evidence_ids": ["E999"]}
    try:
        validate_evidence_binding(out, CONTEXT)
        raise AssertionError("should have raised")
    except EvidenceViolation:
        pass
    validate_evidence_binding({"evidence_ids": ["E001"]}, CONTEXT)
