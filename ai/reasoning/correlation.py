"""Correlation reasoning — explainable rule evaluation.

The Correlation Engine (backend service) does the heavy lifting; this module
provides the *explainability* layer: why did a set of signals correlate?
"""
from __future__ import annotations

from typing import Any

JOIN_KEYS = ("asset_id", "src_ip", "dst_ip", "domain", "user", "ioc")


def explain_correlation(signals: list[dict[str, Any]]) -> list[str]:
    """Return human-readable reasons for a correlated set of signals."""
    reasons: list[str] = []
    iocs = {s.get("value") for s in signals if s.get("kind") == "ioc"}
    src_ips = {s.get("src_ip") for s in signals if s.get("src_ip")}
    assets = {s.get("asset_id") for s in signals if s.get("asset_id")}
    domains = {s.get("domain") for s in signals if s.get("domain")}

    if iocs & src_ips:
        reasons.append(f"攻击源 IP 命中恶意 IOC: {sorted(iocs & src_ips)}")
    if iocs & domains:
        reasons.append(f"域名命中恶意 IOC: {sorted(iocs & domains)}")
    if len(assets) == 1 and len({s.get("kind") for s in signals}) > 1:
        reasons.append(f"同一资产 ({next(iter(assets))}) 出现多种类型信号")
    kinds = {s.get("kind") for s in signals}
    if {"event", "finding"} <= kinds:
        reasons.append("漏洞发现与主机告警同时出现 (event + finding)")
    if "ioc" in kinds and "event" in kinds:
        reasons.append("威胁情报命中主机事件 (ioc + event)")
    if not reasons:
        reasons.append("信号按时间窗口与关联键聚合")
    return reasons
