"""Evidence reasoning (spec §4, §32).

Enforces the platform's core rule: *every AI conclusion must bind evidence*.
An "analysis result" is only valid if all referenced evidence ids exist in
the context passed to the agent.
"""
from __future__ import annotations

from typing import Any


class EvidenceViolation(ValueError):
    pass


def available_evidence_ids(context: dict) -> set[str]:
    return {e.get("id") for e in context.get("evidence", []) if e.get("id")}


def validate_evidence_binding(output: dict[str, Any], context: dict) -> dict[str, Any]:
    """Raise EvidenceViolation when output references unknown evidence."""
    known = available_evidence_ids(context)
    referenced = output.get("evidence_ids") or []
    missing = [eid for eid in referenced if eid not in known]
    if missing:
        raise EvidenceViolation(
            f"Analysis references evidence not present in context: {missing}"
        )
    return output


def enrich_output_with_evidence(output: dict[str, Any], context: dict) -> dict[str, Any]:
    """Attach the referenced evidence snapshots to the output (for auditability)."""
    by_id = {e.get("id"): e for e in context.get("evidence", [])}
    output["evidence"] = [by_id[eid] for eid in (output.get("evidence_ids") or []) if eid in by_id]
    return output
