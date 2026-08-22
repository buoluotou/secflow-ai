"""Context reasoning — validation of the unified context envelope."""
from __future__ import annotations

from typing import Any

REQUIRED_KEYS = (
    "incident",
    "current_event",
    "asset",
    "history",
    "findings",
    "threat_intel",
    "evidence",
    "attack_context",
)


def validate_context(ctx: dict[str, Any]) -> dict[str, Any]:
    """Ensure the envelope contains all spec §33 keys."""
    missing = [k for k in REQUIRED_KEYS if k not in ctx]
    if missing:
        raise ValueError(f"Context missing required keys: {missing}")
    if ctx.get("current_event") is None:
        ctx["current_event"] = []
    if ctx.get("evidence") is None:
        ctx["evidence"] = []
    return ctx
