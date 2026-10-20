# Registro de decisões arquiteturais (ADRs)

## ADR-001 — Monólito modular em Python (FastAPI) + Next.js
**Contexto:** MVP precisa ser executável localmente, com poucas peças móveis.
**Decisão:** um backend FastAPI com módulos internos bem separados e um frontend Next.js que encaminha `/api/*`.
**Consequências:** implantação simples; módulos (agentes, sandbox, análise) podem virar serviços depois sem
mudar contratos HTTP.

## ADR-002 — Fila persistida no banco em vez de Redis/Celery
**Contexto:** o prompt pede filas "quando necessário" e retomada após falhas.
**Decisão:** o estado das tarefas fica nas tabelas `tasks`/`agent_runs`; um despachante reivindica etapas com
`UPDATE ... WHERE status='queued'` (atômico) e as executa em um pool de threads.
**Consequências:** zero dependências extras e retomada natural após reinício. Escala limitada a uma instância
do despachante; trocar por Redis + workers é uma mudança localizada em `orchestrator/engine.py`.

## ADR-003 — Ruflo como referência arquitetural, não como dependência
**Contexto:** Ruflo (ruvnet/ruflo, MIT) é um *harness* Node.js para Claude Code/Codex com servidor MCP,
centenas de ferramentas e plugins. O GENISIA é um serviço Python multiusuário.
**Decisão:** reimplementar no GENISIA apenas os conceitos úteis — decomposição do objetivo em etapas por
agente especializado, contexto seletivo entre etapas, memória por projeto separada da global, verificação
antes de entregar e controles de custo — sem copiar código.
**Consequências:** sem acoplamento a outro runtime; o motor é substituível pela interface `create_workflow`/`tick`.

## ADR-004 — REA via adaptador de linha de comando
**Contexto:** REA (morluto/rea, MIT) é um servidor MCP/CLI Node.js para engenharia reversa de binários,
apps JS/Electron, .NET e sites. Sua CLI `rea analyze-javascript-application <dir> --json` funciona sem
motores nativos e devolve evidências com estado `observed`/`inferred`.
**Decisão:** o analisador próprio (Python) cobre qualquer repositório; quando a CLI `rea` está instalada, o
Engenheiro Reverso a executa (sem rede) para repositórios JS/TS e anexa o resumo normalizado ao relatório.
Recursos nativos (Ghidra/Hopper/IDA, Frida, captura de rede) não foram integrados.
**Consequências:** o REA é opcional; sua ausência é exibida em Configurações e no relatório.

## ADR-005 — Catálogos como metadados (Estratégia A)
**Contexto:** awesome (CC0), public-apis (MIT), free-programming-books (CC BY 4.0), build-your-own-x,
coding-interview-university, system-design-primer, developer-roadmap.
**Decisão:** extrair apenas título, URL, descrição curta, categoria e arquivo de origem; registrar licença e
commit da fonte. Catálogos de repositórios Git públicos são conhecimento global; uploads e diretórios locais
ficam privados.
**Consequências:** nenhum conteúdo protegido é copiado; a atribuição fica visível em cada resultado.

## ADR-006 — Busca textual primeiro
**Decisão:** PostgreSQL FTS (`to_tsvector('simple')` + índice GIN, prefixo `:*`); SQLite usa correspondência
ponderada para desenvolvimento e testes. Busca vetorial fica para quando houver necessidade medida.

## ADR-007 — Sandbox com namespaces do Linux
**Contexto:** o ambiente de construção não tem daemon Docker; `unshare` e `setpriv` estão disponíveis.
**Decisão:** backend `namespace` por padrão (rede desabilitada, usuário 65534, rlimits, cópia descartável);
backend `docker` selecionável; backend `process` só por configuração explícita.

## ADR-008 — Saída estruturada da IA validada por Pydantic
**Decisão:** cada agente de IA declara um modelo Pydantic; o provedor envia o JSON Schema fechado
(`output_config.format`) e valida a resposta. Recusas (`stop_reason=refusal`), truncamento e JSON inválido
viram erros explícitos. O fallback de recusas do servidor (`fallbacks: "default"`) fica ligado por padrão
(`GENISIA_AI_REFUSAL_FALLBACKS`).
**Consequências:** nenhum resultado de IA é aceito sem validação; testes usam um provedor de teste
identificado como `fake-test`, nunca apresentado como IA real.
