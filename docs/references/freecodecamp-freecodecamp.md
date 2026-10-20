<!-- Gerado pelo GENISIA AI (scripts/analyze_references.py) a partir da tarefa 06b801720d48497db0cd8f43627cc4b4. -->

> **Papel no GENISIA AI:** Aprendizagem prática
# Relatório de análise — freeCodeCamp/freeCodeCamp

- **Origem:** https://github.com/freeCodeCamp/freeCodeCamp
- **Commit analisado:** `51140b9d3d8cb6b01bd27c78432e1b725eb31ebc`
- **Analisador:** GENISIA reverse-engineering v1.0.0 (estático)
- **Licença:** BSD-3-Clause (`LICENSE.md`)

> Legenda: ✅ **comprovado** (evidência em arquivo) · 🔎 **hipótese** (inferência heurística).

## Visão geral

> Our full-stack web development and machine learning curriculum is completely free and self-paced. We have thousands of interactive coding challenges to help you expand your skills.

_Trecho extraído do README._

🔎 **Tipo provável:** repositório de conteúdo/documentação, monorepo, aplicação web (frontend), serviço backend/API, ferramenta de linha de comando — documentação (2382169 linhas) domina o código (147072 linhas); 16 package.json e/ou configuração de workspaces

| Métrica | Valor |
|---|---|
| Arquivos | 19687 |
| Tamanho | 80.0 MB |
| Linhas de código | 147072 |
| Linhas de documentação (Markdown) | 2382169 |
| Links em Markdown | 25 |
| Dependências declaradas | 272 |
| Arquivos de teste | 359 |
| Workflows de CI | 20 |

## Linguagens

| Linguagem | Arquivos | Linhas |
|---|---|---|
| Markdown | 16951 | 2382169 |
| JSON | 1266 | 87426 |
| TypeScript | 999 | 127961 |
| JavaScript | 203 | 18963 |
| CSS | 91 | 10005 |
| YAML | 69 | 3867 |
| Shell | 7 | 148 |
| HTML | 2 | 24 |
| Dockerfile | 2 | 168 |

## Estrutura de diretórios (nível superior)

```
curriculum/                              18121 arquivos
client/                                  829 arquivos
tools/                                   281 arquivos
api/                                     214 arquivos
e2e/                                     109 arquivos
packages/                                62 arquivos
.github/                                 37 arquivos
.devcontainer/                           7 arquivos
docker/                                  6 arquivos
.dockerignore                            1 arquivos
.editorconfig                            1 arquivos
.gitattributes                           1 arquivos
.gitignore                               1 arquivos
.gitmodules                              1 arquivos
.nvmrc                                   1 arquivos
.prettierignore                          1 arquivos
.prettierrc                              1 arquivos
.stylelintignore                         1 arquivos
.stylelintrc.json                        1 arquivos
LICENSE.md                               1 arquivos
README.md                                1 arquivos
knip.jsonc                               1 arquivos
package.json                             1 arquivos
pnpm-lock.yaml                           1 arquivos
pnpm-workspace.yaml                      1 arquivos
```

## Tecnologias identificadas ✅

| Tecnologia | Categoria | Evidência |
|---|---|---|
| Fastify | backend | `api/package.json` |
| Gatsby | frontend | `client/package.json`, `tools/client-plugins/gatsby-source-challenges/package.json` |
| Mocha | testing | `curriculum/package.json` |
| Playwright | testing | `package.json` |
| Prisma | database | `api/package.json` |
| React | frontend | `client/package.json` |
| TypeScript | language | `api/package.json`, `client/package.json` |
| Vitest | testing | `api/package.json`, `client/package.json` |
| webpack | build | `tools/client-plugins/browser-scripts/package.json` |
| yargs | cli | `package.json`, `packages/challenge-linter/package.json` |

## Pontos de entrada ✅

- `main` **@freecodecamp/freecodecamp** → `none` (em `package.json`)
- `main` **@freecodecamp/api** → `none` (em `api/package.json`)
- `main` **@freecodecamp/client** → `index.js` (em `client/package.json`)
- `conventional_entry` **index.js** → `client/src/redux/index.js` (em `client/src/redux/index.js`)
- `conventional_entry` **index.js** → `client/utils/gatsby/index.js` (em `client/utils/gatsby/index.js`)
- `conventional_entry` **cli.js** → `packages/challenge-linter/cli.js` (em `packages/challenge-linter/cli.js`)
- `bin` **challenge-linter** → `./cli.js` (em `packages/challenge-linter/package.json`)
- `main` **@freecodecamp/challenge-linter** → `index.js` (em `packages/challenge-linter/package.json`)
- `conventional_entry` **cli.ts** → `packages/challenge-linter/src/cli.ts` (em `packages/challenge-linter/src/cli.ts`)
- `main` **@freecodecamp/curriculum-helper-scripts** → `utils.js` (em `tools/challenge-helper-scripts/package.json`)
- `main` **@freecodecamp/challenge-parser** → `index.js` (em `tools/challenge-parser/package.json`)
- `conventional_entry` **index.js** → `tools/challenge-parser/parser/index.js` (em `tools/challenge-parser/parser/index.js`)
- `conventional_entry` **index.js** → `tools/challenge-parser/translation-parser/index.js` (em `tools/challenge-parser/translation-parser/index.js`)
- `main` **@freecodecamp/browser-scripts** → `index.js` (em `tools/client-plugins/browser-scripts/package.json`)
- `main` **@freecodecamp/gatsby-source-challenges** → `gatsby-node.js` (em `tools/client-plugins/gatsby-source-challenges/package.json`)

## Scripts declarados ✅

`package.json`:
- `audit-challenges`: `cd curriculum && pnpm audit-challenges`
- `analyze-bundle`: `webpack-bundle-analyzer`
- `build`: `turbo build`
- `build:client`: `turbo -F=@freecodecamp/client build`
- `build:curriculum`: `turbo -F=@freecodecamp/curriculum build`
- `build:api`: `turbo -F=@freecodecamp/api build`
- `challenge-editor`: `cd tools/challenge-editor && pnpm dev`
- `challenge-editor-setup`: `git submodule update --init tools/challenge-editor && cd tools/challenge-editor && pnpm install`
- `clean`: `npm-run-all -p clean:client clean:api clean:curriculum --serial clean:packages`
- `clean-and-develop`: `pnpm run clean && pnpm install && pnpm run develop`
- `clean:api`: `cd api && pnpm clean`
- `clean:client`: `cd ./client && pnpm run clean`
- `clean:curriculum`: `rm -rf ./curriculum/generated/curriculum.json`
- `clean:turbo`: `find . -name '.turbo' -type d -prune -exec rm -rf '{}' +`
- `clean:packages`: `find . -name 'node_modules' -type d -prune -exec rm -rf '{}' +`

`api/package.json`:
- `build`: `tsc -p tsconfig.build.json`
- `clean`: `rm -rf dist`
- `develop`: `tsx watch --clear-screen=false src/server.ts`
- `start`: `FREECODECAMP_NODE_ENV=production node dist/server.js`
- `lint`: `eslint --max-warnings 0`
- `test`: `vitest run`
- `test:watch`: `vitest`
- `test:ui`: `vitest --ui`
- `type-check`: `tsc --noEmit`
- `prisma`: `dotenv -e ../.env prisma`
- `postinstall`: `prisma generate`
- `exam-env:seed`: `tsx tools/exam-environment/seed/index.ts`
- `exam-env:test`: `tsx tools/exam-environment/test/index.ts`

`client/package.json`:
- `build`: `NODE_OPTIONS="--max-old-space-size=7168 --no-deprecation" gatsby build --prefix-paths`
- `clean`: `gatsby clean`
- `copy:scripts`: `tsx ./tools/copy-browser-scripts.ts`
- `create:i18n`: `tsx ./tools/create-i18n.ts`
- `create:env`: `DEBUG=fcc:* tsx ./tools/create-env.ts`
- `create:external-curriculum`: `tsx ./tools/external-curriculum/build`
- `create:trending`: `tsx ./tools/download-trending.ts`
- `create:search-placeholder`: `tsx ./tools/generate-search-placeholder`
- `develop`: `NODE_OPTIONS="--max-old-space-size=7168 --no-deprecation" gatsby develop --inspect=9230`
- `lint`: `eslint --max-warnings 0`
- `setup`: `pnpm clean && pnpm create:env && pnpm create:i18n && pnpm create:trending && pnpm create:search-placeholder && pnpm create:external-curriculum && pnpm copy:scripts`
- `serve`: `gatsby serve -p 8000`
- `serve-ci`: `serve -l 8000 -c serve.json public`
- `prestand-alone`: `pnpm run prebuild`
- `stand-alone`: `gatsby develop`

## Interfaces HTTP 🔎

| Método | Caminho | Arquivo |
|---|---|---|
| GET | `/daily-coding-challenge/day/:day` | `api/src/daily-coding-challenge/routes/daily-coding-challenge.ts` |
| GET | `/daily-coding-challenge/today` | `api/src/daily-coding-challenge/routes/daily-coding-challenge.ts` |
| GET | `/daily-coding-challenge/month/:month` | `api/src/daily-coding-challenge/routes/daily-coding-challenge.ts` |
| GET | `/daily-coding-challenge/all` | `api/src/daily-coding-challenge/routes/daily-coding-challenge.ts` |
| GET | `/daily-coding-challenge/newest` | `api/src/daily-coding-challenge/routes/daily-coding-challenge.ts` |
| GET | `/exam-environment/exams` | `api/src/exam-environment/routes/exam-environment.ts` |
| POST | `/exam-environment/exam/generated-exam` | `api/src/exam-environment/routes/exam-environment.ts` |
| POST | `/exam-environment/exam/attempt` | `api/src/exam-environment/routes/exam-environment.ts` |
| GET | `/exam-environment/exam/attempts` | `api/src/exam-environment/routes/exam-environment.ts` |
| GET | `/exam-environment/exam/attempt/:attemptId` | `api/src/exam-environment/routes/exam-environment.ts` |
| GET | `/exam-environment/exams/:examId/attempts` | `api/src/exam-environment/routes/exam-environment.ts` |
| GET | `/exam-environment/token-meta` | `api/src/exam-environment/routes/exam-environment.ts` |
| GET | `/exam-environment/exam-challenge` | `api/src/exam-environment/routes/exam-environment.ts` |
| GET | `/signin` | `api/src/plugins/auth-dev.ts` |
| GET | `/test` | `api/src/plugins/auth.test.ts` |
| GET | `/test` | `api/src/plugins/auth.test.ts` |
| GET | `/test-user` | `api/src/plugins/auth.test.ts` |
| GET | `/test-pii` | `api/src/plugins/auth.test.ts` |
| GET | `/test` | `api/src/plugins/auth.test.ts` |
| GET | `/test` | `api/src/plugins/auth.test.ts` |
| GET | `/test` | `api/src/plugins/auth.test.ts` |
| GET | `/test` | `api/src/plugins/auth.test.ts` |
| GET | `/test` | `api/src/plugins/auth.test.ts` |
| GET | `/test` | `api/src/plugins/auth.test.ts` |
| GET | `/test` | `api/src/plugins/auth.test.ts` |
| GET | `/test` | `api/src/plugins/auth.test.ts` |
| GET | `/test` | `api/src/plugins/auth.test.ts` |
| GET | `/test` | `api/src/plugins/auth.test.ts` |
| GET | `/me` | `api/src/plugins/auth.test.ts` |
| GET | `/user/session-user` | `api/src/plugins/auth.test.ts` |

## Módulos externos mais importados

- `react` (439)
- `vitest` (276)
- `@freecodecamp/shared` (239)
- `react-i18next` (208)
- `@freecodecamp/ui` (147)
- `react-redux` (124)
- `@testing-library/react` (96)
- `@fastify/type-provider-typebox` (86)
- `reselect` (59)
- `@playwright/test` (59)
- `i18next` (54)
- `redux` (54)

## Mapa do README

```
  freeCodeCamp.org's open-source codebase and curriculum
  Table of Contents
    Certifications
    The Learning Platform
    Reporting Bugs and Issues
    Reporting Security Issues and Responsible Disclosure
    Contributing
    License
```

## Descobertas

| Status | Categoria | Descoberta | Evidência |
|---|---|---|---|
| ✅ | estrutura | Linguagens predominantes — Markdown (16951 arq.), JSON (1266 arq.), TypeScript (999 arq.), JavaScript (203 arq.), CSS (91 arq.) | `inventário de arquivos` |
| ✅ | tecnologia | Usa Fastify — Categoria: backend | `api/package.json` |
| ✅ | tecnologia | Usa Gatsby — Categoria: frontend | `client/package.json`<br>`tools/client-plugins/gatsby-source-challenges/package.json` |
| ✅ | tecnologia | Usa Mocha — Categoria: testing | `curriculum/package.json` |
| ✅ | tecnologia | Usa Playwright — Categoria: testing | `package.json` |
| ✅ | tecnologia | Usa Prisma — Categoria: database | `api/package.json` |
| ✅ | tecnologia | Usa React — Categoria: frontend | `client/package.json` |
| ✅ | tecnologia | Usa TypeScript — Categoria: language | `api/package.json`<br>`client/package.json`<br>`e2e/package.json`<br>`package.json` |
| ✅ | tecnologia | Usa Vitest — Categoria: testing | `api/package.json`<br>`client/package.json`<br>`curriculum/package.json`<br>`packages/challenge-builder/package.json` |
| ✅ | tecnologia | Usa webpack — Categoria: build | `tools/client-plugins/browser-scripts/package.json` |
| ✅ | tecnologia | Usa yargs — Categoria: cli | `package.json`<br>`packages/challenge-linter/package.json` |
| ✅ | licença | Licença BSD-3-Clause — Detectada pelo texto do arquivo de licença. | `LICENSE.md` |
| 🔎 | segurança | 1 possível(is) segredo(s) exposto(s) — Padrões de credenciais encontrados. Os valores não foram armazenados. | `api/src/utils/sentry.test.ts:703` |
| 🔎 | segurança | 18 chamada(s) potencialmente perigosa(s) — eval/exec, shell=True, innerHTML etc. Requer revisão manual do contexto. | `client/src/html.tsx:47 (js_inner_html)`<br>`client/src/components/SolutionViewer/solution-viewer.tsx:34 (js_inner_html)`<br>`client/src/components/helpers/skeleton-sprite.tsx:8 (js_inner_html)`<br>`client/src/templates/Challenges/classic/editor.tsx:840 (js_inner_html)` |
| ✅ | qualidade | 359 arquivo(s) de teste — Arquivos com padrão de teste encontrados. | `api/vitest.utils.test.ts`<br>`api/src/schema.test.ts`<br>`api/src/server.test.ts`<br>`api/src/daily-coding-challenge/routes/daily-coding-challenge.test.ts` |
| ✅ | devops | 20 workflow(s) de CI (GitHub Actions) | `.github/workflows/crowdin-download.client-ui.yml`<br>`.github/workflows/crowdin-upload.client-ui.yml`<br>`.github/workflows/crowdin-upload.curriculum.yml`<br>`.github/workflows/curriculum-i18n-submodule.yml` |
| 🔎 | interfaces | 119 rota(s) HTTP detectada(s) — Extraídas por padrões textuais; podem existir rotas dinâmicas não detectadas. | `GET /daily-coding-challenge/day/:day (api/src/daily-coding-challenge/routes/daily-coding-challenge.ts)`<br>`GET /daily-coding-challenge/today (api/src/daily-coding-challenge/routes/daily-coding-challenge.ts)`<br>`GET /daily-coding-challenge/month/:month (api/src/daily-coding-challenge/routes/daily-coding-challenge.ts)`<br>`GET /daily-coding-challenge/all (api/src/daily-coding-challenge/routes/daily-coding-challenge.ts)` |
| ✅ | interfaces | 18 ponto(s) de entrada — Declarados em manifestos ou por convenção de nome. | `main: none (package.json)`<br>`main: none (api/package.json)`<br>`main: index.js (client/package.json)`<br>`conventional_entry: client/src/redux/index.js (client/src/redux/index.js)` |
| ✅ | otimização | 1098 blocos de código duplicados — Janelas de 6 linhas normalizadas repetidas entre arquivos. | `client/src/templates/Challenges/codeally/show.tsx ↔ client/src/templates/Challenges/freecodecamp-os/show.tsx`<br>`client/src/components/profile/components/profile-privacy.tsx ↔ client/src/components/settings/privacy.tsx`<br>`api/src/routes/protected/user.test.ts ↔ api/src/routes/public/user.test.ts`<br>`api/src/routes/protected/donate.test.ts ↔ api/src/routes/public/donate.test.ts` |

## Recomendações

- **segurança:** Revogar e remover as credenciais apontadas, e adicionar varredura de segredos ao CI.

## Limitações da análise

- Análise estática: nenhum código foi executado; comportamento em tempo de execução não foi observado.
- Imports JavaScript/TypeScript e rotas HTTP são extraídos por padrões textuais (não por análise semântica).
- Varredura de segredos baseada em padrões: pode haver falsos positivos e falsos negativos.
- Limites: até 60000 arquivos, 400 KB por arquivo de texto, 8000 arquivos de código analisados.

## Grafo JavaScript (REA)

- Ferramenta: REA JavaScript application analyzer · evidência `ev_8e778cca9a51e4cb04da04fc2df396624a07ae7427c97e0d24acbb04827be255`
- Nós por tipo: {'javascript-module': 12237, 'artifact': 1262, 'javascript-asset': 1182, 'endpoint': 281, 'storage': 21, 'package': 16, 'electron-main': 11, 'worker': 4, 'unknown': 3, 'electron-renderer': 1, 'service-worker': 1}
- Relações: {'imports': 13925, 'contains': 3692, 'exposes': 1886, 'calls': 234, 'persists_to': 37, 'loads': 17, 'maps_to': 2}
- Estados de evidência: {'proven (observed)': 9425, 'hypothesis (inferred)': 29303, 'outros': 3}
- Módulos externos: `vitest` (1424), `react` (1080), `@freecodecamp/ui` (566), `react-i18next` (447), `@testing-library/react` (327), `react-redux` (252), `@playwright/test` (155), `@freecodecamp/shared/config/curriculum` (153), `@fastify/type-provider-typebox` (149), `reselect` (118), `path` (107), `@freecodecamp/shared/config/challenge-types` (102), `redux` (97), `redux-saga/effects` (95), `lodash-es` (93)

Limitações declaradas pelo REA:
- CommonJS and ESM binding relationships were recovered from inert syntax and resolved only within the inventoried artifact container.
- Graph coverage is incomplete; unavailable facts remain explicit and must not be read as absence.
- JavaScript and HTML were parsed as inert text; bundle bootstrap code was never executed.
- Static imports, entrypoints, workers, endpoints, and storage relationships do not prove runtime execution.
- Static paths and relationships may remain unresolved when expressions are dynamic or obfuscated.
- Webpack/Rspack factories were recovered from AST literals; REA did not invoke push handlers or bundle bootstrap code.

---

# Verificação de segurança — freeCodeCamp/freeCodeCamp

- **Severidade geral:** high
- **Possíveis segredos:** 1
- **Chamadas perigosas:** 18
- **Dependências declaradas:** 272

## Possíveis segredos (valores não armazenados)

| Regra | Local | Impressão digital |
|---|---|---|
| generic_secret_assignment | `api/src/utils/sentry.test.ts:703` | `cb0e3c33c1bd` |

## Chamadas que exigem revisão

- `client/src/html.tsx:47` — js_inner_html
- `client/src/components/SolutionViewer/solution-viewer.tsx:34` — js_inner_html
- `client/src/components/helpers/skeleton-sprite.tsx:8` — js_inner_html
- `client/src/templates/Challenges/classic/editor.tsx:840` — js_inner_html
- `client/src/templates/Challenges/components/challenge-transcript.tsx:58` — js_inner_html
- `client/src/templates/Challenges/components/independent-lower-jaw.tsx:353` — js_inner_html
- `client/src/templates/Challenges/components/output.tsx:21` — js_inner_html
- `client/src/templates/Challenges/components/preview-portal.tsx:105` — js_inner_html
- `client/src/templates/Challenges/components/prism-formatted.tsx:49` — js_inner_html
- `client/src/templates/Challenges/components/scene/scene.tsx:401` — js_inner_html
- `client/src/templates/Challenges/utils/index.ts:122` — js_inner_html
- `client/src/templates/Introduction/components/block-intros.tsx:7` — js_inner_html
- `client/src/templates/Introduction/components/super-block-intro.tsx:190` — js_inner_html
- `client/utils/tags.tsx:70` — js_inner_html
- `curriculum/src/file-handler.ts:25` — js_eval
- `e2e/daily-coding-challenge.spec.ts:157` — js_child_process_exec
- `e2e/global-setup.ts:9` — js_child_process_exec
- `packages/challenge-builder/src/transformers.js:214` — js_inner_html

## Limitações
- Detecção por padrões; não substitui auditoria nem verificação de CVEs das dependências.


---

# Métricas de otimização — freeCodeCamp/freeCodeCamp

- Linhas de código: 147072
- Blocos duplicados (janelas de 6 linhas): 1098
- Funções Python com 80+ linhas: 0

## Pares com mais duplicação

- `client/src/templates/Challenges/codeally/show.tsx` ↔ `client/src/templates/Challenges/freecodecamp-os/show.tsx`: 150 blocos
- `client/src/components/profile/components/profile-privacy.tsx` ↔ `client/src/components/settings/privacy.tsx`: 83 blocos
- `api/src/routes/protected/user.test.ts` ↔ `api/src/routes/public/user.test.ts`: 78 blocos
- `api/src/routes/protected/donate.test.ts` ↔ `api/src/routes/public/donate.test.ts`: 64 blocos
- `client/src/assets/icons/a1-chinese.tsx` ↔ `client/src/assets/icons/a1-spanish.tsx`: 39 blocos
- `client/src/templates/Challenges/components/pinyin-to-hanzi-input.tsx` ↔ `client/src/templates/Challenges/components/pinyin-tone-input.tsx`: 34 blocos
- `client/src/templates/Challenges/codeally/local-instructions.tsx` ↔ `client/src/templates/Challenges/freecodecamp-os/local-instructions.tsx`: 29 blocos
- `client/src/templates/Challenges/fill-in-the-blank/show.tsx` ↔ `client/src/templates/Challenges/generic/show.tsx`: 26 blocos
- `client/src/templates/Challenges/projects/backend/show.tsx` ↔ `client/src/templates/Challenges/projects/frontend/show.tsx`: 25 blocos
- `client/src/templates/Challenges/codeally/codespaces-instructions.tsx` ↔ `client/src/templates/Challenges/codeally/local-instructions.tsx`: 24 blocos

