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
- **Catálogo**: o conjunto de artefatos, frameworks e bundles que o overpower conhece e sabe instalar. Curado, não aberto — e **não é um registro**: o catálogo embutido *é* a árvore de `content/`, descoberta olhando. Ver a regra 8 e a [ADR 0006](../adr/0006-a-arvore-e-o-catalogo.md).
- **Fonte remota** (`--from <url>`): um repositório **do GitHub** que não é o do overpower, apontado pelo usuário na linha de comando. A URL é **raiz de busca**, não endereço — raiz do repo, subpasta ou a pasta do artefato dão o mesmo resultado. Qualquer URL do GitHub funciona, sem cadastro, e o critério de curadoria **não se aplica**: ele governa o que entra no wheel, e `--from` é pedido explícito de quem instala. Com `--from`, **só** o remoto é consultado. **A obtenção é `git` como transporte, com fallback tarball puro-Python anônimo** — decidido em [Busca remota](https://github.com/panlabs-tech/overpower/issues/25), que também fixou que outros forges estão fora do escopo.
- **Procedência**: de onde um conteúdo veio — a origem **e o modo de obtenção**, embutido no wheel ou remoto. É atributo do catálogo, nunca do alvo.
- **Curadoria**: o ato de decidir o que entra no catálogo e — para artefatos — o que é recortado a ponto de virar átomo do pool.

### Como o conteúdo aterrissa

- **Artefato de cópia**: skill, comando, agente. Chega como arquivo ou árvore que não existia. Colisão é de **caminho**; no `git status` aparece como arquivo novo.
- **Artefato de enxerto**: servidor MCP, hook. Chega como entrada **dentro de um documento que o usuário também edita** (`.mcp.json`, `.claude/settings.json`). Colisão é de **chave**; no `git diff` aparece como alteração num arquivo do usuário.
  - Os dois não são simétricos, e o layout depende disso: **MCP é só contrato**, sem árvore a vendorizar; **hook é contrato *e* árvore** — no `obra/superpowers`, `run-hook.cmd` e `session-start` são executáveis que aterrissam, enquanto `hooks.json` e `hooks-cursor.json` são a mesma declaração em formato diferente por runtime, e nunca aterrissam como arquivo. Medido em [Onde os assets vivem e como entram no wheel](https://github.com/panlabs-tech/overpower/issues/11).
- **Runtime**: o consumidor do equipamento instalado — Claude Code, Cursor, Codex, Copilot, Devin e outros. Cada um tem caminho próprio e, para enxertos, **formato** próprio. **São 76**, com **55 caminhos de projeto distintos**, e a tabela é transcrita do `src/agents.ts` do [`vercel-labs/skills`](https://github.com/vercel-labs/skills) (MIT, com atribuição) em vez de levantada por medição — decidido em [Seleção de runtime alvo](https://github.com/panlabs-tech/overpower/issues/18). **Não existe caminho único que cubra todos**: medido, o Claude Code 2.1.223 não lê `.agents/skills/` e o Codex não lê `.claude/skills/`. O que **não** é herdado do `npx skills` é a escrita — ver [ADR 0008](../adr/0008-a-tela-e-herdada-a-escrita-nao.md). A tabela mora em `src/overpower/runtimes.py`, transcrita do commit `a4d243c` (`v1.5.22`) com atribuição no `NOTICE`, e a transcrição em [Tabela de caminhos de runtime](https://github.com/panlabs-tech/overpower/issues/27) corrigiu três coisas que a leitura anterior não tinha visto: **caminho global não é universal** — `eve` e `promptscript` declaram `globalSkillsDir: undefined`, então **74 dos 76** têm destino global e o escopo global tem de **recusar** os outros dois em vez de inventar caminho, o que faz o conjunto que `--runtime` aceita ser **função do escopo** ([ADR 0009](../adr/0009-o-conjunto-de-runtime-e-funcao-do-escopo.md)); os globais distintos são **66**, não 68, porque o número anterior contava `undefined` como valor e contava duas grafias do mesmo `~/.agents/skills`; e o **VS Code não tem linha na tabela**, embora seja um dos cinco runtimes que este mapa mediu em fonte primária — em projeto ele é alcançado de carona pelo `.agents/skills` de outros 19, em global não é alcançável e **não é nomeável**.
- **Aterrissagem**: onde o overpower escreve — no repositório corrente ou na máquina (`~/`).

### Termos aposentados

- **Perfil** — fora do vocabulário. Seria "composição nomeada de AI Frameworks", e no modelo atual **não existe composição de frameworks em lugar nenhum**. A palavra também está ocupada upstream com outro sentido: o `.gsd-profile` do GSD e o `profiles/` do agent-os.

## Regras do modelo

Consequências do vocabulário acima. As seis primeiras foram decididas em [Modelo de domínio: AI Framework, perfil e artefato](https://github.com/panlabs-tech/overpower/issues/7); a sétima em [Integridade de referência cruzada entre artefatos do pool](https://github.com/panlabs-tech/overpower/issues/16); a oitava em [Formato do catálogo](https://github.com/panlabs-tech/overpower/issues/10).

1. **Framework instala-se inteiro.** Não existe instalação parcial de framework. Quem quer três skills instala três artefatos, ou um bundle — não um recorte de framework.
2. **Framework não aninha e não entra em bundle.** Framework é escolha de **método**; bundle é escolha de **equipamento**. Um bundle pode *recomendar* um framework em prosa; nunca incluí-lo. Ver [ADR 0002](../adr/0002-bundle-nao-compoe-framework.md).
3. **Artefato de pool e artefato de framework são entidades distintas**, mesmo com bytes idênticos. O do pool foi curado como átomo; o do framework é parte de um corpo acoplado. A duplicação no wheel é deliberada — ver [ADR 0001](../adr/0001-frameworks-autocontidos-e-pool-apartado.md).
4. **O contrato de um artefato de enxerto é lógico, não literal.** Descreve transporte, comando ou URL, e **slots** de segredo — nunca valores — e o overpower **renderiza** para o formato de cada runtime.
5. **Entradas de catálogo não têm eixo de versão.** A versão do overpower **é** a versão do catálogo embutido; conteúdo vindo do repositório remoto de assets é fresco e não reprodutível, por decisão. O modo de obtenção faz parte da identidade do resultado, e por isso `uvx overpower@latest` é requisito de correção, não estilo de README.
6. **No alvo não aterrissa nada além do conteúdo da árvore dos artefatos.** "Framework instalado" não é entidade, é efeito: o repositório tem arquivos e não sabe de onde vieram — ver [ADR 0003](../adr/0003-sem-atribuicao-no-alvo.md).
7. **Não existe dependência entre artefatos.** O conteúdo de um artefato pode mandar o agente invocar outro — medido, **8 das 25** skills promovidas do `mattpocock/skills` fazem isso, e a `wayfinder` sozinha nomeia quatro. O overpower **não declara, não valida, não avisa e não arrasta**: o comando é o contrato, e `install --skill wayfinder` escreve `wayfinder` e mais nada. Quem quer as outras pede as outras.
8. **A árvore é o catálogo, e o que o overpower escreve só carrega o que a árvore não pode saber — caminho, nunca.** O `install` e o `list` descobrem os artefatos embutidos olhando `content/pool/<tipo>/<nome>/` e `content/frameworks/<nome>/`. Registrar caminho é duplicação (o sistema de arquivos já sabe) e produz deriva silenciosa — medido: skill nova no disco sem entrada no catálogo fica **invisível**, sem aviso. Escrever descrição não é duplicação, porque não existe em lugar nenhum. Sobra um arquivo, e nele só entram bundle (não tem árvore, por definição) e a descrição de AI Framework (não tem `SKILL.md`). **Destino também não é campo de entrada**: é função de (tipo, runtime, escopo), logo tabela em código. Ver [ADR 0006](../adr/0006-a-arvore-e-o-catalogo.md). **E a função é parcial** — há par sem destino, e onde ela não é definida o par **não existe**: `eve` e `promptscript` não têm caminho global, logo `--runtime` aceita **76 valores em projeto e 74 em global**. Pedir um par inexistente é invocação válida com resposta negativa — **exit 3**, comando inteiro recusado antes de qualquer escrita, e o runtime nem aparece na tela naquele escopo. Ver [ADR 0009](../adr/0009-o-conjunto-de-runtime-e-funcao-do-escopo.md).

## Critério de curadoria

O que pode entrar no catálogo, decidido em [Critério de elegibilidade e o conjunto de frameworks da v0.1.0](https://github.com/panlabs-tech/overpower/issues/15). São **três portões, e o primeiro que reprova encerra**.

1. **Legal (veto).** O conteúdo é redistribuível dentro do wheel. Framework não-MIT obriga expressão SPDX composta no metadado — senão ele mente exatamente para quem decide se o pacote passa numa allow-list corporativa por licença.
2. **Identidade.** O conteúdo aterrissado funciona sem ferramental que o overpower não pode garantir no alvo. **Reprovar aqui não é "framework recusado" — é não ser um AI Framework neste modelo**, porque autocontido é identidade, não elegibilidade.
3. **Transformação.** Se o que aterrissa não é a árvore versionada, a transformação acontece **na curadoria**, com a saída vendorizada; o produto continua sendo cópia. Ver [ADR 0005](../adr/0005-transformacao-acontece-na-curadoria.md).

**O critério mora no julgamento do curador, não em campo do catálogo.** O catálogo só contém o que já passou — um campo que registrasse "passou" seria constante.

**Para artefato de pool a curadoria é livre**, com duas cláusulas: o mesmo portão legal, e o átomo funciona **sem ferramental que o overpower não pode garantir no alvo** — runtime e binário de terceiro, a mesma leitura do portão 2. **A segunda cláusula não fala de artefato irmão**: pela regra 7 não existe dependência entre artefatos, então um átomo cujo texto manda invocar outro entra no pool assim mesmo, e chega sozinho se for pedido sozinho. **O veto de framework não propaga para o átomo**: origem é propriedade do corpo, não do átomo, e pela regra 6 o alvo não carrega atribuição nenhuma.

**Escrever dentro de arquivo do usuário não reprova ninguém** — enxerto é classe legítima deste modelo. O que reprovou o `open-gsd/gsd-core` foi runtime: o conteúdo aterrissado exige Node ≥22, e os hooks embutem o caminho absoluto do binário da máquina que instalou.

## Axiomas

Posições travadas na cartografia do mapa. Não se renegociam sem reabrir o mapa.

1. **Autocontido.** O overpower **nunca invoca instalador de terceiro** — nada de `npx`, nada que decida *o que* aterrissa ou *onde*. E **nenhum binário de terceiro é requisito**: todo caminho por subprocesso carrega um fallback puro-Python que entrega o mesmo resultado. A razão é ambiental: o alvo de replicação é um ambiente corporativo sem esse ferramental. *Emendado em [Busca remota](https://github.com/panlabs-tech/overpower/issues/25) — a redação anterior proibia subprocesso alheio de qualquer natureza, e o `git` da obtenção de `--from` a contrariava. A linha que separa transporte de instalador é a **autoria da aterrissagem**: `git fetch` move bytes para um diretório que nós nomeamos, e a busca, a resolução de ambiguidade e a cópia continuam sendo código nosso. Ver [ADR 0007](../adr/0007-transporte-nao-e-instalador.md).*
2. **Sem estado no alvo.** O overpower não grava manifesto proprietário no repositório alvo. Num repo git, **o git é o manifesto**: `git status` e `git diff` respondem o que a ferramenta escreveu com fidelidade maior que qualquer lockfile.
3. **Ferramenta genérica.** O overpower não é ferramenta da org `panlabs-tech`. A decisão de distribuição de skills registrada em `panlabs-tech/skills` **não o vincula**.
4. **Só equipamento de AI.** Anatomia de repositório — `pyproject.toml`, CI, portões de commit, layout de testes — está **fora de escopo**. Esse território é do `uv init`, `copier` e `cookiecutter`.
5. **Conteúdo vendorizado.** O conteúdo dos frameworks viaja **dentro do wheel**, com o risco de redistribuição aceito conscientemente. Um repo remoto de assets existe como *override*, não como padrão.

## Reservado para depois da v0.1.0

**A v0.1.0 tem um AI Framework só** — `mattpocock/skills`, as 22 skills promovidas — mais o pool de artefatos e os bundles. Todo o conteúdo é **cópia**: nenhum servidor MCP, nenhum hook. A classe **enxerto** existe no vocabulário e não é exercitada.

Isso é escopo, não modelo. O que o modelo exige é que a v0.1.0 **não feche a porta** do enxerto. Três travas, todas vindas de medição em [Formatos de configuração de MCP por runtime](https://github.com/panlabs-tech/overpower/issues/17):

1. **Destino não é diretório.** Cópia aterrissa numa pasta; enxerto aterrissa em **arquivo mais chave dentro dele**. O destino tem de ser um dado com duas formas já na v0.1.0, mesmo com só uma implementada. Modelar destino como caminho de pasta é a regressão. *A forma dessa trava ficou resolvida em [Formato do catálogo](https://github.com/panlabs-tech/overpower/issues/10): destino é função de (tipo, runtime, escopo), logo **tabela em código**, e são os valores dela que carregam as duas formas. O teste de aceitação escreveu MCP e hook e nenhum dos dois precisou de campo de destino.*
2. **Um artefato pode custar mais de uma escrita, e a segunda pode ser fora do repositório.** Medido: `.mcp.json` commitado sozinho não funciona — o Claude Code exige aprovação gravada em `.claude/settings.local.json`, e o Codex exige `trust_level = "trusted"` na máquina. Um fluxo que assuma *"um artefato, uma escrita, toda dentro do alvo"* obriga reescrita na v0.2.
3. **`--dry-run` e `doctor` falam de escritas planejadas, não de arquivos a copiar.** Consequência da 2, com armadilha medida: sem `trust_level`, o `doctor` dá **falso positivo** — reporta instalado o que não está.

As três se pagam com uma decisão de forma: **toda escrita no alvo passa por uma fronteira única**. A v0.1.0 implementa uma operação (copiar árvore); a v0.2 acrescenta outra (enxertar chave). Somar implementação, não reescrever fluxo.

O trabalho de desenho do enxerto está preservado e **se reabre, não se refaz** — três tickets rotulados `v0.2` ([#20](https://github.com/panlabs-tech/overpower/issues/20), [#21](https://github.com/panlabs-tech/overpower/issues/21), [#22](https://github.com/panlabs-tech/overpower/issues/22)) e as pesquisas em `research/mcp-config-formats` e `research/hook-formats`.

**Fonte remota: skill entra, bundle e AI Framework ficam.** `--from <url>` está **na v0.1.0** para `--skill`, por descoberta de `SKILL.md` em qualquer URL **do GitHub** — outros forges saíram do escopo em [Busca remota](https://github.com/panlabs-tech/overpower/issues/25). Bundle e AI Framework por `--from` saíram em [Formato do catálogo](https://github.com/panlabs-tech/overpower/issues/10), e a razão é a mesma que separa as unidades: **skill é a única que existe no mercado**, enquanto as outras duas só existem em repositório que já conhece o overpower. Com elas sai o padrão de **repositório caseiro** — convenção e/ou manifesto `.overpower` —, preservado em [#26](https://github.com/panlabs-tech/overpower/issues/26). As duas seguem inteiras no modo **embutido**.

## Registro histórico

O raciocínio que produziu estas posições está no mapa de wayfinding deste repo e nos seus tickets de decisão. Quando uma posição parecer arbitrária, o porquê está num deles.
