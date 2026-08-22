"""Copilot chat API tests (rule/mock intent resolution)."""
from app.services.copilot import CopilotService


def _auth(client, admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


def _chat(client, admin_token, message):
    r = client.post("/api/copilot/chat", headers=_auth(client, admin_token),
                    json={"message": message})
    assert r.status_code == 200, r.text
    return r.json()


def _actions(d):
    return [st["action"] for st in d.get("steps", [])]


def test_copilot_scan_intent(client, admin_token):
    d = _chat(client, admin_token, "扫描 http://demo.local 和 10.10.10.5")
    assert "scan" in _actions(d)          # agent planned and executed scan
    assert "findings" in _actions(d)      # then verified findings (multi-step)
    assert "扫描" in d["reply"]


def test_copilot_audit_intent(client, admin_token):
    d = _chat(client, admin_token, "审查今天的操作日志")
    assert "audit" in _actions(d)
    assert d["steps"][0]["ok"] is True


def test_copilot_incidents_intent(client, admin_token):
    d = _chat(client, admin_token, "应急响应，查看未处理事件")
    assert "incidents" in _actions(d)


def test_copilot_health_intent(client, admin_token):
    d = _chat(client, admin_token, "系统健康检查")
    assert "health" in _actions(d)
    assert "健康" in d["reply"] or "正常" in d["reply"]


def test_copilot_advice_intent(client, admin_token):
    d = _chat(client, admin_token, "我的系统安全吗？给防护建议")
    assert "security_advice" in _actions(d)


def test_copilot_patrol_is_multi_step(client, admin_token):
    d = _chat(client, admin_token, "全面安全巡检")
    acts = _actions(d)
    assert {"health", "incidents", "findings", "audit"} <= set(acts)  # autonomous decomposition
    assert "巡检" in d["reply"]


def test_copilot_help_fallback(client, admin_token):
    d = _chat(client, admin_token, "你好")
    assert "help" in _actions(d) or "扫描" in d["reply"]


def test_copilot_generate_report_no_incident(client, admin_token):
    # agent 应自主走到报告生成；无数据时如实提示，有数据时报告成功
    d = _chat(client, admin_token, "为最近的事件生成报告")
    assert "generate_report" in _actions(d)
    assert d["reply"] and len(d["steps"]) >= 2  # findings → incidents → generate
