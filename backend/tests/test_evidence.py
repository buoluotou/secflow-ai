"""Evidence Engine tests — content-addressed dedup + source adapters."""
from app.models.project import Asset, Project
from app.models.security import Finding, IOC, SecurityEvent
from app.services.evidence import EvidenceEngine, compute_hash


def test_hash_deterministic():
    assert compute_hash({"a": 1, "b": [2, 3]}) == compute_hash({"b": [2, 3], "a": 1})
    assert compute_hash({"a": 1}) != compute_hash({"a": 2})


def test_evidence_dedup(db):
    engine = EvidenceEngine(db)
    e1 = engine.add("wazuh_alert", "wazuh", "Alert A", content="x", raw_data={"id": 1})
    e2 = engine.add("wazuh_alert", "wazuh", "Alert A", content="x", raw_data={"id": 1})
    assert e1.id == e2.id  # same payload → same row
    e3 = engine.add("wazuh_alert", "wazuh", "Alert A", content="x", raw_data={"id": 2})
    assert e1.id != e3.id
    db.rollback()


def test_evidence_from_sources(db):
    project = Project(name="P", status="active")
    db.add(project)
    db.flush()
    asset = Asset(project_id=project.id, name="a1", ip="10.0.0.1", criticality=3)
    db.add(asset)
    db.flush()

    event = SecurityEvent(source="wazuh", event_type="E", src_ip="1.2.3.4",
                          asset_id=asset.id, severity="high", raw_data={"summary": "s"})
    db.add(event)
    db.flush()
    finding = Finding(source="nuclei", title="F", severity="high", asset_id=asset.id)
    db.add(finding)
    db.flush()
    ioc = IOC(type="ip", value="1.2.3.4", source="misp")
    db.add(ioc)
    db.flush()

    engine = EvidenceEngine(db)
    ev1 = engine.from_security_event(event)
    ev2 = engine.from_finding(finding)
    ev3 = engine.from_ioc(ioc)
    assert ev1.type == "wazuh_alert"
    assert ev2.type == "nuclei_finding"
    assert ev3.type == "misp_ioc"
    assert all(len(e.hash) == 64 for e in (ev1, ev2, ev3))
    db.rollback()
