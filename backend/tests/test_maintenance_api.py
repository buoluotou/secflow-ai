"""Maintenance & password-change API tests."""
from app.models.organization import User


def _auth(client, admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


def test_maintenance_stats_and_reset(client, admin_token, project_id):
    h = _auth(client, admin_token)
    # seed some data
    client.post("/api/events", json={"source": "wazuh", "event_type": "E1",
                                     "severity": "high", "src_ip": "1.2.3.4"}, headers=h)
    stats = client.get("/api/maintenance/stats", headers=h)
    assert stats.status_code == 200
    assert stats.json()["tables"]["security_events"] >= 1

    r = client.post("/api/maintenance/reset-data", headers=h)
    assert r.status_code == 200
    stats2 = client.get("/api/maintenance/stats", headers=h).json()["tables"]
    assert stats2["security_events"] == 0
    assert stats2["incidents"] == 0
    assert stats2["users"] >= 1  # accounts kept


def test_change_password_flow(client, admin_token):
    h = _auth(client, admin_token)
    # wrong old password rejected
    r = client.post("/api/auth/change-password", headers=h,
                    json={"old_password": "wrong", "new_password": "NewPass12345"})
    assert r.status_code == 400

    # correct flow
    r = client.post("/api/auth/change-password", headers=h,
                    json={"old_password": "TestPass12345", "new_password": "NewPass12345"})
    assert r.status_code == 200

    # login with new password works
    login = client.post("/api/auth/login", json={"username": "testadmin", "password": "NewPass12345"})
    assert login.status_code == 200

    # restore for other tests
    client.post("/api/auth/change-password", headers=h,
                json={"old_password": "NewPass12345", "new_password": "TestPass12345"})
