"""Triage Agent (spec §35): is this worth investigating?"""
from __future__ import annotations

from ai.agents.base import BaseAgent


class TriageAgent(BaseAgent):
    agent_type = "triage"
    prompt_file = "triage.txt"
    prompt_version = "v1.0"

    def _build_user_prompt(self, context: dict) -> str:
        return (
            "AGENT: triage\n"
            "Analyze the following security context and triage the incident.\n"
            "Context (JSON):\n"
            + self._snippet(
                context,
                ["incident", "current_event", "asset", "history", "findings",
                 "threat_intel", "evidence", "attack_context"],
            )
        )
