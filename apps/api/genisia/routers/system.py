from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import audit
from ..agents.registry import AGENTS
from ..ai.providers import EFFORT_LEVELS, PRICING_PER_MTOK, SUPPORTED_MODELS, resolve_provider
from ..analysis.rea_adapter import rea_status
from ..config import settings
from ..db import get_db
from ..deps import Pagination, current_user
from ..execution.sandbox import sandbox_status
from ..models import AgentRun, Approval, AuditEvent, Integration, KnowledgeItem, KnowledgeSource, Project, Repository, Task, User
from ..orchestrator.workflows import WORKFLOWS
from ..schemas import AIConfigIn
from ..security import encrypt_secret

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    db.execute(select(1))
    return {"status": "ok", "database": db.get_bind().dialect.name}


@router.get("/agents")
def agents(db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[dict]:
    stats = db.execute(
        select(AgentRun.agent, AgentRun.status, func.count(), func.coalesce(func.sum(AgentRun.cost_usd), 0.0),
               func.coalesce(func.sum(AgentRun.input_tokens + AgentRun.output_tokens), 0))
        .join(Task, Task.id == AgentRun.task_id).where(Task.owner_id == user.id).group_by(AgentRun.agent, AgentRun.status)
    ).all()
    by_agent: dict[str, dict] = {}
    for agent, st, count, cost, tokens in stats:
        entry = by_agent.setdefault(agent, {"runs": 0, "by_status": {}, "cost_usd": 0.0, "tokens": 0})
        entry["runs"] += count
        entry["by_status"][st] = count
        entry["cost_usd"] = round(entry["cost_usd"] + float(cost), 6)
        entry["tokens"] += int(tokens)
    running = dict(db.execute(select(Task.agent, func.count()).where(Task.owner_id == user.id, Task.status == "running")
                              .group_by(Task.agent)).all())
    return [{**a.info(), "state": "ocupado" if running.get(a.name) else "disponível", "running": running.get(a.name, 0),
             "stats": by_agent.get(a.name, {"runs": 0, "by_status": {}, "cost_usd": 0.0, "tokens": 0})} for a in AGENTS.values()]


@router.get("/workflows")
def workflows(user: User = Depends(current_user)) -> list[dict]:
    return [{"name": w.name, "title": w.title, "description": w.description, "requires": w.requires,
             "steps": [{"key": s.key, "agent": s.agent, "title": s.title, "depends_on": s.depends_on, "optional": s.optional}
                       for s in w.steps]} for w in WORKFLOWS.values()]


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    roots = select(Task).where(Task.owner_id == user.id, Task.parent_id.is_(None))
    by_status = dict(db.execute(select(Task.status, func.count()).where(Task.owner_id == user.id, Task.parent_id.is_(None))
                                .group_by(Task.status)).all())
    cost, tin, tout = db.execute(
        select(func.coalesce(func.sum(AgentRun.cost_usd), 0.0), func.coalesce(func.sum(AgentRun.input_tokens), 0),
               func.coalesce(func.sum(AgentRun.output_tokens), 0)).join(Task, Task.id == AgentRun.task_id).where(Task.owner_id == user.id)
    ).one()
    recent_projects = db.scalars(select(Project).where(Project.owner_id == user.id).order_by(Project.updated_at.desc()).limit(5)).all()
    active = db.scalars(roots.where(Task.status.in_(["queued", "running", "awaiting_approval"])).order_by(Task.created_at.desc()).limit(10)).all()
    failed = db.scalars(roots.where(Task.status == "failed").order_by(Task.finished_at.desc()).limit(5)).all()
    activity = db.scalars(
        select(AuditEvent).where((AuditEvent.actor_id == user.id) | AuditEvent.project_id.in_(select(Project.id).where(Project.owner_id == user.id)))
        .order_by(AuditEvent.created_at.desc()).limit(15)).all()
    pending = db.scalar(select(func.count()).select_from(Approval).where(Approval.owner_id == user.id, Approval.status == "pending"))
    knowledge_items = db.scalar(select(func.count()).select_from(KnowledgeItem).join(KnowledgeSource).where(
        (KnowledgeSource.owner_id == user.id) | KnowledgeSource.owner_id.is_(None)))
    repos = db.scalar(select(func.count()).select_from(Repository).where(Repository.owner_id == user.id))
    task_row = lambda t: {"id": t.id, "title": t.title, "status": t.status, "project_id": t.project_id, "kind": t.kind,  # noqa: E731
                          "error": t.error, "created_at": t.created_at.isoformat()}
    return {
        "counts": {"projects": db.scalar(select(func.count()).select_from(Project).where(Project.owner_id == user.id)),
                   "repositories": repos, "knowledge_items": knowledge_items, "pending_approvals": pending,
                   "workflows_by_status": by_status},
        "ai_usage": {"cost_usd": round(float(cost), 6), "input_tokens": int(tin), "output_tokens": int(tout),
                     "note": "Custo estimado pela tabela de preços por token; confirme no painel do provedor."},
        "recent_projects": [{"id": p.id, "name": p.name, "status": p.status, "updated_at": p.updated_at.isoformat()} for p in recent_projects],
        "active_tasks": [task_row(t) for t in active],
        "failed_tasks": [task_row(t) for t in failed],
        "activity": [{"action": e.action, "actor": e.actor_label, "project_id": e.project_id, "created_at": e.created_at.isoformat(),
                      "details": e.details} for e in activity],
    }


@router.get("/audit")
def audit_log(page: Pagination = Depends(), db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    stmt = select(AuditEvent).where((AuditEvent.actor_id == user.id) |
                                    AuditEvent.project_id.in_(select(Project.id).where(Project.owner_id == user.id)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(AuditEvent.created_at.desc()).limit(page.limit).offset(page.offset)).all()
    return {"items": [{"id": e.id, "action": e.action, "actor": e.actor_label, "project_id": e.project_id,
                       "target_type": e.target_type, "target_id": e.target_id, "details": e.details,
                       "created_at": e.created_at.isoformat()} for e in rows],
            "total": total, "limit": page.limit, "offset": page.offset}


@router.get("/integrations")
def integrations(db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    provider = resolve_provider(db, user.id)
    rows = db.scalars(select(Integration).where(Integration.owner_id == user.id)).all()
    return {
        "ai": {**provider.status(), "supported_models": SUPPORTED_MODELS, "effort_levels": EFFORT_LEVELS,
               "pricing_per_mtok": {k: {"input": v[0], "output": v[1]} for k, v in PRICING_PER_MTOK.items()},
               "default_budget_usd": settings.default_project_budget_usd},
        "sandbox": sandbox_status(),
        "rea": rea_status(),
        "git": {"allowed_hosts": settings.git_allowed_hosts, "local_import_roots": settings.import_roots,
                "max_repo_mb": settings.max_repo_mb},
        "configured": [{"name": i.name, "kind": i.kind, "enabled": i.enabled, "config": i.config,
                        "has_secret": bool(i.secret_ciphertext), "updated_at": i.updated_at.isoformat()} for i in rows],
        "pending": [
            {"name": "GitHub OAuth", "status": "não implementado no MVP",
             "detail": "Repositórios públicos são importados por HTTPS; repositórios privados exigirão um GitHub App com permissões mínimas."},
            {"name": "Teste de endpoints de APIs públicas", "status": "não implementado no MVP",
             "detail": "O catálogo é pesquisável; chamadas externas exigirão aprovação e um executor com lista de hosts permitidos."},
        ],
    }


@router.put("/integrations/ai")
def configure_ai(body: AIConfigIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    if body.model and body.model not in SUPPORTED_MODELS:
        raise HTTPException(422, f"Modelo não suportado: {body.model}")
    integration = db.scalar(select(Integration).where(Integration.owner_id == user.id, Integration.name == "anthropic"))
    if integration is None:
        integration = Integration(owner_id=user.id, name="anthropic", kind="ai_provider", config={})
        db.add(integration)
    config = dict(integration.config or {})
    if body.model:
        config["model"] = body.model
    if body.effort:
        config["effort"] = body.effort
    integration.config = config
    integration.enabled = body.enabled
    if body.api_key:
        integration.secret_ciphertext = encrypt_secret(body.api_key.strip())
    audit.record(db, "integration.ai_configured", actor_id=user.id, target_type="integration",
                 details={"model": config.get("model"), "effort": config.get("effort"), "key_updated": bool(body.api_key)})
    db.commit()
    return {"ok": True, "status": resolve_provider(db, user.id).status()}


@router.delete("/integrations/ai/key")
def remove_ai_key(db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    integration = db.scalar(select(Integration).where(Integration.owner_id == user.id, Integration.name == "anthropic"))
    if integration:
        integration.secret_ciphertext = None
        audit.record(db, "integration.ai_key_removed", actor_id=user.id)
        db.commit()
    return {"ok": True}
