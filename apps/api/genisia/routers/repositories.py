from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import audit
from ..analysis.importer import ImportErrorDetail, extract_zip, repo_name_from_url, validate_git_url, validate_local_path
from ..config import settings
from ..db import get_db
from ..deps import Pagination, current_user, get_owned_project, get_owned_repository
from ..models import Approval, Artifact, Repository, Task, User
from ..orchestrator.engine import WorkflowError, create_workflow
from ..schemas import AnalyzeIn, ApprovalOut, ArtifactSummary, Page, RepositoryIn, RepositoryOut, TaskOut

router = APIRouter(prefix="/api/repositories", tags=["repositories"])


@router.post("", response_model=RepositoryOut, status_code=201)
def register_repository(body: RepositoryIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> Repository:
    if body.project_id:
        get_owned_project(body.project_id, db, user)
    try:
        if body.source_type == "git":
            url = validate_git_url(body.source_url)
            name = body.name or repo_name_from_url(url)
        else:
            url = str(validate_local_path(body.source_url))
            name = body.name or Path(url).name
    except ImportErrorDetail as exc:
        raise HTTPException(422, str(exc)) from exc
    existing = db.scalar(select(Repository).where(Repository.owner_id == user.id, Repository.source_url == url))
    if existing:
        return existing
    repo = Repository(owner_id=user.id, project_id=body.project_id, name=name, source_type=body.source_type, source_url=url,
                      ref=body.ref, authorization_note=body.authorization_note)
    db.add(repo)
    db.flush()
    audit.record(db, "repository.registered", actor_id=user.id, project_id=body.project_id, target_type="repository",
                 target_id=repo.id, details={"source": url, "authorization": body.authorization_note})
    db.commit()
    return repo


@router.post("/upload", response_model=RepositoryOut, status_code=201)
async def upload_repository(file: UploadFile = File(...), authorization_note: str = Form(..., min_length=3, max_length=2000),
                            name: str | None = Form(None), db: Session = Depends(get_db), user: User = Depends(current_user)) -> Repository:
    """Envio de arquivos autorizados em ZIP para o laboratório de engenharia reversa."""
    if not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(422, "Envie um arquivo .zip")
    repo = Repository(owner_id=user.id, name=(name or Path(file.filename or "upload").stem)[:200], source_type="upload",
                      source_url=f"upload:{file.filename}", authorization_note=authorization_note, status="uploading")
    db.add(repo)
    db.flush()
    dest = settings.data_dir / "repositories" / repo.id
    max_bytes = 100 * 1_048_576
    with tempfile.NamedTemporaryFile(dir=settings.data_dir / "uploads", suffix=".zip", delete=False) as tmp:
        size = 0
        while chunk := await file.read(1_048_576):
            size += len(chunk)
            if size > max_bytes:
                tmp.close()
                Path(tmp.name).unlink(missing_ok=True)
                raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Arquivo maior que 100 MB")
            tmp.write(chunk)
    try:
        extract_zip(Path(tmp.name), dest)
    except (ImportErrorDetail, Exception) as exc:  # noqa: BLE001 - zip inválido
        shutil.rmtree(dest, ignore_errors=True)
        raise HTTPException(422, f"ZIP inválido: {exc}") from exc
    finally:
        Path(tmp.name).unlink(missing_ok=True)
    repo.local_path = str(dest)
    repo.status = "imported"
    audit.record(db, "repository.uploaded", actor_id=user.id, target_type="repository", target_id=repo.id,
                 details={"file": file.filename, "bytes": size, "authorization": authorization_note})
    db.commit()
    return repo


@router.get("", response_model=Page[RepositoryOut])
def list_repositories(page: Pagination = Depends(), db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    stmt = select(Repository).where(Repository.owner_id == user.id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.order_by(Repository.updated_at.desc()).limit(page.limit).offset(page.offset)).all()
    return {"items": items, "total": total, "limit": page.limit, "offset": page.offset}


@router.get("/{repo_id}", response_model=RepositoryOut)
def get_repository(repo_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> Repository:
    return get_owned_repository(repo_id, db, user)


@router.post("/{repo_id}/analyze", response_model=TaskOut, status_code=202)
def analyze(repo_id: str, body: AnalyzeIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> Task:
    repo = get_owned_repository(repo_id, db, user)
    params: dict = {}
    if body.force:
        params["reverse"] = {"force": True}
    if body.profile:
        params["ingest"] = {"profile": body.profile}
    if repo.source_type == "upload":
        params["import"] = {}
    try:
        task = create_workflow(db, owner_id=user.id, workflow=body.workflow, repository_id=repo.id, project_id=repo.project_id,
                               objective=f"{body.workflow} de {repo.name}", params=params)
    except WorkflowError as exc:
        raise HTTPException(422, str(exc)) from exc
    repo.last_task_id = task.id
    db.commit()
    return task


@router.get("/{repo_id}/artifacts", response_model=list[ArtifactSummary])
def repository_artifacts(repo_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[Artifact]:
    repo = get_owned_repository(repo_id, db, user)
    return list(db.scalars(select(Artifact).where(Artifact.repository_id == repo.id).order_by(Artifact.created_at.desc()).limit(100)))


@router.delete("/{repo_id}", response_model=ApprovalOut, status_code=202)
def request_delete(repo_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> Approval:
    repo = get_owned_repository(repo_id, db, user)
    approval = Approval(owner_id=user.id, project_id=repo.project_id, action="repository.delete", requested_by="user",
                        payload={"repository_id": repo.id},
                        description=f"Remover o repositório '{repo.name}', sua cópia local e relatórios de análise.")
    db.add(approval)
    db.commit()
    return approval
