"""Busca textual na base de conhecimento.

PostgreSQL: full-text search (``to_tsvector('simple', ...)`` + ``ts_rank``) com índice GIN.
SQLite (desenvolvimento/testes): correspondência por termos com pontuação ponderada.
A busca vetorial pode ser adicionada depois atrás desta mesma interface.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, case, func, literal, or_, select
from sqlalchemy.orm import Session

from ..models import KnowledgeItem, KnowledgeSource, Project

STOPWORDS = set("""
a o as os um uma uns umas de do da dos das em no na nos nas por para com sem que e ou se ao aos à às é ser
sistema quero desenvolver criar fazer usar deve devem precisa precisamos permitir app aplicação aplicativo
the an of to in on for with and or is are be by as at from this that it its into using use build want need
""".split())


def _fold(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(c))


def build_search_text(title: str, description: str, category: str, tags: list[str]) -> str:
    return " ".join([title, title, description, category, " ".join(tags)])[:4000]


def keywords(text: str, limit: int = 12) -> list[str]:
    words = re.findall(r"[a-zA-ZÀ-ÿ0-9+#.]{3,}", text.lower())
    seen: list[str] = []
    for w in words:
        w = w.strip(".")
        if w and w not in STOPWORDS and w not in seen:
            seen.append(w)
    return seen[:limit]


def _visible_sources(user_id: str):
    owned_projects = select(Project.id).where(Project.owner_id == user_id)
    return select(KnowledgeSource.id).where(
        or_(KnowledgeSource.owner_id.is_(None), KnowledgeSource.owner_id == user_id),
        or_(KnowledgeSource.project_id.is_(None), KnowledgeSource.project_id.in_(owned_projects)),
    )


def search(
    db: Session,
    user_id: str,
    query: str,
    *,
    item_type: str | None = None,
    category: str | None = None,
    source_id: str | None = None,
    project_id: str | None = None,
    auth: str | None = None,
    match: str = "all",
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    terms = keywords(query, 10) if match == "any" else [t for t in re.findall(r"\S+", query.lower()) if len(t) >= 2][:10]
    dialect = db.get_bind().dialect.name
    filters = [KnowledgeItem.source_id.in_(_visible_sources(user_id))]
    if item_type:
        filters.append(KnowledgeItem.item_type == item_type)
    if category:
        filters.append(KnowledgeItem.category.ilike(f"%{category}%"))
    if source_id:
        filters.append(KnowledgeItem.source_id == source_id)
    if project_id:
        filters.append(or_(KnowledgeItem.project_id == project_id, KnowledgeItem.project_id.is_(None)))
    if auth:
        filters.append(func.lower(KnowledgeItem.extra["auth"].as_string()) == auth.lower())

    score: Any = literal(0.0)
    if terms:
        if dialect == "postgresql":
            joiner = " & " if match == "all" else " | "
            safe = [re.sub(r"[^\w+#.]", "", _fold(t)) for t in terms]
            safe = [s for s in safe if s]
            if safe:
                tsquery = func.to_tsquery("simple", joiner.join(f"{s}:*" for s in safe))
                vector = func.to_tsvector("simple", func.lower(KnowledgeItem.search_text))
                filters.append(vector.op("@@")(tsquery))
                score = func.ts_rank(vector, tsquery)
        else:
            clauses = []
            weights = []
            for t in terms:
                like = f"%{t}%"
                clauses.append(func.lower(KnowledgeItem.search_text).like(like))
                weights.append(case((func.lower(KnowledgeItem.title).like(like), 3.0), else_=0.0))
                weights.append(case((func.lower(KnowledgeItem.search_text).like(like), 1.0), else_=0.0))
            filters.append(and_(*clauses) if match == "all" else or_(*clauses))
            score = sum(weights[1:], weights[0])

    base = select(KnowledgeItem, KnowledgeSource.name, KnowledgeSource.license, score.label("score")).join(
        KnowledgeSource, KnowledgeSource.id == KnowledgeItem.source_id).where(*filters)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.execute(base.order_by(score.desc(), KnowledgeItem.title).limit(limit).offset(offset)).all()
    return [serialize(item, source_name, license_, float(sc or 0)) for item, source_name, license_, sc in rows], total


def serialize(item: KnowledgeItem, source_name: str | None = None, license_: str | None = None, score: float | None = None) -> dict[str, Any]:
    return {
        "id": item.id, "title": item.title, "url": item.url, "description": item.description,
        "category": item.category, "item_type": item.item_type, "tags": item.tags, "extra": item.extra,
        "source_id": item.source_id, "source_name": source_name, "source_license": license_,
        "origin_path": item.origin_path, "project_id": item.project_id, "score": score,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def recommend(db: Session, user_id: str, text: str, per_type: int = 5) -> dict[str, Any]:
    """Recomendações fundamentadas: cada item traz URL e fonte de origem verificáveis."""
    kws = keywords(text)
    result: dict[str, Any] = {"keywords": kws, "groups": {}}
    if not kws:
        return result
    query = " ".join(kws)
    for item_type in ("tool", "api", "book", "tutorial", "resource"):
        items, total = search(db, user_id, query, item_type=item_type, match="any", limit=per_type)
        if items:
            result["groups"][item_type] = {"total_matches": total, "items": items}
    return result


def add_memory(db: Session, *, owner_id: str, project_id: str, title: str, content: str, item_type: str = "decision",
               origin: str = "", tags: list[str] | None = None) -> KnowledgeItem:
    """Registra uma decisão/memória de projeto (separada da memória global)."""
    source = db.scalar(select(KnowledgeSource).where(KnowledgeSource.project_id == project_id, KnowledgeSource.kind == "memory"))
    if source is None:
        source = KnowledgeSource(owner_id=owner_id, project_id=project_id, name="Memória do projeto", kind="memory",
                                 license="privado", meta={}, indexed_at=datetime.now(timezone.utc))
        db.add(source)
        db.flush()
    tags = tags or []
    item = KnowledgeItem(source_id=source.id, project_id=project_id, item_type=item_type, title=title[:400],
                         description=content[:8000], category="memória do projeto", tags=tags, extra={"origin": origin},
                         origin_path=origin or None, search_text=build_search_text(title, content[:2000], "memória", tags))
    db.add(item)
    source.item_count = (source.item_count or 0) + 1
    return item
