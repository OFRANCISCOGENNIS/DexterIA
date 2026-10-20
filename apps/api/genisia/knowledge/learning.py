"""Trilhas de aprendizagem montadas a partir da base de conhecimento.

A seleção é determinística (busca textual, sem IA): cada item traz o motivo da escolha, ou seja,
quais palavras-chave do objetivo ele cobre, e a fonte de origem verificável.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import LearningPath, LearningPathItem
from .search import _fold, keywords, search

# Etapa da trilha por tipo de material, na ordem de estudo.
STAGES = [("fundamentos", "book"), ("prática", "tutorial"), ("aprofundamento", "resource")]
PER_STAGE = 5


class EmptyPath(ValueError):
    pass


def build_path(db: Session, *, owner_id: str, goal: str, title: str, project_id: str | None = None) -> LearningPath:
    kws = keywords(goal, limit=10)
    if not kws:
        raise EmptyPath("Descreva o objetivo com termos técnicos (ex.: python, banco de dados, react)")
    path = LearningPath(owner_id=owner_id, project_id=project_id, title=title[:200], goal=goal[:4000], keywords=kws)
    db.add(path)
    db.flush()
    position = 0
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()  # catálogos repetem o mesmo material em URLs diferentes
    for stage, item_type in STAGES:
        items, _total = search(db, owner_id, " ".join(kws), item_type=item_type, match="any", limit=PER_STAGE * 3)
        added = 0
        for item in items:
            title_key = _fold(item["title"]).strip()
            if added >= PER_STAGE or not item["url"] or item["url"] in seen_urls or title_key in seen_titles:
                continue
            text = _fold(f"{item['title']} {item['description']} {item['category']}")
            covered = [k for k in kws if _fold(k) in text]
            if not covered:
                continue
            seen_urls.add(item["url"])
            seen_titles.add(title_key)
            position += 1
            added += 1
            db.add(LearningPathItem(
                path_id=path.id, knowledge_item_id=item["id"], position=position, stage=stage, item_type=item_type,
                title=item["title"][:400], url=item["url"], source_name=item["source_name"],
                reason="Cobre: " + ", ".join(covered),
            ))
    if position == 0:
        db.rollback()
        raise EmptyPath("Nenhum material da base de conhecimento corresponde a este objetivo. "
                        "Indexe catálogos (ex.: free-programming-books, build-your-own-x) em Engenharia reversa.")
    db.commit()
    return path


def serialize_path(path: LearningPath, items: list[LearningPathItem]) -> dict:
    done = sum(1 for i in items if i.status == "done")
    return {
        "id": path.id, "title": path.title, "goal": path.goal, "keywords": path.keywords, "project_id": path.project_id,
        "created_at": path.created_at.isoformat(), "total": len(items), "done": done,
        "progress": round(done / len(items), 3) if items else 0.0,
        "items": [{"id": i.id, "position": i.position, "stage": i.stage, "item_type": i.item_type, "title": i.title,
                   "url": i.url, "source_name": i.source_name, "reason": i.reason, "status": i.status,
                   "completed_at": i.completed_at.isoformat() if i.completed_at else None} for i in items],
    }
