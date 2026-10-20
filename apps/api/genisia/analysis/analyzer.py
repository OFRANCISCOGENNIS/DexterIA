"""Analisador estático de repositórios (camada de engenharia reversa do GENISIA AI).

Inspirado no princípio do REA (morluto/rea) de que cada conclusão deve trazer evidência e
limitações. Aqui toda descoberta é marcada como:

- ``proven``: comprovada pela leitura direta de um arquivo (o caminho é citado como evidência);
- ``hypothesis``: inferência heurística — útil, mas não comprovada.

A análise é puramente estática: nenhum código do repositório é executado.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import tomllib
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

ANALYZER_VERSION = "1.2.0"

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".pytest_cache", ".venv", "venv", "dist", "build", ".next",
    ".turbo", ".cache", "coverage", "target", "vendor", ".idea", ".vscode", "bower_components",
}
MAX_TEXT_BYTES = 400_000
MAX_FILES = 60_000

LANGUAGES = {
    ".py": "Python", ".js": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript", ".jsx": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".mts": "TypeScript", ".cts": "TypeScript",
    ".go": "Go", ".rs": "Rust", ".java": "Java", ".kt": "Kotlin", ".rb": "Ruby", ".php": "PHP",
    ".cs": "C#", ".c": "C", ".h": "C/C++ header", ".cpp": "C++", ".cc": "C++", ".hpp": "C++",
    ".swift": "Swift", ".scala": "Scala", ".sh": "Shell", ".bash": "Shell", ".ps1": "PowerShell",
    ".html": "HTML", ".css": "CSS", ".scss": "SCSS", ".vue": "Vue", ".svelte": "Svelte",
    ".md": "Markdown", ".mdx": "MDX", ".json": "JSON", ".yml": "YAML", ".yaml": "YAML", ".toml": "TOML",
    ".sql": "SQL", ".ipynb": "Jupyter", ".lua": "Lua", ".dart": "Dart", ".ex": "Elixir", ".exs": "Elixir",
    ".r": "R", ".jl": "Julia", ".zig": "Zig", ".astro": "Astro",
}
CODE_LANGUAGES = {
    "Python", "JavaScript", "TypeScript", "Go", "Rust", "Java", "Kotlin", "Ruby", "PHP", "C#", "C", "C++",
    "Swift", "Scala", "Shell", "Vue", "Svelte", "Lua", "Dart", "Elixir", "R", "Julia", "Zig", "PowerShell", "Astro",
}

# Dependência -> (framework/tecnologia, categoria)
FRAMEWORK_MAP: dict[str, tuple[str, str]] = {
    "react": ("React", "frontend"), "next": ("Next.js", "frontend"), "vue": ("Vue", "frontend"),
    "nuxt": ("Nuxt", "frontend"), "svelte": ("Svelte", "frontend"), "@sveltejs/kit": ("SvelteKit", "frontend"),
    "@angular/core": ("Angular", "frontend"), "astro": ("Astro", "frontend"), "gatsby": ("Gatsby", "frontend"),
    "tailwindcss": ("Tailwind CSS", "frontend"), "vite": ("Vite", "build"), "webpack": ("webpack", "build"),
    "express": ("Express", "backend"), "fastify": ("Fastify", "backend"), "koa": ("Koa", "backend"),
    "@nestjs/core": ("NestJS", "backend"), "hono": ("Hono", "backend"), "electron": ("Electron", "desktop"),
    "@tauri-apps/api": ("Tauri", "desktop"), "react-native": ("React Native", "mobile"),
    "prisma": ("Prisma", "database"), "@prisma/client": ("Prisma", "database"), "mongoose": ("Mongoose", "database"),
    "typeorm": ("TypeORM", "database"), "sequelize": ("Sequelize", "database"), "drizzle-orm": ("Drizzle", "database"),
    "pg": ("PostgreSQL (driver)", "database"), "redis": ("Redis (cliente)", "database"), "ioredis": ("Redis (cliente)", "database"),
    "jest": ("Jest", "testing"), "vitest": ("Vitest", "testing"), "mocha": ("Mocha", "testing"),
    "@playwright/test": ("Playwright", "testing"), "cypress": ("Cypress", "testing"),
    "typescript": ("TypeScript", "language"), "zod": ("Zod", "validation"),
    "@modelcontextprotocol/sdk": ("Model Context Protocol", "ai"), "@modelcontextprotocol/server": ("Model Context Protocol", "ai"),
    "@anthropic-ai/sdk": ("Anthropic SDK", "ai"), "openai": ("OpenAI SDK", "ai"), "langchain": ("LangChain", "ai"),
    "fastapi": ("FastAPI", "backend"), "django": ("Django", "backend"), "flask": ("Flask", "backend"),
    "starlette": ("Starlette", "backend"), "sqlalchemy": ("SQLAlchemy", "database"), "alembic": ("Alembic", "database"),
    "pydantic": ("Pydantic", "validation"), "pytest": ("pytest", "testing"), "celery": ("Celery", "queue"),
    "numpy": ("NumPy", "data"), "pandas": ("pandas", "data"), "torch": ("PyTorch", "ai"), "tensorflow": ("TensorFlow", "ai"),
    "anthropic": ("Anthropic SDK", "ai"), "scrapy": ("Scrapy", "data"), "click": ("Click", "cli"), "typer": ("Typer", "cli"),
    "commander": ("Commander.js", "cli"), "yargs": ("yargs", "cli"),
    "gin-gonic/gin": ("Gin", "backend"), "labstack/echo": ("Echo", "backend"), "gofiber/fiber": ("Fiber", "backend"),
    "tokio": ("Tokio", "runtime"), "axum": ("Axum", "backend"), "actix-web": ("Actix Web", "backend"), "serde": ("Serde", "serialization"),
    "rails": ("Ruby on Rails", "backend"), "sinatra": ("Sinatra", "backend"),
    "spring-boot": ("Spring Boot", "backend"), "laravel/framework": ("Laravel", "backend"),
}

LICENSE_PATTERNS = [
    ("MIT", re.compile(r"\bMIT License\b|Permission is hereby granted, free of charge", re.I)),
    ("Apache-2.0", re.compile(r"Apache License,?\s+Version 2\.0", re.I)),
    ("GPL-3.0", re.compile(r"GNU GENERAL PUBLIC LICENSE\s+Version 3", re.I)),
    ("GPL-2.0", re.compile(r"GNU GENERAL PUBLIC LICENSE\s+Version 2", re.I)),
    ("AGPL-3.0", re.compile(r"GNU AFFERO GENERAL PUBLIC LICENSE", re.I)),
    ("LGPL", re.compile(r"GNU LESSER GENERAL PUBLIC LICENSE", re.I)),
    ("BSD-3-Clause", re.compile(r"Redistribution and use in source and binary forms.*Neither the name", re.I | re.S)),
    ("BSD-2-Clause", re.compile(r"Redistribution and use in source and binary forms", re.I)),
    ("CC0-1.0", re.compile(r"CC0 1\.0|Creative Commons Zero|Statement of Purpose", re.I)),
    ("CC-BY-SA-4.0", re.compile(r"Attribution-ShareAlike 4\.0", re.I)),
    ("CC-BY-4.0", re.compile(r"Attribution 4\.0 International", re.I)),
    ("BSD-3-Clause (variante)", re.compile(r"BSD 3-Clause", re.I)),
    ("MPL-2.0", re.compile(r"Mozilla Public License,?\s+(Version|v\.?)\s*2\.0", re.I)),
    ("Unlicense", re.compile(r"This is free and unencumbered software", re.I)),
    ("Proprietária (uso pessoal)", re.compile(r"protected by the copyright laws|personal use|all rights reserved", re.I)),
]

# Licenças que permitem reproduzir descrições/metadados com atribuição.
PERMISSIVE_LICENSES = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "BSD-3-Clause (variante)", "CC0-1.0",
                       "CC-BY-4.0", "CC-BY-SA-4.0", "Unlicense", "MPL-2.0"}

SECRET_RULES = [
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("github_token", re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}")),
    ("anthropic_key", re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}")),
    ("openai_key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9]{32,}")),
    ("slack_token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("generic_secret_assignment", re.compile(
        r"(?i)\b(api[_-]?key|secret|passwd|password|token)\b\s*[:=]\s*['\"]([A-Za-z0-9/+_\-]{16,})['\"]")),
]
RISKY_CALLS = [
    ("python_eval_exec", re.compile(r"(?<![\w.])(eval|exec)\("), ("Python",)),
    ("python_shell_true", re.compile(r"subprocess\.\w+\([^)]*shell\s*=\s*True"), ("Python",)),
    ("python_pickle_load", re.compile(r"pickle\.loads?\("), ("Python",)),
    ("js_eval", re.compile(r"(?<![\w.])eval\(|new Function\("), ("JavaScript", "TypeScript")),
    ("js_child_process_exec", re.compile(r"child_process['\"]?\)?\.?\s*\.?exec\(|\bexecSync\("), ("JavaScript", "TypeScript")),
    ("js_inner_html", re.compile(r"dangerouslySetInnerHTML|\.innerHTML\s*="), ("JavaScript", "TypeScript")),
]
ROUTE_PATTERNS = [
    ("FastAPI/Flask", re.compile(r"@(?:\w+\.)?(?:app|router|bp|blueprint|api)\.(get|post|put|patch|delete|route)\(\s*['\"]([^'\"]+)['\"]"), ("Python",)),
    ("Express/Fastify/Hono", re.compile(r"\b(?:app|router|server|fastify)\.(get|post|put|patch|delete|all)\(\s*['\"`](/[^'\"`]*)['\"`]"), ("JavaScript", "TypeScript")),
    ("Go net/http/Gin", re.compile(r"\.(GET|POST|PUT|PATCH|DELETE|HandleFunc|Handle)\(\s*\"(/[^\"]*)\""), ("Go",)),
]
MD_LINK = re.compile(r"\[([^\]]{1,300})\]\((https?://[^)\s]+)\)")
JS_IMPORT = re.compile(r"""(?:import\s+(?:[\w*{}\s,]+\s+from\s+)?|require\(\s*|import\(\s*)['"]([^'"]+)['"]""")


@dataclass
class Finding:
    category: str
    title: str
    detail: str
    status: str  # proven | hypothesis
    evidence: list[str] = field(default_factory=list)
    severity: str = "info"  # info | low | medium | high

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def _read_text(path: Path, limit: int = MAX_TEXT_BYTES) -> str | None:
    try:
        with path.open("rb") as fh:
            data = fh.read(limit + 1)
    except OSError:
        return None
    if b"\x00" in data[:8192]:
        return None
    return data[:limit].decode("utf-8", errors="replace")


def _walk(root: Path):
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not os.path.islink(os.path.join(dirpath, d)))
        for name in sorted(filenames):
            full = Path(dirpath) / name
            if full.is_symlink():
                continue
            count += 1
            if count > MAX_FILES:
                return
            yield full


def _norm_dep(name: str) -> str:
    return re.split(r"[<>=!~;\[\s]", name.strip(), maxsplit=1)[0].lower()


def readme_summary(text: str) -> str:
    """Escolhe o primeiro parágrafo descritivo do README (prosa, sem blocos de código/instalação)."""
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"<(div|p|table|picture)[^>]*>.*?</\1>", "", text, flags=re.S | re.I)
    candidates: list[str] = []
    for para in re.split(r"\n\s*\n", text):
        if re.search(r"(?i)utm_|sign up|sponsor|patreon|buy me a coffee|fork our|https?://\S+\s*$", para) or len(re.findall(r"[·∙|]", para)) > 4:
            continue  # propaganda, patrocínio ou seletor de idiomas
        lines = [re.sub(r"^>\s?", "", ln).strip() for ln in para.strip().splitlines()]
        if not lines or lines[0].startswith(("#", "|", "[!", "- ", "* ", "<", "!", "[![")):
            continue
        clean = re.sub(r"<[^>]+>|!\[[^\]]*\]\([^)]*\)", "", " ".join(lines))
        clean = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", clean)
        clean = re.sub(r"\s+", " ", clean).strip()
        letters = sum(c.isalpha() for c in clean)
        if len(clean) < 40 or letters < len(clean) * 0.6:
            continue
        if re.search(r"(?i)\b(npx|npm|pip|curl|brew|install|configure|run the)\b", clean) and len(candidates) < 5:
            candidates.append(clean)  # parágrafo de instalação: só se não houver descrição melhor
            continue
        return clean[:600]
    return candidates[0][:600] if candidates else ""


class RepositoryAnalyzer:
    def __init__(self, root: Path, name: str | None = None) -> None:
        self.root = root.resolve()
        self.name = name or self.root.name
        self.findings: list[Finding] = []

    # ------------------------------------------------------------------ inventário
    def inventory(self) -> dict[str, Any]:
        files: list[dict[str, Any]] = []
        lang_files: Counter[str] = Counter()
        lang_lines: Counter[str] = Counter()
        ext_counter: Counter[str] = Counter()
        binary = 0
        total_bytes = 0
        truncated = False
        for path in _walk(self.root):
            rel = path.relative_to(self.root).as_posix()
            try:
                size = path.stat().st_size
            except OSError:
                continue
            total_bytes += size
            ext = path.suffix.lower()
            lang = LANGUAGES.get(ext) or ("Dockerfile" if path.name == "Dockerfile" else None)
            lines = 0
            if size <= MAX_TEXT_BYTES and (lang or ext in {".txt", ".cfg", ".ini", ""}):
                text = _read_text(path)
                if text is None:
                    binary += 1
                else:
                    lines = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
            elif not lang:
                binary += 1
            if lang:
                lang_files[lang] += 1
                lang_lines[lang] += lines
            ext_counter[ext or path.name] += 1
            files.append({"path": rel, "size": size, "lines": lines, "language": lang})
        if len(files) >= MAX_FILES:
            truncated = True
        self.files = files
        self.file_index = {f["path"]: f for f in files}
        top_dirs: Counter[str] = Counter()
        for f in files:
            parts = f["path"].split("/")
            top_dirs[parts[0] + ("/" if len(parts) > 1 else "")] += 1
        languages = [
            {"language": lang, "files": lang_files[lang], "lines": lang_lines[lang]}
            for lang, _ in lang_files.most_common()
        ]
        code_lines = sum(lang_lines[lang] for lang in lang_files if lang in CODE_LANGUAGES)
        doc_lines = sum(lang_lines[lang] for lang in ("Markdown", "MDX"))
        return {
            "file_count": len(files),
            "total_bytes": total_bytes,
            "binary_or_unreadable_files": binary,
            "truncated": truncated,
            "languages": languages,
            "code_lines": code_lines,
            "documentation_lines": doc_lines,
            "top_level": [{"path": p, "files": c} for p, c in sorted(top_dirs.items(), key=lambda kv: -kv[1])[:40]],
            "largest_files": sorted(({"path": f["path"], "size": f["size"]} for f in files), key=lambda f: -f["size"])[:15],
        }

    # ------------------------------------------------------------------ manifestos
    def manifests(self) -> dict[str, Any]:
        result: dict[str, Any] = {"package_json": [], "python": [], "go": [], "rust": [], "other": []}
        deps: dict[str, set[str]] = defaultdict(set)  # nome -> arquivos (evidência)
        scripts: dict[str, dict[str, str]] = {}
        entry_points: list[dict[str, str]] = []
        for f in self.files:
            path = f["path"]
            name = PurePosixPath(path).name
            depth = path.count("/")
            if depth > 4:
                continue
            full = self.root / path
            if name == "package.json":
                try:
                    data = json.loads(_read_text(full) or "{}")
                except json.JSONDecodeError:
                    continue
                if not isinstance(data, dict):
                    continue
                pkg_deps = {**(data.get("dependencies") or {}), **(data.get("peerDependencies") or {})}
                dev = data.get("devDependencies") or {}
                for d in list(pkg_deps) + list(dev):
                    deps[d.lower()].add(path)
                if data.get("scripts"):
                    scripts[path] = {k: str(v)[:200] for k, v in list(data["scripts"].items())[:40]}
                bins = data.get("bin")
                if isinstance(bins, str):
                    entry_points.append({"kind": "bin", "name": data.get("name", ""), "target": bins, "evidence": path})
                elif isinstance(bins, dict):
                    for k, v in bins.items():
                        entry_points.append({"kind": "bin", "name": k, "target": str(v), "evidence": path})
                if data.get("main"):
                    entry_points.append({"kind": "main", "name": data.get("name", ""), "target": str(data["main"]), "evidence": path})
                result["package_json"].append({
                    "path": path, "name": data.get("name"), "version": data.get("version"),
                    "license": data.get("license") if isinstance(data.get("license"), str) else None,
                    "private": data.get("private", False), "workspaces": data.get("workspaces"),
                    "engines": data.get("engines"), "dependencies": len(pkg_deps), "dev_dependencies": len(dev),
                })
            elif name == "pyproject.toml":
                try:
                    data = tomllib.loads(_read_text(full) or "")
                except tomllib.TOMLDecodeError:
                    continue
                project = data.get("project", {})
                for d in project.get("dependencies", []) or []:
                    deps[_norm_dep(d)].add(path)
                poetry = data.get("tool", {}).get("poetry", {})
                for d in (poetry.get("dependencies") or {}):
                    if d.lower() != "python":
                        deps[d.lower()].add(path)
                for k, v in (project.get("scripts") or {}).items():
                    entry_points.append({"kind": "console_script", "name": k, "target": str(v), "evidence": path})
                result["python"].append({"path": path, "name": project.get("name") or poetry.get("name"), "version": project.get("version")})
            elif re.fullmatch(r"requirements.*\.txt", name):
                text = _read_text(full) or ""
                count = 0
                for line in text.splitlines():
                    line = line.strip()
                    if line and not line.startswith(("#", "-")):
                        deps[_norm_dep(line)].add(path)
                        count += 1
                result["python"].append({"path": path, "requirements": count})
            elif name == "go.mod":
                text = _read_text(full) or ""
                mod = re.search(r"^module\s+(\S+)", text, re.M)
                for m in re.finditer(r"^\s*([\w.\-/]+\.[\w.\-/]+)\s+v[\d.]+", text, re.M):
                    deps[m.group(1).lower()].add(path)
                result["go"].append({"path": path, "module": mod.group(1) if mod else None})
            elif name == "Cargo.toml":
                try:
                    data = tomllib.loads(_read_text(full) or "")
                except tomllib.TOMLDecodeError:
                    continue
                for d in (data.get("dependencies") or {}):
                    deps[d.lower()].add(path)
                result["rust"].append({"path": path, "name": data.get("package", {}).get("name"), "workspace": "workspace" in data})
            elif name in {"Dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml", "Makefile",
                          "Gemfile", "composer.json", "pom.xml", "build.gradle", "build.gradle.kts", "mkdocs.yml", "netlify.toml",
                          "vercel.json", "turbo.json", "pnpm-workspace.yaml", "lerna.json", "nx.json"}:
                result["other"].append({"path": path, "kind": name})
            if name in {"__main__.py", "manage.py", "main.go", "main.py", "app.py", "server.js", "index.js", "main.rs", "cli.js", "cli.ts", "main.ts"} and depth <= 3:
                entry_points.append({"kind": "conventional_entry", "name": name, "target": path, "evidence": path})
        ci = [f["path"] for f in self.files if f["path"].startswith(".github/workflows/") and f["path"].endswith((".yml", ".yaml"))]
        frameworks: dict[str, dict[str, Any]] = {}
        for dep, sources in deps.items():
            key = dep
            if dep not in FRAMEWORK_MAP:
                key = next((k for k in FRAMEWORK_MAP if "/" in k and dep.endswith(k)), dep)
            if key in FRAMEWORK_MAP:
                label, category = FRAMEWORK_MAP[key]
                entry = frameworks.setdefault(label, {"name": label, "category": category, "evidence": set()})
                entry["evidence"].update(sources)
        result["dependencies"] = sorted(deps)[:400]
        result["dependency_count"] = len(deps)
        result["frameworks"] = [
            {**v, "evidence": sorted(v["evidence"])[:5], "status": "proven"} for v in sorted(frameworks.values(), key=lambda v: v["name"])
        ]
        result["scripts"] = scripts
        result["entry_points"] = entry_points[:60]
        result["ci_workflows"] = ci[:40]
        return result

    # ------------------------------------------------------------------ código
    def code_structure(self) -> dict[str, Any]:
        py_modules: dict[str, dict[str, Any]] = {}
        internal_roots = {f["path"].split("/")[0].removesuffix(".py") for f in self.files if f["language"] == "Python"}
        external_imports: Counter[str] = Counter()
        js_external: Counter[str] = Counter()
        fan_in: Counter[str] = Counter()
        parse_errors: list[str] = []
        routes: list[dict[str, str]] = []
        risky: list[dict[str, Any]] = []
        symbols = {"classes": 0, "functions": 0}
        long_functions: list[dict[str, Any]] = []
        analyzed = 0
        for f in self.files:
            lang = f["language"]
            if lang not in {"Python", "JavaScript", "TypeScript", "Go"} or f["size"] > 300_000:
                continue
            if analyzed >= 8000:
                break
            analyzed += 1
            text = _read_text(self.root / f["path"])
            if text is None:
                continue
            if lang == "Python":
                try:
                    tree = ast.parse(text)
                except (SyntaxError, ValueError):
                    parse_errors.append(f["path"])
                    tree = None
                if tree is not None:
                    imports: set[str] = set()
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            imports.update(a.name.split(".")[0] for a in node.names)
                        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                            imports.add(node.module.split(".")[0])
                        elif isinstance(node, ast.ClassDef):
                            symbols["classes"] += 1
                        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            symbols["functions"] += 1
                            length = (getattr(node, "end_lineno", node.lineno) or node.lineno) - node.lineno + 1
                            if length >= 80:
                                long_functions.append({"path": f["path"], "name": node.name, "lines": length})
                    for mod in imports:
                        if mod in internal_roots:
                            fan_in[mod] += 1
                        else:
                            external_imports[mod] += 1
                    py_modules[f["path"]] = {"imports": sorted(imports)}
            elif lang in {"JavaScript", "TypeScript"}:
                for spec in JS_IMPORT.findall(text):
                    if spec.startswith((".", "/")):
                        target = spec.split("/")[-1]
                        fan_in[target] += 1
                    else:
                        base = "/".join(spec.split("/")[:2]) if spec.startswith("@") else spec.split("/")[0]
                        if not base.startswith("node:"):
                            js_external[base] += 1
            for label, pattern, langs in ROUTE_PATTERNS:
                if lang in langs:
                    for m in pattern.finditer(text):
                        if len(routes) < 300:
                            routes.append({"framework": label, "method": m.group(1).upper(), "path": m.group(2), "file": f["path"]})
            for rule, pattern, langs in RISKY_CALLS:
                if lang in langs and "test" not in f["path"].lower():
                    m = pattern.search(text)
                    if m and len(risky) < 100:
                        line = text.count("\n", 0, m.start()) + 1
                        risky.append({"rule": rule, "file": f["path"], "line": line})
        # Rotas baseadas em sistema de arquivos (Next.js)
        for f in self.files:
            p = f["path"]
            m = re.search(r"(?:^|/)app/(.*)/route\.(?:ts|js)$", p) or re.search(r"(?:^|/)pages/api/(.*)\.(?:ts|js)$", p)
            if m and len(routes) < 300:
                routes.append({"framework": "Next.js (arquivo)", "method": "*", "path": "/" + m.group(1), "file": p})
        tests = [f["path"] for f in self.files if re.search(r"(^|/)(tests?|__tests__|spec)(/|$)|(\.|_)(test|spec)\.\w+$|(^|/)test_[^/]+\.py$", f["path"])]
        return {
            "analyzed_source_files": analyzed,
            "python_symbols": symbols,
            "python_parse_errors": parse_errors[:30],
            "external_imports_python": [{"module": m, "count": c} for m, c in external_imports.most_common(30)],
            "external_imports_js": [{"module": m, "count": c} for m, c in js_external.most_common(30)],
            "most_imported_internal": [{"module": m, "count": c} for m, c in fan_in.most_common(20)],
            "routes": routes,
            "risky_calls": risky,
            "long_functions": sorted(long_functions, key=lambda x: -x["lines"])[:20],
            "test_files": len(tests),
            "test_examples": tests[:15],
        }

    # ------------------------------------------------------------------ documentação
    def documentation(self) -> dict[str, Any]:
        readme = next((f["path"] for f in self.files if re.fullmatch(r"readme(\.\w+)?", f["path"], re.I)), None)
        outline: list[str] = []
        summary = ""
        if readme:
            text = _read_text(self.root / readme) or ""
            for line in text.splitlines():
                m = re.match(r"^(#{1,3})\s+(.+)", line)
                if m and len(outline) < 60:
                    title = re.sub(r"<[^>]+>|!\[[^\]]*\]\([^)]*\)", "", m.group(2)).strip()
                    if title:
                        outline.append(("  " * (len(m.group(1)) - 1)) + title)
            summary = readme_summary(text)
        md_files = [f for f in self.files if f["language"] in {"Markdown", "MDX"}]
        link_total = 0
        link_hosts: Counter[str] = Counter()
        sample = md_files if len(md_files) <= 400 else sorted(md_files, key=lambda f: -f["size"])[:400]
        for f in sample:
            text = _read_text(self.root / f["path"]) or ""
            for _title, url in MD_LINK.findall(text):
                link_total += 1
                host = re.sub(r"^https?://(www\.)?", "", url).split("/")[0].lower()
                link_hosts[host] += 1
        docs_dirs = sorted({f["path"].split("/")[0] for f in self.files if f["path"].lower().startswith(("docs/", "doc/", "documentation/", "website/"))})
        return {
            "readme": readme,
            "readme_summary": summary,
            "readme_outline": outline,
            "markdown_files": len(md_files),
            "markdown_links": link_total,
            "top_link_hosts": [{"host": h, "count": c} for h, c in link_hosts.most_common(15)],
            "docs_dirs": docs_dirs,
            "has_contributing": any(re.fullmatch(r"contributing(\.\w+)?", f["path"], re.I) for f in self.files),
            "has_security_policy": any(re.fullmatch(r"(\.github/)?security(\.\w+)?", f["path"], re.I) for f in self.files),
            "has_code_of_conduct": any(re.search(r"code[_-]of[_-]conduct", f["path"], re.I) for f in self.files),
        }

    def license(self) -> dict[str, Any]:
        candidates = [f["path"] for f in self.files if re.fullmatch(r"(licen[sc]e|copying)(\.\w+|-\w+)?", f["path"], re.I)]
        for path in candidates:
            text = _read_text(self.root / path, 60_000) or ""
            for spdx, pattern in LICENSE_PATTERNS:
                if pattern.search(text):
                    return {"spdx": spdx, "file": path, "status": "proven"}
            return {"spdx": "desconhecida", "file": path, "status": "hypothesis"}
        return {"spdx": None, "file": None, "status": "proven"}

    def secrets(self) -> list[dict[str, Any]]:
        hits: list[dict[str, Any]] = []
        for f in self.files:
            if f["size"] > 300_000 or f["language"] in {"Markdown", "MDX"} and f["size"] > 100_000:
                continue
            if f["path"].endswith((".lock", "package-lock.json", ".min.js", ".svg", ".map")):
                continue
            text = _read_text(self.root / f["path"])
            if not text:
                continue
            for rule, pattern in SECRET_RULES:
                for m in pattern.finditer(text):
                    value = m.group(0)
                    if rule == "generic_secret_assignment":
                        value = m.group(2)
                        if re.search(r"(?i)example|placeholder|your|xxxx|changeme|dummy|test|<|\$\{", m.group(0)):
                            continue
                    line = text.count("\n", 0, m.start()) + 1
                    hits.append({
                        "rule": rule, "file": f["path"], "line": line,
                        # O valor nunca é armazenado: apenas uma impressão digital curta para deduplicação.
                        "fingerprint": hashlib.sha256(value.encode()).hexdigest()[:12],
                    })
                    if len(hits) >= 100:
                        return hits
        return hits

    def duplication(self) -> dict[str, Any]:
        """Detecta blocos de 6 linhas repetidos entre arquivos de código (normalizados)."""
        windows: dict[str, list[str]] = defaultdict(list)
        checked = 0
        for f in self.files:
            if f["language"] not in CODE_LANGUAGES or f["size"] > 200_000 or checked > 3000:
                continue
            checked += 1
            text = _read_text(self.root / f["path"]) or ""
            lines = [ln.strip() for ln in text.splitlines()]
            lines = [ln for ln in lines if len(ln) > 3 and not ln.startswith(("#", "//", "import ", "from ", "*"))]
            seen_in_file: set[str] = set()
            for i in range(0, max(len(lines) - 5, 0)):
                block = "\n".join(lines[i:i + 6])
                h = hashlib.md5(block.encode()).hexdigest()
                if h not in seen_in_file:
                    seen_in_file.add(h)
                    windows[h].append(f["path"])
        dup = [(h, paths) for h, paths in windows.items() if len(paths) > 1]
        pairs: Counter[tuple[str, str]] = Counter()
        for _h, paths in dup:
            uniq = sorted(set(paths))
            if len(uniq) >= 2:
                pairs[(uniq[0], uniq[1])] += 1
        return {
            "files_checked": checked,
            "duplicated_blocks": len(dup),
            "top_pairs": [{"a": a, "b": b, "blocks": c} for (a, b), c in pairs.most_common(10)],
        }

    # ------------------------------------------------------------------ síntese
    def classify(self, inv: dict, man: dict, code: dict, docs: dict) -> dict[str, Any]:
        code_lines = inv["code_lines"]
        doc_lines = inv["documentation_lines"]
        frameworks = {f["name"] for f in man["frameworks"]}
        kinds: list[str] = []
        reasons: list[str] = []
        if docs["markdown_links"] > 300 and doc_lines > code_lines:
            kinds.append("lista curada / catálogo de links")
            reasons.append(f"{docs['markdown_links']} links Markdown e mais linhas de documentação ({doc_lines}) que de código ({code_lines})")
        elif doc_lines > code_lines * 2 and docs["markdown_files"] > 5:
            kinds.append("repositório de conteúdo/documentação")
            reasons.append(f"documentação ({doc_lines} linhas) domina o código ({code_lines} linhas)")
        workspaces = any(p.get("workspaces") for p in man["package_json"]) or any(
            o["kind"] in {"pnpm-workspace.yaml", "lerna.json", "nx.json", "turbo.json"} for o in man["other"])
        if workspaces or len(man["package_json"]) > 5:
            kinds.append("monorepo")
            reasons.append(f"{len(man['package_json'])} package.json e/ou configuração de workspaces")
        if frameworks & {"Next.js", "React", "Vue", "Angular", "Svelte", "SvelteKit", "Nuxt", "Astro", "Gatsby"}:
            kinds.append("aplicação web (frontend)")
        if frameworks & {"Express", "Fastify", "NestJS", "FastAPI", "Django", "Flask", "Hono", "Gin", "Axum"}:
            kinds.append("serviço backend/API")
        if frameworks & {"Model Context Protocol"}:
            kinds.append("servidor/ferramenta MCP para agentes")
        if any(e["kind"] in {"bin", "console_script"} for e in man["entry_points"]):
            kinds.append("ferramenta de linha de comando")
        if frameworks & {"Electron", "Tauri"}:
            kinds.append("aplicação desktop")
        if not kinds:
            kinds.append("biblioteca ou projeto de código" if code_lines else "repositório sem código-fonte reconhecido")
        return {"kinds": kinds, "reasons": reasons, "status": "hypothesis"}

    def build_findings(self, inv, man, code, docs, lic, secrets, dup) -> None:
        F = self.findings
        if inv["languages"]:
            top = ", ".join(f"{l['language']} ({l['files']} arq.)" for l in inv["languages"][:5])
            F.append(Finding("estrutura", "Linguagens predominantes", top, "proven", ["inventário de arquivos"]))
        for fw in man["frameworks"][:25]:
            F.append(Finding("tecnologia", f"Usa {fw['name']}", f"Categoria: {fw['category']}", "proven", fw["evidence"]))
        if lic["spdx"] and lic["spdx"] not in PERMISSIVE_LICENSES and lic["spdx"] != "desconhecida":
            F.append(Finding("licença", f"Licença restritiva: {lic['spdx']}", "Não reutilize código ou conteúdo sem autorização; apenas links podem ser referenciados.",
                             lic["status"], [lic["file"]], "high"))
        elif lic["spdx"]:
            F.append(Finding("licença", f"Licença {lic['spdx']}", "Detectada pelo texto do arquivo de licença.", lic["status"], [lic["file"]]))
        else:
            F.append(Finding("licença", "Sem arquivo de licença", "Sem licença explícita, o reuso de código não é autorizado por padrão.", "proven", [], "medium"))
        if secrets:
            F.append(Finding("segurança", f"{len(secrets)} possível(is) segredo(s) exposto(s)",
                             "Padrões de credenciais encontrados. Os valores não foram armazenados.", "hypothesis",
                             sorted({f"{s['file']}:{s['line']}" for s in secrets})[:10], "high"))
        if code["risky_calls"]:
            F.append(Finding("segurança", f"{len(code['risky_calls'])} chamada(s) potencialmente perigosa(s)",
                             "eval/exec, shell=True, innerHTML etc. Requer revisão manual do contexto.", "hypothesis",
                             [f"{r['file']}:{r['line']} ({r['rule']})" for r in code["risky_calls"][:10]], "medium"))
        if inv["code_lines"] > 500 and code["test_files"] == 0:
            F.append(Finding("qualidade", "Nenhum arquivo de teste encontrado", "Não há arquivos com padrão de teste reconhecido.", "proven", [], "medium"))
        elif code["test_files"]:
            F.append(Finding("qualidade", f"{code['test_files']} arquivo(s) de teste", "Arquivos com padrão de teste encontrados.", "proven", code["test_examples"][:5]))
        if man["ci_workflows"]:
            F.append(Finding("devops", f"{len(man['ci_workflows'])} workflow(s) de CI (GitHub Actions)", "", "proven", man["ci_workflows"][:5]))
        if code["routes"]:
            F.append(Finding("interfaces", f"{len(code['routes'])} rota(s) HTTP detectada(s)", "Extraídas por padrões textuais; podem existir rotas dinâmicas não detectadas.",
                             "hypothesis", [f"{r['method']} {r['path']} ({r['file']})" for r in code["routes"][:10]]))
        if man["entry_points"]:
            F.append(Finding("interfaces", f"{len(man['entry_points'])} ponto(s) de entrada", "Declarados em manifestos ou por convenção de nome.",
                             "proven", [f"{e['kind']}: {e['target']} ({e['evidence']})" for e in man["entry_points"][:10]]))
        if code["long_functions"]:
            F.append(Finding("otimização", f"{len(code['long_functions'])} função(ões) Python com 80+ linhas", "Candidatas a refatoração.",
                             "proven", [f"{x['path']}:{x['name']} ({x['lines']} linhas)" for x in code["long_functions"][:5]], "low"))
        if dup["duplicated_blocks"] > 20:
            F.append(Finding("otimização", f"{dup['duplicated_blocks']} blocos de código duplicados", "Janelas de 6 linhas normalizadas repetidas entre arquivos.",
                             "proven", [f"{p['a']} ↔ {p['b']}" for p in dup["top_pairs"][:5]], "low"))
        big = [f for f in inv["largest_files"] if f["size"] > 5_000_000]
        if big:
            F.append(Finding("estrutura", f"{len(big)} arquivo(s) maior(es) que 5 MB", "Arquivos grandes no repositório aumentam custo de clonagem.", "proven",
                             [b["path"] for b in big[:5]], "low"))

    def recommendations(self, inv, man, code, docs, lic, secrets) -> list[dict[str, str]]:
        recs: list[dict[str, str]] = []
        if secrets:
            recs.append({"area": "segurança", "text": "Revogar e remover as credenciais apontadas, e adicionar varredura de segredos ao CI."})
        if inv["code_lines"] > 500 and code["test_files"] == 0:
            recs.append({"area": "qualidade", "text": "Criar uma suíte mínima de testes para os pontos de entrada principais."})
        if not man["ci_workflows"] and inv["code_lines"] > 500:
            recs.append({"area": "devops", "text": "Adicionar integração contínua para executar testes e lint a cada alteração."})
        if not lic["spdx"]:
            recs.append({"area": "licença", "text": "Definir uma licença antes de qualquer reuso ou incorporação de código."})
        if code["long_functions"]:
            recs.append({"area": "otimização", "text": "Dividir as funções mais longas em unidades menores e testáveis."})
        if not docs["readme"]:
            recs.append({"area": "documentação", "text": "Criar um README com objetivo, instalação e uso."})
        return recs

    def analyze(self) -> dict[str, Any]:
        inv = self.inventory()
        man = self.manifests()
        code = self.code_structure()
        docs = self.documentation()
        lic = self.license()
        secrets = self.secrets()
        dup = self.duplication()
        classification = self.classify(inv, man, code, docs)
        self.build_findings(inv, man, code, docs, lic, secrets, dup)
        return {
            "analyzer_version": ANALYZER_VERSION,
            "name": self.name,
            "inventory": inv,
            "manifests": man,
            "code": code,
            "documentation": docs,
            "license": lic,
            "secrets": secrets,
            "duplication": dup,
            "classification": classification,
            "findings": [f.to_dict() for f in self.findings],
            "recommendations": self.recommendations(inv, man, code, docs, lic, secrets),
            "limitations": [
                "Análise estática: nenhum código foi executado; comportamento em tempo de execução não foi observado.",
                "Imports JavaScript/TypeScript e rotas HTTP são extraídos por padrões textuais (não por análise semântica).",
                "Varredura de segredos baseada em padrões: pode haver falsos positivos e falsos negativos.",
                f"Limites: até {MAX_FILES} arquivos, {MAX_TEXT_BYTES // 1000} KB por arquivo de texto, 8000 arquivos de código analisados.",
            ],
        }


def render_markdown(report: dict[str, Any], *, source: str = "", commit: str | None = None) -> str:
    inv, man, code, docs, lic = report["inventory"], report["manifests"], report["code"], report["documentation"], report["license"]
    lines: list[str] = [f"# Relatório de análise — {report['name']}", ""]
    if source:
        lines.append(f"- **Origem:** {source}")
    if commit:
        lines.append(f"- **Commit analisado:** `{commit}`")
    lines += [
        f"- **Analisador:** GENISIA reverse-engineering v{report['analyzer_version']} (estático)",
        f"- **Licença:** {lic['spdx'] or 'não encontrada'}" + (f" (`{lic['file']}`)" if lic.get("file") else ""),
        "",
        "> Legenda: ✅ **comprovado** (evidência em arquivo) · 🔎 **hipótese** (inferência heurística).",
        "",
        "## Visão geral",
        "",
    ]
    if docs["readme_summary"]:
        lines += [f"> {docs['readme_summary']}", "", "_Trecho extraído do README._", ""]
    cls = report["classification"]
    lines += [f"🔎 **Tipo provável:** {', '.join(cls['kinds'])}" + (f" — {'; '.join(cls['reasons'])}" if cls["reasons"] else ""), ""]
    lines += [
        "| Métrica | Valor |", "|---|---|",
        f"| Arquivos | {inv['file_count']}{' (truncado)' if inv['truncated'] else ''} |",
        f"| Tamanho | {inv['total_bytes'] / 1_048_576:.1f} MB |",
        f"| Linhas de código | {inv['code_lines']} |",
        f"| Linhas de documentação (Markdown) | {inv['documentation_lines']} |",
        f"| Links em Markdown | {docs['markdown_links']} |",
        f"| Dependências declaradas | {man['dependency_count']} |",
        f"| Arquivos de teste | {code['test_files']} |",
        f"| Workflows de CI | {len(man['ci_workflows'])} |",
        "",
        "## Linguagens", "", "| Linguagem | Arquivos | Linhas |", "|---|---|---|",
    ]
    for lang in inv["languages"][:12]:
        lines.append(f"| {lang['language']} | {lang['files']} | {lang['lines']} |")
    lines += ["", "## Estrutura de diretórios (nível superior)", "", "```"]
    lines += [f"{d['path']:<40} {d['files']} arquivos" for d in inv["top_level"][:25]]
    lines += ["```", ""]
    if man["frameworks"]:
        lines += ["## Tecnologias identificadas ✅", "", "| Tecnologia | Categoria | Evidência |", "|---|---|---|"]
        for fw in man["frameworks"][:30]:
            lines.append(f"| {fw['name']} | {fw['category']} | {', '.join(f'`{e}`' for e in fw['evidence'][:2])} |")
        lines.append("")
    if man["entry_points"]:
        lines += ["## Pontos de entrada ✅", ""]
        for e in man["entry_points"][:15]:
            lines.append(f"- `{e['kind']}` **{e['name']}** → `{e['target']}` (em `{e['evidence']}`)")
        lines.append("")
    if man["scripts"]:
        lines += ["## Scripts declarados ✅", ""]
        for path, scripts in list(man["scripts"].items())[:3]:
            lines.append(f"`{path}`:")
            lines += [f"- `{k}`: `{v}`" for k, v in list(scripts.items())[:15]]
            lines.append("")
    if code["routes"]:
        lines += ["## Interfaces HTTP 🔎", "", "| Método | Caminho | Arquivo |", "|---|---|---|"]
        for r in code["routes"][:30]:
            lines.append(f"| {r['method']} | `{r['path']}` | `{r['file']}` |")
        lines.append("")
    ext = code["external_imports_js"][:12] or code["external_imports_python"][:12]
    if ext:
        lines += ["## Módulos externos mais importados", ""]
        lines += [f"- `{m['module']}` ({m['count']})" for m in ext]
        lines.append("")
    if docs["readme_outline"]:
        lines += ["## Mapa do README", "", "```"] + docs["readme_outline"][:40] + ["```", ""]
    if docs["top_link_hosts"] and docs["markdown_links"] > 50:
        lines += ["## Domínios mais referenciados", ""]
        lines += [f"- {h['host']} ({h['count']})" for h in docs["top_link_hosts"][:10]]
        lines.append("")
    lines += ["## Descobertas", "", "| Status | Categoria | Descoberta | Evidência |", "|---|---|---|---|"]
    for f in report["findings"]:
        icon = "✅" if f["status"] == "proven" else "🔎"
        ev = "<br>".join(f"`{e}`" for e in f["evidence"][:4])
        title = f["title"] + (f" — {f['detail']}" if f["detail"] else "")
        lines.append(f"| {icon} | {f['category']} | {title.replace('|', '/')} | {ev} |")
    lines.append("")
    if report["recommendations"]:
        lines += ["## Recomendações", ""] + [f"- **{r['area']}:** {r['text']}" for r in report["recommendations"]] + [""]
    lines += ["## Limitações da análise", ""] + [f"- {l}" for l in report["limitations"]] + [""]
    return "\n".join(lines)
