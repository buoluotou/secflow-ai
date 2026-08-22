"""Copilot chat API tests (rule/mock intent resolution)."""
from app.services.copilot import CopilotService


def _auth(client, admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


def _chat(client, admin_token, message):
    r = client.post("/api/copilot/chat", headers=_auth(client, admin_token),
                    json={"message": message})
    assert r.status_code == 200, r.text
    return r.json()


def test_copilot_scan_intent(client, admin_token):
    d = _chat(client, admin_token, "扫描 http://demo.local 和 10.10.10.5")
    assert d["tool"] == "scan"
    assert "扫描" in d["reply"]


def test_copilot_audit_intent(client, admin_token):
    d = _chat(client, admin_token, "审查今天的操作日志")
    assert d["tool"] == "audit"
    assert d["result_ok"] is True


def test_copilot_incidents_intent(client, admin_token):
    d = _chat(client, admin_token, "应急响应，查看未处理事件")
    assert d["tool"] == "incidents"


def test_copilot_health_intent(client, admin_token):
    d = _chat(client, admin_token, "系统健康检查")
    assert d["tool"] == "health"
    assert d["data"]["db"] is True


def test_copilot_advice_intent(client, admin_token):
    d = _chat(client, admin_token, "我的系统安全吗？给防护建议")
    assert d["tool"] == "security_advice"
    assert d["data"]["advice"]


def test_copilot_help_fallback(client, admin_token):
    d = _chat(client, admin_token, "你好")
    assert d["tool"] == "help"
    assert "扫描" in d["reply"]


def test_copilot_generate_report_no_incident(client, admin_token):
    # 未指定事件 ID 时降级为列出报告（设计行为）
    d = _chat(client, admin_token, "为最近的事件生成报告")
    assert d["tool"] == "reports"
    assert d["result_ok"] is True
