from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import audit
from ..config import settings
from ..db import get_db
from ..deps import Pagination, current_user, get_owned_project
from ..execution.workspace import Workspace, WorkspaceError
from ..models import AgentRun, Approval, Artifact, AuditEvent, Project, Task, User
from ..orchestrator.engine import WorkflowError, create_workflow
from ..schemas import (ApprovalOut, ArtifactSummary, Page, ProjectDetail, ProjectIn, ProjectOut, ProjectUpdate, TaskOut,
                       WorkflowIn)

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> Project:
    project = Project(owner_id=user.id, name=body.name.strip(), description=body.description, requirements=body.requirements,
                      language=body.language, stack=body.stack, settings=body.settings.model_dump(),
                      status="draft" if not body.requirements.strip() else "requirements")
    db.add(project)
    db.flush()
    Workspace(project.id).ensure()
    audit.record(db, "project.created", actor_id=user.id, project_id=project.id, target_type="project", target_id=project.id,
                 details={"name": project.name})
    db.commit()
    return project


@router.get("", response_model=Page[ProjectOut])
def list_projects(q: str | None = Query(None, max_length=100), page: Pagination = Depends(),
                  db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    stmt = select(Project).where(Project.owner_id == user.id)
    if q:
        stmt = stmt.where(Project.name.ilike(f"%{q}%"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.order_by(Project.updated_at.desc()).limit(page.limit).offset(page.offset)).all()
    return {"items": items, "total": total, "limit": page.limit, "offset": page.offset}


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(project_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    project = get_owned_project(project_id, db, user)
    counts = dict(db.execute(select(Task.status, func.count()).where(Task.project_id == project.id, Task.parent_id.is_(None))
                             .group_by(Task.status)).all())
    cost, tin, tout = db.execute(select(func.coalesce(func.sum(AgentRun.cost_usd), 0.0), func.coalesce(func.sum(AgentRun.input_tokens), 0),
                                        func.coalesce(func.sum(AgentRun.output_tokens), 0)).where(AgentRun.project_id == project.id)).one()
    pending = db.scalar(select(func.count()).select_from(Approval).where(Approval.project_id == project.id, Approval.status == "pending"))
    data = ProjectOut.model_validate(project).model_dump()
    data["stats"] = {"workflows_by_status": counts, "ai_cost_usd": round(float(cost), 6), "input_tokens": int(tin),
                     "output_tokens": int(tout), "pending_approvals": pending,
                     "budget_usd": (project.settings or {}).get("ai_budget_usd", settings.default_project_budget_usd)}
    return data


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(project_id: str, body: ProjectUpdate, db: Session = Depends(get_db), user: User = Depends(current_user)) -> Project:
    project = get_owned_project(project_id, db, user)
    changes = body.model_dump(exclude_unset=True)
    if "settings" in changes and changes["settings"] is not None:
        new_settings = body.settings.model_dump()  # type: ignore[union-attr]
        if new_settings.get("sandbox_network") and not (project.settings or {}).get("sandbox_network"):
            audit.record(db, "project.sandbox_network_requested", actor_id=user.id, project_id=project.id,
                         details={"note": "A execução com rede ainda exigirá aprovação por tarefa"})
        project.settings = new_settings
        changes.pop("settings")
    for key, value in changes.items():
        if value is not None:
            setattr(project, key, value)
    if project.requirements.strip() and project.status == "draft":
        project.status = "requirements"
    audit.record(db, "project.updated", actor_id=user.id, project_id=project.id, target_type="project", target_id=project.id,
                 details={"fields": sorted(body.model_dump(exclude_unset=True).keys())})
    db.commit()
    return project


@router.delete("/{project_id}", response_model=ApprovalOut, status_code=202)
def request_delete_project(project_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> Approval:
    """Excluir é irreversível: cria uma solicitação de aprovação, executada somente após confirmação."""
    project = get_owned_project(project_id, db, user)
    existing = db.scalar(select(Approval).where(Approval.project_id == project.id, Approval.action == "project.delete",
                                                Approval.status == "pending"))
    if existing:
        return existing
    approval = Approval(owner_id=user.id, project_id=project.id, action="project.delete", requested_by="user",
                        description=f"Excluir definitivamente o projeto '{project.name}', seu workspace, tarefas e artefatos.")
    db.add(approval)
    audit.record(db, "approval.requested", actor_id=user.id, project_id=project.id, details={"action": "project.delete"})
    db.commit()
    return approval


@router.post("/{project_id}/workflows", response_model=TaskOut, status_code=202)
def start_workflow(project_id: str, body: WorkflowIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> Task:
    project = get_owned_project(project_id, db, user)
    if body.workflow in {"mission", "plan"} and not (project.requirements.strip() or project.description.strip()):
        raise HTTPException(422, "Registre os requisitos do projeto antes de solicitar um plano")
    active = db.scalar(select(func.count()).select_from(Task).where(
        Task.project_id == project.id, Task.parent_id.is_(None), Task.status.in_(["queued", "running", "awaiting_approval"])))
    if active and active >= 3:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Muitos fluxos ativos neste projeto; aguarde ou cancele algum")
    params = {"develop": {"instructions": body.instructions}} if body.instructions else {}
    try:
        return create_workflow(db, owner_id=user.id, workflow=body.workflow, project_id=project.id,
                               objective=body.objective, params=params)
    except WorkflowError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/{project_id}/tasks", response_model=Page[TaskOut])
def project_tasks(project_id: str, page: Pagination = Depends(), db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    project = get_owned_project(project_id, db, user)
    stmt = select(Task).where(Task.project_id == project.id, Task.parent_id.is_(None))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.order_by(Task.created_at.desc()).limit(page.limit).offset(page.offset)).all()
    return {"items": items, "total": total, "limit": page.limit, "offset": page.offset}


@router.get("/{project_id}/artifacts", response_model=Page[ArtifactSummary])
def project_artifacts(project_id: str, kind: str | None = None, page: Pagination = Depends(), db: Session = Depends(get_db),
                      user: User = Depends(current_user)) -> dict:
    project = get_owned_project(project_id, db, user)
    stmt = select(Artifact).where(Artifact.project_id == project.id)
    if kind:
        stmt = stmt.where(Artifact.kind == kind)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.order_by(Artifact.created_at.desc()).limit(page.limit).offset(page.offset)).all()
    return {"items": items, "total": total, "limit": page.limit, "offset": page.offset}


@router.get("/{project_id}/activity")
def project_activity(project_id: str, page: Pagination = Depends(), db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    project = get_owned_project(project_id, db, user)
    stmt = select(AuditEvent).where(AuditEvent.project_id == project.id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(AuditEvent.created_at.desc()).limit(page.limit).offset(page.offset)).all()
    return {"items": [{"id": e.id, "action": e.action, "actor": e.actor_label, "target_type": e.target_type, "target_id": e.target_id,
                       "details": e.details, "created_at": e.created_at.isoformat()} for e in rows],
            "total": total, "limit": page.limit, "offset": page.offset}


# ---------------------------------------------------------------- workspace (Studio)
@router.get("/{project_id}/files")
def list_files(project_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    project = get_owned_project(project_id, db, user)
    ws = Workspace(project.id)
    return {"head": ws.head(), "files": ws.list_files()}


@router.get("/{project_id}/files/content", response_class=PlainTextResponse)
def file_content(project_id: str, path: str = Query(..., max_length=300), db: Session = Depends(get_db),
                 user: User = Depends(current_user)) -> str:
    project = get_owned_project(project_id, db, user)
    try:
        return Workspace(project.id).read_file(path)
    except WorkspaceError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.put("/{project_id}/files/content")
def save_file(project_id: str, body: dict, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    """Edição manual pelo usuário no Studio; cada gravação vira um commit."""
    project = get_owned_project(project_id, db, user)
    path, content = body.get("path"), body.get("content")
    if not isinstance(path, str) or not isinstance(content, str):
        raise HTTPException(422, "Informe path e content")
    from ..execution.workspace import FileChange

    try:
        result = Workspace(project.id).write_files([FileChange(path, content)], f"Edição manual: {path}", user.name)
    except WorkspaceError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    audit.record(db, "workspace.file_saved", actor_id=user.id, project_id=project.id, details={"path": path, "commit": result["commit"]})
    db.commit()
    return result


@router.get("/{project_id}/history")
def history(project_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    project = get_owned_project(project_id, db, user)
    return {"commits": Workspace(project.id).log()}


@router.get("/{project_id}/history/{sha}", response_class=PlainTextResponse)
def commit_diff(project_id: str, sha: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> str:
    project = get_owned_project(project_id, db, user)
    try:
        return Workspace(project.id).show(sha)
    except WorkspaceError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
