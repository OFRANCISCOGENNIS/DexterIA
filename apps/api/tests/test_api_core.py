from __future__ import annotations


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_openapi_documented(client):
    spec = client.get("/openapi.json").json()
    paths = spec["paths"]
    for path in ["/api/projects", "/api/tasks/{task_id}", "/api/repositories/{repo_id}/analyze", "/api/approvals/{approval_id}/decide",
                 "/api/knowledge/search", "/api/integrations", "/api/tasks/{task_id}/cancel", "/api/tasks/{task_id}/logs"]:
        assert path in paths


def test_register_login_me(client):
    r = client.post("/api/auth/register", json={"email": "Ana@Example.com", "name": "Ana", "password": "senha-segura-1"})
    assert r.status_code == 201
    token = r.json()["access_token"]
    assert client.post("/api/auth/register", json={"email": "ana@example.com", "name": "Ana", "password": "senha-segura-1"}).status_code == 409
    assert client.post("/api/auth/login", json={"email": "ana@example.com", "password": "errada"}).status_code == 401
    r = client.post("/api/auth/login", json={"email": "ana@example.com", "password": "senha-segura-1"})
    assert r.status_code == 200
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["email"] == "ana@example.com"


def test_protected_endpoints_require_auth(client):
    assert client.get("/api/projects").status_code == 401
    assert client.get("/api/projects", headers={"Authorization": "Bearer invalido"}).status_code == 401


def test_validation_errors_are_consistent(client, auth):
    r = client.post("/api/projects", json={"name": ""}, headers=auth)
    assert r.status_code == 422
    assert r.json()["detail"] == "Dados inválidos"
    assert r.json()["errors"]


def test_project_crud_and_isolation(client, auth):
    r = client.post("/api/projects", json={"name": "Finanças", "description": "App financeiro", "requirements": "Controle de despesas"},
                    headers=auth)
    assert r.status_code == 201
    project = r.json()
    assert project["status"] == "requirements"
    pid = project["id"]
    listing = client.get("/api/projects?limit=10", headers=auth).json()
    assert listing["total"] >= 1 and listing["limit"] == 10
    r = client.patch(f"/api/projects/{pid}", json={"requirements": "Despesas, metas e relatórios", "stack": ["python"]}, headers=auth)
    assert r.json()["requirements"] == "Despesas, metas e relatórios"
    detail = client.get(f"/api/projects/{pid}", headers=auth).json()
    assert detail["stats"]["ai_cost_usd"] == 0
    # Outro usuário não enxerga o projeto
    other = client.post("/api/auth/register", json={"email": "outro@example.com", "name": "Outro", "password": "senha-segura-2"}).json()
    other_h = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.get(f"/api/projects/{pid}", headers=other_h).status_code == 404
    assert client.get(f"/api/projects/{pid}/files", headers=other_h).status_code == 404
    # Workspace git criado
    files = client.get(f"/api/projects/{pid}/files", headers=auth).json()
    assert files["head"]
    activity = client.get(f"/api/projects/{pid}/activity", headers=auth).json()
    assert any(e["action"] == "project.created" for e in activity["items"])


def test_studio_manual_edit_and_history(client, auth):
    pid = client.post("/api/projects", json={"name": "Studio"}, headers=auth).json()["id"]
    r = client.put(f"/api/projects/{pid}/files/content", json={"path": "src/app.py", "content": "print('oi')\n"}, headers=auth)
    assert r.status_code == 200 and r.json()["changed"]
    assert client.get(f"/api/projects/{pid}/files/content", params={"path": "src/app.py"}, headers=auth).text == "print('oi')\n"
    commits = client.get(f"/api/projects/{pid}/history", headers=auth).json()["commits"]
    assert commits[0]["message"].startswith("Edição manual")
    diff = client.get(f"/api/projects/{pid}/history/{commits[0]['sha']}", headers=auth).text
    assert "+print('oi')" in diff
    for bad in ["../x.py", "/etc/passwd", ".git/config", "a/../../b"]:
        r = client.put(f"/api/projects/{pid}/files/content", json={"path": bad, "content": "x"}, headers=auth)
        assert r.status_code == 400, bad


def test_project_delete_requires_approval(client, auth):
    pid = client.post("/api/projects", json={"name": "Apagar"}, headers=auth).json()["id"]
    r = client.delete(f"/api/projects/{pid}", headers=auth)
    assert r.status_code == 202
    approval = r.json()
    assert approval["action"] == "project.delete" and approval["status"] == "pending"
    assert client.get(f"/api/projects/{pid}", headers=auth).status_code == 200  # ainda existe
    r = client.post(f"/api/approvals/{approval['id']}/decide", json={"approve": True}, headers=auth)
    assert r.status_code == 200 and r.json()["status"] == "approved"
    assert client.get(f"/api/projects/{pid}", headers=auth).status_code == 404
    assert client.post(f"/api/approvals/{approval['id']}/decide", json={"approve": True}, headers=auth).status_code == 409


def test_auth_rate_limit(client):
    from genisia.config import settings

    for i in range(settings.auth_rate_limit_per_minute):
        client.post("/api/auth/login", json={"email": "x@example.com", "password": "y"})
    r = client.post("/api/auth/login", json={"email": "x@example.com", "password": "y"})
    assert r.status_code == 429
    assert "Retry-After" in r.headers


def test_integrations_status_and_secret_never_returned(client, auth):
    data = client.get("/api/integrations", headers=auth).json()
    assert data["ai"]["configured"] is False
    assert "ANTHROPIC_API_KEY" in data["ai"]["reason"]
    r = client.put("/api/integrations/ai", json={"api_key": "sk-ant-test-1234567890abcdef", "model": "claude-sonnet-5-5"}, headers=auth)
    assert r.status_code == 200
    data = client.get("/api/integrations", headers=auth).json()
    assert data["ai"]["configured"] is True and data["ai"]["model"] == "claude-sonnet-5-5"
    assert "sk-ant-test" not in client.get("/api/integrations", headers=auth).text
    assert client.put("/api/integrations/ai", json={"model": "gpt-x"}, headers=auth).status_code == 422
    client.delete("/api/integrations/ai/key", headers=auth)
    assert client.get("/api/integrations", headers=auth).json()["ai"]["configured"] is False
