"""Formatos estruturados exigidos das respostas da IA (validados com Pydantic)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class Technology(BaseModel):
    name: str
    reason: str


class Risk(BaseModel):
    risk: str
    mitigation: str


class Component(BaseModel):
    name: str
    responsibility: str


class Entity(BaseModel):
    name: str
    fields: list[str]


class Endpoint(BaseModel):
    method: str
    path: str
    description: str


class PlannedTask(BaseModel):
    title: str
    description: str
    agent: Literal["architect", "developer", "qa", "security", "documentation", "optimizer", "research"]
    complexity: Literal["baixa", "média", "alta"]


class ProjectPlan(BaseModel):
    summary: str
    functional_requirements: list[str]
    non_functional_requirements: list[str]
    candidate_technologies: list[Technology]
    integrations: list[str]
    risks: list[Risk]
    acceptance_criteria: list[str]
    architecture_style: str
    components: list[Component]
    component_diagram_mermaid: str
    folder_structure: str
    database_engine: str
    entities: list[Entity]
    api_endpoints: list[Endpoint]
    tasks: list[PlannedTask]
    tests_planned: list[str]
    complexity_estimate: str
    mvp_scope_for_first_iteration: str


class GeneratedFile(BaseModel):
    path: str
    content: str


class CodeChange(BaseModel):
    summary: str
    files: list[GeneratedFile]
    test_command: Literal["pytest", "node_test", "none"]
    notes: str


class RepoReview(BaseModel):
    architecture_summary: str
    main_flows: list[str]
    integration_points: list[str]
    refactoring_recommendations: list[str]
    reimplementation_strategy: str
    open_questions: list[str]
