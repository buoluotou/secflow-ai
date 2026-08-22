"""AI agents package."""
from ai.agents.base import BaseAgent, AgentError
from ai.agents.triage_agent import TriageAgent
from ai.agents.threat_agent import ThreatAgent
from ai.agents.vuln_agent import VulnerabilityAgent
from ai.agents.report_agent import ReportAgent

AGENTS = {
    "triage": TriageAgent,
    "threat": ThreatAgent,
    "vuln": VulnerabilityAgent,
    "report": ReportAgent,
}


def create_agent(agent_type: str, llm=None) -> BaseAgent:
    cls = AGENTS.get(agent_type)
    if cls is None:
        raise ValueError(f"Unknown agent type: {agent_type}")
    return cls(llm=llm)
