"""Report Agent (spec §38): narrative sections for security reports."""
from __future__ import annotations

from ai.agents.base import BaseAgent


class ReportAgent(BaseAgent):
    agent_type = "report"
    prompt_file = "report.txt"
    prompt_version = "v1.0"

    def _build_user_prompt(self, context: dict) -> str:
        return (
            "AGENT: report\n"
            "Write the narrative sections for this incident report.\n"
            "Context (JSON):\n"
            + self._snippet(
                context,
                ["incident", "current_event", "asset", "history", "findings",
                 "threat_intel", "evidence", "attack_context"],
            )
        )
