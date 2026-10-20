"""Adaptador para o REA (morluto/rea, licença MIT).

Estratégia B (adaptador): o GENISIA não incorpora código do REA; quando a CLI ``rea`` está
instalada (``npm install -g rea-agents``), ela é chamada como processo externo para gerar o grafo
estático de aplicações JavaScript/TypeScript, e o resultado é normalizado.

Mapeamento de evidência: ``state=observed`` do REA vira ``proven``; ``inferred`` vira ``hypothesis``.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any


def rea_binary() -> str | None:
    return os.environ.get("GENISIA_REA_BIN") or shutil.which("rea")


def rea_status() -> dict[str, Any]:
    binary = rea_binary()
    if not binary:
        return {"available": False, "reason": "CLI 'rea' não instalada (npm install -g rea-agents)"}
    try:
        proc = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=30)
        version = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else None
    except (OSError, subprocess.SubprocessError) as exc:
        return {"available": False, "reason": f"Falha ao executar rea: {exc}"}
    return {"available": True, "binary": binary, "version": version}


def analyze_javascript(path: Path, timeout: int = 900) -> dict[str, Any]:
    """Executa ``rea analyze-javascript-application`` e devolve um resumo normalizado."""
    binary = rea_binary()
    if not binary:
        return {"status": "unavailable", "reason": "CLI 'rea' não instalada"}
    env = {k: v for k, v in os.environ.items() if k in {"PATH", "HOME", "LANG", "NODE_OPTIONS"}}
    env["REA_NO_UPDATE_CHECK"] = "1"
    cmd = [binary, "analyze-javascript-application", str(path), "--json"]
    if shutil.which("unshare") and os.geteuid() == 0:
        cmd = ["unshare", "-n", "--", *cmd]  # análise inerte: sem acesso à rede
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "reason": f"REA excedeu {timeout}s"}
    if proc.returncode != 0:
        return {"status": "error", "reason": (proc.stderr or proc.stdout)[-1500:]}
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"status": "error", "reason": "Saída do REA não é JSON válido"}
    return summarize(data)


def summarize(data: dict[str, Any]) -> dict[str, Any]:
    normalized = data.get("normalized_result") or {}
    graph = normalized.get("graph") or {}
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    node_kinds = Counter(n.get("kind", "?") for n in nodes)
    relations = Counter(e.get("relation", "?") for e in edges)
    states = Counter()
    external: Counter[str] = Counter()
    for e in edges:
        ev = e.get("evidence") or {}
        states[ev.get("state", "?")] += 1
        props = e.get("properties") or {}
        if props.get("resolution_status") == "external" and props.get("specifier"):
            external[props["specifier"]] += 1
    for n in nodes:
        for obs in n.get("observations") or []:
            states[(obs.get("evidence") or {}).get("state", "?")] += 1
    return {
        "status": "ok",
        "tool": (data.get("provider") or {}).get("name", "REA"),
        "evidence_id": data.get("evidence_id"),
        "statistics": normalized.get("statistics"),
        "electron_summary": normalized.get("summary"),
        "node_kinds": dict(node_kinds.most_common(20)),
        "relations": dict(relations.most_common(20)),
        "evidence_states": {
            "proven (observed)": states.get("observed", 0),
            "hypothesis (inferred)": states.get("inferred", 0),
            "outros": sum(v for k, v in states.items() if k not in {"observed", "inferred"}),
        },
        "external_modules": [{"module": m, "count": c} for m, c in external.most_common(25)],
        "limitations": normalized.get("limitations") or data.get("limitations") or [],
    }
