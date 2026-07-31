# Domain docs

Este repo é **single-context**. Os documentos de domínio moram em `docs/`.

## Onde está o quê

| Documento | Papel |
| --- | --- |
| `docs/agents/` | Como um agente trabalha **neste** repo. |
| `docs/adr/` | Decisões de arquitetura deste repo. |

## O que é o overpower

CLI Python, publicada no PyPI, que instala equipamento de agente curado num repositório ou na máquina.

Invocação canônica: `uvx overpower <comando>`.

## Vocabulário

Termos que aparecem em issues, specs e código, e que significam algo específico aqui. O modelo tem **três unidades instaláveis** — artefato, AI Framework e bundle — e elas não são níveis de uma mesma hierarquia: escolhem-se de forma independente.

### As unidades

- **Artefato**: um átomo de equipamento, curado individualmente — uma skill, um comando, um agente, um servidor MCP, um hook. Vive no **pool**, instala-se sozinho, e é o único item que um bundle pode listar.
- **AI Framework**: um corpo **autocontido** de equipamento vindo de uma origem única de mercado (`mattpocock/skills`, `github/spec-kit`, BMAD, `obra/superpowers`), recortado pela curadoria do overpower e instalado **inteiro**. Seus artefatos vivem dentro do contexto do próprio framework — não estão no pool e não são pedíveis sozinhos.
- **Bundle**: uma composição nomeada de artefatos do pool para um **contexto de atuação** no repositório (`api-python`). Origem mista, incluindo criação própria. É um manifesto: aponta nomes, não carrega conteúdo.

### Onde o conteúdo mora

- **Pool**: o conjunto dos artefatos curados individualmente, organizado por tipo. É de onde saem tanto a instalação individual quanto os bundles.
- **Catálogo**: o conjunto de artefatos, frameworks e bundles que o overpower conhece e sabe instalar. Curado, não aberto.
- **Procedência**: de onde um conteúdo veio — a origem **e o modo de obtenção**, embutido no wheel ou remoto. É atributo do catálogo, nunca do alvo.
- **Curadoria**: o ato de decidir o que entra no catálogo e — para artefatos — o que é recortado a ponto de virar átomo do pool.

### Como o conteúdo aterrissa

- **Artefato de cópia**: skill, comando, agente. Chega como arquivo ou árvore que não existia. Colisão é de **caminho**; no `git status` aparece como arquivo novo.
- **Artefato de enxerto**: servidor MCP, hook. Chega como entrada **dentro de um documento que o usuário também edita** (`.mcp.json`, `.claude/settings.json`). Colisão é de **chave**; no `git diff` aparece como alteração num arquivo do usuário.
- **Runtime**: o consumidor do equipamento instalado — Claude Code, Cursor, Codex, Copilot. Cada um tem caminho próprio e, para enxertos, **formato** próprio.
- **Aterrissagem**: onde o overpower escreve — no repositório corrente ou na máquina (`~/`).

### Termos aposentados

- **Perfil** — fora do vocabulário. Seria "composição nomeada de AI Frameworks", e no modelo atual **não existe composição de frameworks em lugar nenhum**. A palavra também está ocupada upstream com outro sentido: o `.gsd-profile` do GSD e o `profiles/` do agent-os.

## Regras do modelo

Consequências do vocabulário acima, decididas em [Modelo de domínio: AI Framework, perfil e artefato](https://github.com/panlabs-tech/overpower/issues/7).

1. **Framework instala-se inteiro.** Não existe instalação parcial de framework. Quem quer três skills instala três artefatos, ou um bundle — não um recorte de framework.
2. **Framework não aninha e não entra em bundle.** Framework é escolha de **método**; bundle é escolha de **equipamento**. Um bundle pode *recomendar* um framework em prosa; nunca incluí-lo. Ver [ADR 0002](../adr/0002-bundle-nao-compoe-framework.md).
3. **Artefato de pool e artefato de framework são entidades distintas**, mesmo com bytes idênticos. O do pool foi curado como átomo; o do framework é parte de um corpo acoplado. A duplicação no wheel é deliberada — ver [ADR 0001](../adr/0001-frameworks-autocontidos-e-pool-apartado.md).
4. **O contrato de um artefato de enxerto é lógico, não literal.** Descreve transporte, comando ou URL, e **slots** de segredo — nunca valores — e o overpower **renderiza** para o formato de cada runtime.
5. **Entradas de catálogo não têm eixo de versão.** A versão do overpower **é** a versão do catálogo embutido; conteúdo vindo do repositório remoto de assets é fresco e não reprodutível, por decisão. O modo de obtenção faz parte da identidade do resultado, e por isso `uvx overpower@latest` é requisito de correção, não estilo de README.
6. **No alvo não aterrissa nada além do conteúdo da árvore dos artefatos.** "Framework instalado" não é entidade, é efeito: o repositório tem arquivos e não sabe de onde vieram — ver [ADR 0003](../adr/0003-sem-atribuicao-no-alvo.md).

## Axiomas

Posições travadas na cartografia do mapa. Não se renegociam sem reabrir o mapa.

1. **Autocontido.** O overpower **nunca invoca instalador de terceiro** — nada de `npx`, nada de subprocesso alheio. Todo buscar-e-posicionar é código Python do próprio overpower. A razão é ambiental: o alvo de replicação é um ambiente corporativo sem esse ferramental.
2. **Sem estado no alvo.** O overpower não grava manifesto proprietário no repositório alvo. Num repo git, **o git é o manifesto**: `git status` e `git diff` respondem o que a ferramenta escreveu com fidelidade maior que qualquer lockfile.
3. **Ferramenta genérica.** O overpower não é ferramenta da org `panlabs-tech`. A decisão de distribuição de skills registrada em `panlabs-tech/skills` **não o vincula**.
4. **Só equipamento de AI.** Anatomia de repositório — `pyproject.toml`, CI, portões de commit, layout de testes — está **fora de escopo**. Esse território é do `uv init`, `copier` e `cookiecutter`.
5. **Conteúdo vendorizado.** O conteúdo dos frameworks viaja **dentro do wheel**, com o risco de redistribuição aceito conscientemente. Um repo remoto de assets existe como *override*, não como padrão.

## Registro histórico

O raciocínio que produziu estas posições está no mapa de wayfinding deste repo e nos seus tickets de decisão. Quando uma posição parecer arbitrária, o porquê está num deles.
