"""Importação segura de repositórios autorizados (Git via HTTPS, diretório local permitido ou ZIP)."""
from __future__ import annotations

import ipaddress
import os
import re
import shutil
import socket
import subprocess
import zipfile
from pathlib import Path
from urllib.parse import urlparse

from ..config import settings
from ..execution.workspace import WorkspaceError, git


class ImportErrorDetail(ValueError):
    pass


GIT_URL = re.compile(r"^https://[A-Za-z0-9.\-]+(:\d+)?/[A-Za-z0-9._\-/]+?(\.git)?/?$")


def validate_git_url(url: str) -> str:
    """Aceita apenas HTTPS para hosts permitidos que resolvem para IPs públicos (proteção contra SSRF)."""
    url = url.strip()
    if not GIT_URL.match(url):
        raise ImportErrorDetail("URL inválida: use https://host/dono/repositorio")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.username or parsed.password:
        raise ImportErrorDetail("Credenciais na URL não são permitidas")
    if settings.git_allowed_hosts and host not in settings.git_allowed_hosts:
        raise ImportErrorDetail(f"Host não permitido: {host}. Permitidos: {', '.join(settings.git_allowed_hosts)}")
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        # Ambientes com proxy de saída podem não resolver DNS localmente; o host já está na lista permitida.
        if os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy"):
            return url.rstrip("/")
        raise ImportErrorDetail(f"Não foi possível resolver {host}") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            raise ImportErrorDetail("O host resolve para um endereço interno; acesso bloqueado")
    return url.rstrip("/")


def repo_name_from_url(url: str) -> str:
    path = urlparse(url).path.strip("/").removesuffix(".git")
    return path


def _dir_size_mb(path: Path) -> float:
    total = 0
    for dirpath, _dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.lstat(os.path.join(dirpath, f)).st_size
            except OSError:
                pass
    return total / 1_048_576


def clone(url: str, dest: Path, ref: str | None = None) -> str:
    url = validate_git_url(url)
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    args = ["clone", "--depth", "1", "--single-branch", "--no-tags", "--filter=blob:limit=5m",
            "-c", "core.symlinks=false", "--config", "submodule.recurse=false"]
    if ref:
        if not re.fullmatch(r"[A-Za-z0-9._/\-]{1,100}", ref) or ref.startswith("-"):
            raise ImportErrorDetail("Referência (branch/tag) inválida")
        args += ["--branch", ref]
    args += ["--", url, str(dest)]
    try:
        git(dest.parent, *args, timeout=settings.git_timeout_seconds)
    except WorkspaceError as exc:
        raise ImportErrorDetail(str(exc)) from exc
    except subprocess.TimeoutExpired as exc:
        shutil.rmtree(dest, ignore_errors=True)
        raise ImportErrorDetail("Tempo limite de clonagem excedido") from exc
    size = _dir_size_mb(dest)
    if size > settings.max_repo_mb:
        shutil.rmtree(dest, ignore_errors=True)
        raise ImportErrorDetail(f"Repositório excede o limite ({size:.0f} MB > {settings.max_repo_mb} MB)")
    return git(dest, "rev-parse", "HEAD").strip()


def validate_local_path(path: str) -> Path:
    """Diretórios locais só podem ser importados se estiverem dentro de GENISIA_IMPORT_ROOTS."""
    if not settings.import_roots:
        raise ImportErrorDetail("Importação de diretórios locais desabilitada (defina GENISIA_IMPORT_ROOTS)")
    target = Path(path).resolve()
    for root in settings.import_roots:
        root_path = Path(root).resolve()
        if target == root_path or root_path in target.parents:
            if not target.is_dir():
                raise ImportErrorDetail("Diretório não encontrado")
            return target
    raise ImportErrorDetail("Diretório fora das raízes autorizadas")


def local_commit(path: Path) -> str | None:
    if (path / ".git").exists():
        try:
            return git(path, "rev-parse", "HEAD").strip()
        except WorkspaceError:
            return None
    return None


def extract_zip(zip_path: Path, dest: Path, max_mb: int = 200, max_files: int = 20000) -> None:
    """Extrai um ZIP enviado pelo usuário com proteção contra zip-slip, links e bombas de compressão."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    total = 0
    with zipfile.ZipFile(zip_path) as zf:
        members = zf.infolist()
        if len(members) > max_files:
            raise ImportErrorDetail("ZIP com arquivos demais")
        for info in members:
            name = info.filename
            if name.startswith("/") or ".." in Path(name).parts or "\\" in name:
                raise ImportErrorDetail(f"Caminho inseguro no ZIP: {name}")
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                continue  # ignora links simbólicos
            total += info.file_size
            if total > max_mb * 1_048_576:
                raise ImportErrorDetail("Conteúdo descompactado excede o limite")
            target = (dest / name).resolve()
            if dest.resolve() not in target.parents and target != dest.resolve():
                raise ImportErrorDetail(f"Caminho inseguro no ZIP: {name}")
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)
