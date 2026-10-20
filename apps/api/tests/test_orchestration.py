from __future__ import annotations

import pytest

from genisia.ai.providers import set_provider_override
from genisia.db import session_scope
from genisia.execution.sandbox import SandboxUnavailable, sandbox_status
from genisia.models import AgentRun, Task
from genisia.orchestrator.engine import recover, run_until_idle

from .fakes import FakeProvider

needs_sandbox = pytest.mark.skipif(not sandbox_status()["available"], reason="sandbox indisponível neste ambiente")

REQS = "Quero desenvolver um sistema financeiro com dashboard, controle de despesas, metas e relatórios."


def _project(client, auth, **extra):
    body = {"name": "Finanças", "description": "Sistema financeiro", "requirements": REQS, **extra}
    return client.post("/api/projects", json=body, headers=auth).json()


def _steps(client, auth, task_id):
    detail = client.get(f"/api/tasks/{task_id}", headers=auth).json()
    return detail, {s["step_key"]: s for s in detail["steps"]}


@needs_sandbox
def test_full_mission_with_approval_tests_and_fix_loop(client, auth):
    fake = FakeProvider(fail_first_code=True)
    set_provider_override(lambda: fake)
    project = _project(client, auth)
    r = client.post(f"/api/projects/{project['id']}/workflows", json={"workflow": "mission"}, headers=auth)
    assert r.status_code == 202
    task_id = r.json()["id"]

    run_until_idle()
    detail, steps = _steps(client, auth, task_id)
    assert steps["research"]["status"] == "succeeded"
    assert steps["architect"]["status"] == "succeeded"
    assert steps["plan_approval"]["status"] == "awaiting_approval"
    assert steps["develop"]["status"] == "queued"
    assert detail["status"] == "awaiting_approval"
    approvals = client.get("/api/approvals?status_=pending", headers=auth).json()["items"]
    approval = next(a for a in approvals if a["task_id"] == steps["plan_approval"]["id"])
    plan = client.get(f"/api/artifacts/{steps['architect']['result']['plan_artifact_id']}", headers=auth).json()
    assert plan["kind"] == "plan" and "Critérios de aceitação" in plan["content"]

    r = client.post(f"/api/approvals/{approval['id']}/decide", json={"approve": True}, headers=auth)
    assert r.status_code == 200
    run_until_idle()

    detail, steps = _steps(client, auth, task_id)
    assert detail["status"] == "succeeded", detail
    qa = steps["qa"]["result"]
    assert qa["passed"] is True
    assert qa["runs"] == 2 and qa["fixes"] == 1  # primeira execução falhou, a correção passou
    assert steps["deliver"]["status"] == "succeeded"
    delivery = client.get(f"/api/artifacts/{steps['deliver']['result']['artifact_id']}", headers=auth).json()
    assert "testes aprovados no sandbox" in delivery["content"]
    test_log = client.get(f"/api/artifacts/{qa['artifact_id']}", headers=auth).json()
    assert "2 failed" in test_log["content"] and "2 passed" in test_log["content"], test_log["content"]
    # Execuções de agentes registradas, incluindo a delegação ao desenvolvedor
    agents = [r["agent"] for r in detail["runs"]]
    assert agents.count("developer") == 2 and "qa" in agents
    assert all(r["provider"] in (None, "fake-test") for r in detail["runs"])
    assert sum(r["input_tokens"] for r in detail["runs"]) == 3000  # 3 chamadas de IA registradas (modelo de teste sem preço)
    # Histórico Git com commits dos agentes
    commits = client.get(f"/api/projects/{project['id']}/history", headers=auth).json()["commits"]
    assert any(c["message"].startswith("Correção após falha") for c in commits)
    assert client.get(f"/api/projects/{project['id']}", headers=auth).json()["status"] == "delivered"
    logs = client.get(f"/api/tasks/{task_id}/logs", headers=auth).json()["logs"]
    assert any("sandbox" in entry["logs"] for entry in logs)
    memory = client.get(f"/api/knowledge/projects/{project['id']}/memory", headers=auth).json()
    assert memory["total"] >= 2


def test_plan_rejection_skips_development(client, auth):
    set_provider_override(lambda: FakeProvider())
    project = _project(client, auth)
    task_id = client.post(f"/api/projects/{project['id']}/workflows", json={"workflow": "mission"}, headers=auth).json()["id"]
    run_until_idle()
    _, steps = _steps(client, auth, task_id)
    approval = next(a for a in client.get("/api/approvals", headers=auth).json()["items"] if a["task_id"] == steps["plan_approval"]["id"])
    client.post(f"/api/approvals/{approval['id']}/decide", json={"approve": False, "reason": "falta escopo"}, headers=auth)
    run_until_idle()
    detail, steps = _steps(client, auth, task_id)
    assert steps["plan_approval"]["status"] == "failed"
    assert steps["develop"]["status"] == "skipped"
    assert steps["deliver"]["status"] in {"succeeded", "failed"}  # relatório final sempre executa
    assert detail["status"] == "failed"
    assert "Rejeitado" in detail["error"]


def test_without_ai_provider_fails_with_clear_message(client, auth):
    project = _project(client, auth)
    task_id = client.post(f"/api/projects/{project['id']}/workflows", json={"workflow": "plan"}, headers=auth).json()["id"]
    run_until_idle()
    detail, steps = _steps(client, auth, task_id)
    assert steps["architect"]["status"] == "failed"
    assert "Nenhum provedor de IA configurado" in steps["architect"]["error"]
    assert steps["architect"]["attempts"] == 1  # erro de configuração não é repetido
    assert detail["status"] == "failed"


def test_budget_limit_blocks_ai_calls(client, auth):
    set_provider_override(lambda: FakeProvider())
    project = _project(client, auth, settings={"ai_budget_usd": 0})
    task_id = client.post(f"/api/projects/{project['id']}/workflows", json={"workflow": "plan"}, headers=auth).json()["id"]
    run_until_idle()
    _, steps = _steps(client, auth, task_id)
    assert "Orçamento de IA" in steps["architect"]["error"]


def test_develop_requires_approved_plan(client, auth):
    project = _project(client, auth)
    r = client.post(f"/api/projects/{project['id']}/workflows", json={"workflow": "develop"}, headers=auth)
    assert r.status_code == 422


def test_cancel_workflow(client, auth):
    project = _project(client, auth)
    task_id = client.post(f"/api/projects/{project['id']}/workflows", json={"workflow": "mission"}, headers=auth).json()["id"]
    r = client.post(f"/api/tasks/{task_id}/cancel", headers=auth)
    assert r.status_code == 200 and r.json()["status"] == "cancelled"
    _, steps = _steps(client, auth, task_id)
    assert all(s["status"] == "cancelled" for s in steps.values())
    run_until_idle()  # nada é executado depois do cancelamento
    detail, _ = _steps(client, auth, task_id)
    assert detail["runs"] == []
    assert client.post(f"/api/tasks/{task_id}/cancel", headers=auth).status_code == 409


def test_retry_failed_workflow(client, auth):
    project = _project(client, auth)
    task_id = client.post(f"/api/projects/{project['id']}/workflows", json={"workflow": "plan"}, headers=auth).json()["id"]
    run_until_idle()
    assert client.get(f"/api/tasks/{task_id}", headers=auth).json()["status"] == "failed"
    set_provider_override(lambda: FakeProvider())
    assert client.post(f"/api/tasks/{task_id}/retry", headers=auth).status_code == 200
    run_until_idle()
    detail, steps = _steps(client, auth, task_id)
    assert steps["architect"]["status"] == "succeeded"
    assert steps["plan_approval"]["status"] == "awaiting_approval"


def test_recovery_requeues_interrupted_steps(client, auth):
    project = _project(client, auth)
    task_id = client.post(f"/api/projects/{project['id']}/workflows", json={"workflow": "plan"}, headers=auth).json()["id"]
    with session_scope() as db:
        step = db.query(Task).filter(Task.parent_id == task_id, Task.step_key == "research").one()
        step.status = "running"
        step.attempts = 1
        db.add(AgentRun(task_id=step.id, agent="research", status="running"))
    with session_scope() as db:
        assert recover(db) >= 1
        step = db.query(Task).filter(Task.parent_id == task_id, Task.step_key == "research").one()
        assert step.status == "queued" and step.attempts == 0
        assert db.query(AgentRun).filter(AgentRun.task_id == step.id).one().status == "interrupted"


@needs_sandbox
def test_test_workflow_runs_in_sandbox_without_ai(client, auth):
    pid = client.post("/api/projects", json={"name": "Somente testes"}, headers=auth).json()["id"]
    client.put(f"/api/projects/{pid}/files/content", json={"path": "test_ok.py", "content": "def test_ok():\n    assert True\n"}, headers=auth)
    task_id = client.post(f"/api/projects/{pid}/workflows", json={"workflow": "test"}, headers=auth).json()["id"]
    run_until_idle()
    detail, steps = _steps(client, auth, task_id)
    assert detail["status"] == "succeeded"
    assert steps["qa"]["result"]["passed"] is True and steps["qa"]["result"]["fixes"] == 0


def test_sandbox_unavailable_is_reported(monkeypatch, client, auth):
    from genisia.agents import development

    def boom(*a, **k):
        raise SandboxUnavailable("sem isolamento")

    monkeypatch.setattr(development, "run_in_sandbox", boom)
    pid = client.post("/api/projects", json={"name": "Sem sandbox"}, headers=auth).json()["id"]
    client.put(f"/api/projects/{pid}/files/content", json={"path": "test_ok.py", "content": "def test_ok():\n    assert True\n"}, headers=auth)
    task_id = client.post(f"/api/projects/{pid}/workflows", json={"workflow": "test"}, headers=auth).json()["id"]
    run_until_idle()
    _, steps = _steps(client, auth, task_id)
    assert steps["qa"]["status"] == "failed" and "sem isolamento" in steps["qa"]["error"]


def test_agents_and_dashboard(client, auth):
    agents = client.get("/api/agents", headers=auth).json()
    names = {a["name"] for a in agents}
    assert {"orchestrator", "architect", "developer", "qa", "reverse_engineer", "research", "security", "documentation",
            "optimizer", "integrations"} <= names
    dash = client.get("/api/dashboard", headers=auth).json()
    assert "workflows_by_status" in dash["counts"]
    assert dash["ai_usage"]["cost_usd"] >= 0


def test_dispatcher_reserves_capacity_for_interactive_work(client, auth):
    from genisia.orchestrator.engine import BACKGROUND_PRIORITY, INTERACTIVE_PRIORITY, create_workflow, tick

    project = _project(client, auth)
    with session_scope() as db:
        owner = db.get(Task, client.post(f"/api/projects/{project['id']}/workflows", json={"workflow": "plan"}, headers=auth).json()["id"]).owner_id
        for _ in range(3):
            create_workflow(db, owner_id=owner, workflow="test", project_id=project["id"], priority=BACKGROUND_PRIORITY)
    with session_scope() as db:
        claimed = tick(db, capacity=3)
        tasks = [db.get(Task, i) for i in claimed]
        # Interativa primeiro; segundo plano usa uma vaga e a última fica reservada
        assert sorted(t.priority for t in tasks) == [INTERACTIVE_PRIORITY, BACKGROUND_PRIORITY]
        for t in tasks:
            t.status = "cancelled"
    with session_scope() as db:
        for t in db.query(Task).filter(Task.status == "queued", Task.project_id == project["id"]):
            t.status = "cancelled"
