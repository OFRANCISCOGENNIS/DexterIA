# Avaliação de integração dos 11 repositórios de referência

Cada repositório foi importado e analisado **pela própria plataforma** (fluxo `analyze_repository`). Os
relatórios completos, com commit, evidências e limitações, estão em [`references/`](references/README.md).
Esta página registra a decisão de integração de cada um: **A** = referências e conhecimento,
**B** = adaptador, **C** = incorporação de código.

| Repositório | Licença (detectada) | Natureza (análise) | Estratégia | O que foi integrado |
|---|---|---|---|---|
| [codecrafters-io/build-your-own-x](https://github.com/codecrafters-io/build-your-own-x) | sem arquivo de licença | lista curada (Markdown) | A, só links | Tutoriais "construa do zero" indexados como `tutorial`. Sem licença explícita: armazenados **somente título e URL** |
| [sindresorhus/awesome](https://github.com/sindresorhus/awesome) | CC0-1.0 | lista curada | A | Índice de listas awesome como `tool`, com categoria e descrição |
| [public-apis/public-apis](https://github.com/public-apis/public-apis) | MIT | lista curada (tabelas) | A | Catálogo de APIs com categoria, autenticação, HTTPS e CORS, filtráveis na tela **APIs**. Disponibilidade **não** é verificada (aviso em cada item) |
| [freeCodeCamp/freeCodeCamp](https://github.com/freeCodeCamp/freeCodeCamp) | BSD-3-Clause | monorepo (plataforma + currículo) | referência | Analisado; o currículo é grande e acoplado à plataforma deles. Não foi ingerido. Próximo passo: extrair só títulos e links de desafios (metadados) |
| [EbookFoundation/free-programming-books](https://github.com/EbookFoundation/free-programming-books) | CC-BY-4.0 | lista curada | A | Livros e cursos (en, pt_BR, por linguagem e assunto) como `book`, com formato (PDF/HTML…) e atribuição. Nenhum livro é copiado |
| [openclaw/openclaw](https://github.com/openclaw/openclaw) | MIT | monorepo TS: assistente pessoal multicanal (Discord, Slack, WhatsApp…), com modelos e harness como plugins | referência | Ideias aproveitadas: ferramentas autorizadas por agente, estado e credenciais sob controle do usuário, relatórios de execução. Não há integração de código: é um produto *standalone* com runtime próprio (Node.js) e escopo de assistente pessoal |
| [donnemartin/system-design-primer](https://github.com/donnemartin/system-design-primer) | CC-BY-4.0 | conteúdo + notebooks | A | Referências de design de sistemas como `resource`. O prompt do Arquiteto pede escalabilidade, gargalos e riscos |
| [nilbuild/developer-roadmap](https://github.com/nilbuild/developer-roadmap) | **proprietária (uso pessoal)** | monorepo (site roadmap.sh) | A, só links | A licença proíbe reutilizar o conteúdo e permite compartilhar links: apenas **título e URL** dos roadmaps são indexados |
| [jwasham/coding-interview-university](https://github.com/jwasham/coding-interview-university) | CC-BY-SA-4.0 | lista de estudo | A | Materiais de algoritmos e estruturas de dados como `resource`, com atribuição |
| [morluto/rea](https://github.com/morluto/rea) | MIT | monorepo TS, servidor MCP + CLI | **B** | Adaptador para `rea analyze-javascript-application --json` (sem rede), executado pelo Engenheiro Reverso em repositórios JS/TS. Evidência `observed` → ✅ e `inferred` → 🔎. Provedores nativos (Ghidra/IDA/Hopper), Frida e captura de rede não foram integrados |
| [ruvnet/ruflo](https://github.com/ruvnet/ruflo) | MIT | monorepo TS (harness para Claude Code/Codex, MCP) | referência | Conceitos reimplementados em Python (ADR-003): decomposição por agentes especializados, contexto seletivo, memória por projeto separada da global, verificação antes da entrega, controle de custos. Nenhum código copiado |

## Verificações feitas em cada repositório

1. Estrutura, linguagens e diretórios (inventário do analisador)
2. README (resumo e mapa de seções) e documentação
3. Licença: detectada pelo texto do arquivo. Fontes sem licença permissiva são indexadas só com links
4. Dependências e frameworks declarados em manifestos (`package.json`, `pyproject.toml`, `requirements*.txt`, `go.mod`, `Cargo.toml`)
5. Arquitetura: tipo provável (🔎), pontos de entrada, rotas e workflows de CI
6. Riscos de segurança: padrões de segredos (valores nunca armazenados) e chamadas perigosas
7. Adaptador quando útil (REA). Origem e commit registrados em cada fonte da base de conhecimento

## Critérios da integração do Ruflo (seção 11 do pedido)

| Critério | Situação |
|---|---|
| Distribuir uma solicitação entre ≥3 agentes | Fluxo `mission`: research, architect, orchestrator, developer, qa, security, optimizer e documentation |
| Compartilhar resultados e respeitar dependências | Cada etapa recebe só o `result` das dependências; o despachante só libera etapas com dependências concluídas |
| Acompanhar pelo painel | Telas **Tarefas**, **Agentes** e **Automações**, com atualização periódica, logs, tokens e custo por execução |
| Tratar erros sem parar o fluxo inteiro | Tentativas limitadas; etapas opcionais falham sem bloquear; o relatório final executa sempre |
| Resultado final verificável | Artefato de entrega com etapas, arquivos, diff, testes executados (log completo) e problemas conhecidos |
| Respeitar permissões e aprovações | Portão humano antes de gerar ou executar código; agentes não alteram permissões nem a configuração |
| Testes automatizados | `tests/test_orchestration.py` (missão completa, rejeição, cancelamento, retomada, prioridade, orçamento) |
