<!-- Gerado pelo GENISIA AI (scripts/analyze_references.py) a partir da tarefa 9db841afba4c4bd5898ac9a9641981c3. -->

> **Papel no GENISIA AI:** Assistentes que executam tarefas
# Relatório de análise — openclaw/openclaw

- **Origem:** https://github.com/openclaw/openclaw
- **Commit analisado:** `a69d352fdc59acd711a64e7ceeb85b0b7bbaaa09`
- **Analisador:** GENISIA reverse-engineering v1.2.0 (estático)
- **Licença:** MIT (`LICENSE`)

> Legenda: ✅ **comprovado** (evidência em arquivo) · 🔎 **hipótese** (inferência heurística).

## Visão geral

> OpenClaw is an open-source AI assistant that runs on your own computer and meets you in the channels you already use: Discord, iMessage, Slack, Teams, Telegram, WhatsApp, and 20+ more, plus native apps for macOS, iOS, Android, Windows, and Linux. One Gateway runs it as a personal assistant on a laptop or as a shared team deployment; configuration is the only difference.

_Trecho extraído do README._

🔎 **Tipo provável:** monorepo, serviço backend/API, servidor/ferramenta MCP para agentes, ferramenta de linha de comando — 207 package.json e/ou configuração de workspaces

| Métrica | Valor |
|---|---|
| Arquivos | 58286 |
| Tamanho | 647.6 MB |
| Linhas de código | 12315630 |
| Linhas de documentação (Markdown) | 441776 |
| Links em Markdown | 65286 |
| Dependências declaradas | 311 |
| Arquivos de teste | 22326 |
| Workflows de CI | 40 |

## Linguagens

| Linguagem | Arquivos | Linhas |
|---|---|---|
| TypeScript | 48901 | 11245462 |
| Markdown | 2097 | 441480 |
| Swift | 1585 | 431195 |
| JSON | 1006 | 178363 |
| YAML | 828 | 121554 |
| JavaScript | 809 | 232642 |
| Kotlin | 620 | 252201 |
| Shell | 306 | 67883 |
| CSS | 224 | 91143 |
| Rust | 72 | 54265 |
| SQL | 69 | 22108 |
| Python | 59 | 18892 |

## Estrutura de diretórios (nível superior)

```
src/                                     27798 arquivos
extensions/                              12342 arquivos
ui/                                      6301 arquivos
apps/                                    3107 arquivos
test/                                    2411 arquivos
scripts/                                 1895 arquivos
docs/                                    1453 arquivos
packages/                                1423 arquivos
qa/                                      617 arquivos
.agents/                                 296 arquivos
.github/                                 250 arquivos
CHANGELOG/                               156 arquivos
skills/                                  75 arquivos
config/                                  30 arquivos
crates/                                  25 arquivos
security/                                15 arquivos
patches/                                 8 arquivos
deploy/                                  5 arquivos
custodian-skills/                        4 arquivos
examples/                                3 arquivos
.claude/                                 2 arquivos
tools/                                   2 arquivos
.crabbox.yaml                            1 arquivos
.dockerignore                            1 arquivos
.env.example                             1 arquivos
```

## Tecnologias identificadas ✅

| Tecnologia | Categoria | Evidência |
|---|---|---|
| Anthropic SDK | ai | `extensions/amazon-bedrock-mantle/package.json`, `package.json` |
| Commander.js | cli | `package.json` |
| Express | backend | `extensions/browser/package.json`, `extensions/msteams/package.json` |
| Model Context Protocol | ai | `extensions/browser/package.json`, `extensions/qa-lab/package.json` |
| OpenAI SDK | ai | `extensions/agentsapi/package.json`, `extensions/memory-lancedb/package.json` |
| PostgreSQL (driver) | database | `package.json` |
| Serde | serialization | `apps/linux/src-tauri/Cargo.toml`, `crates/openclaw-gateway-client/Cargo.toml` |
| Tokio | runtime | `apps/linux/src-tauri/Cargo.toml`, `crates/openclaw-gateway-client/Cargo.toml` |
| TypeScript | language | `package.json`, `scripts/cloudflare/package.json` |
| Vite | build | `extensions/qa-lab/package.json`, `package.json` |
| Vitest | testing | `package.json`, `ui/package.json` |
| Zod | validation | `extensions/a2a/package.json`, `extensions/acpx/package.json` |

## Pontos de entrada ✅

- `bin` **openclaw** → `openclaw.mjs` (em `package.json`)
- `main` **openclaw** → `dist/index.js` (em `package.json`)
- `conventional_entry` **main.rs** → `crates/openclaw-node-host/src/main.rs` (em `crates/openclaw-node-host/src/main.rs`)
- `conventional_entry` **cli.ts** → `extensions/canvas/src/cli.ts` (em `extensions/canvas/src/cli.ts`)
- `conventional_entry` **cli.ts** → `extensions/file-transfer/src/cli.ts` (em `extensions/file-transfer/src/cli.ts`)
- `conventional_entry` **cli.ts** → `extensions/google-meet/src/cli.ts` (em `extensions/google-meet/src/cli.ts`)
- `conventional_entry` **cli.ts** → `extensions/matrix/src/cli.ts` (em `extensions/matrix/src/cli.ts`)
- `conventional_entry` **cli.ts** → `extensions/mcp-relay/src/cli.ts` (em `extensions/mcp-relay/src/cli.ts`)
- `conventional_entry` **cli.ts** → `extensions/memory-core/cli.ts` (em `extensions/memory-core/cli.ts`)
- `conventional_entry` **cli.ts** → `extensions/memory-core/src/cli.ts` (em `extensions/memory-core/src/cli.ts`)
- `conventional_entry` **cli.ts** → `extensions/memory-wiki/src/cli.ts` (em `extensions/memory-wiki/src/cli.ts`)
- `conventional_entry` **cli.ts** → `extensions/microsoft-foundry/cli.ts` (em `extensions/microsoft-foundry/cli.ts`)
- `conventional_entry` **cli.ts** → `extensions/oc-path/src/cli.ts` (em `extensions/oc-path/src/cli.ts`)
- `conventional_entry` **cli.ts** → `extensions/onepassword/src/cli.ts` (em `extensions/onepassword/src/cli.ts`)
- `conventional_entry` **cli.ts** → `extensions/onnx/src/cli.ts` (em `extensions/onnx/src/cli.ts`)

## Scripts declarados ✅

`package.json`:
- `android:assemble`: `node --import ./scripts/tsx.mjs scripts/run-android-gradle.mts :app:assemblePlayDebug :wear:assembleDebug :wear-shared:assembleDebug`
- `android:assemble:third-party`: `node --import ./scripts/tsx.mjs scripts/run-android-gradle.mts :app:assembleThirdPartyDebug`
- `android:bundle:release`: `bash -lc 'source ./scripts/lib/android-fastlane.sh && cd apps/android && run_android_fastlane android play_store_archive'`
- `android:format`: `cd apps/android && ./gradlew :app:ktlintFormat :benchmark:ktlintFormat :wear:ktlintFormat :wear-shared:ktlintFormat`
- `android:install`: `node --import ./scripts/tsx.mjs scripts/run-android-gradle.mts :app:installPlayDebug`
- `android:install:third-party`: `node --import ./scripts/tsx.mjs scripts/run-android-gradle.mts :app:installThirdPartyDebug`
- `android:lint`: `cd apps/android && ./gradlew :app:ktlintCheck :benchmark:ktlintCheck :wear:ktlintCheck :wear-shared:ktlintCheck`
- `android:lint:android`: `node --import ./scripts/tsx.mjs scripts/run-android-gradle.mts :app:lintPlayDebug :app:lintThirdPartyDebug :wear:lintDebug :wear-shared:lintDebug`
- `android:run`: `node --import ./scripts/tsx.mjs scripts/run-android-gradle.mts :app:runPlayDebug`
- `android:run:third-party`: `node --import ./scripts/tsx.mjs scripts/run-android-gradle.mts :app:runThirdPartyDebug`
- `android:release`: `bash scripts/android-release.sh`
- `android:release:archive`: `bash -lc 'source ./scripts/lib/android-fastlane.sh && cd apps/android && run_android_fastlane android play_store_archive'`
- `android:release:auth:check`: `bash -lc 'source ./scripts/lib/android-fastlane.sh && cd apps/android && run_android_fastlane android auth_check'`
- `android:release:metadata`: `bash -lc 'source ./scripts/lib/android-fastlane.sh && cd apps/android && run_android_fastlane android metadata'`
- `android:release:preflight`: `bash -lc 'source ./scripts/lib/android-fastlane.sh && cd apps/android && run_android_fastlane android release_preflight'`

`examples/ai-chat/package.json`:
- `start`: `node index.mjs`

`extensions/facetime/package.json`:
- `install:driver`: `bash scripts/install-driver.sh`
- `uninstall:driver`: `bash scripts/install-driver.sh --uninstall`
- `inject:helper`: `bash scripts/inject-helper.sh`
- `inject:helper:phone`: `bash scripts/inject-helper.sh --app Phone`
- `inject:helper:terminal`: `bash scripts/inject-helper-terminal.sh`

## Interfaces HTTP 🔎

| Método | Caminho | Arquivo |
|---|---|---|
| GET | `/sandbox/novnc` | `extensions/browser/src/browser/bridge-server.ts` |
| POST | `/mutate` | `extensions/browser/src/browser/server-middleware.test.ts` |
| POST | `/act` | `extensions/browser/src/browser/routes/agent.act.ts` |
| POST | `/screencast` | `extensions/browser/src/browser/routes/agent.screencast.ts` |
| POST | `/navigate` | `extensions/browser/src/browser/routes/agent.snapshot.ts` |
| POST | `/pdf` | `extensions/browser/src/browser/routes/agent.snapshot.ts` |
| POST | `/screenshot` | `extensions/browser/src/browser/routes/agent.snapshot.ts` |
| GET | `/snapshot` | `extensions/browser/src/browser/routes/agent.snapshot.ts` |
| GET | `/system-profiles` | `extensions/browser/src/browser/routes/basic.ts` |
| GET | `/system-profile-import/status` | `extensions/browser/src/browser/routes/basic.ts` |
| POST | `/system-profile-import/dismiss` | `extensions/browser/src/browser/routes/basic.ts` |
| GET | `/profiles` | `extensions/browser/src/browser/routes/basic.ts` |
| POST | `/profiles/create` | `extensions/browser/src/browser/routes/basic.ts` |
| POST | `/profiles/import` | `extensions/browser/src/browser/routes/basic.ts` |
| DELETE | `/profiles/:name` | `extensions/browser/src/browser/routes/basic.ts` |
| GET | `/slow` | `extensions/browser/src/browser/routes/dispatcher.abort.test.ts` |
| GET | `/echo/:id` | `extensions/browser/src/browser/routes/dispatcher.abort.test.ts` |
| GET | `/snapshot` | `extensions/browser/src/browser/routes/dispatcher.path-normalization.test.ts` |
| POST | `/permissions/grant` | `extensions/browser/src/browser/routes/permissions.ts` |
| GET | `/tabs` | `extensions/browser/src/browser/routes/tabs.ts` |
| POST | `/tabs/open` | `extensions/browser/src/browser/routes/tabs.ts` |
| POST | `/tabs/focus` | `extensions/browser/src/browser/routes/tabs.ts` |
| DELETE | `/tabs/:targetId` | `extensions/browser/src/browser/routes/tabs.ts` |
| POST | `/tabs/action` | `extensions/browser/src/browser/routes/tabs.ts` |

## Módulos externos mais importados

- `openclaw` (15441)
- `vitest` (3466)
- `discord-api-types` (161)
- `@openclaw/normalization-core` (144)
- `playwright-core` (100)
- `matrix-js-sdk` (93)
- `zod` (88)
- `commander` (82)
- `typebox` (79)
- `nostr-tools` (68)
- `ws` (49)
- `@line/bot-sdk` (46)

## Mapa do README

```
OpenClaw 🦞 — Your assistant, on your devices, in your chats
  Install
macOS / Linux / WSL2
Windows PowerShell
  Quick start
  How it fits together
  Security
  Documentation
  Development
  Governance
  Community
  Donors and sponsors
  Contributors
  License
```

## Domínios mais referenciados

- github.com (62193)
- docs.openclaw.ai (2761)
- cdn.simpleicons.org (28)
- developers.openai.com (27)
- raw.githubusercontent.com (19)
- platform.claude.com (17)
- twilio.com (13)
- docs.aws.amazon.com (9)
- docs.x.ai (7)
- clawhub.ai (6)

## Descobertas

| Status | Categoria | Descoberta | Evidência |
|---|---|---|---|
| ✅ | estrutura | Linguagens predominantes — TypeScript (48901 arq.), Markdown (2097 arq.), Swift (1585 arq.), JSON (1006 arq.), YAML (828 arq.) | `inventário de arquivos` |
| ✅ | tecnologia | Usa Anthropic SDK — Categoria: ai | `extensions/amazon-bedrock-mantle/package.json`<br>`package.json`<br>`packages/ai/package.json` |
| ✅ | tecnologia | Usa Commander.js — Categoria: cli | `package.json` |
| ✅ | tecnologia | Usa Express — Categoria: backend | `extensions/browser/package.json`<br>`extensions/msteams/package.json`<br>`package.json` |
| ✅ | tecnologia | Usa Model Context Protocol — Categoria: ai | `extensions/browser/package.json`<br>`extensions/qa-lab/package.json`<br>`package.json` |
| ✅ | tecnologia | Usa OpenAI SDK — Categoria: ai | `extensions/agentsapi/package.json`<br>`extensions/memory-lancedb/package.json`<br>`package.json`<br>`packages/ai/package.json` |
| ✅ | tecnologia | Usa PostgreSQL (driver) — Categoria: database | `package.json` |
| ✅ | tecnologia | Usa Serde — Categoria: serialization | `apps/linux/src-tauri/Cargo.toml`<br>`crates/openclaw-gateway-client/Cargo.toml`<br>`crates/openclaw-node-host/Cargo.toml` |
| ✅ | tecnologia | Usa Tokio — Categoria: runtime | `apps/linux/src-tauri/Cargo.toml`<br>`crates/openclaw-gateway-client/Cargo.toml`<br>`crates/openclaw-node-host/Cargo.toml` |
| ✅ | tecnologia | Usa TypeScript — Categoria: language | `package.json`<br>`scripts/cloudflare/package.json`<br>`tools/solid-lint/package.json` |
| ✅ | tecnologia | Usa Vite — Categoria: build | `extensions/qa-lab/package.json`<br>`package.json`<br>`packages/mermaid-renderer/package.json`<br>`ui/package.json` |
| ✅ | tecnologia | Usa Vitest — Categoria: testing | `package.json`<br>`ui/package.json` |
| ✅ | tecnologia | Usa Zod — Categoria: validation | `extensions/a2a/package.json`<br>`extensions/acpx/package.json`<br>`extensions/agentsapi/package.json`<br>`extensions/apple-fm/package.json` |
| ✅ | licença | Licença MIT — Detectada pelo texto do arquivo de licença. | `LICENSE` |
| 🔎 | segurança | 100 possível(is) segredo(s) exposto(s) — Padrões de credenciais encontrados. Os valores não foram armazenados. | `.agents/skills/telegram-e2e-userbot/scripts/run-published-upgrade-user-e2e.test.mjs:139`<br>`.agents/skills/telegram-e2e-userbot/scripts/run-published-upgrade-user-e2e.test.mjs:216`<br>`apps/android/app/src/test/java/ai/openclaw/app/GatewayBootstrapAuthTest.kt:1873`<br>`apps/android/app/src/test/java/ai/openclaw/app/GatewayBootstrapAuthTest.kt:534` |
| 🔎 | segurança | 9 chamada(s) potencialmente perigosa(s) — eval/exec, shell=True, innerHTML etc. Requer revisão manual do contexto. | `.github/actions/git-owner/owner.py:58 (python_eval_exec)`<br>`apps/linux/ui/gateway-notice.js:24 (js_inner_html)`<br>`apps/linux/ui/gateways.js:182 (js_inner_html)`<br>`apps/linux/ui/window-chrome.js:156 (js_inner_html)` |
| ✅ | qualidade | 22326 arquivo(s) de teste — Arquivos com padrão de teste encontrados. | `.agents/skills/plugin-sdk-impact/scripts/query.test.mjs`<br>`.agents/skills/plugin-sdk-impact/scripts/scan-bundled.test.mjs`<br>`.agents/skills/telegram-e2e-userbot/scripts/followup-drain-control-preload.test.mjs`<br>`.agents/skills/telegram-e2e-userbot/scripts/qa-credential-lease.test.mjs` |
| ✅ | devops | 40 workflow(s) de CI (GitHub Actions) | `.github/workflows/android-emulator-diagnostic.yml`<br>`.github/workflows/android-release-e2e.yml`<br>`.github/workflows/android-release.yml`<br>`.github/workflows/android-store-release.yml` |
| 🔎 | interfaces | 24 rota(s) HTTP detectada(s) — Extraídas por padrões textuais; podem existir rotas dinâmicas não detectadas. | `GET /sandbox/novnc (extensions/browser/src/browser/bridge-server.ts)`<br>`POST /mutate (extensions/browser/src/browser/server-middleware.test.ts)`<br>`POST /act (extensions/browser/src/browser/routes/agent.act.ts)`<br>`POST /screencast (extensions/browser/src/browser/routes/agent.screencast.ts)` |
| ✅ | interfaces | 44 ponto(s) de entrada — Declarados em manifestos ou por convenção de nome. | `bin: openclaw.mjs (package.json)`<br>`main: dist/index.js (package.json)`<br>`conventional_entry: crates/openclaw-node-host/src/main.rs (crates/openclaw-node-host/src/main.rs)`<br>`conventional_entry: extensions/canvas/src/cli.ts (extensions/canvas/src/cli.ts)` |
| ✅ | otimização | 20 função(ões) Python com 80+ linhas — Candidatas a refatoração. | `apps/linux/tests/gateway_switch.py:exercise (297 linhas)`<br>`apps/linux/tests/packaged_runtime_smoke.py:main (222 linhas)`<br>`apps/linux/tests/first_run.py:main (183 linhas)`<br>`.agents/skills/telegram-e2e-userbot/scripts/user-record.py:run_scenario (171 linhas)` |
| ✅ | otimização | 1301 blocos de código duplicados — Janelas de 6 linhas normalizadas repetidas entre arquivos. | `apps/ios/Tests/LocationServiceCallbackTests.swift ↔ apps/macos/Tests/OpenClawIPCTests/MacNodeLocationServiceTests.swift`<br>`apps/ios/Tests/IOSGatewayChatTransportTests.swift ↔ apps/macos/Tests/OpenClawIPCTests/MacGatewayChatTransportMappingTests.swift`<br>`apps/ios/Sources/Chat/IOSGatewayChatTransport.swift ↔ apps/macos/Sources/OpenClaw/WebChatSwiftUI.swift`<br>`apps/linux/tests/first_run.py ↔ apps/linux/tests/remote_connection_smoke.py` |
| ✅ | estrutura | 2 arquivo(s) maior(es) que 5 MB — Arquivos grandes no repositório aumentam custo de clonagem. | `ui/src/i18n/.i18n/th.tm.jsonl`<br>`ui/src/i18n/.i18n/hi.tm.jsonl` |

## Recomendações

- **segurança:** Revogar e remover as credenciais apontadas, e adicionar varredura de segredos ao CI.
- **otimização:** Dividir as funções mais longas em unidades menores e testáveis.

## Grafo JavaScript (REA)

Não gerado (timeout): o REA excedeu o limite de 900 s neste repositório.

## Limitações da análise

- Análise estática: nenhum código foi executado; comportamento em tempo de execução não foi observado.
- Imports JavaScript/TypeScript e rotas HTTP são extraídos por padrões textuais (não por análise semântica).
- Varredura de segredos baseada em padrões: pode haver falsos positivos e falsos negativos.
- Limites: até 60000 arquivos, 400 KB por arquivo de texto, 8000 arquivos de código analisados.

---

# Verificação de segurança — openclaw/openclaw

- **Severidade geral:** high
- **Possíveis segredos:** 100
- **Chamadas perigosas:** 9
- **Dependências declaradas:** 311

## Possíveis segredos (valores não armazenados)

| Regra | Local | Impressão digital |
|---|---|---|
| generic_secret_assignment | `.agents/skills/telegram-e2e-userbot/scripts/run-published-upgrade-user-e2e.test.mjs:139` | `6035152cb6fd` |
| generic_secret_assignment | `.agents/skills/telegram-e2e-userbot/scripts/run-published-upgrade-user-e2e.test.mjs:216` | `6035152cb6fd` |
| generic_secret_assignment | `apps/android/app/src/test/java/ai/openclaw/app/GatewayBootstrapAuthTest.kt:534` | `cddf50016e64` |
| generic_secret_assignment | `apps/android/app/src/test/java/ai/openclaw/app/GatewayBootstrapAuthTest.kt:576` | `cddf50016e64` |
| generic_secret_assignment | `apps/android/app/src/test/java/ai/openclaw/app/GatewayBootstrapAuthTest.kt:590` | `34997354f2ec` |
| generic_secret_assignment | `apps/android/app/src/test/java/ai/openclaw/app/GatewayBootstrapAuthTest.kt:590` | `e165f014af94` |
| generic_secret_assignment | `apps/android/app/src/test/java/ai/openclaw/app/GatewayBootstrapAuthTest.kt:646` | `79752b9a0d1a` |
| generic_secret_assignment | `apps/android/app/src/test/java/ai/openclaw/app/GatewayBootstrapAuthTest.kt:725` | `b5cce2ab6580` |
| generic_secret_assignment | `apps/android/app/src/test/java/ai/openclaw/app/GatewayBootstrapAuthTest.kt:747` | `b5cce2ab6580` |
| generic_secret_assignment | `apps/android/app/src/test/java/ai/openclaw/app/GatewayBootstrapAuthTest.kt:1873` | `3a954a431e86` |
| generic_secret_assignment | `apps/android/app/src/test/java/ai/openclaw/app/NodeForegroundServiceTest.kt:331` | `6cc3b57f875d` |
| generic_secret_assignment | `apps/android/app/src/test/java/ai/openclaw/app/NodeForegroundServiceTest.kt:364` | `6cc3b57f875d` |
| generic_secret_assignment | `apps/android/app/src/test/java/ai/openclaw/app/NodeForegroundServiceTest.kt:683` | `75dca09171fd` |
| generic_secret_assignment | `apps/android/app/src/test/java/ai/openclaw/app/NodeForegroundServiceTest.kt:859` | `535b8451d4cf` |
| generic_secret_assignment | `apps/android/app/src/test/java/ai/openclaw/app/NodeForegroundServiceTest.kt:1277` | `6cc3b57f875d` |
| generic_secret_assignment | `apps/android/app/src/test/java/ai/openclaw/app/NodeForegroundServiceTest.kt:1939` | `a50bb71186cb` |
| generic_secret_assignment | `apps/android/app/src/test/java/ai/openclaw/app/NodeForegroundServiceTest.kt:1985` | `389d99f84e9f` |
| generic_secret_assignment | `apps/android/app/src/test/java/ai/openclaw/app/chat/ChatFullMessageCancellationTest.kt:360` | `09ac1c336ebf` |
| generic_secret_assignment | `apps/android/app/src/test/java/ai/openclaw/app/gateway/GatewayRegistryStoreTest.kt:30` | `d7edf5af6b41` |
| generic_secret_assignment | `apps/android/app/src/test/java/ai/openclaw/app/gateway/GatewaySessionInvokeTest.kt:910` | `18a85b270f4e` |
| generic_secret_assignment | `apps/android/app/src/test/java/ai/openclaw/app/gateway/GatewaySessionInvokeTest.kt:1078` | `12bcb1be8976` |
| generic_secret_assignment | `apps/android/app/src/test/java/ai/openclaw/app/gateway/GatewaySessionInvokeTest.kt:1139` | `a895273eea4d` |
| generic_secret_assignment | `apps/android/app/src/test/java/ai/openclaw/app/gateway/GatewaySessionInvokeTest.kt:1145` | `12bcb1be8976` |
| generic_secret_assignment | `apps/android/app/src/test/java/ai/openclaw/app/gateway/GatewaySessionInvokeTest.kt:1625` | `12bcb1be8976` |
| generic_secret_assignment | `apps/android/app/src/test/java/ai/openclaw/app/ui/SettingsScreensContrastTest.kt:485` | `4258b3f9a91f` |
| generic_secret_assignment | `apps/android/app/src/test/java/ai/openclaw/app/ui/SettingsScreensContrastTest.kt:566` | `4258b3f9a91f` |
| generic_secret_assignment | `apps/android/app/src/test/java/ai/openclaw/app/ui/SettingsScreensContrastTest.kt:715` | `d4c3ebcd10f9` |
| generic_secret_assignment | `apps/android/app/src/test/java/ai/openclaw/app/ui/SidebarGatewayPickerTest.kt:378` | `b8abd910c410` |
| generic_secret_assignment | `apps/android/app/src/test/java/ai/openclaw/app/ui/WorkspaceFilesShareLayoutTest.kt:128` | `c33003a15880` |
| generic_secret_assignment | `apps/android/app/src/test/java/ai/openclaw/app/ui/chat/ChatFullMessageOwnershipLayoutTest.kt:167` | `09ac1c336ebf` |
| generic_secret_assignment | `apps/android/app/src/test/java/ai/openclaw/app/wear/NodeRuntimeWearProxyTest.kt:77` | `13ba34d7a721` |
| generic_secret_assignment | `apps/ios/Tests/ChatSendHydrationTests.swift:210` | `13ff1ce933b0` |
| generic_secret_assignment | `apps/ios/Tests/ChatSendHydrationTests.swift:270` | `9e978485399f` |
| generic_secret_assignment | `apps/ios/Tests/ChatTypingFocusTests.swift:277` | `13ff1ce933b0` |
| generic_secret_assignment | `apps/ios/Tests/ChatTypingFocusTests.swift:332` | `9e978485399f` |
| generic_secret_assignment | `apps/ios/Tests/GatewayAccessRestartTests.swift:203` | `08e64fa14724` |
| generic_secret_assignment | `apps/ios/Tests/GatewayAccessRestartTests.swift:205` | `992c62e8b877` |
| generic_secret_assignment | `apps/ios/Tests/GatewayConnectionControllerTests.swift:1019` | `d4c83ca2e3ec` |
| generic_secret_assignment | `apps/ios/Tests/GatewayConnectionControllerTests.swift:1242` | `177af8f35109` |
| generic_secret_assignment | `apps/ios/Tests/GatewayConnectionControllerTests.swift:1246` | `0a7beca87ca7` |
| generic_secret_assignment | `apps/ios/Tests/GatewayConnectionControllerTests.swift:1250` | `6686e853a012` |
| generic_secret_assignment | `apps/ios/Tests/GatewayConnectionControllerTests.swift:1262` | `d77b3519a8bf` |
| generic_secret_assignment | `apps/ios/Tests/GatewayConnectionControllerTests.swift:1263` | `a8eeabfea990` |
| generic_secret_assignment | `apps/ios/Tests/GatewayConnectionControllerTests.swift:1276` | `a92a42e8f651` |
| generic_secret_assignment | `apps/ios/Tests/GatewayConnectionControllerTests.swift:1314` | `a9c166a84862` |
| generic_secret_assignment | `apps/ios/Tests/GatewayConnectionControllerTests.swift:1318` | `2d987d8fbcc7` |
| generic_secret_assignment | `apps/ios/Tests/GatewayConnectionControllerTests.swift:1357` | `88456ec34271` |
| generic_secret_assignment | `apps/ios/Tests/GatewayConnectionControllerTests.swift:1362` | `d7f903403de6` |
| generic_secret_assignment | `apps/ios/Tests/GatewayConnectionControllerTests.swift:1413` | `8bb2b35f8451` |
| generic_secret_assignment | `apps/ios/Tests/GatewayConnectionControllerTests.swift:2636` | `ecedc7aabc95` |

## Chamadas que exigem revisão

- `.github/actions/git-owner/owner.py:58` — python_eval_exec
- `apps/linux/ui/gateway-notice.js:24` — js_inner_html
- `apps/linux/ui/gateways.js:182` — js_inner_html
- `apps/linux/ui/window-chrome.js:156` — js_inner_html
- `extensions/browser/src/browser/pw-tools-core.interactions.actions.ts:307` — js_eval
- `extensions/browser/src/browser/pw-tools-core.interactions.content.ts:115` — js_eval
- `extensions/diffs/src/viewer-client.ts:115` — js_inner_html
- `extensions/discord/src/activities/shell.ts:29` — js_inner_html
- `extensions/mcp-relay/src/control-ui.ts:299` — js_inner_html

## Limitações
- Detecção por padrões; não substitui auditoria nem verificação de CVEs das dependências.


---

# Métricas de otimização — openclaw/openclaw

- Linhas de código: 12315630
- Blocos duplicados (janelas de 6 linhas): 1301
- Funções Python com 80+ linhas: 20

## Pares com mais duplicação

- `apps/ios/Tests/LocationServiceCallbackTests.swift` ↔ `apps/macos/Tests/OpenClawIPCTests/MacNodeLocationServiceTests.swift`: 49 blocos
- `apps/ios/Tests/IOSGatewayChatTransportTests.swift` ↔ `apps/macos/Tests/OpenClawIPCTests/MacGatewayChatTransportMappingTests.swift`: 42 blocos
- `apps/ios/Sources/Chat/IOSGatewayChatTransport.swift` ↔ `apps/macos/Sources/OpenClaw/WebChatSwiftUI.swift`: 30 blocos
- `apps/linux/tests/first_run.py` ↔ `apps/linux/tests/remote_connection_smoke.py`: 23 blocos
- `extensions/music-generation-providers.live.test.ts` ↔ `extensions/video-generation-providers.live.test.ts`: 22 blocos
- `apps/android/app/src/test/java/ai/openclaw/app/ui/SettingsScreensContrastTest.kt` ↔ `apps/android/app/src/test/java/ai/openclaw/app/ui/WorkspaceFilesShareLayoutTest.kt`: 18 blocos
- `apps/android/app/src/test/java/ai/openclaw/app/NodeForegroundServiceTest.kt` ↔ `apps/android/app/src/test/java/ai/openclaw/app/gateway/GatewaySessionCustomHeadersTest.kt`: 17 blocos
- `apps/android/app/src/test/java/ai/openclaw/app/chat/ChatControllerModelSelectionTest.kt` ↔ `apps/android/app/src/test/java/ai/openclaw/app/chat/ChatControllerPermissionSelectionTest.kt`: 16 blocos
- `apps/android/app/src/test/java/ai/openclaw/app/ui/ScreenTypographyLayoutTest.kt` ↔ `apps/android/app/src/testThirdParty/java/ai/openclaw/app/ui/SensitivePhoneCapabilitiesSettingsTest.kt`: 15 blocos
- `crates/openclaw-gateway-client/src/session.rs` ↔ `crates/openclaw-node-host/src/node.rs`: 15 blocos

## Funções longas

- `apps/linux/tests/gateway_switch.py` `exercise` — 297 linhas
- `apps/linux/tests/packaged_runtime_smoke.py` `main` — 222 linhas
- `apps/linux/tests/first_run.py` `main` — 183 linhas
- `.agents/skills/telegram-e2e-userbot/scripts/user-record.py` `run_scenario` — 171 linhas
- `apps/linux/tests/quick_chat.py` `exercise` — 162 linhas
- `apps/linux/tests/first_run.py` `exercise` — 158 linhas
- `apps/macos/scripts/audit-async-sleep-frames.py` `audit` — 150 linhas
- `apps/linux/tests/desktop_sharing.py` `exercise` — 125 linhas
- `apps/linux/tests/first_run.py` `drive` — 117 linhas
- `.agents/skills/telegram-e2e-userbot/scripts/user-record.py` `main` — 114 linhas
- `.agents/skills/telegram-e2e-userbot/scripts/user-record.py` `_events_for` — 114 linhas
- `apps/linux/tests/inline_browser.py` `open_native_menu` — 114 linhas
- `apps/linux/tests/gateway_switch.py` `exercise` — 105 linhas
- `.agents/skills/telegram-e2e-userbot/scripts/user-driver.py` `prepare_forum` — 103 linhas
- `.agents/skills/telegram-e2e-userbot/scripts/user-driver.py` `main` — 102 linhas
- `extensions/onnx/scripts/export-gliclass-instruct.py` `export` — 102 linhas
- `.agents/skills/telegram-e2e-userbot/scripts/user-record.test.py` `test_reply_barrier_binds_distinct_native_replies_before_advancing` — 101 linhas
- `apps/linux/tests/remote_connection_smoke.py` `drive` — 91 linhas
- `.agents/skills/telegram-e2e-userbot/scripts/user-driver.py` `authorize` — 87 linhas
- `.agents/skills/telegram-e2e-userbot/scripts/telegram-binding-forum.py` `prepare_owned_forum` — 85 linhas

