#!/usr/bin/env python3
"""Usa a própria API do GENISIA AI para fazer engenharia reversa dos repositórios de referência.

Fluxo (tudo pela API REST, como um usuário faria):
1. entra (ou cria) o usuário informado;
2. registra cada repositório público por HTTPS;
3. executa o fluxo ``analyze_repository`` (importação → análise estática + REA → segurança →
   otimização → revisão por IA opcional → relatório);
4. para os repositórios-catálogo, executa ``ingest_knowledge`` (links/APIs/livros → base de conhecimento);
5. exporta os relatórios em Markdown para ``docs/references/``.

Uso:
    python3 scripts/analyze_references.py --api http://localhost:8000 --email voce@exemplo.com --password ...
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

import httpx

REFERENCES = [
    # (url, papel no GENISIA, ingerir catálogo?)
    ("https://github.com/codecrafters-io/build-your-own-x", "Laboratório de construção do zero (tutoriais)", True),
    ("https://github.com/sindresorhus/awesome", "Catálogo de ferramentas e recursos", True),
    ("https://github.com/public-apis/public-apis", "Catálogo de APIs", True),
    ("https://github.com/freeCodeCamp/freeCodeCamp", "Aprendizagem prática", False),
    ("https://github.com/EbookFoundation/free-programming-books", "Biblioteca de livros e cursos gratuitos", True),
    ("https://github.com/openclaw/openclaw", "Assistentes que executam tarefas", False),
    ("https://github.com/donnemartin/system-design-primer", "Arquiteto de software assistido", True),
    ("https://github.com/nilbuild/developer-roadmap", "Planejador de evolução técnica", True),
    ("https://github.com/jwasham/coding-interview-university", "Ciência da computação e algoritmos", True),
    ("https://github.com/morluto/rea", "Engenharia reversa assistida (adaptador)", False),
    ("https://github.com/ruvnet/ruflo", "Orquestração multiagente (referência)", False),
]

TERMINAL = {"succeeded", "failed", "cancelled"}


def slug(url: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", url.rstrip("/").split("github.com/")[-1].lower()).strip("-")


def login(client: httpx.Client, email: str, password: str) -> None:
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    if r.status_code == 401:
        r = client.post("/api/auth/register", json={"email": email, "name": "Análise de referências", "password": password})
    r.raise_for_status()
    client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"


def wait(client: httpx.Client, task_id: str, label: str, timeout: int = 7200) -> dict:
    start = time.time()
    last = None
    while time.time() - start < timeout:
        detail = client.get(f"/api/tasks/{task_id}").json()
        state = " ".join(f"{s['step_key']}={s['status']}" for s in detail["steps"])
        if state != last:
            print(f"  [{label}] {detail['status']}: {state}", flush=True)
            last = state
        if detail["status"] in TERMINAL:
            return detail
        time.sleep(5)
    raise TimeoutError(f"{label}: tempo esgotado")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "docs" / "references"))
    parser.add_argument("--only", nargs="*", help="slugs a processar (padrão: todos)")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    client = httpx.Client(base_url=args.api, timeout=120)
    login(client, args.email, args.password)
    note = "Repositório público de referência; análise estática somente leitura para estudo e documentação."
    pending: list[tuple[str, str, str, bool, str]] = []
    for url, role, ingest in REFERENCES:
        if args.only and slug(url) not in args.only:
            continue
        repo = client.post("/api/repositories", json={"source_type": "git", "source_url": url, "authorization_note": note})
        repo.raise_for_status()
        repo_id = repo.json()["id"]
        task = client.post(f"/api/repositories/{repo_id}/analyze", json={"workflow": "analyze_repository"})
        task.raise_for_status()
        print(f"Análise iniciada: {url} (tarefa {task.json()['id']})", flush=True)
        pending.append((url, role, repo_id, ingest, task.json()["id"]))
    results = []
    for url, role, repo_id, ingest, task_id in pending:
        detail = wait(client, task_id, slug(url))
        repo = client.get(f"/api/repositories/{repo_id}").json()
        ingest_detail = None
        if ingest and detail["status"] == "succeeded":
            t = client.post(f"/api/repositories/{repo_id}/analyze", json={"workflow": "ingest_knowledge"}).json()
            ingest_detail = wait(client, t["id"], slug(url) + ":ingest")
        report = client.get(f"/api/artifacts/{repo['last_analysis_artifact_id']}").json() if repo.get("last_analysis_artifact_id") else None
        steps = {s["step_key"]: s for s in detail["steps"]}
        extra = []
        for key in ("security", "optimize", "ai_review"):
            s = steps.get(key)
            if s and s["status"] == "succeeded" and (s.get("result") or {}).get("artifact_id"):
                art = client.get(f"/api/artifacts/{s['result']['artifact_id']}").json()
                extra.append(art)
        name = slug(url)
        if report:
            header = [f"<!-- Gerado pelo GENISIA AI (scripts/analyze_references.py) a partir da tarefa {task_id}. -->", "",
                      f"> **Papel no GENISIA AI:** {role}", ""]
            body = report["content"]
            ingest_note = ""
            if ingest_detail:
                ing = next((s for s in ingest_detail["steps"] if s["step_key"] == "ingest"), None)
                if ing and ing["status"] == "succeeded":
                    r = ing["result"]
                    ingest_note = (f"\n## Indexação na base de conhecimento\n\n- Itens indexados: **{r['items']}** {r['by_type']}\n"
                                   f"- Arquivos de origem: {', '.join('`' + f + '`' for f in r['files'])}\n"
                                   f"- Somente metadados e links foram armazenados (licença da fonte: {r['license'] or 'desconhecida'}).\n")
                elif ing:
                    ingest_note = f"\n## Indexação na base de conhecimento\n\nFalhou: {ing['error']}\n"
            appendix = "".join(f"\n---\n\n{a['content']}\n" for a in extra)
            (out / f"{name}.md").write_text("\n".join(header) + body + ingest_note + appendix)
        results.append({"url": url, "role": role, "status": detail["status"], "summary": repo.get("summary"), "commit": repo.get("commit_sha"),
                        "file": f"{name}.md" if report else None, "error": detail.get("error"),
                        "ingest": (next((s["result"] for s in ingest_detail["steps"] if s["step_key"] == "ingest"), None)
                                   if ingest_detail else None)})
    lines = ["# Engenharia reversa dos repositórios de referência", "",
             "Relatórios gerados pelo próprio GENISIA AI (fluxo `analyze_repository`), com análise estática do commit indicado. "
             "✅ = comprovado por arquivo; 🔎 = hipótese. Nenhum código dos repositórios foi executado.", "",
             "| Repositório | Papel | Tipo provável | Linguagens | Licença | Arquivos | Itens indexados | Relatório |",
             "|---|---|---|---|---|---|---|---|"]
    for r in results:
        s = r["summary"] or {}
        ing = r["ingest"] or {}
        link = f"[{r['file']}]({r['file']})" if r["file"] else f"falhou: {r['error']}"
        lines.append(f"| [{r['url'].split('github.com/')[-1]}]({r['url']}) | {r['role']} | {', '.join(s.get('kinds', []))} | "
                     f"{', '.join(s.get('languages', [])[:3])} | {s.get('license') or '-'} | {s.get('files', '-')} | "
                     f"{ing.get('items', '-')} | {link} |")
    index = out / "README.md"
    previous = index.read_text() if index.exists() else ""
    marker = "<!-- tabela -->"
    table = "\n".join(lines)
    if marker in previous:
        before, _sep, _ = previous.partition(marker)
        after = previous.split("<!-- /tabela -->", 1)[1] if "<!-- /tabela -->" in previous else ""
        index.write_text(f"{before}{marker}\n{table}\n<!-- /tabela -->{after}")
    else:
        index.write_text(f"{marker}\n{table}\n<!-- /tabela -->\n")
    print("\n".join(lines))
    return 0 if all(r["status"] == "succeeded" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
