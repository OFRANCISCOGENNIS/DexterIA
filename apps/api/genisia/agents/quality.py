"""Agentes de Segurança, Otimização e Documentação."""
from __future__ import annotations

from typing import Any

from ..analysis.analyzer import RepositoryAnalyzer
from ..execution.workspace import Workspace
from ..knowledge.search import add_memory
from ..models import Artifact, Repository, Task
from .base import Agent, AgentContext
from .repository import target_path


class SecurityAgent(Agent):
    name = "security"
    title = "Segurança"
    description = "Procura segredos expostos, chamadas perigosas e lista dependências do alvo analisado."
    responsibilities = ["Procurar segredos expostos", "Identificar chamadas perigosas", "Listar dependências", "Recomendar correções"]

    def run(self, ctx: AgentContext) -> dict[str, Any]:
        path, name = target_path(ctx)
        analyzer = RepositoryAnalyzer(path, name)
        analyzer.inventory()
        secrets = analyzer.secrets()
        code = analyzer.code_structure()
        manifests = analyzer.manifests()
        risky = code["risky_calls"]
        severity = "high" if secrets else ("medium" if risky else "low")
        md = [f"# Verificação de segurança — {name}", "", f"- **Severidade geral:** {severity}",
              f"- **Possíveis segredos:** {len(secrets)}", f"- **Chamadas perigosas:** {len(risky)}",
              f"- **Dependências declaradas:** {manifests['dependency_count']}", ""]
        if secrets:
            md += ["## Possíveis segredos (valores não armazenados)", "", "| Regra | Local | Impressão digital |", "|---|---|---|"]
            md += [f"| {s['rule']} | `{s['file']}:{s['line']}` | `{s['fingerprint']}` |" for s in secrets[:50]]
            md.append("")
        if risky:
            md += ["## Chamadas que exigem revisão", ""] + [f"- `{r['file']}:{r['line']}` — {r['rule']}" for r in risky[:50]] + [""]
        md += ["## Limitações", "- Detecção por padrões; não substitui auditoria nem verificação de CVEs das dependências.", ""]
        repo_id = ctx.params.get("repository_id")
        artifact = ctx.add_artifact("security", f"Segurança — {name}", "\n".join(md),
                                    data={"secrets": secrets, "risky_calls": risky, "dependencies": manifests["dependencies"]},
                                    repository_id=repo_id)
        ctx.log(f"Segurança: {len(secrets)} segredo(s) potencial(is), {len(risky)} chamada(s) perigosa(s)")
        return {"artifact_id": artifact.id, "severity": severity, "secrets": len(secrets), "risky_calls": len(risky)}


class OptimizationAgent(Agent):
    name = "optimizer"
    title = "Otimização"
    description = "Mede duplicação, funções longas e arquivos grandes, com números verificáveis para orientar refatorações."
    responsibilities = ["Detectar duplicações", "Avaliar complexidade", "Recomendar refatorações com métricas"]

    def run(self, ctx: AgentContext) -> dict[str, Any]:
        path, name = target_path(ctx)
        analyzer = RepositoryAnalyzer(path, name)
        inv = analyzer.inventory()
        dup = analyzer.duplication()
        code = analyzer.code_structure()
        md = [f"# Métricas de otimização — {name}", "", f"- Linhas de código: {inv['code_lines']}",
              f"- Blocos duplicados (janelas de 6 linhas): {dup['duplicated_blocks']}",
              f"- Funções com 80+ linhas: {len(code['long_functions'])}", ""]
        if dup["top_pairs"]:
            md += ["## Pares com mais duplicação", ""] + [f"- `{p['a']}` ↔ `{p['b']}`: {p['blocks']} blocos" for p in dup["top_pairs"]] + [""]
        if code["long_functions"]:
            md += ["## Funções longas", ""] + [f"- `{f['path']}` `{f['name']}` — {f['lines']} linhas" for f in code["long_functions"]] + [""]
        artifact = ctx.add_artifact("optimization", f"Otimização — {name}", "\n".join(md),
                                    data={"duplication": dup, "long_functions": code["long_functions"], "code_lines": inv["code_lines"]},
                                    repository_id=ctx.params.get("repository_id"))
        return {"artifact_id": artifact.id, "duplicated_blocks": dup["duplicated_blocks"], "long_functions": len(code["long_functions"])}


class DocumentationAgent(Agent):
    name = "documentation"
    title = "Documentação e Aprendizagem"
    description = "Consolida resultados dos agentes em um relatório de entrega verificável e registra decisões na memória do projeto."
    responsibilities = ["Gerar relatório de entrega", "Documentar decisões", "Associar resultados a materiais de estudo"]

    def run(self, ctx: AgentContext) -> dict[str, Any]:
        if ctx.params.get("mode") == "repository_report":
            return self.repository_report(ctx)
        return self.delivery(ctx)

    def _steps(self, ctx: AgentContext) -> list[Task]:
        return list(ctx.db.query(Task).filter(Task.parent_id == ctx.task.parent_id, Task.id != ctx.task.id).order_by(Task.created_at))

    def delivery(self, ctx: AgentContext) -> dict[str, Any]:
        project = ctx.project
        dev = ctx.inputs.get("develop") or {}
        qa_step = next((t for t in self._steps(ctx) if t.step_key == "qa"), None)
        qa = (qa_step.result if qa_step else None) or {}
        sec = ctx.inputs.get("security") or {}
        opt = ctx.inputs.get("optimize") or {}
        steps = self._steps(ctx)
        workspace = Workspace(project.id)
        diffstat = workspace.diff_stat(dev.get("base_commit")) if workspace.exists else ""
        files = sorted(set(dev.get("files", [])) | {f for fix in ((ctx.db.get(Artifact, qa["artifact_id"]).data or {}).get("fixes", [])
                                                              if qa.get("artifact_id") else []) for f in fix.get("files", [])})
        verified = qa.get("passed") is True
        md = [f"# Entrega — {project.name}", "",
              f"**Status da verificação:** {'✅ testes aprovados no sandbox' if verified else '❌ não verificado / testes reprovados'}", ""]
        if dev.get("summary"):
            md += ["## Funcionalidades implementadas", "", dev["summary"], ""]
        md += ["## Etapas executadas", "", "| Etapa | Agente | Status | Tentativas |", "|---|---|---|---|"]
        md += [f"| {t.title} | {t.agent} | {t.status} | {t.attempts} |" for t in steps]
        md.append("")
        if files:
            md += ["## Arquivos criados/modificados", ""] + [f"- `{f}`" for f in files] + [""]
        if diffstat:
            md += ["## Resumo do diff (desde o início da iteração)", "", "```", diffstat.strip(), "```", ""]
        if qa:
            md += ["## Testes executados", "", f"- Comando: `{qa.get('test_command', '?')}`", f"- Execuções: {qa.get('runs', 0)}",
                   f"- Correções automáticas: {qa.get('fixes', 0)}", f"- Commit final: `{(qa.get('final_commit') or '')[:10]}`",
                   f"- Log completo: artefato `{qa.get('artifact_id')}`", ""]
        issues = [f"Etapa '{t.title}' terminou como {t.status}: {t.error}" for t in steps if t.status in {"failed", "skipped", "cancelled"} and t.error]
        if sec.get("secrets"):
            issues.append(f"Segurança: {sec['secrets']} possível(is) segredo(s) no código")
        if sec.get("risky_calls"):
            issues.append(f"Segurança: {sec['risky_calls']} chamada(s) perigosa(s) a revisar")
        if opt.get("duplicated_blocks"):
            issues.append(f"Otimização: {opt['duplicated_blocks']} bloco(s) duplicado(s)")
        md += ["## Problemas conhecidos", ""] + ([f"- {i}" for i in issues] or ["- Nenhum registrado"]) + [""]
        md += ["## Como executar", "", "O código está no workspace Git do projeto (aba Studio). Para rodar localmente:", "",
               "```bash", "# baixe os arquivos pelo Studio ou copie o workspace", "python3 -m pytest -q  # projetos Python",
               "node --test           # projetos Node.js", "```", "",
               "Consulte o README.md gerado no workspace para instruções específicas.", "",
               "## Próximas melhorias", "", "- Revisar o plano e solicitar a próxima iteração com novas instruções.",
               "- Resolver os problemas conhecidos acima.", ""]
        notes = dev.get("notes")
        if notes:
            md += ["## Notas do desenvolvedor", "", notes, ""]
        artifact = ctx.add_artifact("delivery", f"Entrega — {project.name}", "\n".join(md),
                                    data={"verified": verified, "files": files, "issues": issues})
        add_memory(ctx.db, owner_id=project.owner_id, project_id=project.id,
                   title=f"Entrega {'verificada' if verified else 'não verificada'}",
                   content=(dev.get("summary") or "") + "\n" + "\n".join(issues), item_type="memory", origin=f"artifact:{artifact.id}")
        project.status = "delivered" if verified else "needs_attention"
        ctx.db.commit()
        return {"artifact_id": artifact.id, "verified": verified, "issues": len(issues)}

    def repository_report(self, ctx: AgentContext) -> dict[str, Any]:
        repo = ctx.db.get(Repository, ctx.params.get("repository_id"))
        steps = self._steps(ctx)
        parts = []
        for t in steps:
            if t.result and t.result.get("artifact_id"):
                art = ctx.db.get(Artifact, t.result["artifact_id"])
                if art and art.kind != "analysis":
                    parts.append(art)
        md = [f"# Relatório consolidado — {repo.name}", "", f"Origem: {repo.source_url} · commit `{repo.commit_sha or '-'}`", "",
              "| Etapa | Agente | Status |", "|---|---|---|"] + [f"| {t.title} | {t.agent} | {t.status} |" for t in steps]
        md += ["", f"Relatório principal: artefato `{repo.last_analysis_artifact_id}`.", ""]
        for art in parts:
            md += [f"## {art.title}", "", art.content.split("\n", 2)[-1][:6000], ""]
        artifact = ctx.add_artifact("report", f"Relatório consolidado — {repo.name}", "\n".join(md), repository_id=repo.id)
        return {"artifact_id": artifact.id}
