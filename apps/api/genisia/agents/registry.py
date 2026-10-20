from __future__ import annotations

from .base import Agent
from .development import DeveloperAgent, QAAgent
from .planning import ArchitectAgent, OrchestratorGateAgent, ResearchAgent
from .quality import DocumentationAgent, OptimizationAgent, SecurityAgent
from .repository import IntegrationAgent, ReverseEngineerAgent

AGENTS: dict[str, Agent] = {
    agent.name: agent
    for agent in (
        OrchestratorGateAgent(), ArchitectAgent(), DeveloperAgent(), ReverseEngineerAgent(), ResearchAgent(),
        QAAgent(), SecurityAgent(), DocumentationAgent(), OptimizationAgent(), IntegrationAgent(),
    )
}
