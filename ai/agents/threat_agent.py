"""Threat Agent (spec §36): IOC / MISP / history → malicious entity verdict."""
from __future__ import annotations

from ai.agents.base import BaseAgent


class ThreatAgent(BaseAgent):
    agent_type = "threat"
    prompt_file = "threat.txt"
    prompt_version = "v1.0"

    def _build_user_prompt(self, context: dict) -> str:
        return (
            "AGENT: threat\n"
            "Analyze the following threat intelligence context.\n"
            "Context (JSON):\n"
            + self._snippet(context, ["threat_intel", "current_event", "history", "evidence"])
        )
