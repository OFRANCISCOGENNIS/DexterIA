"""Modelos de fluxos multiagente (grafos de etapas com dependências).

Inspirado no conceito de "swarm" do Ruflo (ruvnet/ruflo): o orquestrador divide o objetivo em
etapas atribuídas a agentes especializados, cada etapa recebe apenas os resultados das etapas
das quais depende (contexto seletivo), e etapas opcionais podem falhar sem interromper o fluxo.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StepSpec:
    key: str
    agent: str
    title: str
    depends_on: list[str] = field(default_factory=list)
    optional: bool = False
    run_always: bool = False  # executa mesmo se dependências falharem (ex.: relatório final)
    max_attempts: int = 2
    timeout_seconds: int = 900
    input: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowSpec:
    name: str
    title: str
    description: str
    requires: str  # project | repository
    steps: list[StepSpec]


def _dev_steps(after: list[str]) -> list[StepSpec]:
    return [
        StepSpec("develop", "developer", "Implementar incremento", after, max_attempts=2, timeout_seconds=1200),
        StepSpec("qa", "qa", "Executar testes isolados e corrigir", ["develop"], max_attempts=1, timeout_seconds=2400),
        StepSpec("security", "security", "Verificação de segurança", ["develop"], optional=True, max_attempts=1),
        StepSpec("optimize", "optimizer", "Métricas de otimização", ["develop"], optional=True, max_attempts=1),
        StepSpec("deliver", "documentation", "Consolidar entrega", ["qa", "security", "optimize"], run_always=True, max_attempts=1),
    ]


WORKFLOWS: dict[str, WorkflowSpec] = {
    "mission": WorkflowSpec(
        "mission", "Missão completa",
        "Pesquisa → plano (IA) → aprovação humana → código (IA) → testes isolados com correção → segurança/otimização → entrega.",
        "project",
        [
            StepSpec("research", "research", "Pesquisar referências"),
            StepSpec("architect", "architect", "Gerar plano de desenvolvimento", ["research"], timeout_seconds=1200),
            StepSpec("plan_approval", "orchestrator", "Aprovação humana do plano", ["architect"], max_attempts=1,
                     timeout_seconds=7 * 24 * 3600, input={"gate_action": "plan.execute"}),
            *_dev_steps(["plan_approval"]),
        ],
    ),
    "plan": WorkflowSpec(
        "plan", "Plano de desenvolvimento", "Pesquisa → plano (IA) → aprovação humana do plano.", "project",
        [
            StepSpec("research", "research", "Pesquisar referências"),
            StepSpec("architect", "architect", "Gerar plano de desenvolvimento", ["research"], timeout_seconds=1200),
            StepSpec("plan_approval", "orchestrator", "Aprovação humana do plano", ["architect"], max_attempts=1,
                     timeout_seconds=7 * 24 * 3600, input={"gate_action": "plan.execute"}),
        ],
    ),
    "develop": WorkflowSpec(
        "develop", "Iteração de desenvolvimento", "Código (IA) a partir do plano aprovado → testes → segurança/otimização → entrega.",
        "project", _dev_steps([]),
    ),
    "test": WorkflowSpec(
        "test", "Executar testes", "Executa os testes do workspace no sandbox, sem correção automática.", "project",
        [StepSpec("qa", "qa", "Executar testes isolados", max_attempts=1, input={"fix": False})],
    ),
    "analyze_repository": WorkflowSpec(
        "analyze_repository", "Análise de repositório",
        "Importação → engenharia reversa estática (+REA) → segurança e otimização → revisão por IA (opcional) → relatório.",
        "repository",
        [
            StepSpec("import", "integrations", "Importar repositório", max_attempts=3, timeout_seconds=900),
            StepSpec("reverse", "reverse_engineer", "Análise estática", ["import"], timeout_seconds=1800),
            StepSpec("security", "security", "Verificação de segurança", ["import"], optional=True, max_attempts=1),
            StepSpec("optimize", "optimizer", "Métricas de otimização", ["import"], optional=True, max_attempts=1),
            StepSpec("ai_review", "architect", "Revisão arquitetural por IA (hipóteses)", ["reverse"], optional=True,
                     max_attempts=1, input={"mode": "repo_review"}),
            StepSpec("report", "documentation", "Relatório consolidado", ["reverse", "security", "optimize", "ai_review"],
                     max_attempts=1, input={"mode": "repository_report"}),
        ],
    ),
    "ingest_knowledge": WorkflowSpec(
        "ingest_knowledge", "Indexar catálogo na base de conhecimento",
        "Importação → análise → extração de links/APIs/livros (somente metadados) para a base de conhecimento.",
        "repository",
        [
            StepSpec("import", "integrations", "Importar repositório", max_attempts=3, timeout_seconds=900),
            StepSpec("reverse", "reverse_engineer", "Análise estática (licença e estrutura)", ["import"], timeout_seconds=1800,
                     input={"use_rea": False}),
            StepSpec("ingest", "research", "Extrair catálogo para a base de conhecimento", ["reverse"], input={"action": "ingest"}),
        ],
    ),
}
