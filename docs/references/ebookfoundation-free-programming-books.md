<!-- Gerado pelo GENISIA AI (scripts/analyze_references.py) a partir da tarefa 10e6f8a839c0475fad97142468aae863. -->

> **Papel no GENISIA AI:** Biblioteca de livros e cursos gratuitos
# Relatório de análise — EbookFoundation/free-programming-books

- **Origem:** https://github.com/EbookFoundation/free-programming-books
- **Commit analisado:** `eb55e4e8c3ac3a57f89bd36258ab7f826d3a74a6`
- **Analisador:** GENISIA reverse-engineering v1.2.0 (estático)
- **Licença:** CC-BY-4.0 (`LICENSE`)

> Legenda: ✅ **comprovado** (evidência em arquivo) · 🔎 **hipótese** (inferência heurística).

## Visão geral

> This list was originally a clone of StackOverflow - List of Freely Available Programming Books with contributions from Karan Bhangui and George Stocker.

_Trecho extraído do README._

🔎 **Tipo provável:** lista curada / catálogo de links — 11941 links Markdown e mais linhas de documentação (32463) que de código (605)

| Métrica | Valor |
|---|---|
| Arquivos | 234 |
| Tamanho | 2.2 MB |
| Linhas de código | 605 |
| Linhas de documentação (Markdown) | 32463 |
| Links em Markdown | 11941 |
| Dependências declaradas | 0 |
| Arquivos de teste | 0 |
| Workflows de CI | 7 |

## Linguagens

| Linguagem | Arquivos | Linhas |
|---|---|---|
| Markdown | 217 | 32463 |
| YAML | 11 | 801 |
| HTML | 1 | 9 |
| Python | 1 | 605 |

## Estrutura de diretórios (nível superior)

```
docs/                                    94 arquivos
books/                                   48 arquivos
courses/                                 41 arquivos
casts/                                   21 arquivos
more/                                    11 arquivos
.github/                                 10 arquivos
scripts/                                 2 arquivos
.editorconfig                            1 arquivos
.gitignore                               1 arquivos
LICENSE                                  1 arquivos
README.md                                1 arquivos
_config.yml                              1 arquivos
favicon.ico                              1 arquivos
_includes/                               1 arquivos
```

## Módulos externos mais importados

- `os` (1)
- `re` (1)
- `yaml` (1)
- `bidi` (1)
- `argparse` (1)
- `subprocess` (1)
- `sys` (1)

## Mapa do README

```
List of Free Learning Resources In Many Languages
  Intro
  How To Contribute
  How To Share
  Resources
    Books
    Cheat Sheets
    Free Online Courses
    Interactive Programming Resources
    Problem Sets and Competitive Programming
    Podcast - Screencast
    Programming Playgrounds
  Translations
  License
```

## Domínios mais referenciados

- youtube.com (3467)
- github.com (648)
- web.archive.org (316)
- example.com (211)
- udemy.com (171)
- example.org (145)
- docs.github.com (112)
- syncfusion.com (73)
- contributor-overtime-api.apiseven.com (72)
- leanpub.com (63)

## Descobertas

| Status | Categoria | Descoberta | Evidência |
|---|---|---|---|
| ✅ | estrutura | Linguagens predominantes — Markdown (217 arq.), YAML (11 arq.), HTML (1 arq.), Python (1 arq.) | `inventário de arquivos` |
| ✅ | licença | Licença CC-BY-4.0 — Detectada pelo texto do arquivo de licença. | `LICENSE` |
| ✅ | qualidade | Nenhum arquivo de teste encontrado — Não há arquivos com padrão de teste reconhecido. |  |
| ✅ | devops | 7 workflow(s) de CI (GitHub Actions) | `.github/workflows/check-urls.yml`<br>`.github/workflows/comment-pr.yml`<br>`.github/workflows/detect-conflicting-prs.yml`<br>`.github/workflows/fpb-lint.yml` |
| ✅ | otimização | 2 função(ões) Python com 80+ linhas — Candidatas a refatoração. | `scripts/rtl_ltr_linter.py:lint_file (207 linhas)`<br>`scripts/rtl_ltr_linter.py:main (158 linhas)` |

## Recomendações

- **qualidade:** Criar uma suíte mínima de testes para os pontos de entrada principais.
- **otimização:** Dividir as funções mais longas em unidades menores e testáveis.

## Limitações da análise

- Análise estática: nenhum código foi executado; comportamento em tempo de execução não foi observado.
- Imports JavaScript/TypeScript e rotas HTTP são extraídos por padrões textuais (não por análise semântica).
- Varredura de segredos baseada em padrões: pode haver falsos positivos e falsos negativos.
- Limites: até 60000 arquivos, 400 KB por arquivo de texto, 8000 arquivos de código analisados.

## Indexação na base de conhecimento

- Itens indexados: **4292** {'book': 4292}
- Arquivos de origem: `books/free-programming-books-langs.md`, `books/free-programming-books-subjects.md`, `books/free-programming-books-pt_BR.md`, `courses/free-courses-pt_BR.md`, `courses/free-courses-en.md`
- Somente metadados e links foram armazenados (licença da fonte: CC-BY-4.0).

---

# Verificação de segurança — EbookFoundation/free-programming-books

- **Severidade geral:** low
- **Possíveis segredos:** 0
- **Chamadas perigosas:** 0
- **Dependências declaradas:** 0

## Limitações
- Detecção por padrões; não substitui auditoria nem verificação de CVEs das dependências.


---

# Métricas de otimização — EbookFoundation/free-programming-books

- Linhas de código: 605
- Blocos duplicados (janelas de 6 linhas): 0
- Funções Python com 80+ linhas: 2

## Funções longas

- `scripts/rtl_ltr_linter.py` `lint_file` — 207 linhas
- `scripts/rtl_ltr_linter.py` `main` — 158 linhas

