from __future__ import annotations

from datetime import timedelta

from genisia.db import session_scope
from genisia.models import ScheduledTrigger, Task, utcnow
from genisia.orchestrator.scheduler import run_due_triggers

from .test_repositories_knowledge import _git_repo

BOOKS = """# Livros

## Python

- [Python para Iniciantes](https://livros.example.org/python) - Introdução à linguagem Python (PDF)
- [Banco de Dados com Python](https://livros.example.org/db) - SQL e PostgreSQL na prática (HTML)
- [Banco de Dados com Python](https://espelho.example.org/db) - Mesmo livro em outro endereço

## Culinária

- [Bolos Caseiros](https://livros.example.org/bolos) - Receitas
"""

TUTORIALS = """# Build your own

## Tutoriais

- [**Python**: _Construa um banco de dados_](https://tut.example.org/db) - passo a passo
- [**Go**: _Construa um servidor_](https://tut.example.org/go)
"""


def _project(client, auth, **extra):
    return client.post("/api/projects", json={"name": "Automação", **extra}, headers=auth).json()


def _due(trigger_id: str) -> None:
    with session_scope() as db:
        db.get(ScheduledTrigger, trigger_id).next_run_at = utcnow() - timedelta(minutes=1)


def test_trigger_validation_rules(client, auth):
    project = _project(client, auth)
    base = {"name": "Testes noturnos", "interval_minutes": 60}
    # Fluxos que geram código por IA não podem ser agendados
    for workflow in ("mission", "develop", "plan"):
        r = client.post("/api/triggers", json={**base, "workflow": workflow, "project_id": project["id"]}, headers=auth)
        assert r.status_code == 422, workflow
    assert client.post("/api/triggers", json={**base, "workflow": "test", "project_id": project["id"], "interval_minutes": 5},
                       headers=auth).status_code == 422  # abaixo do intervalo mínimo
    assert client.post("/api/triggers", json={**base, "workflow": "test"}, headers=auth).status_code == 422  # sem projeto
    assert client.post("/api/triggers", json={**base, "workflow": "analyze_repository", "repository_id": "x" * 32},
                       headers=auth).status_code == 404
    other = client.post("/api/auth/register", json={"email": "trg-outro@example.com", "name": "O", "password": "senha-segura-7"}).json()
    other_h = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.post("/api/triggers", json={**base, "workflow": "test", "project_id": project["id"]},
                       headers=other_h).status_code == 404  # projeto de outro usuário


def test_trigger_fires_once_and_skips_overlap(client, auth):
    project = _project(client, auth)
    r = client.post("/api/triggers", json={"name": "Testes", "workflow": "test", "interval_minutes": 30, "project_id": project["id"]},
                    headers=auth)
    assert r.status_code == 201
    trigger = r.json()
    with session_scope() as db:
        assert run_due_triggers(db) == []  # ainda não venceu
    _due(trigger["id"])
    with session_scope() as db:
        created = run_due_triggers(db)
        assert len(created) == 1
        task = db.get(Task, created[0])
        assert task.kind == "workflow:test" and task.objective.startswith("Gatilho agendado")
    # Vencido de novo com a execução anterior ainda na fila: não cria outra
    _due(trigger["id"])
    with session_scope() as db:
        assert run_due_triggers(db) == []
    listed = next(t for t in client.get("/api/triggers", headers=auth).json() if t["id"] == trigger["id"])
    assert listed["run_count"] == 1 and "anterior" in listed["last_error"]
    # Desabilitado: não dispara
    client.patch(f"/api/triggers/{trigger['id']}", json={"enabled": False}, headers=auth)
    _due(trigger["id"])
    with session_scope() as db:
        db.get(Task, created[0]).status = "succeeded"
    with session_scope() as db:
        assert run_due_triggers(db) == []
    assert client.delete(f"/api/triggers/{trigger['id']}", headers=auth).status_code == 204
    assert all(t["id"] != trigger["id"] for t in client.get("/api/triggers", headers=auth).json())


def test_learning_path_from_project_with_progress(client, auth, import_root):
    for name, readme, profile in (("livros-trilha", BOOKS, "free-programming-books"), ("tutoriais-trilha", TUTORIALS, "build-your-own-x")):
        path = import_root / name
        _git_repo(path, {"README.md": readme, "LICENSE": "MIT License\n\nPermission is hereby granted, free of charge"})
        repo = client.post("/api/repositories", json={"source_type": "local", "source_url": str(path), "authorization_note": "teste"},
                           headers=auth).json()
        from genisia.orchestrator.engine import run_until_idle

        client.post(f"/api/repositories/{repo['id']}/analyze", json={"workflow": "ingest_knowledge", "profile": "generic"}, headers=auth)
        run_until_idle()
    # O perfil genérico indexa tudo como "resource"; ajustamos os tipos para simular livros e tutoriais
    with session_scope() as db:
        from genisia.models import KnowledgeItem

        books = KnowledgeItem.url.like("https://livros.example.org/%") | KnowledgeItem.url.like("https://espelho.example.org/%")
        for item in db.query(KnowledgeItem).filter(books):
            item.item_type = "book"
        for item in db.query(KnowledgeItem).filter(KnowledgeItem.url.like("https://tut.example.org/%")):
            item.item_type = "tutorial"
    project = _project(client, auth, requirements="Sistema em Python com banco de dados PostgreSQL")
    r = client.post("/api/learning/paths", json={"project_id": project["id"]}, headers=auth)
    assert r.status_code == 201, r.text
    path = r.json()
    urls = [i["url"] for i in path["items"]]
    assert "https://livros.example.org/bolos" not in urls  # sem relação com o objetivo
    assert len({i["title"] for i in path["items"]}) == len(path["items"])  # mesmo material em outra URL não se repete
    stages = [i["stage"] for i in path["items"]]
    assert stages == sorted(stages, key=["fundamentos", "prática", "aprofundamento"].index)  # ordem de estudo
    assert {"https://livros.example.org/python", "https://tut.example.org/db"} <= set(urls)
    assert all(i["reason"].startswith("Cobre:") and i["source_name"] for i in path["items"])
    assert path["progress"] == 0
    first = path["items"][0]
    updated = client.patch(f"/api/learning/paths/{path['id']}/items/{first['id']}", json={"status": "done"}, headers=auth).json()
    assert updated["done"] == 1 and updated["progress"] == round(1 / updated["total"], 3)
    assert client.get("/api/learning/paths", headers=auth).json()[0]["id"] == path["id"]
    assert client.delete(f"/api/learning/paths/{path['id']}", headers=auth).status_code == 204


def test_learning_path_without_matches_is_explicit(client, auth):
    r = client.post("/api/learning/paths", json={"goal": "xilofonequântico zumbizarro"}, headers=auth)
    assert r.status_code == 422
    assert "Nenhum material" in r.json()["detail"]
