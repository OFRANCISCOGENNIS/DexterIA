# CLAUDE.md — DexterIA / GENISIA AI

Plataforma de desenvolvimento assistida por agentes: requisitos → plano (IA) → aprovação humana → código (IA) →
testes em sandbox → entrega; mais análise estática de repositórios e base de conhecimento. Visão geral e estado do
MVP no [README](README.md); arquitetura em [docs/architecture.md](docs/architecture.md); decisões em
[docs/decisions.md](docs/decisions.md).

## Estrutura

- `apps/api/` — backend FastAPI (pacote `genisia`)
  - `routers/` endpoints REST · `schemas.py` Pydantic · `models.py` SQLAlchemy 2 · `migrations/` Alembic
  - `orchestrator/` motor de fluxos (`engine.py`: `create_workflow`, `tick`, `execute_step`, `recover`) modelos (`workflows.py`) e gatilhos agendados (`scheduler.py`)
  - `agents/` agentes (`registry.py` lista todos; contrato em `base.py`: `Agent.run(ctx) -> dict`)
  - `execution/` workspace Git por projeto (`workspace.py`) e sandbox (`sandbox.py`)
  - `analysis/` analisador estático, importação segura, adaptador REA · `knowledge/` ingestão, busca e trilhas de aprendizagem (`learning.py`)
  - `ai/providers.py` provedor Anthropic, preços e saída estruturada
- `apps/web/` — Next.js 16 + React 19 + Tailwind 4 (App Router; páginas em `app/(app)/`, componentes em `components/`)
- `scripts/analyze_references.py` — usa a API para analisar os 11 repositórios de referência → `docs/references/`
- `infrastructure/docker/sandbox.Dockerfile` — imagem do backend docker do sandbox

## Comandos

```bash
# Backend
cd apps/api
pip install -r requirements-dev.txt
python3 -m pytest -q                                   # SQLite (padrão)
TEST_DATABASE_URL=postgresql://genisia:genisia@localhost:5432/genisia_test python3 -m pytest -q
uvicorn genisia.main:app --port 8000                   # aplica migrações e inicia o orquestrador
alembic revision --autogenerate -m "descricao"         # nova migração após alterar models.py

# Frontend
cd apps/web
npm install
npm run typecheck && npm run build
npm run dev                                            # http://localhost:3000; /api/* é encaminhado ao backend
```

O CI (`.github/workflows/ci.yml`) roda os testes em SQLite e PostgreSQL, constrói a imagem do sandbox e faz o
typecheck e o build do frontend. Rode os mesmos comandos antes de fazer push.

## Convenções

- Textos de interface, mensagens de erro da API, logs e docs em **português do Brasil**. Identificadores no código em inglês.
- Comentários escassos, só para explicar o porquê (decisões de segurança, limitações).
- Toda alteração de esquema exige uma migração Alembic; a aplicação as aplica na inicialização.
- Novo agente: subclasse de `Agent` em `agents/`, registrada em `agents/registry.py`, usada por uma etapa em
  `orchestrator/workflows.py`. Ele recebe somente os resultados das etapas de que depende (`ctx.inputs`).
- Respostas de IA sempre por um modelo Pydantic via `ctx.ai(...)`, que valida e controla o orçamento do projeto.
- Erros de agente: `NonRetryableError` (configuração ou entrada inválida), `AgentError` (pode repetir), `AgentSkip`
  (não se aplica), `ApprovalRequired` (ação sensível).

## Regras que não podem ser quebradas

- **Nunca simule resultados de IA ou de ferramentas.** Sem provedor configurado, a etapa falha com mensagem explícita.
  O `FakeProvider` (`tests/fakes.py`, identificado como `fake-test`) existe só para testes.
- **Código gerado nunca roda no processo do backend.** Use sempre `run_in_sandbox` (sem rede por padrão).
- Gatilhos agendados só podem iniciar fluxos sem geração de código por IA (`SCHEDULABLE_WORKFLOWS`).
- Ações sensíveis (executar o plano, excluir projeto ou repositório, liberar rede) exigem um registro `Approval`.
- Nunca grave segredos em texto puro: use `encrypt_secret` e passe logs por `redact()`. A varredura de segredos guarda só impressões digitais.
- Caminhos vindos de agentes ou usuários passam por `normalize_relpath`; importação Git só via `validate_git_url`.
- Catálogos de fontes sem licença permissiva são indexados só com título e link (`PERMISSIVE_LICENSES`).
- Não marque um teste como ignorado nem o desabilite para o CI passar; os testes de sandbox usam `skipif` só quando não há isolamento disponível.

## Notas de ambiente

- O sandbox escolhe `namespace` (unshare + usuário 65534, se root) ou `docker` (imagem `GENISIA_SANDBOX_IMAGE`).
  Se o diretório de dados não for atravessável por outros usuários, defina `GENISIA_SANDBOX_DIR=/var/tmp/genisia-sandbox`.
- O backend lê apenas variáveis de ambiente (referência em `.env.example`); ele não carrega `.env` sozinho.
- `apps/api/data/` (banco SQLite, workspaces, clones) é estado local e está no `.gitignore`. Os testes coletam somente `tests/` (`pytest.ini`).
