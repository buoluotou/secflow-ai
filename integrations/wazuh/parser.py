"""Wazuh alert parser — converts raw Wazuh API items into normalized dicts.

Input: one item of GET /security/events (affected_items).
Output: a flat dict that the mapper can turn into a SecurityEvent.
"""
from __future__ import annotations

from typing import Any


def parse_alert(item: dict[str, Any]) -> dict[str, Any]:
    data = item.get("data", {})
    rule = data.get("rule", {})
    agent = data.get("agent", {})
    src = data.get("srcip") or data.get("src_ip")
    dst = data.get("dstip") or data.get("dst_ip")

    level = int(data.get("level") or rule.get("level") or 5)
    severity = "info" if level < 4 else "low" if level < 7 else "medium" if level < 10 else "high" if level < 13 else "critical"

    techniques = _techniques_from_rule(rule)
    indicators: list[str] = [src] if src else []
    if data.get("sha256"):
        indicators.append(data["sha256"])
    if data.get("md5"):
        indicators.append(data["md5"])
    if data.get("url"):
        indicators.append(data["url"])

    return {
        "external_id": str(data.get("id") or item.get("id") or ""),
        "event_type": rule.get("description") or data.get("description") or "security event",
        "timestamp": data.get("timestamp"),
        "user": data.get("user") or data.get("data", {}).get("win", {}).get("eventdata", {}).get("user"),
        "src_ip": src,
        "src_port": data.get("srcport") or data.get("src_port"),
        "dst_ip": dst,
        "dst_port": data.get("dstport") or data.get("dst_port"),
        "severity": severity,
        "confidence": min(1.0, 0.4 + level / 20.0),
        "indicators": indicators,
        "techniques": techniques,
        "raw_data": data,
        "agent_name": agent.get("name"),
        "agent_id": agent.get("id"),
        "groups": rule.get("groups", []),
        "mitre": rule.get("mitre", {}),
    }


def _techniques_from_rule(rule: dict[str, Any]) -> list[str]:
    mitre = rule.get("mitre", {})
    techs: list[str] = []
    for t in mitre.get("technique", []):
        if isinstance(t, dict):
            techs.append(t.get("id") or t.get("name") or "")
        else:
            techs.append(str(t))
    return [t for t in techs if t]
