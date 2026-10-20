"""Extração de catálogos (links, APIs, livros) de repositórios em Markdown.

Estratégia A (referências e conhecimento): armazenamos apenas metadados — título, URL,
descrição curta, categoria e origem — nunca o conteúdo dos materiais referenciados.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

LINK_ITEM = re.compile(
    r"^\s*[-*+]\s+(?:\*\*)?\[(?P<title>[^\]]{1,300})\]\((?P<url>https?://[^)\s]+)\)(?:\*\*)?(?P<rest>.*)$"
)
TABLE_ROW = re.compile(r"^\|\s*\[(?P<title>[^\]]+)\]\((?P<url>https?://[^)\s]+)\)\s*\|(?P<cells>.*)\|\s*$")
HEADING = re.compile(r"^(?P<level>#{1,6})\s+(?P<title>.+?)\s*#*\s*$")
SKIP_HEADINGS = re.compile(r"(?i)^(contents|table of contents|índice|sumário|license|licença|contributing|footnotes|related|sponsors?|backers?)$")


@dataclass
class ParsedItem:
    title: str
    url: str
    description: str
    category: str
    item_type: str
    origin_path: str
    tags: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


def _clean(text: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>|`", "", text)
    text = text.replace("**", "").replace("__", "")
    text = re.sub(r"\s+", " ", text).strip(" -–—:|")
    return text[:500]


def _clean_heading(title: str) -> str:
    return _clean(re.sub(r"^[\W_]+", "", title)).strip()


def parse_markdown_links(text: str, origin_path: str, item_type: str = "resource", min_heading: int = 1) -> list[ParsedItem]:
    items: list[ParsedItem] = []
    stack: list[tuple[int, str]] = []
    in_code = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        h = HEADING.match(line)
        if h:
            level = len(h.group("level"))
            title = _clean_heading(h.group("title"))
            stack = [(lvl, t) for lvl, t in stack if lvl < level]
            stack.append((level, title))
            continue
        m = LINK_ITEM.match(line)
        if not m:
            continue
        headings = [t for lvl, t in stack if lvl >= min_heading and t]
        if headings and SKIP_HEADINGS.match(headings[-1]):
            continue
        url = m.group("url")
        if "#" in url and "github.com" in url and url.split("#")[0].rstrip("/").count("/") <= 4 and not headings:
            continue
        title = _clean(m.group("title"))
        rest = _clean(m.group("rest"))
        if not title or title.lower() in {"back to top", "voltar ao topo"}:
            continue
        items.append(ParsedItem(title=title, url=url, description=rest, category=" › ".join(headings[-3:]),
                                item_type=item_type, origin_path=origin_path))
    return items


def parse_public_apis(text: str, origin_path: str) -> list[ParsedItem]:
    """Formato do public-apis: `### Categoria` seguido de tabela | API | Descrição | Auth | HTTPS | CORS |."""
    items: list[ParsedItem] = []
    category = ""
    for line in text.splitlines():
        h = HEADING.match(line)
        if h:
            category = _clean_heading(h.group("title"))
            continue
        m = TABLE_ROW.match(line)
        if not m:
            continue
        cells = [_clean(c) for c in m.group("cells").split("|")]
        while len(cells) < 4:
            cells.append("")
        description, auth, https, cors = cells[0], cells[1], cells[2], cells[3]
        auth_norm = auth if auth and auth.lower() != "no" else "none"
        items.append(ParsedItem(
            title=_clean(m.group("title")), url=m.group("url"), description=description, category=category,
            item_type="api", origin_path=origin_path,
            tags=[t for t in [category.lower(), f"auth:{auth_norm.lower()}", "https" if https.lower() == "yes" else "http"] if t],
            extra={"auth": auth_norm, "https": https.lower() == "yes", "cors": cors.lower() or "unknown",
                   "note": "Disponibilidade e condições de uso não verificadas; consulte a documentação oficial."},
        ))
    return items


def parse_book_list(text: str, origin_path: str) -> list[ParsedItem]:
    items = parse_markdown_links(text, origin_path, item_type="book")
    lang_hint = Path(origin_path).stem.replace("free-programming-books", "").strip("-_") or "en"
    for it in items:
        fmt = re.findall(r"\((PDF|HTML|EPUB|MOBI|Markdown|Leanpub|.*?account.*?)\)", it.description, re.I)
        it.extra = {"formats": fmt[:4], "list_language": lang_hint}
        it.tags = [lang_hint] + [f.lower() for f in fmt[:3]]
    return items


# Perfis de extração para os repositórios de referência. Arquivos podem ser glob.
INGEST_PROFILES: dict[str, dict[str, Any]] = {
    "awesome": {"files": ["readme.md", "README.md"], "parser": "links", "item_type": "tool", "kind": "catalog", "min_heading": 2},
    "public-apis": {"files": ["README.md"], "parser": "public_apis", "kind": "api_catalog"},
    "free-programming-books": {
        "files": ["books/free-programming-books-langs.md", "books/free-programming-books-subjects.md",
                  "books/free-programming-books-pt_BR.md", "courses/free-courses-pt_BR.md", "courses/free-courses-en.md"],
        "parser": "books", "kind": "book_list",
    },
    "build-your-own-x": {"files": ["README.md"], "parser": "links", "item_type": "tutorial", "kind": "catalog", "min_heading": 2},
    "coding-interview-university": {"files": ["README.md", "translations/README-ptbr.md"], "parser": "links", "item_type": "resource", "kind": "catalog", "min_heading": 2},
    "system-design-primer": {"files": ["README.md"], "parser": "links", "item_type": "resource", "kind": "catalog", "min_heading": 2},
    "developer-roadmap": {"files": ["readme.md", "README.md"], "parser": "links", "item_type": "resource", "kind": "catalog", "min_heading": 1},
    "freecodecamp": {"files": ["README.md"], "parser": "links", "item_type": "resource", "kind": "catalog", "min_heading": 1},
    "generic": {"files": ["README.md", "readme.md"], "parser": "links", "item_type": "resource", "kind": "catalog", "min_heading": 1},
}


def profile_for(repo_name: str) -> str:
    key = repo_name.lower().split("/")[-1].removesuffix(".git")
    return key if key in INGEST_PROFILES else "generic"


def extract_catalog(root: Path, profile_name: str) -> tuple[list[ParsedItem], list[str]]:
    profile = INGEST_PROFILES[profile_name]
    items: list[ParsedItem] = []
    used: list[str] = []
    seen_files: set[Path] = set()
    for rel in profile["files"]:
        path = (root / rel).resolve()
        if root.resolve() not in path.parents or not path.is_file() or path in seen_files:
            continue
        seen_files.add(path)
        text = path.read_text(encoding="utf-8", errors="replace")
        used.append(rel)
        if profile["parser"] == "public_apis":
            items += parse_public_apis(text, rel)
        elif profile["parser"] == "books":
            items += parse_book_list(text, rel)
        else:
            items += parse_markdown_links(text, rel, profile.get("item_type", "resource"), profile.get("min_heading", 1))
    # Deduplicação por URL dentro da mesma fonte
    unique: dict[str, ParsedItem] = {}
    for it in items:
        unique.setdefault(it.url, it)
    return list(unique.values()), used
