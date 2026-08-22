"""Wazuh parser tests (spec §28)."""
from integrations.wazuh.parser import parse_alert


def test_parse_high_level_alert():
    alert = {
        "data": {
            "id": 9001,
            "timestamp": "2026-08-22T09:15:00.000Z",
            "rule": {
                "description": "Command execution detected",
                "level": 12,
                "groups": ["sysmon", "execution"],
                "mitre": {"technique": [{"id": "T1059.001", "name": "PowerShell"}]},
            },
            "agent": {"id": "001", "name": "web-01"},
            "srcip": "203.0.113.66",
            "dstip": "10.0.0.5",
            "user": "www-data",
        }
    }
    parsed = parse_alert(alert)
    assert parsed["external_id"] == "9001"
    assert parsed["severity"] == "high"          # level 12
    assert parsed["techniques"] == ["T1059.001"]
    assert parsed["src_ip"] == "203.0.113.66"
    assert parsed["confidence"] > 0.8
    assert parsed["raw_data"]["id"] == 9001


def test_parse_low_level_alert():
    alert = {"data": {"id": 1, "rule": {"description": "port scan", "level": 4}, "timestamp": "t"}}
    parsed = parse_alert(alert)
    assert parsed["severity"] == "low"
    assert parsed["confidence"] < 0.8


def test_parse_missing_rule():
    parsed = parse_alert({"data": {}})
    assert parsed["event_type"] == "security event"
    assert parsed["severity"] == "low"
