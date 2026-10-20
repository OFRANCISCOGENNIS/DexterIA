from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import audit
from ..config import settings
from ..db import get_db
from ..deps import Pagination, current_user
from ..execution.workspace import Workspace
from ..models import Approval, Project, Repository, User, utcnow
from ..orchestrator.engine import WorkflowError, decide_approval
from ..schemas import ApprovalDecision, ApprovalOut, Page

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


@router.get("", response_model=Page[ApprovalOut])
def list_approvals(status_: str | None = None, page: Pagination = Depends(), db: Session = Depends(get_db),
                   user: User = Depends(current_user)) -> dict:
    stmt = select(Approval).where(Approval.owner_id == user.id)
    if status_:
        stmt = stmt.where(Approval.status == status_)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.order_by(Approval.created_at.desc()).limit(page.limit).offset(page.offset)).all()
    return {"items": items, "total": total, "limit": page.limit, "offset": page.offset}


def _execute_direct_action(db: Session, approval: Approval, user: User) -> None:
    """Ações sensíveis solicitadas diretamente pelo usuário (sem tarefa de agente)."""
    if approval.action == "project.delete":
        project = db.get(Project, approval.project_id)
        if project and project.owner_id == user.id:
            ws_root = Workspace(project.id).root
            audit.record(db, "project.deleted", actor_id=user.id, details={"project_id": project.id, "name": project.name})
            approval.project_id = None
            db.flush()
            db.delete(project)
            db.commit()
            shutil.rmtree(ws_root, ignore_errors=True)
    elif approval.action == "repository.delete":
        repo = db.get(Repository, approval.payload.get("repository_id"))
        if repo and repo.owner_id == user.id:
            path = Path(repo.local_path) if repo.local_path else None
            audit.record(db, "repository.deleted", actor_id=user.id, details={"repository_id": repo.id, "name": repo.name})
            db.delete(repo)
            db.commit()
            # Só removemos cópias gerenciadas pela plataforma, nunca diretórios locais do usuário.
            managed = (settings.data_dir / "repositories").resolve()
            if path and managed in path.resolve().parents:
                shutil.rmtree(path, ignore_errors=True)


@router.post("/{approval_id}/decide", response_model=ApprovalOut)
def decide(approval_id: str, body: ApprovalDecision, db: Session = Depends(get_db), user: User = Depends(current_user)) -> Approval:
    approval = db.get(Approval, approval_id)
    if approval is None or approval.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aprovação não encontrada")
    try:
        approval = decide_approval(db, approval, approve=body.approve, actor_id=user.id, reason=body.reason)
    except WorkflowError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    if body.approve and approval.task_id is None:
        _execute_direct_action(db, approval, user)
        approval.decided_at = approval.decided_at or utcnow()
        db.commit()
    return approval
