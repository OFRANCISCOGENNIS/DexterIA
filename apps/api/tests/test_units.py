from __future__ import annotations

from types import SimpleNamespace

import pytest

from genisia.agents.ai_schemas import ProjectPlan
from genisia.ai import providers
from genisia.ai.providers import AIError, AIUsage, AnthropicProvider, strict_json_schema
from genisia.execution.sandbox import run_in_sandbox, sandbox_status
from genisia.execution.workspace import WorkspaceError, normalize_relpath
from genisia.knowledge.ingest import parse_markdown_links, parse_public_apis
from genisia.security import decrypt_secret, encrypt_secret, redact

from .test_repositories_knowledge import AWESOME_README, PUBLIC_APIS


def test_strict_schema_is_closed():
    schema = strict_json_schema(ProjectPlan)

    def walk(node):
        if isinstance(node, dict):
            if "properties" in node:
                assert node["additionalProperties"] is False
                assert set(node["required"]) == set(node["properties"])
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(schema)


def test_cost_estimate():
    usage = AIUsage(provider="anthropic", model="claude-opus-5-5", input_tokens=1_000_000, output_tokens=100_000)
    assert usage.cost_usd == pytest.approx(4.0 + 2.0)


class _FakeMessages:
    def __init__(self, response):
        self.response = response
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return self.response


def _provider_with(response, monkeypatch):
    messages = _FakeMessages(response)
    provider = AnthropicProvider("sk-ant-x", "claude-opus-5-5", "medium", "teste")
    monkeypatch.setattr(provider, "_client", lambda: SimpleNamespace(messages=messages))
    return provider, messages


def test_anthropic_provider_parses_structured_output(monkeypatch):
    from .fakes import make_plan

    text = make_plan().model_dump_json()
    response = SimpleNamespace(stop_reason="end_turn", model="claude-opus-5-5", content=[SimpleNamespace(type="text", text=text)],
                               usage=SimpleNamespace(input_tokens=10, output_tokens=20))
    provider, messages = _provider_with(response, monkeypatch)
    result = provider.generate_structured(system="s", prompt="p", schema=ProjectPlan)
    assert result.data.summary.startswith("Sistema financeiro")
    assert result.usage.input_tokens == 10
    assert messages.kwargs["output_config"]["format"]["type"] == "json_schema"
    assert messages.kwargs["output_config"]["effort"] == "medium"
    assert messages.kwargs["extra_body"] == {"fallbacks": "default"}


def test_anthropic_provider_refusal_and_invalid_json(monkeypatch):
    refusal = SimpleNamespace(stop_reason="refusal", model="m", content=[], usage=SimpleNamespace(input_tokens=1, output_tokens=0))
    provider, _ = _provider_with(refusal, monkeypatch)
    with pytest.raises(AIError, match="recusou"):
        provider.generate_structured(system="s", prompt="p", schema=ProjectPlan)
    bad = SimpleNamespace(stop_reason="end_turn", model="m", content=[SimpleNamespace(type="text", text="{}")],
                          usage=SimpleNamespace(input_tokens=1, output_tokens=1))
    provider, _ = _provider_with(bad, monkeypatch)
    with pytest.raises(AIError, match="formato esperado"):
        provider.generate_structured(system="s", prompt="p", schema=ProjectPlan)


def test_resolve_provider_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from genisia.db import session_scope

    with session_scope() as db:
        provider = providers.resolve_provider(db, None)
    assert provider.status()["configured"] is False


def test_secret_encryption_and_redaction():
    token = encrypt_secret("sk-ant-segredo-123456789")
    assert "segredo" not in token
    assert decrypt_secret(token) == "sk-ant-segredo-123456789"
    assert decrypt_secret("lixo") is None
    assert "[REDACTED]" in redact("chave sk-ant-abcdefghijklmnop e ghp_" + "a" * 36)


@pytest.mark.parametrize("path", ["../a", "/abs", ".git/hooks/x", "a/../../b", "a\\b", "", ".github/workflows/x.yml"])
def test_workspace_rejects_unsafe_paths(path):
    with pytest.raises(WorkspaceError):
        normalize_relpath(path)


def test_markdown_link_parser():
    items = parse_markdown_links(AWESOME_README, "README.md", "tool", min_heading=2)
    assert [i.title for i in items] == ["FastAPI", "Express", "PostgreSQL"]
    assert items[0].description == "Framework web moderno para APIs em Python."


def test_public_apis_parser():
    items = parse_public_apis(PUBLIC_APIS, "README.md")
    assert len(items) == 3
    cambio = items[0]
    assert cambio.category == "Finance" and cambio.extra["auth"] == "none" and cambio.extra["https"] is True
    assert items[1].extra["auth"] == "apiKey"


needs_sandbox = pytest.mark.skipif(not sandbox_status()["available"], reason="sandbox indisponível")


@needs_sandbox
def test_sandbox_blocks_network_and_enforces_timeout(tmp_path):
    (tmp_path / "net.py").write_text(
        "import socket\ntry:\n    socket.create_connection(('1.1.1.1', 80), timeout=2)\n    print('REDE-ACESSIVEL')\n"
        "except OSError as e:\n    print('SEM-REDE', type(e).__name__)\n")
    result = run_in_sandbox(tmp_path, ["python3", "net.py"])
    assert "SEM-REDE" in result.output and result.passed
    slow = run_in_sandbox(tmp_path, ["python3", "-c", "while True: pass"], timeout=2)
    assert slow.timed_out and not slow.passed


@needs_sandbox
def test_sandbox_cannot_read_platform_data(tmp_path):
    from genisia.config import settings

    secret = settings.data_dir / ".probe"
    secret.write_text("x")
    secret.chmod(0o600)
    result = run_in_sandbox(tmp_path, ["python3", "-c", f"open({str(secret)!r}).read()"])
    if sandbox_status()["namespace_mode"] == "root":
        assert result.exit_code != 0 and "PermissionError" in result.output


def test_clean_removes_underscore_emphasis_only():
    from genisia.knowledge.ingest import _clean

    assert _clean("**Python**: _Implementing a RESTful API_") == "Python: Implementing a RESTful API"
    assert _clean("use my_snake_case_name") == "use my_snake_case_name"
