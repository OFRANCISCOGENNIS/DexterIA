<!-- Gerado pelo GENISIA AI (scripts/analyze_references.py) a partir da tarefa ce2b0b872ffd4972aa7efc92d3c86ae8. -->

> **Papel no GENISIA AI:** Planejador de evolução técnica
# Relatório de análise — nilbuild/developer-roadmap

- **Origem:** https://github.com/nilbuild/developer-roadmap
- **Commit analisado:** `46aa6a6b533feda20a8f36172188ddb4d7e82ed4`
- **Analisador:** GENISIA reverse-engineering v1.2.0 (estático)
- **Licença:** Proprietária (uso pessoal) (`license`)

> Legenda: ✅ **comprovado** (evidência em arquivo) · 🔎 **hipótese** (inferência heurística).

## Visão geral

> Roadmaps are now interactive, you can click the nodes to read more about the topics.

_Trecho extraído do README._

🔎 **Tipo provável:** lista curada / catálogo de links, monorepo — 1794 links Markdown e mais linhas de documentação (89673) que de código (815); 1 package.json e/ou configuração de workspaces

| Métrica | Valor |
|---|---|
| Arquivos | 11080 |
| Tamanho | 7.5 MB |
| Linhas de código | 815 |
| Linhas de documentação (Markdown) | 89673 |
| Links em Markdown | 1794 |
| Dependências declaradas | 9 |
| Arquivos de teste | 0 |
| Workflows de CI | 8 |

## Linguagens

| Linguagem | Arquivos | Linhas |
|---|---|---|
| Markdown | 11048 | 89673 |
| YAML | 17 | 992 |
| TypeScript | 8 | 811 |
| JSON | 2 | 43 |
| JavaScript | 1 | 4 |

## Estrutura de diretórios (nível superior)

```
roadmaps/                                11046 arquivos
.github/                                 15 arquivos
scripts/                                 9 arquivos
.gitignore                               1 arquivos
.prettierrc.cjs                          1 arquivos
code_of_conduct.md                       1 arquivos
contributing.md                          1 arquivos
license                                  1 arquivos
package.json                             1 arquivos
pnpm-lock.yaml                           1 arquivos
pnpm-workspace.yaml                      1 arquivos
readme.md                                1 arquivos
tsconfig.json                            1 arquivos
```

## Tecnologias identificadas ✅

| Tecnologia | Categoria | Evidência |
|---|---|---|
| TypeScript | language | `package.json` |

## Scripts declarados ✅

`package.json`:
- `format`: `prettier --write .`
- `sync:content-to-repo`: `tsx ./scripts/sync-content-to-repo.ts`
- `sync:repo-to-database`: `tsx ./scripts/sync-repo-to-database.ts`
- `cleanup:orphaned-content`: `tsx ./scripts/cleanup-orphaned-content.ts`

## Módulos externos mais importados

- `node-html-parser` (1)
- `turndown` (1)
- `markdown-it` (1)

## Mapa do README

```
    [View all Roadmaps](https://roadmap.sh) &nbsp;&middot;&nbsp; [Best Practices](https://roadmap.sh/best-practices) &nbsp;&middot;&nbsp; [Questions](https://roadmap.sh/questions)
  Share with the community
  Repository Structure
  Contribution
  Thanks to all contributors ❤
  License
```

## Domínios mais referenciados

- youtube.com (351)
- roadmap.sh (168)
- elastic.co (79)
- medium.com (73)
- github.com (39)
- towardsdatascience.com (39)
- thenewstack.io (32)
- postgresql.org (25)
- mongodb.com (24)
- code.claude.com (23)

## Descobertas

| Status | Categoria | Descoberta | Evidência |
|---|---|---|---|
| ✅ | estrutura | Linguagens predominantes — Markdown (11048 arq.), YAML (17 arq.), TypeScript (8 arq.), JSON (2 arq.), JavaScript (1 arq.) | `inventário de arquivos` |
| ✅ | tecnologia | Usa TypeScript — Categoria: language | `package.json` |
| ✅ | licença | Licença restritiva: Proprietária (uso pessoal) — Não reutilize código ou conteúdo sem autorização; apenas links podem ser referenciados. | `license` |
| ✅ | qualidade | Nenhum arquivo de teste encontrado — Não há arquivos com padrão de teste reconhecido. |  |
| ✅ | devops | 8 workflow(s) de CI (GitHub Actions) | `.github/workflows/aws-costs.yml`<br>`.github/workflows/cleanup-orphaned-content.yml`<br>`.github/workflows/close-feedback-pr.yml`<br>`.github/workflows/cloudfront-api-cache.yml` |

## Recomendações

- **qualidade:** Criar uma suíte mínima de testes para os pontos de entrada principais.

## Limitações da análise

- Análise estática: nenhum código foi executado; comportamento em tempo de execução não foi observado.
- Imports JavaScript/TypeScript e rotas HTTP são extraídos por padrões textuais (não por análise semântica).
- Varredura de segredos baseada em padrões: pode haver falsos positivos e falsos negativos.
- Limites: até 60000 arquivos, 400 KB por arquivo de texto, 8000 arquivos de código analisados.

## Grafo JavaScript (REA)

- Ferramenta: REA JavaScript application analyzer · evidência `ev_897849ceedc226e3c05a74e7a865364fa08da6bb6c07203b4e04df536f2ed583`
- Nós por tipo: javascript-module (60), javascript-asset (9), endpoint (5), artifact (3), unknown (1), package (1)
- Relações: imports (36), contains (22), exposes (15), calls (5)
- Estados de evidência: proven (observed): 63, hypothesis (inferred): 104, outros: 1
- Módulos externos: `node:fs/promises` (6), `node:path` (6), `node:url` (6), `markdown-it` (2), `turndown` (2), `node-html-parser` (2)

Limitações declaradas pelo REA:
- CommonJS and ESM binding relationships were recovered from inert syntax and resolved only within the inventoried artifact container.
- Graph coverage is incomplete; unavailable facts remain explicit and must not be read as absence.
- JavaScript and HTML were parsed as inert text; bundle bootstrap code was never executed.
- Static imports, entrypoints, workers, endpoints, and storage relationships do not prove runtime execution.
- Static paths and relationships may remain unresolved when expressions are dynamic or obfuscated.
- Webpack/Rspack factories were recovered from AST literals; REA did not invoke push handlers or bundle bootstrap code.

## Indexação na base de conhecimento

- Itens indexados: **98** {'resource': 98}
- Arquivos de origem: `readme.md`
- Somente metadados e links foram armazenados (licença da fonte: Proprietária (uso pessoal)).

---

# Verificação de segurança — nilbuild/developer-roadmap

- **Severidade geral:** low
- **Possíveis segredos:** 0
- **Chamadas perigosas:** 0
- **Dependências declaradas:** 9

## Limitações
- Detecção por padrões; não substitui auditoria nem verificação de CVEs das dependências.


---

# Métricas de otimização — nilbuild/developer-roadmap

- Linhas de código: 815
- Blocos duplicados (janelas de 6 linhas): 0
- Funções Python com 80+ linhas: 0

