"""Execução isolada de código gerado (testes) fora do processo principal do backend.

Backends:
- ``namespace`` (padrão quando disponível): processo filho em um namespace de rede próprio
  (sem acesso à rede), executado como usuário sem privilégios (65534) quando o backend roda
  como root, com limites de CPU, memória, tamanho de arquivo e tempo, ambiente limpo e uma
  cópia descartável dos arquivos.
- ``docker``: contêiner com ``--network none``, limites de memória/CPU/PIDs. Selecionado
  automaticamente apenas se o daemon Docker responder.
- ``process``: sem isolamento de rede/usuário. Só é usado se configurado explicitamente
  (GENISIA_SANDBOX_BACKEND=process) e deve ficar restrito a desenvolvimento.
"""
from __future__ import annotations

import json
import os
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path

from ..config import settings
from ..security import redact
from .workspace import IGNORED_DIRS

NOBODY_UID = 65534
NOBODY_GID = 65534


class SandboxUnavailable(RuntimeError):
    pass


@dataclass
class SandboxResult:
    command: list[str]
    backend: str
    exit_code: int | None
    output: str
    duration_seconds: float
    timed_out: bool = False
    cancelled: bool = False
    network: bool = False
    truncated: bool = False
    limits: dict = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.exit_code == 0 and not self.timed_out and not self.cancelled

    def to_dict(self) -> dict:
        data = asdict(self)
        data["passed"] = self.passed
        return data


@lru_cache(maxsize=1)
def _namespace_support() -> str | None:
    """Retorna 'root' ou 'user' conforme o tipo de namespace que funciona aqui, ou None."""
    if not shutil.which("unshare"):
        return None
    if os.geteuid() == 0 and shutil.which("setpriv"):
        probe = ["unshare", "-n", "--", "setpriv", f"--reuid={NOBODY_UID}", f"--regid={NOBODY_GID}", "--clear-groups", "--", "true"]
        if subprocess.run(probe, capture_output=True, timeout=10).returncode == 0:
            return "root"
    if subprocess.run(["unshare", "-rn", "--", "true"], capture_output=True, timeout=10).returncode == 0:
        return "user"
    return None


@lru_cache(maxsize=1)
def _docker_available() -> bool:
    if not shutil.which("docker"):
        return False
    try:
        return subprocess.run(["docker", "info"], capture_output=True, timeout=10).returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


def select_backend() -> str:
    choice = settings.sandbox_backend
    if choice == "auto":
        if _namespace_support():
            return "namespace"
        if _docker_available():
            return "docker"
        raise SandboxUnavailable(
            "Nenhum mecanismo de isolamento disponível (unshare/Docker). "
            "Configure GENISIA_SANDBOX_BACKEND=docker com o daemon ativo, ou =process apenas em desenvolvimento."
        )
    if choice == "namespace" and not _namespace_support():
        raise SandboxUnavailable("Namespaces Linux (unshare) indisponíveis neste ambiente")
    if choice == "docker" and not _docker_available():
        raise SandboxUnavailable("Daemon Docker indisponível")
    if choice not in {"namespace", "docker", "process"}:
        raise SandboxUnavailable(f"Backend de sandbox desconhecido: {choice}")
    return choice


def _traversable_by_others(path: Path) -> bool:
    """O usuário sem privilégios precisa atravessar todos os diretórios ancestrais."""
    for parent in [path, *path.parents]:
        if parent.exists() and not (parent.stat().st_mode & 0o001):
            return False
    return True


def _check_sandbox_dir(backend: str) -> None:
    if (backend == "namespace" and _namespace_support() == "root") or backend == "docker":
        if not _traversable_by_others(settings.sandbox_dir):
            raise SandboxUnavailable(
                f"O diretório de sandbox {settings.sandbox_dir} não é acessível ao usuário sem privilégios "
                "(algum diretório ancestral não tem permissão de travessia). Defina GENISIA_SANDBOX_DIR, por exemplo /var/tmp/genisia-sandbox."
            )


def sandbox_status() -> dict:
    try:
        backend = select_backend()
        _check_sandbox_dir(backend)
        available, reason = True, None
    except SandboxUnavailable as exc:
        backend, available, reason = None, False, str(exc)
    return {
        "available": available,
        "backend": backend,
        "reason": reason,
        "namespace_mode": _namespace_support(),
        "docker": _docker_available(),
        "network_default": "desabilitada",
        "timeout_seconds": settings.sandbox_timeout_seconds,
        "memory_mb": settings.sandbox_memory_mb,
    }


def detect_test_command(root: Path) -> tuple[str, list[str]] | None:
    """Detecta um comando de teste conhecido. Apenas comandos desta lista podem ser executados."""
    files = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and not (set(p.relative_to(root).parts) & IGNORED_DIRS)}
    py_tests = [f for f in files if f.endswith(".py") and (Path(f).name.startswith("test_") or Path(f).name.endswith("_test.py"))]
    if py_tests or "pytest.ini" in files or "conftest.py" in files:
        return "pytest", ["python3", "-m", "pytest", "-q", "-p", "no:cacheprovider", "--color=no"]
    pkg = root / "package.json"
    if pkg.is_file():
        try:
            data = json.loads(pkg.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            data = {}
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        if data.get("scripts", {}).get("test") and not deps:
            return "npm_test", ["npm", "test", "--silent"]
    js_tests = [f for f in files if f.endswith((".test.js", ".test.mjs", ".spec.js"))]
    if js_tests:
        return "node_test", ["node", "--test", *sorted(js_tests)]
    return None


def _limits() -> dict:
    return {
        "cpu_seconds": settings.sandbox_timeout_seconds,
        "memory_mb": settings.sandbox_memory_mb,
        "file_size_mb": 50,
        "open_files": 256,
        "wall_clock_seconds": settings.sandbox_timeout_seconds,
    }


def _preexec(limits: dict) -> Callable[[], None]:
    def apply() -> None:  # executado no processo filho antes do exec
        os.setsid()
        resource.setrlimit(resource.RLIMIT_CPU, (limits["cpu_seconds"], limits["cpu_seconds"] + 5))
        mem = limits["memory_mb"] * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
        fsz = limits["file_size_mb"] * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_FSIZE, (fsz, fsz))
        resource.setrlimit(resource.RLIMIT_NOFILE, (limits["open_files"], limits["open_files"]))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    return apply


def _copy_tree(src: Path, dst: Path) -> None:
    def ignore(_dir: str, names: list[str]) -> set[str]:
        return {n for n in names if n in IGNORED_DIRS}

    shutil.copytree(src, dst, ignore=ignore, symlinks=False, ignore_dangling_symlinks=True)


def _chown_tree(path: Path, uid: int, gid: int) -> None:
    os.chown(path, uid, gid)
    for dirpath, dirnames, filenames in os.walk(path):
        for name in dirnames + filenames:
            os.chown(os.path.join(dirpath, name), uid, gid, follow_symlinks=False)


def run_in_sandbox(
    source_dir: Path,
    command: list[str],
    *,
    network: bool = False,
    timeout: int | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> SandboxResult:
    backend = select_backend()
    _check_sandbox_dir(backend)
    limits = _limits()
    if timeout:
        limits["wall_clock_seconds"] = min(timeout, limits["wall_clock_seconds"])
    settings.sandbox_dir.mkdir(parents=True, exist_ok=True)
    run_root = settings.sandbox_dir / uuid.uuid4().hex
    work = run_root / "work"
    run_root.mkdir(parents=True)
    os.chmod(run_root, 0o711)
    _copy_tree(source_dir, work)

    env = {
        "PATH": f"{Path(sys.executable).parent}:/usr/local/bin:/usr/bin:/bin",
        "HOME": str(work),
        "LANG": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
        "CI": "1",
        "npm_config_cache": str(work / ".npm-cache"),
        "npm_config_update_notifier": "false",
    }
    if backend == "namespace":
        mode = _namespace_support()
        if mode == "root":
            _chown_tree(work, NOBODY_UID, NOBODY_GID)
            prefix = ["unshare"] + ([] if network else ["-n"]) + ["--", "setpriv", f"--reuid={NOBODY_UID}",
                     f"--regid={NOBODY_GID}", "--clear-groups", "--"]
        else:
            prefix = ["unshare", "-r"] + ([] if network else ["-n"]) + ["--"]
        argv = prefix + command
        cwd = work
    elif backend == "docker":  # pragma: no cover - não validado neste ambiente (sem daemon)
        image = "python:3.12-slim" if command[0].startswith("python") else "node:22-slim"
        argv = ["docker", "run", "--rm", "--network", "bridge" if network else "none",
                "--memory", f"{limits['memory_mb']}m", "--cpus", "1", "--pids-limit", "256",
                "--user", f"{NOBODY_UID}:{NOBODY_GID}", "-e", "HOME=/work", "-v", f"{work}:/work", "-w", "/work",
                image, *command]
        _chown_tree(work, NOBODY_UID, NOBODY_GID)
        cwd = run_root
    else:
        argv = command
        cwd = work

    start = time.monotonic()
    timed_out = cancelled = False
    with tempfile.TemporaryFile() as out:
        proc = subprocess.Popen(
            argv, cwd=cwd, env=env, stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
            preexec_fn=_preexec(limits) if backend != "docker" else os.setsid,
        )
        while True:
            try:
                proc.wait(timeout=0.25)
                break
            except subprocess.TimeoutExpired:
                pass
            if time.monotonic() - start > limits["wall_clock_seconds"]:
                timed_out = True
            elif cancel_check and cancel_check():
                cancelled = True
            if timed_out or cancelled:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait()
                break
        duration = time.monotonic() - start
        out.seek(0)
        max_bytes = settings.sandbox_max_output_kb * 1024
        raw = out.read(max_bytes + 1)
    shutil.rmtree(run_root, ignore_errors=True)
    truncated = len(raw) > max_bytes
    text = redact(raw[:max_bytes].decode("utf-8", errors="replace"))
    if truncated:
        text += "\n[saída truncada]"
    return SandboxResult(
        command=command, backend=backend, exit_code=None if (timed_out or cancelled) else proc.returncode,
        output=text, duration_seconds=round(duration, 3), timed_out=timed_out, cancelled=cancelled,
        network=network, truncated=truncated, limits=limits,
    )
