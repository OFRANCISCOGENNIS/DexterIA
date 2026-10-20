<!-- Gerado pelo GENISIA AI (scripts/analyze_references.py) a partir da tarefa 1bf88db55a584122bfd1fae3d72c0912. -->

> **Papel no GENISIA AI:** Catálogo de APIs
# Relatório de análise — public-apis/public-apis

- **Origem:** https://github.com/public-apis/public-apis
- **Commit analisado:** `93086df88fbce354dd612373ab755f941f53a473`
- **Analisador:** GENISIA reverse-engineering v1.0.0 (estático)
- **Licença:** MIT (`LICENSE`)

> Legenda: ✅ **comprovado** (evidência em arquivo) · 🔎 **hipótese** (inferência heurística).

## Visão geral

> Fork our official [APILayer Postman Collection](https://www.postman.com/apilayer/apilayer/collection/2uo8qbu/apilayer-suite) and get started in under 60 seconds.

_Trecho extraído do README._

🔎 **Tipo provável:** lista curada / catálogo de links — 2260 links Markdown e mais linhas de documentação (2918) que de código (1251)

| Métrica | Valor |
|---|---|
| Arquivos | 23 |
| Tamanho | 0.4 MB |
| Linhas de código | 1251 |
| Linhas de documentação (Markdown) | 2918 |
| Links em Markdown | 2260 |
| Dependências declaradas | 5 |
| Arquivos de teste | 3 |
| Workflows de CI | 3 |

## Linguagens

| Linguagem | Arquivos | Linhas |
|---|---|---|
| Python | 6 | 1194 |
| Markdown | 5 | 2918 |
| YAML | 3 | 94 |
| Shell | 1 | 57 |

## Estrutura de diretórios (nível superior)

```
.github/                                 9 arquivos
scripts/                                 9 arquivos
.gitattributes                           1 arquivos
.gitignore                               1 arquivos
CONTRIBUTING.md                          1 arquivos
LICENSE                                  1 arquivos
README.md                                1 arquivos
```

## Módulos externos mais importados

- `validate` (3)
- `unittest` (2)
- `sys` (2)
- `typing` (2)
- `re` (2)
- `string` (1)
- `requests` (1)
- `random` (1)

## Mapa do README

```
APILayer Unified Suite in now Live! 🎉 🥳
    APIs Covered Under APILayer Suite!
Try Public APIs for free
  APILayer APIs
  MCP Servers
  Learn more about Public APIs
  Index
    Animals
    Anime
    Anti-Malware
    Art & Design
    Authentication & Authorization
    Blockchain
    Books
    Business
    Calendar
    Cloud Storage & File Sharing
    Continuous Integration
    Cryptocurrency
    Currency Exchange
    Data Validation
    Development
    Dictionaries
    Documents & Productivity
    Email
    Entertainment
    Environment
    Events
    Finance
    Food & Drink
    Games & Comics
    Geocoding
    Government
    Health
    Jobs
    Machine Learning
    Music
    News
    Open Data
    Open Source Projects
```

## Domínios mais referenciados

- github.com (125)
- rapidapi.com (28)
- glama.ai (18)
- apilayer.com (17)
- developers.google.com (17)
- god.gw.postman.com (7)
- documenter.getpostman.com (6)
- abstractapi.com (6)
- sthan.io (6)
- tenders.guru (5)

## Descobertas

| Status | Categoria | Descoberta | Evidência |
|---|---|---|---|
| ✅ | estrutura | Linguagens predominantes — Python (6 arq.), Markdown (5 arq.), YAML (3 arq.), Shell (1 arq.) | `inventário de arquivos` |
| ✅ | licença | Licença MIT — Detectada pelo texto do arquivo de licença. | `LICENSE` |
| ✅ | qualidade | 3 arquivo(s) de teste — Arquivos com padrão de teste encontrados. | `scripts/tests/__init__.py`<br>`scripts/tests/test_validate_format.py`<br>`scripts/tests/test_validate_links.py` |
| ✅ | devops | 3 workflow(s) de CI (GitHub Actions) | `.github/workflows/test_of_push_and_pull.yml`<br>`.github/workflows/test_of_validate_package.yml`<br>`.github/workflows/validate_links.yml` |

## Limitações da análise

- Análise estática: nenhum código foi executado; comportamento em tempo de execução não foi observado.
- Imports JavaScript/TypeScript e rotas HTTP são extraídos por padrões textuais (não por análise semântica).
- Varredura de segredos baseada em padrões: pode haver falsos positivos e falsos negativos.
- Limites: até 60000 arquivos, 400 KB por arquivo de texto, 8000 arquivos de código analisados.

## Indexação na base de conhecimento

- Itens indexados: **2180** {'api': 2180}
- Arquivos de origem: `README.md`
- Somente metadados e links foram armazenados (licença da fonte: MIT).

---

# Verificação de segurança — public-apis/public-apis

- **Severidade geral:** low
- **Possíveis segredos:** 0
- **Chamadas perigosas:** 0
- **Dependências declaradas:** 5

## Limitações
- Detecção por padrões; não substitui auditoria nem verificação de CVEs das dependências.


---

# Métricas de otimização — public-apis/public-apis

- Linhas de código: 1251
- Blocos duplicados (janelas de 6 linhas): 0
- Funções Python com 80+ linhas: 0

