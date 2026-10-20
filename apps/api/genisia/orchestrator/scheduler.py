"""Gatilhos agendados do Centro de Automação.

Apenas fluxos determinísticos podem ser agendados: eles não geram nem executam código produzido
por IA, então um agendamento nunca gasta orçamento de IA nem contorna uma aprovação humana.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import audit
from ..models import ScheduledTrigger, Task, utcnow
from .engine import BACKGROUND_PRIORITY, WorkflowError, create_workflow

SCHEDULABLE_WORKFLOWS = {"test": "project", "analyze_repository": "repository", "ingest_knowledge": "repository"}
MIN_INTERVAL_MINUTES = 15
MAX_INTERVAL_MINUTES = 60 * 24 * 30


def run_due_triggers(db: Session, now: datetime | None = None) -> list[str]:
    """Inicia os fluxos dos gatilhos vencidos. Retorna os ids das tarefas criadas."""
    now = now or utcnow()
    created: list[str] = []
    due = db.scalars(select(ScheduledTrigger).where(ScheduledTrigger.enabled.is_(True), ScheduledTrigger.next_run_at <= now)).all()
    for trigger in due:
        # Próxima execução a partir de agora: um servidor parado não dispara uma rajada de execuções atrasadas.
        trigger.next_run_at = now + timedelta(minutes=trigger.interval_minutes)
        previous = db.get(Task, trigger.last_task_id) if trigger.last_task_id else None
        if previous is not None and previous.status in {"queued", "running", "awaiting_approval"}:
            trigger.last_error = "Execução anterior ainda em andamento; esta foi pulada"
            db.commit()
            continue
        try:
            task = create_workflow(db, owner_id=trigger.owner_id, workflow=trigger.workflow, project_id=trigger.project_id,
                                   repository_id=trigger.repository_id, objective=f"Gatilho agendado: {trigger.name}",
                                   priority=BACKGROUND_PRIORITY)
        except WorkflowError as exc:
            trigger.last_error = str(exc)
            db.commit()
            continue
        trigger.last_task_id = task.id
        trigger.last_run_at = now
        trigger.last_error = None
        trigger.run_count += 1
        audit.record(db, "trigger.fired", actor_label="scheduler", project_id=trigger.project_id, target_type="trigger",
                     target_id=trigger.id, details={"workflow": trigger.workflow, "task_id": task.id})
        db.commit()
        created.append(task.id)
    return created
