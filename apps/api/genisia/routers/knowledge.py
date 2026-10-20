from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from .. import audit
from ..db import get_db
from ..deps import Pagination, current_user, get_owned_project
from ..knowledge.search import add_memory, recommend, search, serialize
from ..models import KnowledgeItem, KnowledgeSource, User
from ..schemas import KnowledgeSourceOut, MemoryIn

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("/search")
def search_knowledge(q: str = Query("", max_length=300), item_type: str | None = Query(None, max_length=30),
                     category: str | None = Query(None, max_length=100), source_id: str | None = None,
                     project_id: str | None = None, auth: str | None = Query(None, max_length=30),
                     match: str = Query("all", pattern="^(all|any)$"), page: Pagination = Depends(),
                     db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    if project_id:
        get_owned_project(project_id, db, user)
    items, total = search(db, user.id, q, item_type=item_type, category=category, source_id=source_id, project_id=project_id,
                          auth=auth, match=match, limit=page.limit, offset=page.offset)
    return {"items": items, "total": total, "limit": page.limit, "offset": page.offset}


@router.get("/recommendations")
def recommendations(project_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    project = get_owned_project(project_id, db, user)
    text = f"{project.name} {project.description} {project.requirements} {' '.join(project.stack or [])}"
    return recommend(db, user.id, text)


@router.get("/sources", response_model=list[KnowledgeSourceOut])
def sources(db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[KnowledgeSource]:
    return list(db.scalars(select(KnowledgeSource).where(or_(KnowledgeSource.owner_id.is_(None), KnowledgeSource.owner_id == user.id))
                           .order_by(KnowledgeSource.name)))


@router.get("/categories")
def categories(item_type: str | None = None, db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[dict]:
    stmt = (select(KnowledgeItem.category, func.count()).join(KnowledgeSource, KnowledgeSource.id == KnowledgeItem.source_id)
            .where(or_(KnowledgeSource.owner_id.is_(None), KnowledgeSource.owner_id == user.id)))
    if item_type:
        stmt = stmt.where(KnowledgeItem.item_type == item_type)
    rows = db.execute(stmt.group_by(KnowledgeItem.category).order_by(func.count().desc()).limit(100)).all()
    return [{"category": c, "count": n} for c, n in rows if c]


@router.delete("/sources/{source_id}", status_code=204)
def delete_source(source_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> Response:
    source = db.get(KnowledgeSource, source_id)
    if source is None or source.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fonte não encontrada")
    audit.record(db, "knowledge.source_deleted", actor_id=user.id, details={"source": source.name, "items": source.item_count})
    db.delete(source)
    db.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------- memória do projeto
@router.get("/projects/{project_id}/memory")
def list_memory(project_id: str, page: Pagination = Depends(), db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    project = get_owned_project(project_id, db, user)
    stmt = select(KnowledgeItem).where(KnowledgeItem.project_id == project.id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(KnowledgeItem.created_at.desc()).limit(page.limit).offset(page.offset)).all()
    return {"items": [serialize(r) for r in rows], "total": total, "limit": page.limit, "offset": page.offset}


@router.post("/projects/{project_id}/memory", status_code=201)
def create_memory(project_id: str, body: MemoryIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    project = get_owned_project(project_id, db, user)
    item = add_memory(db, owner_id=user.id, project_id=project.id, title=body.title, content=body.content,
                      item_type=body.item_type, origin=f"user:{user.id}", tags=body.tags)
    audit.record(db, "memory.created", actor_id=user.id, project_id=project.id, details={"title": body.title})
    db.commit()
    return serialize(item)


@router.get("/projects/{project_id}/memory/export")
def export_memory(project_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> Response:
    project = get_owned_project(project_id, db, user)
    rows = db.scalars(select(KnowledgeItem).where(KnowledgeItem.project_id == project.id).order_by(KnowledgeItem.created_at)).all()
    payload = json.dumps({"project": project.name, "items": [serialize(r) for r in rows]}, ensure_ascii=False, indent=2)
    return Response(payload, media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="memoria-{project.id}.json"'})


@router.delete("/projects/{project_id}/memory/{item_id}", status_code=204)
def delete_memory(project_id: str, item_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> Response:
    project = get_owned_project(project_id, db, user)
    result = db.execute(delete(KnowledgeItem).where(KnowledgeItem.id == item_id, KnowledgeItem.project_id == project.id))
    if result.rowcount == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item não encontrado")
    audit.record(db, "memory.deleted", actor_id=user.id, project_id=project.id, details={"item_id": item_id})
    db.commit()
    return Response(status_code=204)
