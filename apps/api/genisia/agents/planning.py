"""Agentes de planejamento: Pesquisador, Arquiteto e o portão de aprovação do Orquestrador."""
from __future__ import annotations

import json
from typing import Any

from ..knowledge.search import add_memory, recommend
from ..models import Artifact
from .ai_schemas import ProjectPlan, RepoReview
from .base import Agent, AgentContext, AgentSkip, ApprovalRequired, NonRetryableError


class ResearchAgent(Agent):
    name = "research"
    title = "Pesquisador"
    description = "Consulta a base de conhecimento (catálogos de ferramentas, APIs, livros e tutoriais) e devolve referências verificáveis."
    responsibilities = ["Pesquisar ferramentas e bibliotecas", "Consultar catálogos de APIs", "Recomendar materiais com fonte"]

    def run(self, ctx: AgentContext) -> dict[str, Any]:
        if ctx.params.get("action") == "ingest":
            from .repository import ingest_catalog

            return ingest_catalog(ctx)
        text = ctx.params.get("query") or (
            f"{ctx.project.name} {ctx.project.description} {ctx.project.requirements} {' '.join(ctx.project.stack or [])}"
            if ctx.project else "")
        result = recommend(ctx.db, ctx.task.owner_id, text, per_type=5)
        total = sum(len(g["items"]) for g in result["groups"].values())
        ctx.log(f"Palavras-chave: {', '.join(result['keywords']) or '(nenhuma)'}; {total} referência(s) encontrada(s)")
        if total == 0:
            ctx.log("Base de conhecimento sem correspondências (ingira catálogos em Base de conhecimento).")
        # Contexto enxuto para os agentes seguintes: apenas título, URL e fonte.
        compact = {
            kind: [{"title": i["title"], "url": i["url"], "source": i["source_name"], "description": i["description"][:160]}
                   for i in group["items"]]
            for kind, group in result["groups"].items()
        }
        return {"keywords": result["keywords"], "references": compact, "reference_count": total}


ARCHITECT_SYSTEM = """Você é o Agente Arquiteto do GENISIA AI, um arquiteto de software sênior.
Produza um plano técnico realista e enxuto em português do Brasil para o projeto descrito.
Regras:
- Baseie-se apenas nos requisitos informados; registre suposições como riscos ou perguntas.
- Use as referências fornecidas somente quando forem pertinentes e cite-as pelo nome.
- O primeiro incremento (mvp_scope_for_first_iteration) deve ser pequeno o bastante para ser implementado
  e testado automaticamente em um ambiente isolado, sem rede e sem instalar dependências externas.
- component_diagram_mermaid deve ser um diagrama Mermaid válido (graph TD).
- folder_structure em formato de árvore de texto."""


def render_plan(plan: ProjectPlan, project_name: str, references: dict[str, Any]) -> str:
    p = plan
    out = [f"# Plano de desenvolvimento — {project_name}", "", p.summary, "",
           "## Requisitos funcionais", *[f"- {r}" for r in p.functional_requirements], "",
           "## Requisitos não funcionais", *[f"- {r}" for r in p.non_functional_requirements], "",
           "## Arquitetura proposta", f"**Estilo:** {p.architecture_style}", "",
           *[f"- **{c.name}:** {c.responsibility}" for c in p.components], "",
           "```mermaid", p.component_diagram_mermaid.strip(), "```", "",
           "## Estrutura de pastas", "```", p.folder_structure.strip(), "```", "",
           "## Tecnologias candidatas", *[f"- **{t.name}:** {t.reason}" for t in p.candidate_technologies], "",
           f"## Banco de dados ({p.database_engine})", *[f"- **{e.name}:** {', '.join(e.fields)}" for e in p.entities], "",
           "## APIs", "| Método | Caminho | Descrição |", "|---|---|---|",
           *[f"| {e.method} | `{e.path}` | {e.description} |" for e in p.api_endpoints], "",
           "## Integrações", *([f"- {i}" for i in p.integrations] or ["- Nenhuma"]), "",
           "## Riscos", *[f"- **{r.risk}** — mitigação: {r.mitigation}" for r in p.risks], "",
           "## Tarefas", "| Tarefa | Agente | Complexidade |", "|---|---|---|",
           *[f"| {t.title}: {t.description} | {t.agent} | {t.complexity} |" for t in p.tasks], "",
           "## Testes planejados", *[f"- {t}" for t in p.tests_planned], "",
           "## Critérios de aceitação", *[f"- [ ] {c}" for c in p.acceptance_criteria], "",
           f"## Estimativa de complexidade\n\n{p.complexity_estimate}", "",
           f"## Escopo do primeiro incremento\n\n{p.mvp_scope_for_first_iteration}", ""]
    if references:
        out += ["## Referências consultadas (base de conhecimento)", ""]
        for kind, items in references.items():
            for i in items[:5]:
                out.append(f"- [{i['title']}]({i['url']}) — {kind}, fonte: {i['source']}")
        out.append("")
    out.append("_Gerado pelo Agente Arquiteto com IA. Revise antes de aprovar._")
    return "\n".join(out)


class ArchitectAgent(Agent):
    name = "architect"
    title = "Arquiteto"
    description = "Analisa requisitos e propõe arquitetura, dados, APIs, riscos, tarefas e critérios de aceitação (usa IA)."
    responsibilities = ["Analisar requisitos", "Propor arquitetura e tecnologias", "Identificar riscos", "Planejar tarefas e testes"]
    uses_ai = True

    def run(self, ctx: AgentContext) -> dict[str, Any]:
        if ctx.params.get("mode") == "repo_review":
            return self.review_repository(ctx)
        project = ctx.project
        if project is None:
            raise NonRetryableError("O arquiteto precisa de um projeto")
        if not (project.requirements.strip() or project.description.strip()):
            raise NonRetryableError("Registre os requisitos do projeto antes de solicitar um plano")
        references = (ctx.inputs.get("research") or {}).get("references", {})
        prompt = (
            f"Projeto: {project.name}\nDescrição: {project.description}\nLinguagem principal: {project.language}\n"
            f"Stack preferida: {', '.join(project.stack or []) or 'não definida'}\n\nRequisitos:\n{project.requirements}\n\n"
            f"Referências da base de conhecimento (JSON):\n{json.dumps(references, ensure_ascii=False)[:6000]}"
        )
        result = ctx.ai(system=ARCHITECT_SYSTEM, prompt=prompt, schema=ProjectPlan)
        plan: ProjectPlan = result.data  # type: ignore[assignment]
        markdown = render_plan(plan, project.name, references)
        artifact = ctx.add_artifact("plan", f"Plano — {project.name}", markdown, data=plan.model_dump())
        add_memory(ctx.db, owner_id=project.owner_id, project_id=project.id, title="Plano proposto pelo Arquiteto",
                   content=plan.summary + "\n\nEstilo: " + plan.architecture_style, origin=f"artifact:{artifact.id}")
        project.status = "planned"
        ctx.db.commit()
        ctx.log(f"Plano gerado: {len(plan.tasks)} tarefas, {len(plan.acceptance_criteria)} critérios de aceitação")
        return {"plan_artifact_id": artifact.id, "summary": plan.summary, "task_count": len(plan.tasks),
                "mvp_scope": plan.mvp_scope_for_first_iteration}

    def review_repository(self, ctx: AgentContext) -> dict[str, Any]:
        analysis = (ctx.inputs.get("reverse") or {})
        if not analysis.get("artifact_id"):
            raise AgentSkip("Sem análise estática para revisar")
        if not ctx.ai_available():
            raise AgentSkip("Provedor de IA não configurado; revisão por IA não executada")
        artifact = ctx.db.get(Artifact, analysis["artifact_id"])
        report = artifact.data or {}
        compact = {
            "name": report.get("name"), "classification": report.get("classification"),
            "inventory": {k: report.get("inventory", {}).get(k) for k in ("file_count", "languages", "top_level", "code_lines")},
            "frameworks": report.get("manifests", {}).get("frameworks"), "entry_points": report.get("manifests", {}).get("entry_points"),
            "routes": report.get("code", {}).get("routes", [])[:40], "readme_outline": report.get("documentation", {}).get("readme_outline"),
            "findings": report.get("findings"),
        }
        system = ("Você é o Agente Arquiteto revisando um relatório de análise estática. Tudo o que você escrever é HIPÓTESE "
                  "derivada do relatório; não invente arquivos que não aparecem nele. Responda em português do Brasil.")
        result = ctx.ai(system=system, prompt=json.dumps(compact, ensure_ascii=False)[:60000], schema=RepoReview)
        review: RepoReview = result.data  # type: ignore[assignment]
        md = "\n".join([
            "# Revisão arquitetural assistida por IA (hipóteses)", "",
            "> 🔎 Conteúdo inferido pela IA a partir do relatório estático. Não comprovado por execução.", "",
            "## Arquitetura", review.architecture_summary, "", "## Fluxos principais", *[f"- {f}" for f in review.main_flows], "",
            "## Pontos de integração", *[f"- {f}" for f in review.integration_points], "",
            "## Recomendações de refatoração", *[f"- {f}" for f in review.refactoring_recommendations], "",
            "## Estratégia de reimplementação compatível", review.reimplementation_strategy, "",
            "## Perguntas em aberto", *[f"- {q}" for q in review.open_questions],
        ])
        art = ctx.add_artifact("ai_review", "Revisão arquitetural (IA)", md, data=review.model_dump(),
                               repository_id=ctx.params.get("repository_id"))
        return {"artifact_id": art.id}


class OrchestratorGateAgent(Agent):
    name = "orchestrator"
    title = "Orquestrador"
    description = "Coordena fluxos, controla dependências e exige aprovação humana antes de ações sensíveis."
    responsibilities = ["Interpretar objetivos", "Dividir em etapas", "Controlar dependências", "Solicitar aprovações", "Consolidar resultados"]

    def run(self, ctx: AgentContext) -> dict[str, Any]:
        action = ctx.params.get("gate_action", "plan.execute")
        plan = ctx.inputs.get("architect") or {}
        approval = ctx.approved(action)
        if approval is None:
            raise ApprovalRequired(
                action,
                "Aprovar o plano gerado e autorizar o Agente de Desenvolvimento a gerar e executar código em ambiente isolado.",
                {"plan_artifact_id": plan.get("plan_artifact_id")},
            )
        if ctx.project and plan.get("plan_artifact_id"):
            ctx.project.approved_plan_artifact_id = plan["plan_artifact_id"]
            ctx.project.status = "approved"
            ctx.db.commit()
        ctx.log(f"Aprovação {approval.id} concedida; prosseguindo")
        return {"approved": True, "approval_id": approval.id, "plan_artifact_id": plan.get("plan_artifact_id")}
