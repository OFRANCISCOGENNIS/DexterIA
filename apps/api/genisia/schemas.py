"""Esquemas de entrada/saída da API (validação com Pydantic)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------- auth
class RegisterIn(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(ORM):
    id: str
    email: str
    name: str
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------------------------------------------------------------- projetos
LANGUAGES = Literal["python", "javascript"]


class ProjectSettings(BaseModel):
    ai_budget_usd: float = Field(2.0, ge=0, le=1000)
    max_fix_iterations: int = Field(2, ge=0, le=5)
    sandbox_network: bool = False


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = Field("", max_length=5000)
    requirements: str = Field("", max_length=20000)
    language: LANGUAGES = "python"
    stack: list[str] = Field(default_factory=list, max_length=20)
    settings: ProjectSettings = Field(default_factory=ProjectSettings)

    @field_validator("stack")
    @classmethod
    def _stack(cls, v: list[str]) -> list[str]:
        return [s.strip()[:40] for s in v if s.strip()]


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=160)
    description: str | None = Field(None, max_length=5000)
    requirements: str | None = Field(None, max_length=20000)
    language: LANGUAGES | None = None
    stack: list[str] | None = Field(None, max_length=20)
    settings: ProjectSettings | None = None


class ProjectOut(ORM):
    id: str
    name: str
    description: str
    requirements: str
    language: str
    stack: list[str]
    settings: dict[str, Any]
    status: str
    approved_plan_artifact_id: str | None
    created_at: datetime
    updated_at: datetime


class ProjectDetail(ProjectOut):
    stats: dict[str, Any]


# ---------------------------------------------------------------- tarefas
class WorkflowIn(BaseModel):
    workflow: Literal["mission", "plan", "develop", "test"]
    objective: str = Field("", max_length=2000)
    instructions: str = Field("", max_length=8000)


class TaskOut(ORM):
    id: str
    project_id: str | None
    parent_id: str | None
    kind: str
    step_key: str | None
    agent: str | None
    title: str
    objective: str
    status: str
    priority: int
    depends_on: list[str]
    input: dict[str, Any]
    result: dict[str, Any] | None
    error: str | None
    optional: bool
    attempts: int
    max_attempts: int
    cancel_requested: bool
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class AgentRunOut(ORM):
    id: str
    task_id: str
    agent: str
    attempt: int
    status: str
    started_at: datetime
    finished_at: datetime | None
    provider: str | None
    model: str | None
    input_tokens: int
    output_tokens: int
    cost_usd: float
    summary: str | None
    error: str | None
    logs: str


class TaskDetail(TaskOut):
    steps: list[TaskOut] = []
    runs: list[AgentRunOut] = []
    approvals: list["ApprovalOut"] = []


class ArtifactSummary(ORM):
    id: str
    project_id: str | None
    repository_id: str | None
    task_id: str | None
    kind: str
    title: str
    content_type: str
    created_at: datetime


class ArtifactOut(ArtifactSummary):
    content: str
    data: dict[str, Any] | None


# ---------------------------------------------------------------- aprovações
class ApprovalOut(ORM):
    id: str
    project_id: str | None
    task_id: str | None
    action: str
    description: str
    payload: dict[str, Any]
    status: str
    requested_by: str
    decided_by: str | None
    decided_at: datetime | None
    reason: str | None
    created_at: datetime


class ApprovalDecision(BaseModel):
    approve: bool
    reason: str | None = Field(None, max_length=2000)


# ---------------------------------------------------------------- repositórios
class RepositoryIn(BaseModel):
    source_type: Literal["git", "local"] = "git"
    source_url: str = Field(min_length=3, max_length=500)
    ref: str | None = Field(None, max_length=100)
    name: str | None = Field(None, max_length=200)
    project_id: str | None = None
    authorization_note: str = Field(..., min_length=3, max_length=2000,
                                    description="Declaração de que o usuário tem autorização para analisar este repositório")


class RepositoryOut(ORM):
    id: str
    project_id: str | None
    name: str
    source_type: str
    source_url: str
    ref: str | None
    commit_sha: str | None
    status: str
    authorization_note: str
    last_task_id: str | None
    last_analysis_artifact_id: str | None
    summary: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class AnalyzeIn(BaseModel):
    workflow: Literal["analyze_repository", "ingest_knowledge"] = "analyze_repository"
    force: bool = False
    profile: str | None = Field(None, max_length=60)


# ---------------------------------------------------------------- conhecimento
class KnowledgeSourceOut(ORM):
    id: str
    project_id: str | None
    name: str
    kind: str
    origin_url: str | None
    origin_commit: str | None
    license: str | None
    meta: dict[str, Any]
    item_count: int
    indexed_at: datetime | None


class MemoryIn(BaseModel):
    title: str = Field(min_length=1, max_length=400)
    content: str = Field(min_length=1, max_length=8000)
    item_type: Literal["decision", "memory"] = "decision"
    tags: list[str] = Field(default_factory=list, max_length=10)


# ---------------------------------------------------------------- integrações
class AIConfigIn(BaseModel):
    api_key: str | None = Field(None, min_length=10, max_length=300)
    model: str | None = None
    effort: Literal["low", "medium", "high", "xhigh", "max"] | None = None
    enabled: bool = True


TaskDetail.model_rebuild()
