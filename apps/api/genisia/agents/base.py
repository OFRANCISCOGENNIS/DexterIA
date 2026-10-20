"""Contrato dos agentes e contexto de execução compartilhado."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..ai.providers import AIError, AIProvider, AIResult, AINotConfigured, resolve_provider
from ..config import settings
from ..models import AgentRun, Approval, Artifact, Project, Task, utcnow
from ..security import redact


class AgentError(RuntimeError):
    retryable = True

    def __init__(self, message: str, result: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.result = result


class NonRetryableError(AgentError):
    retryable = False


class BudgetExceeded(NonRetryableError):
    pass


class TaskCancelled(Exception):
    pass


class AgentSkip(Exception):
    """A etapa não se aplica (ex.: dependência opcional ausente). Não é falha."""


class ApprovalRequired(Exception):
    def __init__(self, action: str, description: str, payload: dict[str, Any] | None = None) -> None:
        super().__init__(description)
        self.action = action
        self.description = description
        self.payload = payload or {}


@dataclass
class AgentContext:
    db: Session
    task: Task
    run: AgentRun
    project: Project | None
    inputs: dict[str, Any] = field(default_factory=dict)
    started: float = field(default_factory=time.monotonic)
    _provider: AIProvider | None = None

    # ------------------------------------------------------------- utilidades
    @property
    def params(self) -> dict[str, Any]:
        return self.task.input or {}

    def log(self, message: str) -> None:
        stamp = utcnow().strftime("%H:%M:%S")
        self.run.logs = (self.run.logs or "") + f"[{stamp}] {redact(message)}\n"
        self.db.commit()

    def check_cancel(self) -> None:
        self.db.refresh(self.task, attribute_names=["cancel_requested"])
        if self.task.cancel_requested:
            raise TaskCancelled()
        if time.monotonic() - self.started > self.task.timeout_seconds:
            raise NonRetryableError(f"Tempo limite da etapa excedido ({self.task.timeout_seconds}s)")

    def cancel_requested(self) -> bool:
        try:
            self.check_cancel()
        except TaskCancelled:
            return True
        except NonRetryableError:
            return True
        return False

    def add_artifact(self, kind: str, title: str, content: str, data: dict | None = None,
                     content_type: str = "text/markdown", repository_id: str | None = None) -> Artifact:
        artifact = Artifact(
            project_id=self.project.id if self.project else None, repository_id=repository_id, task_id=self.task.id,
            owner_id=self.task.owner_id, kind=kind, title=title[:200], content=content, data=data, content_type=content_type,
        )
        self.db.add(artifact)
        self.db.commit()
        return artifact

    def delegate(self, agent_name: str) -> "AgentContext":
        """Cria um contexto para outro agente na mesma tarefa (registrado como execução separada)."""
        sub_run = AgentRun(task_id=self.task.id, project_id=self.task.project_id, agent=agent_name,
                           attempt=self.task.attempts, status="running")
        self.db.add(sub_run)
        self.db.commit()
        self.log(f"Delegando para o agente '{agent_name}' (execução {sub_run.id})")
        return AgentContext(db=self.db, task=self.task, run=sub_run, project=self.project, inputs=self.inputs,
                            started=self.started, _provider=self._provider)

    def approved(self, action: str) -> Approval | None:
        return self.db.scalar(select(Approval).where(Approval.task_id == self.task.id, Approval.action == action,
                                                     Approval.status == "approved"))

    # ------------------------------------------------------------- IA
    def provider(self) -> AIProvider:
        if self._provider is None:
            self._provider = resolve_provider(self.db, self.task.owner_id)
        return self._provider

    def ai_available(self) -> bool:
        return bool(self.provider().status().get("configured"))

    def budget(self) -> tuple[float, float]:
        if not self.project:
            return 0.0, settings.default_project_budget_usd
        spent = self.db.scalar(select(func.coalesce(func.sum(AgentRun.cost_usd), 0.0)).where(AgentRun.project_id == self.project.id)) or 0.0
        limit = float((self.project.settings or {}).get("ai_budget_usd", settings.default_project_budget_usd))
        return float(spent), limit

    def ai(self, *, system: str, prompt: str, schema: type[BaseModel], max_tokens: int | None = None) -> AIResult:
        spent, limit = self.budget()
        if spent >= limit:
            raise BudgetExceeded(f"Orçamento de IA do projeto esgotado (US$ {spent:.4f} de US$ {limit:.2f})")
        provider = self.provider()
        self.log(f"Chamando IA ({provider.name}/{provider.model}); gasto atual US$ {spent:.4f} de US$ {limit:.2f}")
        self.check_cancel()
        try:
            result = provider.generate_structured(system=system, prompt=prompt, schema=schema, max_tokens=max_tokens)
        except AINotConfigured as exc:
            raise NonRetryableError(str(exc)) from exc
        except AIError as exc:
            raise AgentError(str(exc)) from exc
        usage = result.usage
        self.run.provider = usage.provider
        self.run.model = usage.model
        self.run.input_tokens += usage.input_tokens
        self.run.output_tokens += usage.output_tokens
        self.run.cost_usd = round(self.run.cost_usd + usage.cost_usd, 6)
        self.log(f"IA respondeu: {usage.input_tokens} tokens de entrada, {usage.output_tokens} de saída, US$ {usage.cost_usd:.4f}")
        return result


class Agent:
    name: str = "agent"
    title: str = "Agente"
    description: str = ""
    responsibilities: list[str] = []
    uses_ai: bool = False

    def run(self, ctx: AgentContext) -> dict[str, Any]:  # pragma: no cover - interface
        raise NotImplementedError

    def info(self) -> dict[str, Any]:
        return {"name": self.name, "title": self.title, "description": self.description,
                "responsibilities": self.responsibilities, "uses_ai": self.uses_ai}
