from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import Pagination, current_user, get_owned_task
from ..models import AgentRun, Approval, Artifact, Task, User
from ..orchestrator.engine import WorkflowError, cancel_task, retry_task
from ..schemas import AgentRunOut, ApprovalOut, ArtifactOut, ArtifactSummary, Page, TaskDetail, TaskOut

router = APIRouter(prefix="/api", tags=["tasks"])


@router.get("/tasks", response_model=Page[TaskOut])
def list_tasks(status_: str | None = Query(None, alias="status"), page: Pagination = Depends(), db: Session = Depends(get_db),
               user: User = Depends(current_user)) -> dict:
    stmt = select(Task).where(Task.owner_id == user.id, Task.parent_id.is_(None))
    if status_:
        stmt = stmt.where(Task.status == status_)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.order_by(Task.created_at.desc()).limit(page.limit).offset(page.offset)).all()
    return {"items": items, "total": total, "limit": page.limit, "offset": page.offset}


@router.get("/tasks/{task_id}", response_model=TaskDetail)
def get_task(task_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    task = get_owned_task(task_id, db, user)
    steps = db.scalars(select(Task).where(Task.parent_id == task.id).order_by(Task.created_at)).all()
    ids = [task.id] + [s.id for s in steps]
    runs = db.scalars(select(AgentRun).where(AgentRun.task_id.in_(ids)).order_by(AgentRun.started_at)).all()
    approvals = db.scalars(select(Approval).where(Approval.task_id.in_(ids)).order_by(Approval.created_at)).all()
    data = TaskOut.model_validate(task).model_dump()
    data["steps"] = [TaskOut.model_validate(s) for s in steps]
    data["runs"] = [AgentRunOut.model_validate(r) for r in runs]
    data["approvals"] = [ApprovalOut.model_validate(a) for a in approvals]
    return data


@router.post("/tasks/{task_id}/cancel", response_model=TaskOut)
def cancel(task_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> Task:
    task = get_owned_task(task_id, db, user)
    if task.status in {"succeeded", "failed", "cancelled"} and task.parent_id is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "O fluxo já terminou")
    return cancel_task(db, task, user.id)


@router.post("/tasks/{task_id}/retry", response_model=TaskOut)
def retry(task_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> Task:
    task = get_owned_task(task_id, db, user)
    try:
        return retry_task(db, task, user.id)
    except WorkflowError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.get("/tasks/{task_id}/logs")
def task_logs(task_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    task = get_owned_task(task_id, db, user)
    ids = [task.id] + list(db.scalars(select(Task.id).where(Task.parent_id == task.id)))
    runs = db.scalars(select(AgentRun).where(AgentRun.task_id.in_(ids)).order_by(AgentRun.started_at)).all()
    return {"task_id": task.id, "logs": [{"run_id": r.id, "agent": r.agent, "status": r.status, "attempt": r.attempt,
                                          "started_at": r.started_at.isoformat(), "logs": r.logs} for r in runs]}


@router.get("/agent-runs", response_model=Page[AgentRunOut])
def list_runs(agent: str | None = None, page: Pagination = Depends(), db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    stmt = select(AgentRun).join(Task, Task.id == AgentRun.task_id).where(Task.owner_id == user.id)
    if agent:
        stmt = stmt.where(AgentRun.agent == agent)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.order_by(AgentRun.started_at.desc()).limit(page.limit).offset(page.offset)).all()
    return {"items": items, "total": total, "limit": page.limit, "offset": page.offset}


@router.get("/artifacts", response_model=Page[ArtifactSummary])
def list_artifacts(kind: str | None = Query(None, max_length=40), page: Pagination = Depends(), db: Session = Depends(get_db),
                   user: User = Depends(current_user)) -> dict:
    stmt = select(Artifact).where(Artifact.owner_id == user.id)
    if kind:
        stmt = stmt.where(Artifact.kind == kind)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.order_by(Artifact.created_at.desc()).limit(page.limit).offset(page.offset)).all()
    return {"items": items, "total": total, "limit": page.limit, "offset": page.offset}


@router.get("/artifacts/{artifact_id}", response_model=ArtifactOut)
def get_artifact(artifact_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> Artifact:
    artifact = db.get(Artifact, artifact_id)
    if artifact is None or artifact.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Artefato não encontrado")
    return artifact
