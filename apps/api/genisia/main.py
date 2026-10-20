"""Aplicação FastAPI do GENISIA AI."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import API_ROOT, settings
from .db import get_engine, init_engine
from .ratelimit import RateLimitMiddleware
from .routers import approvals, auth, knowledge, projects, repositories, system, tasks

log = logging.getLogger("genisia")


def run_migrations() -> None:
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(API_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", settings.sqlalchemy_url.replace("%", "%%"))
    with get_engine().begin() as connection:
        cfg.attributes["connection"] = connection
        command.upgrade(cfg, "head")
    db_file = settings.data_dir / "genisia.db"
    if db_file.exists():
        db_file.chmod(0o600)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_engine()
    run_migrations()
    from .orchestrator.engine import start_worker, stop_worker

    if settings.worker_enabled:
        start_worker()
    yield
    if settings.worker_enabled:
        stop_worker()


def create_app() -> FastAPI:
    app = FastAPI(
        title="GENISIA AI API",
        version="0.1.0",
        description="Ecossistema de desenvolvimento de software com agentes especializados, execução isolada e supervisão humana.",
        lifespan=lifespan,
    )
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=False,
                       allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"], allow_headers=["Authorization", "Content-Type"])

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_request: Request, exc: RequestValidationError):
        errors = [{"loc": list(e.get("loc", [])), "msg": e.get("msg"), "type": e.get("type")} for e in exc.errors()]
        return JSONResponse({"detail": "Dados inválidos", "errors": errors}, status_code=422)

    @app.exception_handler(Exception)
    async def unhandled(_request: Request, exc: Exception):  # pragma: no cover - rede de segurança
        log.exception("Erro não tratado", exc_info=exc)
        return JSONResponse({"detail": "Erro interno"}, status_code=500)

    for router in (auth.router, projects.router, tasks.router, approvals.router, repositories.router, knowledge.router, system.router):
        app.include_router(router)
    return app


app = create_app()
_ = Path  # mantém import usado por ferramentas de análise
