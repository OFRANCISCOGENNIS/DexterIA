"""Motor de orquestração: fila persistida no banco, despacho por dependências, tentativas,
cancelamento, aprovações e retomada após falhas/reinícios.

Toda a máquina de estados vive nas tabelas ``tasks``/``agent_runs``/``approvals``; os threads de
trabalho são apenas executores, então o processo pode ser reiniciado sem perder o estado.
"""
from __future__ import annotations

import logging
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from .. import audit
from ..agents.base import AgentContext, AgentError, AgentSkip, ApprovalRequired, TaskCancelled
from ..agents.registry import AGENTS
from ..config import settings
from ..db import session_factory
from ..models import AgentRun, Approval, Project, Task, utcnow
from ..security import redact
from .workflows import WORKFLOWS

log = logging.getLogger("genisia.orchestrator")

TERMINAL = {"succeeded", "failed", "cancelled", "skipped"}
ACTIVE = {"queued", "running", "awaiting_approval", "pending"}


class WorkflowError(ValueError):
    pass


def create_workflow(db: Session, *, owner_id: str, workflow: str, project_id: str | None = None,
                    repository_id: str | None = None, objective: str = "", params: dict[str, Any] | None = None,
                    priority: int = 5) -> Task:
    spec = WORKFLOWS.get(workflow)
    if spec is None:
        raise WorkflowError(f"Fluxo desconhecido: {workflow}")
    if spec.requires == "project" and not project_id:
        raise WorkflowError("Este fluxo exige um projeto")
    if spec.requires == "repository" and not repository_id:
        raise WorkflowError("Este fluxo exige um repositório")
    if workflow == "develop":
        project = db.get(Project, project_id)
        if not project or not project.approved_plan_artifact_id:
            raise WorkflowError("Aprove um plano antes de iniciar uma iteração de desenvolvimento")
    params = params or {}
    root = Task(owner_id=owner_id, project_id=project_id, kind=f"workflow:{workflow}", title=spec.title,
                objective=objective or spec.description, status="queued", priority=priority,
                input={"workflow": workflow, "repository_id": repository_id, **params})
    db.add(root)
    db.flush()
    ids: dict[str, str] = {}
    for step in spec.steps:
        step_input = {**step.input, **({"repository_id": repository_id} if repository_id else {}), **params.get(step.key, {})}
        if step.run_always:
            step_input["_run_always"] = True
        task = Task(owner_id=owner_id, project_id=project_id, parent_id=root.id, kind="step", step_key=step.key,
                    agent=step.agent, title=step.title, objective=step.title, status="queued", priority=priority,
                    depends_on=[ids[d] for d in step.depends_on], input=step_input, optional=step.optional,
                    max_attempts=step.max_attempts, timeout_seconds=step.timeout_seconds)
        db.add(task)
        db.flush()
        ids[step.key] = task.id
    audit.record(db, "workflow.created", actor_id=owner_id, project_id=project_id, target_type="task", target_id=root.id,
                 details={"workflow": workflow, "repository_id": repository_id})
    db.commit()
    return root


def _dep_state(deps: list[Task]) -> str:
    """Retorna 'ready', 'waiting' ou 'blocked'."""
    for d in deps:
        if d.status not in TERMINAL:
            return "waiting"
    for d in deps:
        if d.status != "succeeded" and not (d.optional and d.status in {"failed", "skipped"}):
            return "blocked"
    return "ready"


INTERACTIVE_PRIORITY = 3  # fluxos de projeto iniciados pelo usuário
BACKGROUND_PRIORITY = 6   # análises/ingestões de repositórios (longas)


def tick(db: Session, capacity: int | None = None) -> list[str]:
    """Propaga bloqueios, finaliza fluxos concluídos e reivindica etapas prontas.

    ``capacity`` limita quantas etapas são reivindicadas (vagas livres no pool). Etapas de segundo
    plano nunca ocupam a última vaga livre, para que tarefas interativas não fiquem presas atrás de
    análises demoradas. Retorna os ids das etapas reivindicadas (status ``running``).
    """
    claimed: list[str] = []
    queued = db.scalars(select(Task).where(Task.kind == "step", Task.status == "queued")
                        .order_by(Task.priority, Task.created_at)).all()
    for task in queued:
        deps = list(db.scalars(select(Task).where(Task.id.in_(task.depends_on)))) if task.depends_on else []
        state = _dep_state(deps)
        if state == "blocked" and not task.input.get("_run_always"):
            failed = [d.title for d in deps if d.status != "succeeded"]
            task.status = "skipped"
            task.error = f"Dependência não concluída: {', '.join(failed)}"
            task.finished_at = utcnow()
            db.commit()
            continue
        if state == "waiting":
            continue
        if capacity is not None:
            free = capacity - len(claimed)
            if free <= 0:
                break
            if task.priority > INTERACTIVE_PRIORITY and free <= 1 and capacity > 1:
                continue
        result = db.execute(update(Task).where(Task.id == task.id, Task.status == "queued").values(
            status="running", attempts=Task.attempts + 1, started_at=utcnow()))
        db.commit()
        if result.rowcount == 1:
            claimed.append(task.id)
            parent = db.get(Task, task.parent_id) if task.parent_id else None
            if parent and parent.status == "queued":
                parent.status = "running"
                parent.started_at = utcnow()
                db.commit()
    _finalize_workflows(db)
    return claimed


def _finalize_workflows(db: Session) -> None:
    roots = db.scalars(select(Task).where(Task.parent_id.is_(None), Task.kind.like("workflow:%"),
                                          Task.status.in_(["queued", "running", "awaiting_approval"]))).all()
    for root in roots:
        steps = db.scalars(select(Task).where(Task.parent_id == root.id)).all()
        if any(s.status == "awaiting_approval" for s in steps):
            if root.status != "awaiting_approval":
                root.status = "awaiting_approval"
                db.commit()
            continue
        if any(s.status not in TERMINAL for s in steps):
            if root.status == "awaiting_approval":
                root.status = "running"
                db.commit()
            continue
        cost = db.scalar(select(func.coalesce(func.sum(AgentRun.cost_usd), 0.0))
                         .where(AgentRun.task_id.in_([s.id for s in steps]))) or 0.0
        required_ok = all(s.status == "succeeded" or s.optional for s in steps)
        if root.cancel_requested or any(s.status == "cancelled" for s in steps):
            root.status = "cancelled"
        else:
            root.status = "succeeded" if required_ok else "failed"
        root.finished_at = utcnow()
        root.result = {
            "steps": [{"key": s.step_key, "agent": s.agent, "status": s.status, "error": s.error,
                       "artifact_id": (s.result or {}).get("artifact_id")} for s in steps],
            "cost_usd": round(float(cost), 6),
        }
        failed = [s for s in steps if s.status in {"failed", "skipped"} and not s.optional]
        if failed:
            root.error = "; ".join(f"{s.title}: {s.error}" for s in failed if s.error)[:2000]
        audit.record(db, f"workflow.{root.status}", actor_label="orchestrator", project_id=root.project_id,
                     target_type="task", target_id=root.id, details={"cost_usd": root.result["cost_usd"]})
        db.commit()


def execute_step(task_id: str) -> None:
    db = session_factory()()
    try:
        _execute(db, task_id)
    finally:
        db.close()


def _execute(db: Session, task_id: str) -> None:
    task = db.get(Task, task_id)
    if task is None or task.status != "running":
        return
    agent = AGENTS.get(task.agent or "")
    run = AgentRun(task_id=task.id, project_id=task.project_id, agent=task.agent or "?", attempt=task.attempts, status="running")
    db.add(run)
    db.commit()
    if agent is None:
        _finish(db, task, run, "failed", error=f"Agente desconhecido: {task.agent}")
        return
    project = db.get(Project, task.project_id) if task.project_id else None
    deps = list(db.scalars(select(Task).where(Task.id.in_(task.depends_on)))) if task.depends_on else []
    inputs = {d.step_key: d.result for d in deps if d.step_key and d.result}
    ctx = AgentContext(db=db, task=task, run=run, project=project, inputs=inputs)
    ctx.log(f"Agente '{agent.title}' iniciou (tentativa {task.attempts}/{task.max_attempts})")
    try:
        if task.cancel_requested:
            raise TaskCancelled()
        result = agent.run(ctx)
        _finish(db, task, run, "succeeded", result=result)
    except ApprovalRequired as req:
        existing = db.scalar(select(Approval).where(Approval.task_id == task.id, Approval.action == req.action,
                                                    Approval.status == "pending"))
        if existing is None:
            db.add(Approval(owner_id=task.owner_id, project_id=task.project_id, task_id=task.id, action=req.action,
                            description=req.description, payload=req.payload, requested_by=agent.name))
        ctx.log(f"Aguardando aprovação humana: {req.action}")
        audit.record(db, "approval.requested", actor_label=agent.name, project_id=task.project_id, target_type="task",
                     target_id=task.id, details={"action": req.action})
        _finish(db, task, run, "awaiting_approval", terminal=False)
    except AgentSkip as skip:
        ctx.log(f"Etapa não aplicável: {skip}")
        _finish(db, task, run, "skipped", error=str(skip))
    except TaskCancelled:
        ctx.log("Cancelada a pedido do usuário")
        _finish(db, task, run, "cancelled", error="Cancelada pelo usuário")
    except Exception as exc:  # noqa: BLE001 - qualquer falha de agente é registrada
        retryable = getattr(exc, "retryable", True) if isinstance(exc, AgentError) else True
        message = redact(str(exc)) or exc.__class__.__name__
        if not isinstance(exc, AgentError):
            log.exception("Falha inesperada no agente %s", task.agent)
            ctx.log("Erro inesperado:\n" + redact(traceback.format_exc()[-3000:]))
        partial = getattr(exc, "result", None)
        if retryable and task.attempts < task.max_attempts and not task.cancel_requested:
            ctx.log(f"Falha ({message}); nova tentativa será agendada")
            run.status, run.error, run.finished_at = "failed", message, utcnow()
            task.status = "queued"
            task.error = message
            db.commit()
        else:
            ctx.log(f"Falha definitiva: {message}")
            _finish(db, task, run, "failed", error=message, result=partial)


def _finish(db: Session, task: Task, run: AgentRun, status: str, *, result: dict | None = None,
            error: str | None = None, terminal: bool = True) -> None:
    run.status = status
    run.error = error
    run.finished_at = utcnow()
    if result is not None:
        run.summary = str({k: v for k, v in result.items() if k in {"summary", "passed", "artifact_id", "items", "verified"}})[:1000]
    task.status = status
    task.error = error
    if result is not None:
        task.result = result
    if terminal:
        task.finished_at = utcnow()
    audit.record(db, f"step.{status}", actor_label=task.agent or "agent", project_id=task.project_id, target_type="task",
                 target_id=task.id, details={"step": task.step_key, "error": error})
    db.commit()


def cancel_task(db: Session, task: Task, actor_id: str) -> Task:
    root = task if task.parent_id is None else db.get(Task, task.parent_id)
    targets = [root] + list(db.scalars(select(Task).where(Task.parent_id == root.id)))
    for t in targets:
        t.cancel_requested = True
        if t.status in {"queued", "pending", "awaiting_approval"} and t.kind == "step":
            t.status = "cancelled"
            t.error = "Cancelada pelo usuário"
            t.finished_at = utcnow()
    for approval in db.scalars(select(Approval).where(Approval.task_id.in_([t.id for t in targets]), Approval.status == "pending")):
        approval.status = "cancelled"
        approval.decided_at = utcnow()
    audit.record(db, "workflow.cancel_requested", actor_id=actor_id, project_id=root.project_id, target_type="task", target_id=root.id)
    db.commit()
    _finalize_workflows(db)
    return root


def retry_task(db: Session, task: Task, actor_id: str) -> Task:
    """Reexecuta um fluxo terminado com falha a partir das etapas que não concluíram."""
    root = task if task.parent_id is None else db.get(Task, task.parent_id)
    if root.status not in {"failed", "cancelled"}:
        raise WorkflowError("Só é possível retomar fluxos com falha ou cancelados")
    for t in db.scalars(select(Task).where(Task.parent_id == root.id)):
        if t.status in {"failed", "skipped", "cancelled"}:
            t.status, t.error, t.attempts, t.cancel_requested, t.finished_at = "queued", None, 0, False, None
    root.status, root.error, root.cancel_requested, root.finished_at = "queued", None, False, None
    audit.record(db, "workflow.retried", actor_id=actor_id, project_id=root.project_id, target_type="task", target_id=root.id)
    db.commit()
    return root


def decide_approval(db: Session, approval: Approval, *, approve: bool, actor_id: str, reason: str | None = None) -> Approval:
    if approval.status != "pending":
        raise WorkflowError("Esta aprovação já foi decidida")
    approval.status = "approved" if approve else "rejected"
    approval.decided_by = actor_id
    approval.decided_at = utcnow()
    approval.reason = reason
    task = db.get(Task, approval.task_id) if approval.task_id else None
    if task is not None and task.status == "awaiting_approval":
        if approve:
            task.status = "queued"
            task.attempts = max(task.attempts - 1, 0)  # a espera por aprovação não consome tentativa
        else:
            task.status = "failed"
            task.error = f"Rejeitado pelo usuário{': ' + reason if reason else ''}"
            task.finished_at = utcnow()
    audit.record(db, f"approval.{approval.status}", actor_id=actor_id, project_id=approval.project_id,
                 target_type="approval", target_id=approval.id, details={"action": approval.action, "reason": reason})
    db.commit()
    return approval


def recover(db: Session) -> int:
    """Etapas que estavam em execução quando o processo parou voltam para a fila."""
    stuck = db.scalars(select(Task).where(Task.kind == "step", Task.status == "running")).all()
    for t in stuck:
        t.status = "queued"
        t.attempts = max(t.attempts - 1, 0)
        t.error = "Retomada após reinício do servidor"
        for run in db.scalars(select(AgentRun).where(AgentRun.task_id == t.id, AgentRun.status == "running")):
            run.status, run.error, run.finished_at = "interrupted", "Servidor reiniciado durante a execução", utcnow()
    if stuck:
        audit.record(db, "orchestrator.recovered", actor_label="orchestrator", details={"steps": len(stuck)})
    db.commit()
    return len(stuck)


def run_until_idle(max_rounds: int = 200) -> None:
    """Executa o fluxo de forma síncrona (usado em testes e scripts)."""
    for _ in range(max_rounds):
        db = session_factory()()
        try:
            claimed = tick(db)
        finally:
            db.close()
        if not claimed:
            return
        for task_id in claimed:
            execute_step(task_id)


class Worker:
    """Despachante em segundo plano com um pool de threads executoras."""

    def __init__(self, threads: int | None = None, poll_seconds: float | None = None) -> None:
        self.threads = threads or settings.worker_threads
        self.poll = poll_seconds or settings.worker_poll_seconds
        self._stop = threading.Event()
        self._pool = ThreadPoolExecutor(max_workers=self.threads, thread_name_prefix="genisia-agent")
        self._thread = threading.Thread(target=self._loop, name="genisia-dispatcher", daemon=True)
        self._inflight: set[str] = set()
        self._lock = threading.Lock()

    def start(self) -> None:
        db = session_factory()()
        try:
            recovered = recover(db)
            if recovered:
                log.info("%s etapa(s) retomada(s) após reinício", recovered)
        finally:
            db.close()
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)
        self._pool.shutdown(wait=False, cancel_futures=True)

    def _done(self, task_id: str) -> None:
        with self._lock:
            self._inflight.discard(task_id)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                with self._lock:
                    busy = len(self._inflight)
                if busy < self.threads:
                    db = session_factory()()
                    try:
                        claimed = tick(db, capacity=self.threads - busy)
                    finally:
                        db.close()
                    for task_id in claimed:
                        with self._lock:
                            self._inflight.add(task_id)
                        future = self._pool.submit(execute_step, task_id)
                        future.add_done_callback(lambda _f, tid=task_id: self._done(tid))
            except Exception:  # noqa: BLE001
                log.exception("Erro no despachante")
            self._stop.wait(self.poll)


_worker: Worker | None = None


def start_worker() -> Worker:
    global _worker
    if _worker is None:
        _worker = Worker()
        _worker.start()
    return _worker


def stop_worker() -> None:
    global _worker
    if _worker is not None:
        _worker.stop()
        _worker = None
