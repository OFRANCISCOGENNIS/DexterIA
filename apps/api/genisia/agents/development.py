"""Agente de Desenvolvimento e Agente de Testes e Qualidade."""
from __future__ import annotations

import json
from typing import Any

from ..execution.sandbox import SandboxUnavailable, detect_test_command, run_in_sandbox
from ..execution.workspace import FileChange, Workspace, WorkspaceError, normalize_relpath
from ..models import Artifact, utcnow
from .ai_schemas import CodeChange
from .base import Agent, AgentContext, AgentError, ApprovalRequired, NonRetryableError

DEV_SYSTEM = """Você é o Agente de Desenvolvimento do GENISIA AI, um engenheiro de software sênior.
Implemente, em código real e completo, o escopo indicado. Regras obrigatórias:
- Linguagem: {language}. Para Python use apenas a biblioteca padrão e pytest; para JavaScript use apenas
  módulos nativos do Node.js e o executor node:test. Não dependa de rede nem de pacotes a instalar.
- Inclua testes automatizados significativos (pytest: arquivos tests/test_*.py; node: arquivos *.test.js).
- Inclua um README.md com instruções de execução e limitações conhecidas.
- Caminhos relativos simples (sem '..', sem caminhos absolutos, sem .git). No máximo 40 arquivos.
- Nunca inclua credenciais, chaves ou dados pessoais reais.
- Retorne o conteúdo COMPLETO de cada arquivo criado ou alterado.
- test_command: "pytest" para Python, "node_test" para Node, "none" se não houver testes."""


def _apply_change(ctx: AgentContext, change: CodeChange, message: str, author: str) -> dict[str, Any]:
    files = []
    for f in change.files:
        try:
            files.append(FileChange(path=normalize_relpath(f.path), content=f.content))
        except WorkspaceError as exc:
            raise NonRetryableError(f"A IA propôs um caminho inválido: {exc}") from exc
    workspace = Workspace(ctx.project.id)
    try:
        return workspace.write_files(files, message, author)
    except WorkspaceError as exc:
        raise NonRetryableError(str(exc)) from exc


def _plan_for(ctx: AgentContext) -> Artifact:
    plan_id = (ctx.inputs.get("plan_approval") or {}).get("plan_artifact_id") or \
              (ctx.inputs.get("architect") or {}).get("plan_artifact_id") or ctx.project.approved_plan_artifact_id
    artifact = ctx.db.get(Artifact, plan_id) if plan_id else None
    if artifact is None:
        raise NonRetryableError("Nenhum plano aprovado para este projeto")
    if ctx.project.approved_plan_artifact_id != artifact.id:
        raise NonRetryableError("O plano ainda não foi aprovado pelo usuário")
    return artifact


class DeveloperAgent(Agent):
    name = "developer"
    title = "Engenheiro de Código"
    description = "Gera e modifica código no workspace isolado (Git) do projeto, sempre com testes (usa IA)."
    responsibilities = ["Criar arquivos", "Implementar funcionalidades", "Criar testes", "Corrigir falhas apontadas pelo QA"]
    uses_ai = True

    def run(self, ctx: AgentContext) -> dict[str, Any]:
        if ctx.project is None:
            raise NonRetryableError("O desenvolvedor precisa de um projeto")
        plan = _plan_for(ctx)
        workspace = Workspace(ctx.project.id)
        workspace.ensure()
        base_commit = workspace.head()
        existing = workspace.snapshot()
        plan_data = plan.data or {}
        scope = ctx.params.get("instructions") or plan_data.get("mvp_scope_for_first_iteration") or "Primeiro incremento do plano"
        prompt = (
            f"Projeto: {ctx.project.name}\nRequisitos:\n{ctx.project.requirements}\n\n"
            f"Plano aprovado (JSON resumido):\n{json.dumps({k: plan_data.get(k) for k in ('summary', 'components', 'entities', 'api_endpoints', 'acceptance_criteria', 'tests_planned', 'folder_structure')}, ensure_ascii=False)[:12000]}\n\n"
            f"Escopo desta iteração:\n{scope}\n\n"
            f"Arquivos existentes no workspace ({len(existing)}):\n{json.dumps(existing, ensure_ascii=False)[:40000]}"
        )
        system = DEV_SYSTEM.format(language=ctx.project.language)
        change: CodeChange = ctx.ai(system=system, prompt=prompt, schema=CodeChange).data  # type: ignore[assignment]
        if not change.files:
            raise AgentError("A IA não retornou arquivos")
        commit = _apply_change(ctx, change, f"Desenvolvimento: {change.summary[:150]}", "Agente de Desenvolvimento")
        ctx.log(f"{len(commit['files'])} arquivo(s) gravado(s); commit {commit['commit'][:10]}")
        return {"base_commit": base_commit, "commit": commit["commit"], "files": commit["files"],
                "summary": change.summary, "notes": change.notes, "test_command": change.test_command}

    def fix(self, ctx: AgentContext, test_output: str) -> dict[str, Any]:
        workspace = Workspace(ctx.project.id)
        existing = workspace.snapshot()
        prompt = (
            "Os testes automatizados falharam no ambiente isolado. Corrija o código (ou testes incorretos) para que passem, "
            "sem remover verificações legítimas.\n\n"
            f"Saída dos testes (final):\n{test_output[-12000:]}\n\nArquivos atuais:\n{json.dumps(existing, ensure_ascii=False)[:60000]}"
        )
        system = DEV_SYSTEM.format(language=ctx.project.language)
        change: CodeChange = ctx.ai(system=system, prompt=prompt, schema=CodeChange).data  # type: ignore[assignment]
        commit = _apply_change(ctx, change, f"Correção após falha de testes: {change.summary[:120]}", "Agente de Desenvolvimento")
        ctx.run.status = "succeeded"
        ctx.run.summary = change.summary
        ctx.run.finished_at = utcnow()
        ctx.db.commit()
        return {"commit": commit["commit"], "files": commit["files"], "summary": change.summary}


class QAAgent(Agent):
    name = "qa"
    title = "Testes e Qualidade"
    description = "Executa testes em ambiente isolado (sem rede, usuário sem privilégios, limites de recursos) e aciona correções."
    responsibilities = ["Executar testes autorizados", "Analisar resultados e logs", "Identificar regressões", "Solicitar correções ao desenvolvedor"]

    def run(self, ctx: AgentContext) -> dict[str, Any]:
        if ctx.project is None:
            raise NonRetryableError("QA precisa de um projeto")
        workspace = Workspace(ctx.project.id)
        if not workspace.exists:
            raise NonRetryableError("O projeto ainda não tem código no workspace")
        network = bool((ctx.project.settings or {}).get("sandbox_network"))
        if network and ctx.approved("sandbox.network") is None:
            raise ApprovalRequired("sandbox.network", "Permitir acesso à rede durante a execução de testes deste projeto.")
        detected = detect_test_command(workspace.root)
        if detected is None:
            raise NonRetryableError("Nenhum teste automatizado detectado no workspace (pytest, node --test ou npm test)",
                                    result={"passed": False, "reason": "sem testes"})
        name, command = detected
        allow_fix = ctx.params.get("fix", True)
        max_fix = int((ctx.project.settings or {}).get("max_fix_iterations", 2))
        runs: list[dict[str, Any]] = []
        fixes: list[dict[str, Any]] = []
        while True:
            ctx.check_cancel()
            ctx.log(f"Executando '{' '.join(command)}' no sandbox (rede {'habilitada' if network else 'desabilitada'})")
            try:
                result = run_in_sandbox(workspace.root, command, network=network, cancel_check=ctx.cancel_requested)
            except SandboxUnavailable as exc:
                raise NonRetryableError(str(exc)) from exc
            data = result.to_dict()
            data["commit"] = workspace.head()
            runs.append(data)
            ctx.log(f"Resultado: {'aprovado' if result.passed else 'reprovado'} (código {result.exit_code}, {result.duration_seconds}s, backend {result.backend})")
            if result.cancelled:
                ctx.check_cancel()
            if result.passed or not allow_fix or len(fixes) >= max_fix or not ctx.ai_available():
                break
            from .registry import AGENTS

            dev_ctx = ctx.delegate("developer")
            try:
                fixes.append(AGENTS["developer"].fix(dev_ctx, result.output))  # type: ignore[attr-defined]
            except AgentError as exc:
                dev_ctx.run.status = "failed"
                dev_ctx.run.error = str(exc)
                dev_ctx.run.finished_at = utcnow()
                ctx.db.commit()
                ctx.log(f"Correção automática falhou: {exc}")
                break
        passed = runs[-1]["passed"]
        md = [f"# Resultado dos testes — {ctx.project.name}", "",
              f"- **Comando:** `{' '.join(command)}` ({name})", f"- **Execuções:** {len(runs)}",
              f"- **Correções automáticas:** {len(fixes)}", f"- **Resultado final:** {'✅ aprovado' if passed else '❌ reprovado'}", ""]
        for i, r in enumerate(runs, 1):
            md += [f"## Execução {i} — {'aprovada' if r['passed'] else 'reprovada'}",
                   f"commit `{(r['commit'] or '')[:10]}` · backend `{r['backend']}` · rede {'sim' if r['network'] else 'não'} · "
                   f"{r['duration_seconds']}s · código de saída {r['exit_code']}{' · tempo esgotado' if r['timed_out'] else ''}",
                   "", "```", r["output"][-8000:], "```", ""]
        artifact = ctx.add_artifact("test_log", f"Testes — {ctx.project.name}", "\n".join(md),
                                    data={"runs": runs, "fixes": fixes, "passed": passed})
        summary = {"passed": passed, "runs": len(runs), "fixes": len(fixes), "artifact_id": artifact.id,
                   "test_command": " ".join(command), "final_commit": runs[-1]["commit"]}
        if not passed:
            raise NonRetryableError(f"Testes reprovados após {len(fixes)} correção(ões) automática(s)", result=summary)
        return summary
