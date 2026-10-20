"""Configuração central lida de variáveis de ambiente (nunca de código-fonte)."""
from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    return value if value not in (None, "") else default


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)))  # type: ignore[arg-type]
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(_env(name, str(default)))  # type: ignore[arg-type]
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    value = _env(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


API_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Settings:
    env: str = field(default_factory=lambda: _env("GENISIA_ENV", "development"))
    data_dir: Path = field(default_factory=lambda: Path(_env("GENISIA_DATA_DIR", str(API_ROOT / "data"))).resolve())
    database_url: str | None = field(default_factory=lambda: _env("DATABASE_URL"))
    secret_key: str | None = field(default_factory=lambda: _env("GENISIA_SECRET_KEY"))
    access_token_minutes: int = field(default_factory=lambda: _env_int("GENISIA_ACCESS_TOKEN_MINUTES", 720))
    cors_origins: list[str] = field(
        default_factory=lambda: [o.strip() for o in (_env("GENISIA_CORS_ORIGINS", "http://localhost:3000") or "").split(",") if o.strip()]
    )
    rate_limit_per_minute: int = field(default_factory=lambda: _env_int("GENISIA_RATE_LIMIT_PER_MINUTE", 240))
    auth_rate_limit_per_minute: int = field(default_factory=lambda: _env_int("GENISIA_AUTH_RATE_LIMIT_PER_MINUTE", 20))

    # Worker / orquestrador
    worker_enabled: bool = field(default_factory=lambda: _env_bool("GENISIA_WORKER_ENABLED", True))
    worker_threads: int = field(default_factory=lambda: _env_int("GENISIA_WORKER_THREADS", 3))
    worker_poll_seconds: float = field(default_factory=lambda: _env_float("GENISIA_WORKER_POLL_SECONDS", 0.5))

    # IA
    ai_provider: str = field(default_factory=lambda: _env("GENISIA_AI_PROVIDER", "anthropic"))
    ai_model: str = field(default_factory=lambda: _env("GENISIA_AI_MODEL", "claude-opus-5-5"))
    ai_effort: str = field(default_factory=lambda: _env("GENISIA_AI_EFFORT", "medium"))
    ai_max_tokens: int = field(default_factory=lambda: _env_int("GENISIA_AI_MAX_TOKENS", 16000))
    ai_timeout_seconds: float = field(default_factory=lambda: _env_float("GENISIA_AI_TIMEOUT_SECONDS", 600))
    ai_refusal_fallbacks: bool = field(default_factory=lambda: _env_bool("GENISIA_AI_REFUSAL_FALLBACKS", True))
    default_project_budget_usd: float = field(default_factory=lambda: _env_float("GENISIA_DEFAULT_PROJECT_BUDGET_USD", 2.0))

    # Execução isolada
    sandbox_backend: str = field(default_factory=lambda: _env("GENISIA_SANDBOX_BACKEND", "auto"))
    sandbox_timeout_seconds: int = field(default_factory=lambda: _env_int("GENISIA_SANDBOX_TIMEOUT_SECONDS", 120))
    sandbox_memory_mb: int = field(default_factory=lambda: _env_int("GENISIA_SANDBOX_MEMORY_MB", 1024))
    sandbox_image: str = field(default_factory=lambda: _env("GENISIA_SANDBOX_IMAGE", "genisia-sandbox:latest"))
    sandbox_dir_override: str | None = field(default_factory=lambda: _env("GENISIA_SANDBOX_DIR"))
    sandbox_max_output_kb: int = field(default_factory=lambda: _env_int("GENISIA_SANDBOX_MAX_OUTPUT_KB", 256))

    # Importação de repositórios
    git_allowed_hosts: list[str] = field(
        default_factory=lambda: [h.strip().lower() for h in (_env("GENISIA_GIT_ALLOWED_HOSTS", "github.com,gitlab.com,bitbucket.org,codeberg.org") or "").split(",") if h.strip()]
    )
    import_roots: list[str] = field(
        default_factory=lambda: [p for p in (_env("GENISIA_IMPORT_ROOTS", "") or "").split(os.pathsep) if p]
    )
    max_repo_mb: int = field(default_factory=lambda: _env_int("GENISIA_MAX_REPO_MB", 800))
    git_timeout_seconds: int = field(default_factory=lambda: _env_int("GENISIA_GIT_TIMEOUT_SECONDS", 600))

    @property
    def sqlalchemy_url(self) -> str:
        if self.database_url:
            url = self.database_url
            if url.startswith("postgresql://"):
                url = "postgresql+psycopg://" + url[len("postgresql://"):]
            return url
        return f"sqlite:///{self.data_dir / 'genisia.db'}"

    @property
    def sandbox_dir(self) -> Path:
        if self.sandbox_dir_override:
            return Path(self.sandbox_dir_override).resolve()
        return self.data_dir / "sandbox"

    def ensure_dirs(self) -> None:
        for sub in ("", "workspaces", "repositories", "sandbox", "uploads"):
            path = self.data_dir / sub
            path.mkdir(parents=True, exist_ok=True)
            # O diretório de dados só é acessível pelo processo do backend: o código em sandbox
            # roda com outro usuário e não pode ler o banco nem segredos.
            try:
                # Raiz e sandbox: apenas travessia (711) para que o usuário sem privilégios do
                # sandbox alcance seu próprio diretório de trabalho; o restante é 700.
                os.chmod(path, 0o711 if sub in ("", "sandbox") else 0o700)
            except PermissionError:
                pass
        if self.sandbox_dir_override:
            self.sandbox_dir.mkdir(parents=True, exist_ok=True)
            os.chmod(self.sandbox_dir, 0o711)

    def resolved_secret_key(self) -> str:
        """Chave usada para JWT e criptografia de segredos.

        Em desenvolvimento, gera e persiste uma chave local (arquivo com permissão 600) se nenhuma
        for informada. Em produção a variável GENISIA_SECRET_KEY é obrigatória.
        """
        if self.secret_key:
            return self.secret_key
        if self.env == "production":
            raise RuntimeError("GENISIA_SECRET_KEY é obrigatória em produção")
        self.ensure_dirs()
        key_file = self.data_dir / ".secret_key"
        if not key_file.exists():
            key_file.write_text(secrets.token_urlsafe(48))
            os.chmod(key_file, 0o600)
        self.secret_key = key_file.read_text().strip()
        return self.secret_key


settings = Settings()


def reload_settings() -> Settings:
    """Recarrega configurações (usado em testes)."""
    global settings
    new = Settings()
    settings.__dict__.update(new.__dict__)
    return settings
