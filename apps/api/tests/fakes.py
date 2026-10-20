"""Provedor de IA determinístico usado SOMENTE nos testes automatizados.

Ele é identificado como ``fake-test`` em todos os registros, para que nunca seja confundido com
uma resposta real de IA.
"""
from __future__ import annotations

from pydantic import BaseModel

from genisia.agents.ai_schemas import CodeChange, GeneratedFile, ProjectPlan, RepoReview
from genisia.ai.providers import AIResult, AIUsage

BUGGY_MODULE = '''def total_despesas(despesas):
    """Soma o valor das despesas."""
    return sum(d["valor"] for d in despesas) + 1  # bug proposital
'''
FIXED_MODULE = '''def total_despesas(despesas):
    """Soma o valor das despesas."""
    return sum(d["valor"] for d in despesas)
'''
TEST_MODULE = '''from financas.despesas import total_despesas


def test_total():
    assert total_despesas([{"valor": 10}, {"valor": 5}]) == 15


def test_vazio():
    assert total_despesas([]) == 0
'''


def make_plan() -> ProjectPlan:
    return ProjectPlan.model_validate({
        "summary": "Sistema financeiro com controle de despesas, metas e relatórios.",
        "functional_requirements": ["Registrar despesas", "Definir metas", "Gerar relatórios"],
        "non_functional_requirements": ["Testes automatizados"],
        "candidate_technologies": [{"name": "Python", "reason": "simplicidade"}],
        "integrations": [],
        "risks": [{"risk": "Escopo amplo", "mitigation": "Iterações pequenas"}],
        "acceptance_criteria": ["Total de despesas correto"],
        "architecture_style": "Monólito modular",
        "components": [{"name": "despesas", "responsibility": "Cálculos de despesas"}],
        "component_diagram_mermaid": "graph TD\n  UI-->Despesas",
        "folder_structure": "financas/\n  despesas.py\ntests/",
        "database_engine": "SQLite",
        "entities": [{"name": "Despesa", "fields": ["id", "valor"]}],
        "api_endpoints": [{"method": "GET", "path": "/despesas", "description": "Lista"}],
        "tasks": [{"title": "Módulo de despesas", "description": "Somar despesas", "agent": "developer", "complexity": "baixa"}],
        "tests_planned": ["test_total"],
        "complexity_estimate": "Baixa",
        "mvp_scope_for_first_iteration": "Função de total de despesas com testes.",
    })


class FakeProvider:
    name = "fake-test"
    model = "fake-test-model"

    def __init__(self, fail_first_code: bool = True) -> None:
        self.calls: list[str] = []
        self.code_calls = 0
        self.fail_first_code = fail_first_code

    def status(self) -> dict:
        return {"provider": self.name, "configured": True, "model": self.model}

    def generate_structured(self, *, system: str, prompt: str, schema: type[BaseModel], max_tokens: int | None = None) -> AIResult:
        self.calls.append(schema.__name__)
        usage = AIUsage(provider=self.name, model=self.model, input_tokens=1000, output_tokens=500)
        if schema is ProjectPlan:
            data: BaseModel = make_plan()
        elif schema is CodeChange:
            self.code_calls += 1
            buggy = self.fail_first_code and self.code_calls == 1
            data = CodeChange(
                summary="Módulo de despesas" if self.code_calls == 1 else "Corrige soma",
                files=[GeneratedFile(path="financas/__init__.py", content=""),
                       GeneratedFile(path="financas/despesas.py", content=BUGGY_MODULE if buggy else FIXED_MODULE),
                       GeneratedFile(path="tests/test_despesas.py", content=TEST_MODULE),
                       GeneratedFile(path="README.md", content="# Finanças\n\nExecute `python3 -m pytest`.\n")],
                test_command="pytest", notes="Gerado pelo provedor de teste")
        elif schema is RepoReview:
            data = RepoReview(architecture_summary="Hipótese", main_flows=[], integration_points=[], refactoring_recommendations=[],
                              reimplementation_strategy="n/a", open_questions=[])
        else:  # pragma: no cover
            raise AssertionError(schema)
        return AIResult(data=data, usage=usage, raw_text=data.model_dump_json())
