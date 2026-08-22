"""Correlation Engine tests — cross-source correlation → incident (spec §31)."""
from app.models.project import Asset, Project
from app.models.security import Finding, IOC, SecurityEvent
from app.services.correlation import CorrelationEngine


def _setup(db):
    project = Project(name="P", status="active")
    db.add(project)
    db.flush()
    asset = Asset(project_id=project.id, name="web-01", ip="10.0.0.5",
                  domain="web.example.com", criticality=4, environment="production")
    db.add(asset)
    db.flush()
    return project, asset


def test_high_severity_event_creates_incident(db):
    _setup(db)
    event = SecurityEvent(source="wazuh", event_type="Command execution",
                          severity="high", confidence=0.9, src_ip="1.2.3.4",
                          techniques=["T1059.001"])
    db.add(event)
    db.flush()

    incident = CorrelationEngine(db).on_event(event)
    assert incident is not None
    assert incident.severity == "high"
    assert incident.evidence_ids, "incident must carry evidence"
    assert incident.attack_stage is not None
    db.rollback()


def test_low_event_alone_does_not_create_incident(db):
    _setup(db)
    event = SecurityEvent(source="wazuh", event_type="port scan",
                          severity="low", confidence=0.3)
    db.add(event)
    db.flush()
    incident = CorrelationEngine(db).on_event(event)
    assert incident is None
    db.rollback()


def test_finding_plus_same_asset_event_correlates(db):
    project, asset = _setup(db)
    event = SecurityEvent(source="wazuh", event_type="Anomaly", asset_id=asset.id,
                          severity="medium", confidence=0.7)
    db.add(event)
    db.flush()
    finding = Finding(source="nuclei", title="RCE", asset_id=asset.id,
                      project_id=project.id, severity="high")
    db.add(finding)
    db.flush()

    incident = CorrelationEngine(db).on_finding(finding)
    assert incident is not None
    assert event.id in incident.related_event_ids
    assert len(incident.evidence_ids) >= 2  # finding evidence + historical event evidence
    db.rollback()


def test_malicious_ioc_on_event_src_ip(db):
    project, asset = _setup(db)
    ioc = IOC(type="ip", value="203.0.113.66", source="misp", confidence=0.95)
    db.add(ioc)
    db.flush()
    event = SecurityEvent(source="wazuh", event_type="Brute force", severity="medium",
                          confidence=0.6, src_ip="203.0.113.66", indicators=["203.0.113.66"])
    db.add(event)
    db.flush()

    incident = CorrelationEngine(db).on_event(event)
    assert incident is not None
    assert ioc.id in incident.related_ioc_ids
    assert "IOC" in (incident.correlation_reason or "")
    db.rollback()


def test_merge_into_existing_open_incident(db):
    project, asset = _setup(db)
    event = SecurityEvent(source="wazuh", event_type="Brute force", severity="high",
                          confidence=0.9, src_ip="203.0.113.66")
    db.add(event)
    db.flush()
    incident1 = CorrelationEngine(db).on_event(event)

    event2 = SecurityEvent(source="wazuh", event_type="Privilege escalation",
                           severity="critical", confidence=0.9, src_ip="203.0.113.66")
    db.add(event2)
    db.flush()
    incident2 = CorrelationEngine(db).on_event(event2)
    assert incident2.id == incident1.id
    assert event2.id in incident2.related_event_ids
    db.rollback()
