"""Gatilhos agendados (Centro de Automação) e trilhas de aprendizagem."""
from __future__ import annotations

from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import audit
from ..db import get_db
from ..deps import current_user, get_owned_project, get_owned_repository
from ..knowledge.learning import EmptyPath, build_path, serialize_path
from ..models import LearningPath, LearningPathItem, ScheduledTrigger, User, utcnow
from ..orchestrator.scheduler import MAX_INTERVAL_MINUTES, MIN_INTERVAL_MINUTES, SCHEDULABLE_WORKFLOWS

router = APIRouter(prefix="/api", tags=["automation"])


# ---------------------------------------------------------------- gatilhos
class TriggerIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    workflow: Literal["test", "analyze_repository", "ingest_knowledge"]
    interval_minutes: int = Field(ge=MIN_INTERVAL_MINUTES, le=MAX_INTERVAL_MINUTES)
    project_id: str | None = None
    repository_id: str | None = None
    enabled: bool = True


class TriggerUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    interval_minutes: int | None = Field(None, ge=MIN_INTERVAL_MINUTES, le=MAX_INTERVAL_MINUTES)
    enabled: bool | None = None


def _trigger_out(t: ScheduledTrigger) -> dict:
    return {"id": t.id, "name": t.name, "workflow": t.workflow, "interval_minutes": t.interval_minutes, "enabled": t.enabled,
            "project_id": t.project_id, "repository_id": t.repository_id, "next_run_at": t.next_run_at.isoformat(),
            "last_run_at": t.last_run_at.isoformat() if t.last_run_at else None, "last_task_id": t.last_task_id,
            "last_error": t.last_error, "run_count": t.run_count, "created_at": t.created_at.isoformat()}


def _owned_trigger(trigger_id: str, db: Session, user: User) -> ScheduledTrigger:
    trigger = db.get(ScheduledTrigger, trigger_id)
    if trigger is None or trigger.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gatilho não encontrado")
    return trigger


@router.get("/triggers")
def list_triggers(db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[dict]:
    rows = db.scalars(select(ScheduledTrigger).where(ScheduledTrigger.owner_id == user.id).order_by(ScheduledTrigger.created_at)).all()
    return [_trigger_out(t) for t in rows]


@router.post("/triggers", status_code=201)
def create_trigger(body: TriggerIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    target = SCHEDULABLE_WORKFLOWS[body.workflow]
    if target == "project":
        if not body.project_id:
            raise HTTPException(422, "Este fluxo exige um projeto")
        get_owned_project(body.project_id, db, user)
        repository_id = None
        project_id = body.project_id
    else:
        if not body.repository_id:
            raise HTTPException(422, "Este fluxo exige um repositório")
        repo = get_owned_repository(body.repository_id, db, user)
        if repo.source_type == "upload":
            raise HTTPException(422, "Arquivos enviados (ZIP) não mudam; agende apenas repositórios Git ou locais")
        repository_id, project_id = repo.id, repo.project_id
    if db.scalar(select(func.count()).select_from(ScheduledTrigger).where(ScheduledTrigger.owner_id == user.id)) >= 20:
        raise HTTPException(429, "Limite de 20 gatilhos por usuário")
    trigger = ScheduledTrigger(owner_id=user.id, project_id=project_id, repository_id=repository_id, name=body.name.strip(),
                               workflow=body.workflow, interval_minutes=body.interval_minutes, enabled=body.enabled,
                               next_run_at=utcnow() + timedelta(minutes=body.interval_minutes))
    db.add(trigger)
    db.flush()
    audit.record(db, "trigger.created", actor_id=user.id, project_id=project_id, target_type="trigger", target_id=trigger.id,
                 details={"workflow": body.workflow, "interval_minutes": body.interval_minutes})
    db.commit()
    return _trigger_out(trigger)


@router.patch("/triggers/{trigger_id}")
def update_trigger(trigger_id: str, body: TriggerUpdate, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    trigger = _owned_trigger(trigger_id, db, user)
    changes = body.model_dump(exclude_unset=True)
    for key, value in changes.items():
        if value is not None:
            setattr(trigger, key, value)
    if body.interval_minutes or body.enabled:
        trigger.next_run_at = utcnow() + timedelta(minutes=trigger.interval_minutes)
    audit.record(db, "trigger.updated", actor_id=user.id, project_id=trigger.project_id, target_type="trigger",
                 target_id=trigger.id, details={k: v for k, v in changes.items() if v is not None})
    db.commit()
    return _trigger_out(trigger)


@router.delete("/triggers/{trigger_id}", status_code=204)
def delete_trigger(trigger_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> Response:
    trigger = _owned_trigger(trigger_id, db, user)
    audit.record(db, "trigger.deleted", actor_id=user.id, project_id=trigger.project_id, details={"name": trigger.name})
    db.delete(trigger)
    db.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------- trilhas de aprendizagem
class PathIn(BaseModel):
    project_id: str | None = None
    goal: str = Field("", max_length=4000)
    title: str | None = Field(None, max_length=200)


class PathItemUpdate(BaseModel):
    status: Literal["todo", "doing", "done"]


def _owned_path(path_id: str, db: Session, user: User) -> LearningPath:
    path = db.get(LearningPath, path_id)
    if path is None or path.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Trilha não encontrada")
    return path


def _items(db: Session, path_id: str) -> list[LearningPathItem]:
    return list(db.scalars(select(LearningPathItem).where(LearningPathItem.path_id == path_id).order_by(LearningPathItem.position)))


@router.post("/learning/paths", status_code=201)
def create_path(body: PathIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    goal = body.goal.strip()
    title = body.title
    if body.project_id:
        project = get_owned_project(body.project_id, db, user)
        goal = goal or f"{project.description} {project.requirements} {' '.join(project.stack or [])} {project.language}"
        title = title or f"Trilha para {project.name}"
    if not goal:
        raise HTTPException(422, "Informe um objetivo ou um projeto")
    try:
        path = build_path(db, owner_id=user.id, goal=goal, title=title or goal[:80], project_id=body.project_id)
    except EmptyPath as exc:
        raise HTTPException(422, str(exc)) from exc
    audit.record(db, "learning.path_created", actor_id=user.id, project_id=body.project_id, target_type="learning_path",
                 target_id=path.id)
    db.commit()
    return serialize_path(path, _items(db, path.id))


@router.get("/learning/paths")
def list_paths(db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[dict]:
    paths = db.scalars(select(LearningPath).where(LearningPath.owner_id == user.id).order_by(LearningPath.created_at.desc())).all()
    return [serialize_path(p, _items(db, p.id)) for p in paths]


@router.get("/learning/paths/{path_id}")
def get_path(path_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    path = _owned_path(path_id, db, user)
    return serialize_path(path, _items(db, path.id))


@router.patch("/learning/paths/{path_id}/items/{item_id}")
def update_path_item(path_id: str, item_id: str, body: PathItemUpdate, db: Session = Depends(get_db),
                     user: User = Depends(current_user)) -> dict:
    path = _owned_path(path_id, db, user)
    item = db.get(LearningPathItem, item_id)
    if item is None or item.path_id != path.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item não encontrado")
    item.status = body.status
    item.completed_at = utcnow() if body.status == "done" else None
    db.commit()
    return serialize_path(path, _items(db, path.id))


@router.delete("/learning/paths/{path_id}", status_code=204)
def delete_path(path_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> Response:
    path = _owned_path(path_id, db, user)
    db.delete(path)
    db.commit()
    return Response(status_code=204)
