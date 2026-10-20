"""Cópia de trabalho de cada projeto: um repositório Git local isolado.

Cada alteração de agente vira um commit, o que dá histórico verificável e diffs entre versões.
"""
from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from ..config import settings

MAX_FILE_BYTES = 512 * 1024
MAX_FILES_PER_CHANGE = 60
_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9._\-@+ ]+$")
IGNORED_DIRS = {".git", "node_modules", "__pycache__", ".pytest_cache", ".venv", "venv", "dist", "build", ".next"}


class WorkspaceError(ValueError):
    pass


@dataclass
class FileChange:
    path: str
    content: str


def _git_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k in {"PATH", "LANG", "LC_ALL", "HOME"}}
    env.update({
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_AUTHOR_NAME": "GENISIA AI",
        "GIT_AUTHOR_EMAIL": "agents@genisia.local",
        "GIT_COMMITTER_NAME": "GENISIA AI",
        "GIT_COMMITTER_EMAIL": "agents@genisia.local",
    })
    return env


def git(cwd: Path, *args: str, check: bool = True, env_extra: dict[str, str] | None = None, timeout: int = 60) -> str:
    env = _git_env()
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "-c", "protocol.file.allow=never", *args],
        cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout,
    )
    if check and proc.returncode != 0:
        raise WorkspaceError(f"git {' '.join(args[:2])} falhou: {proc.stderr.strip()[:500]}")
    return proc.stdout


def normalize_relpath(path: str) -> str:
    """Valida um caminho relativo enviado por um agente ou usuário."""
    if not path or len(path) > 300:
        raise WorkspaceError("Caminho vazio ou longo demais")
    if "\\" in path or "\x00" in path:
        raise WorkspaceError(f"Caminho inválido: {path!r}")
    pure = PurePosixPath(path)
    if pure.is_absolute():
        raise WorkspaceError(f"Caminho absoluto não permitido: {path}")
    parts = [p for p in pure.parts if p not in ("", ".")]
    if not parts:
        raise WorkspaceError("Caminho inválido")
    for part in parts:
        if part == ".." or not _SAFE_SEGMENT.match(part):
            raise WorkspaceError(f"Segmento de caminho não permitido: {part!r}")
    if parts[0] == ".git" or parts[0] in {".github"}:
        raise WorkspaceError("Alterações em .git/.github não são permitidas a agentes")
    return "/".join(parts)


class Workspace:
    def __init__(self, project_id: str) -> None:
        if not re.fullmatch(r"[a-f0-9]{32}", project_id):
            raise WorkspaceError("Identificador de projeto inválido")
        self.root = (settings.data_dir / "workspaces" / project_id).resolve()

    @property
    def exists(self) -> bool:
        return (self.root / ".git").is_dir()

    def ensure(self) -> None:
        if self.exists:
            return
        self.root.mkdir(parents=True, exist_ok=True)
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "commit", "-q", "--allow-empty", "-m", "Workspace criado pelo GENISIA AI")

    def resolve(self, relpath: str) -> Path:
        rel = normalize_relpath(relpath)
        target = (self.root / rel).resolve()
        if self.root not in target.parents:
            raise WorkspaceError("Caminho fora do workspace")
        return target

    def write_files(self, changes: list[FileChange], message: str, author: str) -> dict:
        self.ensure()
        if len(changes) > MAX_FILES_PER_CHANGE:
            raise WorkspaceError(f"Muitos arquivos em uma alteração ({len(changes)} > {MAX_FILES_PER_CHANGE})")
        written: list[str] = []
        for change in changes:
            data = change.content.encode("utf-8")
            if len(data) > MAX_FILE_BYTES:
                raise WorkspaceError(f"Arquivo grande demais: {change.path}")
            target = self.resolve(change.path)
            if target.is_symlink():
                raise WorkspaceError(f"Link simbólico não pode ser sobrescrito: {change.path}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            written.append(normalize_relpath(change.path))
        git(self.root, "add", "-A")
        status = git(self.root, "status", "--porcelain")
        if not status.strip():
            return {"commit": self.head(), "files": written, "changed": False}
        git(self.root, "commit", "-q", "-m", message[:200],
            env_extra={"GIT_AUTHOR_NAME": author, "GIT_COMMITTER_NAME": "GENISIA AI"})
        return {"commit": self.head(), "files": written, "changed": True}

    def head(self) -> str | None:
        if not self.exists:
            return None
        return git(self.root, "rev-parse", "HEAD").strip()

    def list_files(self) -> list[dict]:
        if not self.exists:
            return []
        out = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = sorted(d for d in dirnames if d not in IGNORED_DIRS)
            for name in sorted(filenames):
                full = Path(dirpath) / name
                rel = full.relative_to(self.root).as_posix()
                out.append({"path": rel, "size": full.stat().st_size})
        return out

    def read_file(self, relpath: str) -> str:
        target = self.resolve(relpath)
        if not target.is_file():
            raise WorkspaceError("Arquivo não encontrado")
        if target.stat().st_size > MAX_FILE_BYTES:
            raise WorkspaceError("Arquivo grande demais para visualização")
        data = target.read_bytes()
        if b"\x00" in data[:4096]:
            raise WorkspaceError("Arquivo binário")
        return data.decode("utf-8", errors="replace")

    def snapshot(self, max_total_bytes: int = 120_000) -> dict[str, str]:
        """Conteúdo textual dos arquivos (para dar contexto ao agente), limitado em tamanho."""
        result: dict[str, str] = {}
        total = 0
        for entry in self.list_files():
            if entry["size"] > 60_000:
                continue
            try:
                content = self.read_file(entry["path"])
            except WorkspaceError:
                continue
            total += len(content)
            if total > max_total_bytes:
                break
            result[entry["path"]] = content
        return result

    def log(self, limit: int = 50) -> list[dict]:
        if not self.exists:
            return []
        fmt = "%H%x1f%an%x1f%aI%x1f%s"
        out = git(self.root, "log", f"-n{limit}", f"--format={fmt}", "--shortstat")
        commits: list[dict] = []
        for line in out.splitlines():
            if "\x1f" in line:
                sha, author, date, subject = line.split("\x1f", 3)
                commits.append({"sha": sha, "author": author, "date": date, "message": subject, "stat": ""})
            elif line.strip() and commits:
                commits[-1]["stat"] = line.strip()
        return commits

    def show(self, sha: str) -> str:
        if not re.fullmatch(r"[0-9a-f]{7,40}", sha):
            raise WorkspaceError("Commit inválido")
        return git(self.root, "show", "--stat", "--patch", "--format=commit %H%nAutor: %an%nData: %aI%n%n    %s%n", sha)[:400_000]

    def diff_stat(self, base: str | None, head: str | None = None) -> str:
        if not base:
            return ""
        return git(self.root, "diff", "--stat", base, head or "HEAD", check=False)
