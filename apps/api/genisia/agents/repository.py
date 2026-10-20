"""Agentes de repositório: Integrações (importação), Engenheiro Reverso e ingestão de catálogos."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select

from ..analysis import rea_adapter
from ..analysis.analyzer import ANALYZER_VERSION, PERMISSIVE_LICENSES, RepositoryAnalyzer, render_markdown
from ..analysis.importer import ImportErrorDetail, clone, local_commit, remote_head, validate_local_path
from ..config import settings
from ..execution.workspace import Workspace
from ..knowledge.ingest import INGEST_PROFILES, extract_catalog, profile_for
from ..knowledge.search import build_search_text
from ..models import Artifact, KnowledgeItem, KnowledgeSource, Repository
from .base import Agent, AgentContext, AgentSkip, NonRetryableError


def get_repository(ctx: AgentContext) -> Repository:
    repo_id = ctx.params.get("repository_id")
    repo = ctx.db.get(Repository, repo_id) if repo_id else None
    if repo is None or repo.owner_id != ctx.task.owner_id:
        raise NonRetryableError("Repositório não encontrado")
    return repo


def target_path(ctx: AgentContext) -> tuple[Path, str]:
    """Diretório a analisar: repositório importado ou workspace do projeto."""
    if ctx.params.get("repository_id"):
        repo = get_repository(ctx)
        if not repo.local_path or not Path(repo.local_path).is_dir():
            raise NonRetryableError("Repositório ainda não importado")
        return Path(repo.local_path), repo.name
    if ctx.project is not None:
        ws = Workspace(ctx.project.id)
        if not ws.exists:
            raise AgentSkip("Projeto sem código no workspace")
        return ws.root, ctx.project.name
    raise NonRetryableError("Nenhum alvo de análise")


class IntegrationAgent(Agent):
    name = "integrations"
    title = "Integrações"
    description = "Importa repositórios autorizados (Git HTTPS em hosts permitidos, diretório local autorizado) com limites de tamanho e tempo."
    responsibilities = ["Importar repositórios", "Validar origens (proteção contra SSRF)", "Registrar commit analisado", "Repetição controlada"]

    def run(self, ctx: AgentContext) -> dict[str, Any]:
        repo = get_repository(ctx)
        repo.status = "importing"
        ctx.db.commit()
        try:
            if repo.source_type == "git":
                dest = settings.data_dir / "repositories" / repo.id
                current = remote_head(repo.source_url, repo.ref) if repo.commit_sha and (dest / ".git").is_dir() else None
                if current and current == repo.commit_sha:
                    ctx.log(f"Cópia local já está no commit remoto {current[:10]}; clonagem dispensada")
                    sha = current
                else:
                    ctx.log(f"Clonando {repo.source_url} (raso, sem submódulos)")
                    sha = clone(repo.source_url, dest, repo.ref)
                repo.local_path = str(dest)
            elif repo.source_type == "local":
                path = validate_local_path(repo.source_url)
                sha = local_commit(path)
                repo.local_path = str(path)
            elif repo.source_type == "upload":
                if not repo.local_path or not Path(repo.local_path).is_dir():
                    raise NonRetryableError("Arquivo enviado não encontrado")
                sha = None
            else:
                raise NonRetryableError(f"Tipo de origem desconhecido: {repo.source_type}")
        except ImportErrorDetail as exc:
            repo.status = "error"
            ctx.db.commit()
            raise NonRetryableError(str(exc)) from exc
        repo.commit_sha = sha
        repo.status = "imported"
        ctx.db.commit()
        ctx.log(f"Importado: commit {sha or '(sem git)'}")
        return {"repository_id": repo.id, "commit": sha, "path": repo.local_path}


class ReverseEngineerAgent(Agent):
    name = "reverse_engineer"
    title = "Engenheiro Reverso"
    description = ("Análise estática de projetos autorizados: estrutura, tecnologias, dependências, interfaces, riscos. "
                   "Separa fatos comprovados de hipóteses. Usa o REA como adaptador opcional para JS/TS.")
    responsibilities = ["Mapear arquivos e dependências", "Identificar frameworks", "Mapear APIs e pontos de entrada",
                        "Produzir documentação técnica", "Recomendar refatorações"]

    def run(self, ctx: AgentContext) -> dict[str, Any]:
        path, name = target_path(ctx)
        repo = get_repository(ctx) if ctx.params.get("repository_id") else None
        commit = repo.commit_sha if repo else None
        # Evita repetir análise quando o commit e a versão do analisador não mudaram.
        if repo and commit and not ctx.params.get("force"):
            cached = ctx.db.scalars(select(Artifact).where(Artifact.repository_id == repo.id, Artifact.kind == "analysis")
                                    .order_by(Artifact.created_at.desc())).first()
            if cached and (cached.data or {}).get("commit") == commit and (cached.data or {}).get("analyzer_version") == ANALYZER_VERSION:
                ctx.log(f"Análise reaproveitada: commit {commit[:10]} já analisado (artefato {cached.id})")
                return {"artifact_id": cached.id, "cached": True, "summary": (cached.data or {}).get("summary")}
        ctx.log(f"Analisando {name} estaticamente")
        report = RepositoryAnalyzer(path, name).analyze()
        ctx.check_cancel()
        languages = {l["language"] for l in report["inventory"]["languages"]}
        use_rea = ctx.params.get("use_rea", True) and languages & {"JavaScript", "TypeScript"}
        if use_rea:
            status = rea_adapter.rea_status()
            if status["available"]:
                ctx.log(f"Executando REA {status.get('version')} (analyze-javascript-application)")
                report["rea"] = rea_adapter.analyze_javascript(path)
                ctx.log(f"REA: {report['rea'].get('status')}")
            else:
                report["rea"] = {"status": "unavailable", "reason": status["reason"]}
        report["commit"] = commit
        source = repo.source_url if repo else f"workspace do projeto {name}"
        md = render_markdown(report, source=source, commit=commit)
        if report.get("rea", {}).get("status") == "ok":
            rea = report["rea"]
            md += "\n## Grafo JavaScript (REA)\n\n" + "\n".join([
                f"- Ferramenta: {rea['tool']} · evidência `{rea['evidence_id']}`",
                "- Nós por tipo: " + ", ".join(f"{k} ({v})" for k, v in rea["node_kinds"].items()),
                "- Relações: " + ", ".join(f"{k} ({v})" for k, v in rea["relations"].items()),
                "- Estados de evidência: " + ", ".join(f"{k}: {v}" for k, v in rea["evidence_states"].items()),
                "- Módulos externos: " + ", ".join(f"`{m['module']}` ({m['count']})" for m in rea["external_modules"][:15]),
                "", "Limitações declaradas pelo REA:", *[f"- {l}" for l in rea["limitations"]], ""])
        summary = {
            "files": report["inventory"]["file_count"], "code_lines": report["inventory"]["code_lines"],
            "languages": [l["language"] for l in report["inventory"]["languages"][:5]],
            "frameworks": [f["name"] for f in report["manifests"]["frameworks"]][:15],
            "license": report["license"]["spdx"], "kinds": report["classification"]["kinds"],
            "findings": len(report["findings"]), "secrets": len(report["secrets"]),
            "rea": report.get("rea", {}).get("status"),
        }
        report["summary"] = summary
        artifact = ctx.add_artifact("analysis", f"Análise — {name}", md, data=report, repository_id=repo.id if repo else None)
        if repo:
            repo.last_analysis_artifact_id = artifact.id
            repo.summary = summary
            repo.status = "analyzed"
            ctx.db.commit()
        return {"artifact_id": artifact.id, "cached": False, "summary": summary}


def ingest_catalog(ctx: AgentContext) -> dict[str, Any]:
    """Extrai o catálogo de links/APIs/livros de um repositório importado para a base de conhecimento."""
    repo = get_repository(ctx)
    if not repo.local_path:
        raise NonRetryableError("Repositório ainda não importado")
    profile_name = ctx.params.get("profile") or profile_for(repo.name)
    if profile_name not in INGEST_PROFILES:
        raise NonRetryableError(f"Perfil de ingestão desconhecido: {profile_name}")
    items, used = extract_catalog(Path(repo.local_path), profile_name)
    if not items:
        raise NonRetryableError(f"Nenhum item extraído (perfil {profile_name}; arquivos: {used or 'nenhum encontrado'})")
    analysis = ctx.db.get(Artifact, repo.last_analysis_artifact_id) if repo.last_analysis_artifact_id else None
    license_ = ((analysis.data or {}).get("license") or {}).get("spdx") if analysis else None
    # Catálogos de repositórios Git públicos viram conhecimento global da plataforma (compartilhado
    # entre usuários); ZIPs enviados e diretórios locais permanecem privados de quem os importou.
    owner_id = None if repo.source_type == "git" else ctx.task.owner_id
    source = ctx.db.scalar(select(KnowledgeSource).where(
        KnowledgeSource.owner_id.is_(None) if owner_id is None else KnowledgeSource.owner_id == owner_id,
        KnowledgeSource.origin_url == repo.source_url))
    if source is None:
        source = KnowledgeSource(owner_id=owner_id, name=repo.name, kind=INGEST_PROFILES[profile_name]["kind"],
                                 origin_url=repo.source_url, meta={})
        ctx.db.add(source)
        ctx.db.flush()
    else:
        ctx.db.execute(delete(KnowledgeItem).where(KnowledgeItem.source_id == source.id))
    links_only = license_ not in PERMISSIVE_LICENSES
    if links_only:
        # Sem licença permissiva: guardamos apenas título e URL (referência), nunca descrições.
        for it in items:
            it.description = ""
        ctx.log(f"Licença '{license_ or 'ausente'}' não é permissiva: somente títulos e links serão indexados")
    source.license = license_
    source.origin_commit = repo.commit_sha
    source.meta = {"profile": profile_name, "files": used, "repository_id": repo.id,
                   "links_only": links_only,
                   "note": "Somente metadados e links; o conteúdo referenciado não é copiado."}
    for it in items:
        ctx.db.add(KnowledgeItem(
            source_id=source.id, item_type=it.item_type, title=it.title[:400], url=it.url[:1000], description=it.description,
            category=it.category[:300], tags=it.tags, extra=it.extra, origin_path=it.origin_path,
            search_text=build_search_text(it.title, it.description, it.category, it.tags),
        ))
    source.item_count = len(items)
    source.indexed_at = datetime.now(timezone.utc)
    ctx.db.commit()
    by_type: dict[str, int] = {}
    for it in items:
        by_type[it.item_type] = by_type.get(it.item_type, 0) + 1
    ctx.log(f"{len(items)} item(ns) indexado(s) de {', '.join(used)} (licença da fonte: {license_ or 'desconhecida'})")
    return {"source_id": source.id, "items": len(items), "by_type": by_type, "files": used, "license": license_,
            "links_only": links_only}
