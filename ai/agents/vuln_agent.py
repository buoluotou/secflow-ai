"""Vulnerability Agent (spec §37): finding authenticity, priority, impact, exploit risk."""
from __future__ import annotations

from ai.agents.base import BaseAgent


class VulnerabilityAgent(BaseAgent):
    agent_type = "vuln"
    prompt_file = "vuln.txt"
    prompt_version = "v1.0"

    def _build_user_prompt(self, context: dict) -> str:
        return (
            "AGENT: vuln\n"
            "Assess the vulnerability finding in the following context.\n"
            "Context (JSON):\n"
            + self._snippet(context, ["findings", "asset", "threat_intel", "evidence"])
        )
