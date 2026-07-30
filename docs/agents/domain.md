# Domain docs

Este repo é **single-context**. Os documentos de domínio moram em `docs/`.

## Onde está o quê

| Documento | Papel |
| --- | --- |
| `docs/agents/` | Como um agente trabalha **neste** repo. |
| `docs/adr/` | Decisões de arquitetura deste repo, quando houver. |

## O que é o overpower

CLI Python, publicada no PyPI, que instala **AI Frameworks** curados num repositório ou na máquina.

Invocação canônica: `uvx overpower <comando>`.

## Vocabulário

Termos que aparecem em issues, specs e código, e que significam algo específico aqui:

- **AI Framework**: um corpo nomeado e coerente de equipamento de agente vindo de uma **origem única**, que se instala como **unidade**. Pode conter skills, comandos e configuração de MCP. `mattpocock/skills`, `github/spec-kit`, BMAD e GSD são exemplos. É a unidade de instalação do overpower — não o arquivo, não a skill isolada.
- **Artefato**: um item concreto dentro de um AI Framework — um diretório de skill, um arquivo de comando, uma entrada de configuração de MCP. Artefato não se instala sozinho; chega pelo framework que o contém.
- **Catálogo**: o conjunto de AI Frameworks que o overpower conhece e sabe instalar. Curado, não aberto.
- **Perfil**: uma composição nomeada de AI Frameworks aplicável de uma vez. Se perfil e framework são um nível ou dois é decisão em aberto no mapa.
- **Runtime**: o consumidor do equipamento instalado — Claude Code, Cursor, Codex, Copilot. Cada um tem seu próprio caminho e formato.
- **Aterrissagem**: onde o overpower escreve — no repositório corrente ou na máquina (`~/`).
- **Curadoria**: o ato de decidir o que entra no catálogo. Restrita, por design; o overpower não é marketplace.

## Axiomas

Posições travadas na cartografia do mapa. Não se renegociam sem reabrir o mapa.

1. **Autocontido.** O overpower **nunca invoca instalador de terceiro** — nada de `npx`, nada de subprocesso alheio. Todo buscar-e-posicionar é código Python do próprio overpower. A razão é ambiental: o alvo de replicação é um ambiente corporativo sem esse ferramental.
2. **Sem estado no alvo.** O overpower não grava manifesto proprietário no repositório alvo. Num repo git, **o git é o manifesto**: `git status` e `git diff` respondem o que a ferramenta escreveu com fidelidade maior que qualquer lockfile.
3. **Ferramenta genérica.** O overpower não é ferramenta da org `panlabs-tech`. A decisão de distribuição de skills registrada em `panlabs-tech/skills` **não o vincula**.
4. **Só equipamento de AI.** Anatomia de repositório — `pyproject.toml`, CI, portões de commit, layout de testes — está **fora de escopo**. Esse território é do `uv init`, `copier` e `cookiecutter`.
5. **Conteúdo vendorizado.** O conteúdo dos frameworks viaja **dentro do wheel**, com o risco de redistribuição aceito conscientemente. Um repo remoto de assets existe como *override*, não como padrão.

## Registro histórico

O raciocínio que produziu estas posições está no mapa de wayfinding deste repo e nos seus tickets de decisão. Quando uma posição parecer arbitrária, o porquê está num deles.
