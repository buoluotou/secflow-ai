"""Settings / LLM runtime config API tests — honest mock semantics + validation."""
from app.models.analysis import SystemSetting


def _auth(client, admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


def test_health_llm_mock_is_explicit(client):
    """Mock mode must NOT pretend a real model is connected."""
    r = client.get("/api/health/llm")
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "mock"
    assert d["ok"] is True  # system AI capability available
    assert d["provider"] == "mock"
    assert d["model"] is None
    assert "未接入真实模型" in d["detail"]


def test_test_connection_rejects_mock_honestly(client, admin_token):
    r = client.post("/api/settings/llm/test", headers=_auth(client, admin_token))
    d = r.json()
    assert d["ok"] is False
    assert d["status"] == "mock"
    assert "未接入真实模型" in d["error"]


def test_save_requires_key_for_preset_vendors(client, admin_token):
    h = _auth(client, admin_token)
    # DeepSeek without a key must be rejected
    r = client.post("/api/settings/llm", headers=h, json={"provider": "deepseek", "api_key": ""})
    assert r.status_code == 400
    assert "密钥" in r.json()["detail"]


def test_save_masks_key_and_takes_effect(client, admin_token):
    h = _auth(client, admin_token)
    r = client.post("/api/settings/llm", headers=h,
                    json={"provider": "deepseek", "api_key": "sk-test-1234567890"})
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "saved"
    assert d["provider"] == "deepseek"
    assert d["model"] == "deepseek-chat"          # preset model applied
    assert d["base_url"] == "https://api.deepseek.com/v1"
    assert d["key_configured"] is True
    assert "1234567890" not in d["api_key"]       # never echoed raw

    # GET shows masked key + runtime source
    g = client.get("/api/settings/llm", headers=h).json()
    assert g["source"] == "runtime"
    assert g["provider"] == "deepseek"
    assert g["api_key"].startswith("sk-t") and "****" in g["api_key"]

    # health/config reflects runtime config
    c = client.get("/api/health/config").json()
    assert c["llm"]["provider"] == "deepseek"
    assert c["llm"]["source"] == "runtime"

    # cleanup
    client.delete("/api/settings/llm", headers=h)


def test_save_custom_requires_url_and_model(client, admin_token):
    h = _auth(client, admin_token)
    r = client.post("/api/settings/llm", headers=h, json={"provider": "custom", "base_url": "", "model": ""})
    assert r.status_code == 400
    r = client.post("/api/settings/llm", headers=h,
                    json={"provider": "custom", "base_url": "http://127.0.0.1:9999/v1", "model": "m"})
    assert r.status_code == 200
    client.delete("/api/settings/llm", headers=h)


def test_reset_restores_env_default(client, admin_token):
    h = _auth(client, admin_token)
    client.post("/api/settings/llm", headers=h, json={"provider": "openai", "api_key": "sk-abcdefghij"})
    r = client.delete("/api/settings/llm", headers=h)
    assert r.status_code == 200
    g = client.get("/api/settings/llm", headers=h).json()
    assert g["source"] == "env"
    assert g["provider"] == "mock"
    assert client.get("/api/health/llm").json()["status"] == "mock"
