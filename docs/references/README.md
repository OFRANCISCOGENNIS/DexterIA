# Repositórios de referência — engenharia reversa pelo GENISIA AI

Estes relatórios foram produzidos **pela própria plataforma**: o script `scripts/analyze_references.py` usa a API
para importar cada repositório público, executar o fluxo `analyze_repository` (importação → análise estática + REA
→ segurança → otimização → relatório) e, nos catálogos, o fluxo `ingest_knowledge`, que alimenta a base de
conhecimento. Nenhum código dos repositórios foi executado. A decisão de integração de cada um está em
[`../integration-evaluation.md`](../integration-evaluation.md).

**Principais conclusões**

- 7 catálogos indexados, com cerca de 8.200 itens na base de conhecimento. Só metadados e links foram armazenados, cada item com fonte e licença.
- **developer-roadmap** tem licença proprietária (uso pessoal), e **build-your-own-x** não tem arquivo de licença. Dos dois, foram indexados apenas títulos e links.
- **REA** (MIT) virou um adaptador: a CLI `rea` gerou os grafos de JS/TS de freeCodeCamp, developer-roadmap, REA e Ruflo. Veja a seção “Grafo JavaScript (REA)” de cada relatório. No OpenClaw (cerca de 58 mil arquivos), o REA excedeu o limite de 900 s; esse relatório traz só a análise estática própria.
- **Ruflo** e **OpenClaw** (ambos MIT, Node.js) serviram de referência arquitetural. Os conceitos foram reimplementados em Python, sem copiar código.

<!-- tabela -->
## Resumo por repositório

Relatórios gerados pelo próprio GENISIA AI (fluxo `analyze_repository`), com análise estática do commit indicado. ✅ = comprovado por arquivo; 🔎 = hipótese. Nenhum código dos repositórios foi executado.

| Repositório | Papel | Tipo provável | Linguagens | Licença | Arquivos | Itens indexados | Relatório |
|---|---|---|---|---|---|---|---|
| [codecrafters-io/build-your-own-x](https://github.com/codecrafters-io/build-your-own-x) | Laboratório de construção do zero (tutoriais) | lista curada / catálogo de links | Markdown | - | 4 | 359 | [codecrafters-io-build-your-own-x.md](codecrafters-io-build-your-own-x.md) |
| [sindresorhus/awesome](https://github.com/sindresorhus/awesome) | Catálogo de ferramentas e recursos | lista curada / catálogo de links | Markdown, YAML, Shell | CC0-1.0 | 23 | 671 | [sindresorhus-awesome.md](sindresorhus-awesome.md) |
| [public-apis/public-apis](https://github.com/public-apis/public-apis) | Catálogo de APIs | lista curada / catálogo de links | Python, Markdown, YAML | MIT | 23 | 2180 | [public-apis-public-apis.md](public-apis-public-apis.md) |
| [freeCodeCamp/freeCodeCamp](https://github.com/freeCodeCamp/freeCodeCamp) | Aprendizagem prática | repositório de conteúdo/documentação, monorepo, aplicação web (frontend), serviço backend/API, ferramenta de linha de comando | Markdown, JSON, TypeScript | BSD-3-Clause | 19687 | - | [freecodecamp-freecodecamp.md](freecodecamp-freecodecamp.md) |
| [EbookFoundation/free-programming-books](https://github.com/EbookFoundation/free-programming-books) | Biblioteca de livros e cursos gratuitos | lista curada / catálogo de links | Markdown, YAML, HTML | CC-BY-4.0 | 234 | 4292 | [ebookfoundation-free-programming-books.md](ebookfoundation-free-programming-books.md) |
| [openclaw/openclaw](https://github.com/openclaw/openclaw) | Assistentes que executam tarefas | monorepo, serviço backend/API, servidor/ferramenta MCP para agentes, ferramenta de linha de comando | TypeScript, Markdown, Swift | MIT | 58286 | - | [openclaw-openclaw.md](openclaw-openclaw.md) |
| [donnemartin/system-design-primer](https://github.com/donnemartin/system-design-primer) | Arquiteto de software assistido | lista curada / catálogo de links | Python, Markdown, Jupyter | CC-BY-4.0 | 139 | 157 | [donnemartin-system-design-primer.md](donnemartin-system-design-primer.md) |
| [nilbuild/developer-roadmap](https://github.com/nilbuild/developer-roadmap) | Planejador de evolução técnica | lista curada / catálogo de links, monorepo | Markdown, YAML, TypeScript | Proprietária (uso pessoal) | 11080 | 98 | [nilbuild-developer-roadmap.md](nilbuild-developer-roadmap.md) |
| [jwasham/coding-interview-university](https://github.com/jwasham/coding-interview-university) | Ciência da computação e algoritmos | lista curada / catálogo de links | Markdown, YAML | CC-BY-SA-4.0 | 46 | 431 | [jwasham-coding-interview-university.md](jwasham-coding-interview-university.md) |
| [morluto/rea](https://github.com/morluto/rea) | Engenharia reversa assistida (adaptador) | monorepo, servidor/ferramenta MCP para agentes, ferramenta de linha de comando | TypeScript, JavaScript, Markdown | MIT | 4778 | - | [morluto-rea.md](morluto-rea.md) |
| [ruvnet/ruflo](https://github.com/ruvnet/ruflo) | Orquestração multiagente (referência) | monorepo, aplicação web (frontend), serviço backend/API, servidor/ferramenta MCP para agentes, ferramenta de linha de comando | TypeScript, Markdown, JavaScript | MIT | 7981 | - | [ruvnet-ruflo.md](ruvnet-ruflo.md) |
<!-- /tabela -->
