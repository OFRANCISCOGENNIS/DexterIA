from __future__ import annotations

import io
import json
import subprocess
import zipfile

from genisia.orchestrator.engine import run_until_idle

AWESOME_README = """# Awesome Teste

## Contents

- [Plataformas](#plataformas)

## Plataformas

- [FastAPI](https://fastapi.tiangolo.com) - Framework web moderno para APIs em Python.
- [Express](https://expressjs.com) - Framework web minimalista para Node.js.

## Bancos de dados

- [PostgreSQL](https://www.postgresql.org) - Banco relacional com busca textual.

## License

- [CC0](https://creativecommons.org/publicdomain/zero/1.0/)
"""

PUBLIC_APIS = """# Public APIs

### Finance
API | Description | Auth | HTTPS | CORS |
|---|---|---|---|---|
| [Câmbio Aberto](https://cambio.example.org/docs) | Cotações de moedas | No | Yes | Yes |
| [Banco Teste](https://banco.example.org) | Dados bancários de teste | `apiKey` | Yes | Unknown |

### Weather
API | Description | Auth | HTTPS | CORS |
|---|---|---|---|---|
| [Clima](https://clima.example.org) | Previsão do tempo | `apiKey` | No | No |
"""


def _git_repo(path, files):
    path.mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        target = path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t", "PATH": "/usr/bin:/bin"}
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=path, check=True, env=env)


def test_repository_analysis_flow_with_cache(client, auth, import_root):
    repo_dir = import_root / "app-demo"
    _git_repo(repo_dir, {
        "README.md": "# App Demo\n\nAplicação de demonstração usada para validar a análise estática do GENISIA AI com rotas e dependências.\n",
        "LICENSE": "MIT License\n\nPermission is hereby granted, free of charge, to any person obtaining a copy",
        "requirements.txt": "fastapi==0.1\nsqlalchemy\n",
        "app/main.py": "from fastapi import FastAPI\nimport sqlalchemy\napp = FastAPI()\n\n@app.get('/items')\ndef items():\n    return []\n",
        "app/config.py": "API_KEY = 'AKIAABCDEFGHIJKLMNOP'\n",
        "tests/test_main.py": "def test_x():\n    assert True\n",
        "web/package.json": json.dumps({"name": "web", "dependencies": {"react": "19", "next": "16"}, "scripts": {"dev": "next dev"}}),
    })
    r = client.post("/api/repositories", json={"source_type": "local", "source_url": str(repo_dir),
                                               "authorization_note": "Repositório próprio de teste"}, headers=auth)
    assert r.status_code == 201, r.text
    repo = r.json()
    task_id = client.post(f"/api/repositories/{repo['id']}/analyze", json={}, headers=auth).json()["id"]
    run_until_idle()
    detail = client.get(f"/api/tasks/{task_id}", headers=auth).json()
    steps = {s["step_key"]: s for s in detail["steps"]}
    assert steps["import"]["status"] == "succeeded"
    assert steps["reverse"]["status"] == "succeeded"
    assert steps["ai_review"]["status"] == "skipped"  # sem provedor de IA: etapa opcional pulada, sem simulação
    assert detail["status"] == "succeeded"
    repo = client.get(f"/api/repositories/{repo['id']}", headers=auth).json()
    assert repo["status"] == "analyzed" and repo["commit_sha"]
    report = client.get(f"/api/artifacts/{repo['last_analysis_artifact_id']}", headers=auth).json()
    data = report["data"]
    frameworks = {f["name"] for f in data["manifests"]["frameworks"]}
    assert {"FastAPI", "SQLAlchemy", "React", "Next.js"} <= frameworks
    assert data["license"]["spdx"] == "MIT"
    assert any(r["path"] == "/items" for r in data["code"]["routes"])
    assert data["secrets"] and "AKIA" not in json.dumps(data["secrets"])  # valor do segredo nunca é armazenado
    statuses = {f["status"] for f in data["findings"]}
    assert statuses == {"proven", "hypothesis"}
    assert "✅" in report["content"] and "🔎" in report["content"]
    # Segunda análise do mesmo commit reaproveita o resultado
    task2 = client.post(f"/api/repositories/{repo['id']}/analyze", json={}, headers=auth).json()["id"]
    run_until_idle()
    steps2 = {s["step_key"]: s for s in client.get(f"/api/tasks/{task2}", headers=auth).json()["steps"]}
    assert steps2["reverse"]["result"]["cached"] is True
    artifacts = client.get(f"/api/repositories/{repo['id']}/artifacts", headers=auth).json()
    assert {"analysis", "security", "optimization", "report"} <= {a["kind"] for a in artifacts}


def test_local_import_outside_roots_is_rejected(client, auth):
    r = client.post("/api/repositories", json={"source_type": "local", "source_url": "/etc", "authorization_note": "teste"}, headers=auth)
    assert r.status_code == 422


def test_git_url_validation(client, auth):
    for url in ["http://github.com/a/b", "https://user:pass@github.com/a/b", "https://localhost/a/b", "https://10.0.0.1/a/b",
                "https://evil.example.com/a/b", "file:///etc", "https://github.com/a/b;rm -rf"]:
        r = client.post("/api/repositories", json={"source_url": url, "authorization_note": "teste"}, headers=auth)
        assert r.status_code == 422, url


def test_knowledge_ingestion_and_search(client, auth, import_root):
    awesome = import_root / "awesome"
    _git_repo(awesome, {"README.md": AWESOME_README, "license": "CC0 1.0 Universal\n\nStatement of Purpose"})
    apis = import_root / "public-apis"
    _git_repo(apis, {"README.md": PUBLIC_APIS, "LICENSE": "MIT License\n\nPermission is hereby granted, free of charge"})
    for path in (awesome, apis):
        repo = client.post("/api/repositories", json={"source_type": "local", "source_url": str(path), "authorization_note": "teste"},
                           headers=auth).json()
        task = client.post(f"/api/repositories/{repo['id']}/analyze", json={"workflow": "ingest_knowledge"}, headers=auth).json()
        run_until_idle()
        detail = client.get(f"/api/tasks/{task['id']}", headers=auth).json()
        assert detail["status"] == "succeeded", detail
    sources = {s["name"]: s for s in client.get("/api/knowledge/sources", headers=auth).json()}
    assert sources[str(awesome.name)]["license"] == "CC0-1.0"
    assert sources[str(awesome.name)]["item_count"] == 3  # links do índice e da licença ignorados
    res = client.get("/api/knowledge/search", params={"q": "fastapi"}, headers=auth).json()
    assert res["total"] == 1 and res["items"][0]["url"] == "https://fastapi.tiangolo.com"
    assert res["items"][0]["category"] == "Plataformas"
    apis_found = client.get("/api/knowledge/search", params={"q": "", "item_type": "api", "auth": "apikey"}, headers=auth).json()
    assert {i["title"] for i in apis_found["items"]} == {"Banco Teste", "Clima"}
    assert client.get("/api/knowledge/search", params={"q": "moedas", "item_type": "api"}, headers=auth).json()["items"][0]["extra"]["https"] is True
    pid = client.post("/api/projects", json={"name": "API", "requirements": "API em Python com banco PostgreSQL"}, headers=auth).json()["id"]
    rec = client.get("/api/knowledge/recommendations", params={"project_id": pid}, headers=auth).json()
    assert "tool" in rec["groups"]
    titles = {i["title"] for i in rec["groups"]["tool"]["items"]}
    assert "PostgreSQL" in titles
    # Outro usuário não vê as fontes privadas
    other = client.post("/api/auth/register", json={"email": "kb-outro@example.com", "name": "O", "password": "senha-segura-9"}).json()
    other_h = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.get("/api/knowledge/search", params={"q": "fastapi"}, headers=other_h).json()["total"] == 0


def test_project_memory_review_export_delete(client, auth):
    pid = client.post("/api/projects", json={"name": "Memória"}, headers=auth).json()["id"]
    item = client.post(f"/api/knowledge/projects/{pid}/memory", json={"title": "Usar PostgreSQL", "content": "Decisão: FTS nativo"},
                       headers=auth).json()
    exported = client.get(f"/api/knowledge/projects/{pid}/memory/export", headers=auth)
    assert "Usar PostgreSQL" in exported.text
    assert client.get("/api/knowledge/search", params={"q": "postgresql", "project_id": pid}, headers=auth).json()["total"] >= 1
    assert client.delete(f"/api/knowledge/projects/{pid}/memory/{item['id']}", headers=auth).status_code == 204
    assert client.get(f"/api/knowledge/projects/{pid}/memory", headers=auth).json()["total"] == 0


def test_zip_upload_with_traversal_rejected(client, auth):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../evil.py", "x")
    r = client.post("/api/repositories/upload", files={"file": ("evil.zip", buf.getvalue(), "application/zip")},
                    data={"authorization_note": "teste"}, headers=auth)
    assert r.status_code == 422
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("src/app.py", "print('ok')\n")
    r = client.post("/api/repositories/upload", files={"file": ("ok.zip", buf.getvalue(), "application/zip")},
                    data={"authorization_note": "arquivo próprio"}, headers=auth)
    assert r.status_code == 201
    repo = r.json()
    task = client.post(f"/api/repositories/{repo['id']}/analyze", json={}, headers=auth).json()
    run_until_idle()
    assert client.get(f"/api/tasks/{task['id']}", headers=auth).json()["status"] == "succeeded"


def test_public_git_catalog_is_global_knowledge(client, auth, import_root, monkeypatch):
    """Catálogos de repositórios Git públicos ficam visíveis para todos os usuários."""
    import shutil

    from genisia.agents import repository as repo_agent
    from genisia.db import session_scope
    from genisia.models import Repository
    from genisia.security import decode_access_token

    src = import_root / "awesome-global"
    _git_repo(src, {"README.md": AWESOME_README.replace("FastAPI", "Quarkus Global")})

    def fake_clone(url, dest, ref=None):  # evita rede: copia um repositório local
        shutil.copytree(src, dest)
        return "f" * 40

    monkeypatch.setattr(repo_agent, "clone", fake_clone)
    owner = decode_access_token(auth["Authorization"].split()[1])
    with session_scope() as db:
        repo = Repository(owner_id=owner, name="sindresorhus/awesome-teste", source_type="git",
                          source_url="https://github.com/sindresorhus/awesome-teste", authorization_note="público")
        db.add(repo)
        db.flush()
        repo_id = repo.id
    task = client.post(f"/api/repositories/{repo_id}/analyze", json={"workflow": "ingest_knowledge", "profile": "awesome"}, headers=auth).json()
    run_until_idle()
    assert client.get(f"/api/tasks/{task['id']}", headers=auth).json()["status"] == "succeeded"
    other = client.post("/api/auth/register", json={"email": "kb-global@example.com", "name": "G", "password": "senha-segura-8"}).json()
    other_h = {"Authorization": f"Bearer {other['access_token']}"}
    res = client.get("/api/knowledge/search", params={"q": "quarkus"}, headers=other_h).json()
    assert res["total"] == 1
    source_id = res["items"][0]["source_id"]
    assert client.delete(f"/api/knowledge/sources/{source_id}", headers=other_h).status_code == 404  # global: não removível por usuários



def test_restrictive_license_indexes_links_only(client, auth, import_root):
    path = import_root / "roadmap-like"
    _git_repo(path, {"README.md": AWESOME_README, "license": "Everything in this project is protected by the copyright laws. Personal use only."})
    repo = client.post("/api/repositories", json={"source_type": "local", "source_url": str(path), "authorization_note": "teste"}, headers=auth).json()
    task = client.post(f"/api/repositories/{repo['id']}/analyze", json={"workflow": "ingest_knowledge", "profile": "generic"}, headers=auth).json()
    run_until_idle()
    ingest = next(s for s in client.get(f"/api/tasks/{task['id']}", headers=auth).json()["steps"] if s["step_key"] == "ingest")
    assert ingest["result"]["links_only"] is True and ingest["result"]["license"] == "Proprietária (uso pessoal)"
    res = client.get("/api/knowledge/search", params={"q": "postgresql", "source_id": ingest["result"]["source_id"]}, headers=auth).json()
    assert res["items"][0]["description"] == ""
