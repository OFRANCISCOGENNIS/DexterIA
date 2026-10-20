# DexterIA · GENISIA AI

Plataforma de desenvolvimento de software assistida por agentes especializados. Ela transforma requisitos em
planos, código e testes executados em ambiente isolado, analisa repositórios autorizados (engenharia reversa
estática) e mantém uma base de conhecimento com fontes verificáveis. Toda ação sensível passa por
aprovação humana.

> Este repositório contém o **MVP funcional** do GENISIA AI. O que está implementado, o que depende de
> credenciais e o que ainda não existe está descrito em [Estado do MVP](#estado-do-mvp).

## O que funciona hoje

| Área | Funcionalidade |
|---|---|
| Projetos e Studio | Criar projetos, registrar requisitos, workspace Git por projeto, árvore de arquivos, editor com commit, histórico e diffs |
| Orquestrador multiagente | Fluxos em grafo com dependências, contexto seletivo entre agentes, tentativas limitadas, etapas opcionais, cancelamento, retomada após reinício |
| Agentes | Orquestrador, Arquiteto (IA), Desenvolvedor (IA), QA, Segurança, Otimização, Documentação, Pesquisador, Engenheiro Reverso, Integrações |
| Missão completa | Pesquisa → plano por IA → **sua aprovação** → código por IA → testes no sandbox com correção automática → segurança/otimização → relatório de entrega |
| Execução isolada | Testes rodam fora do backend: sem rede, usuário sem privilégios, limites de CPU/memória/tempo, cópia descartável |
| Engenharia reversa | Importação Git (HTTPS), diretório local autorizado ou ZIP; inventário, tecnologias, dependências, pontos de entrada, rotas, licença, segredos, duplicação; ✅ comprovado vs 🔎 hipótese; adaptador para a CLI do [REA](https://github.com/morluto/rea) |
| Base de conhecimento | Ingestão de catálogos (awesome, public-apis, free-programming-books…), busca full-text no PostgreSQL, filtros (tipo, categoria, autenticação de APIs), recomendações por projeto, memória do projeto com exportação e exclusão |
| Governança | Autenticação JWT, autorização por projeto, auditoria, aprovações, limite de requisições, orçamento de IA por projeto, segredos cifrados |

Os relatórios dos 11 repositórios de referência, gerados pela própria plataforma, estão em
[`docs/references/`](docs/references/README.md).

## Requisitos

- Linux (o sandbox usa `unshare`/`setpriv` do util-linux); Python 3.12+; Node.js 22+; Git
- PostgreSQL 14+ (recomendado). Sem ele, o backend usa SQLite automaticamente.
- Opcional: chave da Anthropic (`ANTHROPIC_API_KEY`) para os agentes de IA; CLI `rea` (`npm install -g rea-agents`)

## Como executar localmente

```bash
# 1. Banco (ou use um PostgreSQL existente; `docker compose up -d postgres` se tiver Docker)
sudo -u postgres psql -c "CREATE USER genisia WITH PASSWORD 'genisia' CREATEDB;" -c "CREATE DATABASE genisia OWNER genisia;"

# 2. Backend
cd apps/api
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL=postgresql://genisia:genisia@localhost:5432/genisia
export ANTHROPIC_API_KEY=...            # opcional; também pode ser cadastrada na tela Configurações
uvicorn genisia.main:app --port 8000    # aplica as migrações e inicia o orquestrador

# 3. Frontend (outro terminal)
cd apps/web
npm install
npm run build && npm start              # ou: npm run dev
```

Acesse http://localhost:3000, crie uma conta e use **Projetos → Novo projeto → Usar exemplo → Missão completa**.
A documentação da API (OpenAPI) fica em http://localhost:8000/docs.

As variáveis disponíveis estão em [`.env.example`](.env.example). O backend lê variáveis de ambiente (use
`set -a; source .env; set +a`).

> **Sandbox:** em Linux com namespaces, o backend padrão é `namespace`. Sem namespaces (ex.: runners do GitHub), use Docker:
> `docker build -t genisia-sandbox:latest -f infrastructure/docker/sandbox.Dockerfile infrastructure/docker`.
> Os dois backends são exercitados pelos testes (local e CI).
>
> **Permissões:** com o backend rodando como root, o código testado roda como o usuário 65534.
> Esse usuário precisa atravessar o diretório do sandbox. Se algum diretório ancestral de `apps/api/data` não
> tiver permissão `o+x`, defina `GENISIA_SANDBOX_DIR=/var/tmp/genisia-sandbox`. O estado do sandbox aparece
> em **Configurações**.

## Testes

```bash
cd apps/api
python3 -m pytest -q                                   # SQLite
TEST_DATABASE_URL=postgresql://genisia:genisia@localhost:5432/genisia_test python3 -m pytest -q   # PostgreSQL

cd ../web && npm run typecheck && npm run build
```

São 45 testes de backend. Eles cobrem autenticação, isolamento entre usuários, o fluxo completo de missão
(plano → aprovação → código → testes que falham → correção automática → aprovação nos testes), rejeição do
plano, falta de provedor de IA, orçamento, cancelamento, retomada, isolamento do sandbox (rede, tempo,
leitura de segredos), análise de repositório com cache por commit, ingestão e busca na base de conhecimento,
validação de URLs (SSRF), *zip-slip* e caminhos inseguros. Nos testes, a IA é substituída por um provedor
determinístico identificado como `fake-test`.

## Reanalisar os repositórios de referência

```bash
# com a API rodando
python3 scripts/analyze_references.py --email voce@example.com --password 'sua-senha'
```

O script usa apenas a API pública da plataforma: registra os repositórios, executa `analyze_repository` e
`ingest_knowledge` e grava os relatórios em `docs/references/`.

## Estado do MVP

**Implementado e verificado por testes:** todos os itens da tabela "O que funciona hoje".

**Depende de credencial:** os agentes Arquiteto e Desenvolvedor (e a revisão arquitetural por IA de
repositórios) precisam de `ANTHROPIC_API_KEY` ou de uma chave cadastrada. Sem ela, essas etapas falham com
uma mensagem explícita, e nenhuma resposta é simulada. O provedor real foi testado com respostas simuladas
do SDK, mas **não foi executado contra a API real neste ambiente**, porque não havia chave disponível.

**Ainda não implementado:**
- OAuth/GitHub App para repositórios privados (hoje: HTTPS público, diretório local autorizado ou ZIP)
- Teste de endpoints das APIs do catálogo e geração de clientes HTTP
- Gatilhos agendados no Centro de Automação (os fluxos são iniciados manualmente ou via API)
- Trilhas e exercícios com avaliação automatizada (o módulo de aprendizagem hoje é um catálogo pesquisável)
- Busca vetorial, Redis e workers distribuídos (ver [decisões](docs/decisions.md))

Documentação técnica: [arquitetura](docs/architecture.md) · [decisões (ADRs)](docs/decisions.md) ·
[avaliação de integração dos repositórios](docs/integration-evaluation.md).

---

## Visão original do DexterIA

Plataforma inteligente para análise, automação e otimização de código. Ela é capaz de replicar soluções,
desenvolver automações, criar agentes autônomos e aprimorar tecnologias para escalar processos e acelerar o
desenvolvimento de software.

- **Análise e engenharia reversa:** examinar estruturas, códigos e funcionalidades de sistemas existentes para compreender seu funcionamento e desenvolver soluções compatíveis.
- **Automação inteligente:** automatizar tarefas repetitivas e otimizar fluxos de trabalho.
- **Agentes autônomos:** agentes capazes de executar tarefas, utilizar ferramentas e tomar decisões dentro de objetivos e limites definidos.
- **Reprodução de soluções:** reconstruir funcionalidades com base em referências e sistemas analisados, respeitando as permissões e licenças aplicáveis.
- **Otimização de código:** identificar falhas, oportunidades de melhoria e possibilidades de ganho de desempenho.
- **Escalabilidade tecnológica:** estruturar soluções para facilitar sua expansão, manutenção e integração com novas tecnologias.

**Mais do que automatizar tarefas, o objetivo é desenvolver tecnologias capazes de analisar, executar e
aprender com resultados sob supervisão humana.**
