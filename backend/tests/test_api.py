"""API smoke tests — auth, CRUD, analysis pipeline (mock LLM), reports."""
from app.models.analysis import AIAnalysis, Report, RiskAssessment
from app.models.incident import Incident


def _auth(client, admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"
    assert client.get("/api/health/db").json()["ok"] is True
    assert client.get("/api/health/llm").json()["ok"] is True  # mock provider


def test_login_and_auth_required(client, admin_token):
    resp = client.post("/api/auth/login", json={"username": "testadmin", "password": "TestPass12345"})
    assert resp.status_code == 200
    assert resp.json()["access_token"]
    assert client.get("/api/projects").status_code == 401  # no token
    assert client.get("/api/projects", headers=_auth(client, admin_token)).status_code == 200


def test_project_asset_flow(client, admin_token):
    h = _auth(client, admin_token)
    pid = client.post("/api/projects", json={"name": "Demo"}, headers=h).json()["id"]
    asset = client.post("/api/assets", json={
        "project_id": pid, "name": "web-01", "ip": "10.0.0.5",
        "asset_type": "webapp", "environment": "dmz", "criticality": 4,
    }, headers=h)
    assert asset.status_code == 201
    assert client.get("/api/assets", headers=h).status_code == 200


def test_event_ingestion_triggers_incident(client, admin_token, project_id):
    h = _auth(client, admin_token)
    client.post("/api/iocs", json={"type": "ip", "value": "45.83.66.101",
                                   "confidence": 0.9, "source": "test"}, headers=h)
    resp = client.post("/api/events", json={
        "source": "wazuh", "event_type": "Command execution detected",
        "severity": "high", "confidence": 0.9, "src_ip": "45.83.66.101",
        "project_id": project_id, "techniques": ["T1059.001"],
    }, headers=h)
    assert resp.status_code == 201
    incidents = client.get("/api/incidents", headers=h).json()
    assert incidents, "correlation should have created an incident"


def test_incident_ai_analysis_and_risk(client, admin_token, project_id):
    h = _auth(client, admin_token)
    # asset (criticality 4, dmz) — feeds the Risk Engine's asset/exposure factors
    asset = client.post("/api/assets", json={
        "project_id": project_id, "name": "web-01", "ip": "10.0.0.5",
        "asset_type": "webapp", "environment": "dmz", "criticality": 4,
    }, headers=h).json()
    client.post("/api/iocs", json={"type": "ip", "value": "9.9.9.9", "confidence": 0.9,
                                   "source": "test"}, headers=h)
    client.post("/api/events", json={
        "source": "wazuh", "event_type": "Execution", "severity": "high",
        "confidence": 0.9, "src_ip": "9.9.9.9", "project_id": project_id,
        "asset_id": asset["id"],
    }, headers=h)
    incident_id = client.get("/api/incidents", headers=h).json()[0]["id"]

    resp = client.post(f"/api/incidents/{incident_id}/analyze", headers=h)
    assert resp.status_code == 200, resp.text
    results = resp.json()["results"]
    assert "triage" in results
    assert "risk" in results
    assert results["risk"]["risk_level"] in ("high", "critical")

    # approve → report
    client.post(f"/api/incidents/{incident_id}/approve", headers=h,
                json={"decision": "approve", "comment": "ok"})
    report = client.post("/api/reports", json={"incident_id": incident_id}, headers=h)
    assert report.status_code == 201
    assert client.get(f"/api/reports/{report.json()['id']}/markdown", headers=h).status_code == 200


def test_scan_creation_queued(client, admin_token, project_id):
    h = _auth(client, admin_token)
    resp = client.post("/api/scans", json={
        "project_id": project_id, "scan_type": "nuclei",
        "targets": ["http://demo.local"],
    }, headers=h)
    assert resp.status_code == 202
    assert resp.json()["status"] == "queued"
    assert client.get("/api/scans", headers=h).status_code == 200


def test_audit_logs_recorded(client, admin_token):
    h = _auth(client, admin_token)
    logs = client.get("/api/audit/logs", headers=h).json()
    actions = {l["action"] for l in logs}
    assert "auth.login" in actions
    assert "project.create" in actions
