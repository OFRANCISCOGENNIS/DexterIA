from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import pytest

_TMP = Path(tempfile.mkdtemp(prefix="genisia-test-"))
os.environ["GENISIA_DATA_DIR"] = str(_TMP / "data")
os.environ.setdefault("GENISIA_SANDBOX_DIR", "/var/tmp/genisia-sandbox-test")
os.environ["GENISIA_WORKER_ENABLED"] = "false"
os.environ["GENISIA_SECRET_KEY"] = "test-secret-key-for-genisia-only"
os.environ["GENISIA_IMPORT_ROOTS"] = str(_TMP / "imports")
os.environ["GENISIA_RATE_LIMIT_PER_MINUTE"] = "100000"
os.environ.pop("ANTHROPIC_API_KEY", None)
if os.environ.get("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
else:
    os.environ.pop("DATABASE_URL", None)

from fastapi.testclient import TestClient  # noqa: E402

from genisia.ai.providers import set_provider_override  # noqa: E402
from genisia.config import reload_settings  # noqa: E402
from genisia.ratelimit import limiter  # noqa: E402

reload_settings()

from genisia.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        if os.environ.get("TEST_DATABASE_URL"):
            from genisia.db import Base, get_engine

            with get_engine().begin() as conn:
                for table in reversed(Base.metadata.sorted_tables):
                    conn.execute(table.delete())
        yield c
    shutil.rmtree(_TMP, ignore_errors=True)


@pytest.fixture(autouse=True)
def _reset():
    limiter.reset()
    set_provider_override(None)
    yield
    set_provider_override(None)


@pytest.fixture
def import_root() -> Path:
    path = _TMP / "imports"
    path.mkdir(parents=True, exist_ok=True)
    return path


_counter = {"n": 0}


@pytest.fixture
def auth(client):
    _counter["n"] += 1
    email = f"user{_counter['n']}@example.com"
    r = client.post("/api/auth/register", json={"email": email, "name": f"Usuária {_counter['n']}", "password": "senha-forte-123"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
