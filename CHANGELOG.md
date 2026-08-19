# Changelog

The format is [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html) —
including §4, so while the version is `0.x` a break does not promote the first
digit. There is one deliberate addition to the six sections of Keep a Changelog:
**Breaking**, which the spec has no room for and a consumer needs first.

The type of each fragment is also what decides the version. See
[ADR 0012](docs/adr/0012-o-bump-e-ato-do-autor-e-o-portao-o-ensina.md).

Entries are not written by hand. Each pull request that changes behaviour drops
a fragment into `changelog.d/`, named `<issue>.<type>.md` — where `<type>` is one
of `breaking`, `added`, `changed`, `deprecated`, `removed`, `fixed`, `security` —
and the release assembles them:

```bash
uv run towncrier build --version "$(uv version --short)"
```

The issue link comes free from the filename, which turns this file into a
navigable index of the decisions that produced it.

<!-- towncrier release notes start -->

## [0.24.0] - 2026-08-19

### Changed

- The one file the overpower writes about its own content is now YAML:
  `catalog.toml` became `catalog.yaml` inside the wheel, and the reader that
  decodes it goes through a sanctioned module that answers `object` — the same
  discipline the JSON reader already followed, and `yaml.load` is banned beside
  `json.load` for the same blind spot plus one of its own, since a loader without
  `Loader` builds arbitrary Python out of the document. **Nothing answers
  differently:** `list`, `install` and `doctor` print what they printed, byte for
  byte, and the same files land on disk. What the move buys is *one* reader — the
  manifest a homemade repository federates reaches this same decoder, so a second
  validator can never disagree with the first. It costs one guarantee: TOML had no
  key type but string, so a table key is now checked where it used to be cast. The
  recipe of an MCP server did not move and will not — `.overpower/` is a
  namespace, not a format. ([#136](https://github.com/panlabs-tech/overpower/issues/136))

### Fixed

- A skill description written as a YAML block no longer arrives with the block
  marker inside the text. `description: >` produced *"> first half second half"*
  and `description: |` the same with a pipe, because the frontmatter was read by a
  parser written here by hand instead of by YAML. **The hand-rolled parser is
  gone**, which is the second thing the dependency paid for: keeping one next to a
  real one is the weak form of the two-readers defect. It was invisible while the
  product only read its own content — 0 of the 26 embedded `SKILL.md` use a block,
  and all 26 read byte-identically before and after — and it would have surfaced
  the first time somebody else's frontmatter rendered. ([#136](https://github.com/panlabs-tech/overpower/issues/136))


## [0.23.0] - 2026-08-19

### Changed

- **The documentation site is now canonical, and `README.md` shrinks to point at it.** The `Contributing` sidebar's six pages carry real prose — the development loop and local hooks, the testing doctrine, how a screen is snapshot-tested, the module map and the two sibling content roots, how vendored content is curated, and how a release ships. `README.md` shrinks to the pitch, the install line, one screen showing the catalog format, and a link to the site; `pyproject.toml [project.urls]` gains `Homepage` and `Documentation`, both pointing at [panlabs-tech.github.io/overpower](https://panlabs-tech.github.io/overpower/). ([#132](https://github.com/panlabs-tech/overpower/issues/132))


## [0.22.0] - 2026-08-18

### Added

- **`--from` answers the question before the name: *what does this repository
  offer?*** `list --from <url>` with no selector prints that repository's showcase
  — its skills with name and description, and the MCP recipes it federates — in
  one command, and `install --from <url>` with no selector opens the **same
  wizard** anyone already knows, with the remote catalog in place of the embedded
  one and the sections that repository has nothing in left out. Nobody learns a
  second flow because of provenance. `list --skill <name> --from <url>` gains the
  selector it was missing, so a skill can be read whole before it is installed.

  The showcase is **anchored**: it walks `<repository>/skills/**` — a direct child
  of the root, free depth below it, so `skills/<category>/<name>/` is offered
  exactly as `skills/<name>/` is — plus `<repository>/.overpower/mcp/*.toml`. It
  **ignores the URL's subpath entirely**, because an offer is a property of the
  repository and not of the path someone pasted: the root URL and a subfolder's
  return the same list. The price is declared rather than hidden — **2 of the 75
  `SKILL.md` measured** fall outside the anchor and stay installable by name. The
  sentence is *"`list` shows the showcase; `--skill` reaches what you can name"*.

  A repository with nothing installable is refused at **exit 3** naming the URL,
  rather than opening a wizard with no choices in it: the problem is the address,
  not any answer the person could have given. `--bundle` and `--ai-framework`
  alongside `--from` still exit 2 before anything is obtained. ([#135](https://github.com/panlabs-tech/overpower/issues/135))

### Fixed

- **A repository equipped with the overpower can be installed from again.** One
  that has run `overpower install` on itself carries its skill twice — at
  `skills/<name>/`, which is what it offers, and at the runtime's own destination
  such as `.claude/skills/<name>/`, which is where the install put it. `--from
  --skill <name>` found both and refused the line as ambiguous, and that refusal
  was **false**: there is one skill there, and the second path is a copy of the
  first.

  The reach now discards installed copies, derived from the runtime table itself
  so a row added there needs no second edit — and it discards them **as a
  tie-break, not as a filter**: a copy never wins against an offer, and never
  hides what would otherwise be the only answer. Both halves of that matter.
  Pointing `--from` inside a runtime's own folder still reaches what is there,
  and so does a repository whose only skill lives under one — `github/spec-kit`
  is that repository, measured, and two rows of the table (`agent/skills`,
  `data/skills`) are ordinary folder names something could genuinely be offering
  from. Two real offers of the same name under one root are still refused, and
  still name every candidate.
  ([#135](https://github.com/panlabs-tech/overpower/issues/135))


## [0.21.4] - 2026-08-17

### Fixed

- **A configuration file carrying the same key twice is refused instead of written
  into.** Every parser measured — `json.loads`, `JSON.parse` — resolves a repeated
  key by the **last** occurrence, and the graft landed on the **first**: `install`
  exited 0, reported `1 write · 1 file`, named `.mcp.json › mcpServers.cloudflare`
  in its plan, and the runtime went on reading the user's old value. It was also
  an evasion of a refusal that already existed — a `mcpServers` that is a string
  exits 3 on its own and exited 0 hidden behind a duplicated root key.

  The refusal is **narrow by construction**: it covers the keys the graft actually
  looks up to decide where to land — the root key, the server name under it, and
  the id of an `inputs[]` entry — and nothing else. A key repeated anywhere else
  in the document is still none of the product's business, the same way every
  other thing in a file that is not ours to repair is not. RFC 8259 § 4 calls the
  result of a duplicate *unpredictable*, and ADR 0013 now carries the amendment
  that says why that makes it a broken file rather than a collision to overwrite. ([#125](https://github.com/panlabs-tech/overpower/issues/125))
- **A trailing comma or a comment in a document whose runtime parses strict JSON is
  refused instead of written into.** `.mcp.json` and Devin's `mcp_config.json` are
  read on the other side by a strict parser, so a file carrying either is already
  a file that runtime cannot read — and `install` was exiting 0 over it, leaving a
  graft on disk that nothing would ever see. `.vscode/mcp.json` is JSONC, where a
  comment and a trailing comma are idiomatic, and nothing changes there: the graft
  still reads every document through the tolerant parser that keeps them alive
  across a write.

  Strictness is now a **column of the table that decides the document**, beside the
  one that knows a server is born pending. It is a fact of the file and is never
  derived from the dialect, which spells keys and not syntax: the Copilot CLI
  reads a strict `.mcp.json` and a JSONC `~/.copilot/mcp-config.json` under one
  spelling of the root key, so a dialect would have to answer twice. ([#126](https://github.com/panlabs-tech/overpower/issues/126))


## [0.21.3] - 2026-08-16

### Fixed

- Um comentario de fim de linha fica na entrada que ele anota. A insercao movia o rabo de whitespace inteiro do ultimo par para o servidor recem-escrito, entao um `// nota` que estava na linha de um servidor passava a anotar o que o overpower acabou de escrever — o diff deixava de ser aditivo, com uma linha removida. O comentario em linha propria, que anota o objeto e nao uma entrada, continua descendo com o fecho. ([#122](https://github.com/panlabs-tech/overpower/issues/122))
- Um arquivo de configuracao que existe e nao pode ser lido produz um erro nomeado, dizendo qual arquivo e o que o sistema respondeu. Antes caia no painel de excecao inesperada e o produto se acusava — "This is a bug in the overpower, not in what you typed" — por uma permissao que outra pessoa pos. O exit code nao muda: continua 1, e a parada continua sendo antes do primeiro byte. ([#123](https://github.com/panlabs-tech/overpower/issues/123))


## [0.21.2] - 2026-08-16

### Fixed

- Os dois contadores do sumario reconciliam com o documento. Um MCP no VS Code contava `2 writes` pelo par servidor + `inputs[]` que a spec define como uma escrita so, "porque aterrissam no mesmo lugar"; e varios MCPs no mesmo documento contavam um arquivo cada, onde o `git status` mostra um. O caso federado — clone mais enxerto, dois lugares — continua contando duas escritas, como sempre contou. ([#119](https://github.com/panlabs-tech/overpower/issues/119))
- A linha de fecho que sai por um pipe passa a pluralizar como o painel do terminal ja pluralizava: `1 write · 1 file` nos dois, onde a versao pipada dizia `1 writes · 1 files`. Eram duas grafias da mesma frase, que e como as duas deixam de ser a mesma frase. ([#120](https://github.com/panlabs-tech/overpower/issues/120))


## [0.21.1] - 2026-08-16

### Fixed

- A tela de `list --mcp` para de prometer o que o install recusa. Uma receita que traz codigo-fonte nao e mais oferecida em escopo de projeto — o install ja recusava e o wizard ja obedecia, so a tela nao. E a linha que `list --mcp <slug> --from <url>` manda copiar carrega a origem: sem ela, colada de volta, saia com exit 2 dizendo que nao existe MCP com esse nome. ([#115](https://github.com/panlabs-tech/overpower/issues/115))
- Dois slots de nomes distintos que chegam ao mesmo prompt sao recusados na leitura da receita. A derivacao do identificador de prompt nao e injetiva — baixa a caixa e troca `_` por `-` —, entao `API_KEY` e `API-KEY` viravam um prompt so: a segunda declaracao apagava a primeira e os dois lugares recebiam calados o mesmo segredo, em exit 0. Dois slots com o **mesmo** nome continuam valendo, que e justamente o ponto de derivar o identificador: um segredo, perguntado uma vez. ([#116](https://github.com/panlabs-tech/overpower/issues/116))
- A tabela de runtimes para de dizer que a linha do Devin e doc do fornecedor "e nao uma medicao", com o binario "ausente da maquina". Desde a medicao em sandbox as duas frases sao falsas, e o commit da medicao nao tinha tocado este arquivo. O que continua em aberto — os valores de `transport` e se um servidor nasce pendente, ambos atras do login obrigatorio — segue marcado como aberto, agora por afirmacao e nao por linha inteira. ([#117](https://github.com/panlabs-tech/overpower/issues/117))


## [0.21.0] - 2026-08-16

### Added

- A tela de `list --mcp <slug>` mostra os slots que a receita exige, com o papel de cada um, e as precondicoes que ela declara. Eram as duas unicas coisas que a secao Descobrir da spec pedia por escrito e que a tela nunca mostrou: quem avaliava um servidor descobria o segredo que falta num 401 e o ferramental que falta num erro do agente. ([#113](https://github.com/panlabs-tech/overpower/issues/113))

### Fixed

- As receitas `coolify` e `hostinger-vps` declaram que precisam do `npx`. Instalar qualquer uma numa maquina sem Node recusava nada: escrevia a configuracao, saia 0, e a falta so aparecia depois, como erro obscuro do agente. Agora a recusa vem antes do primeiro byte, nomeando o que falta. ([#112](https://github.com/panlabs-tech/overpower/issues/112))


## [0.20.0] - 2026-08-14

### Added

- **`doctor` conhece enxerto.** Quatro checagens novas sobre servidor MCP, lidas de volta do documento — `doctor` não tem `Plan`. **Exit 3:** um servidor escrito em `.mcp.json` que o Claude Code ainda não aprovou, contra o registro que ele mesmo grava em `.claude/settings.local.json`/`.claude/settings.json` (ADR 0014); e uma configuração ainda apontando para um clone `[source]` que sumiu da máquina. **Exit 0, informativo:** um slot cujo nome não está no ambiente de quem roda o `doctor`, e um clone órfão em `~/.overpower/mcp/` que configuração nenhuma referencia mais — nomeado, nunca apagado. ([#86](https://github.com/panlabs-tech/overpower/issues/86))


## [0.19.1] - 2026-08-14

### Fixed

- **As docstrings do renderizador do Devin trocam citação especulativa por medida.** `_devin` e `_devin_reference` justificavam a grafia emitida citando "os vizinhos medidos" por analogia — o binário não estava nesta máquina quando foram escritas. Medido depois, em sandbox: chave raiz errada, campo desconhecido e até JSON malformado no `.devin/mcp_config.json` saem calados, exit 0, confirmando a suposição que a docstring só inferia. O comportamento emitido não muda; a citação que o justifica passa a apontar para medição, não para doc do fornecedor. ([#87](https://github.com/panlabs-tech/overpower/issues/87))


## [0.19.0] - 2026-08-14

### Added

- **MCP aparece no passo de artefatos do wizard.** `overpower install` pelado num terminal passa a oferecer MCP como a quarta classe no mesmo passo que já mostrava AI Frameworks, bundles e pool skills — a seleção produz exatamente o `Request` que `--mcp` produziria, e o contador da sessão passa a contar as quatro classes do catálogo, não três. Uma receita com `[source]` escolhida ali dentro também restringe o passo de escopo seguinte, a mesma leitura que ADR 0009 e ADR 0015 já aplicavam a uma receita nomeada por `--mcp`: o wizard não oferece "This project" quando a resposta já está decidida. ([#85](https://github.com/panlabs-tech/overpower/issues/85))


## [0.18.0] - 2026-08-14

### Added

- **Receita com `[source]` clona o próprio código para a máquina.** `[source]` numa receita de MCP declara um repositório GitHub a clonar — o clone é uma escrita do plano, com caminho e contagem de arquivos, e aparece tanto no `--dry-run` quanto no relatório do que aterrissou. `{source}` em `command`, `args`, `url` ou `[server.env]` resolve para o caminho absoluto do clone em `~/.overpower/mcp/<slug>/`. Uma receita com `[source]` só aterrissa em escopo de máquina — pedir escopo de projeto recusa com **exit 3**, nomeando o conserto (`--global`). Reinstalar re-clona incondicionalmente, sem cache; uma receita sem `[source]` continua indo para os dois escopos. ([#84](https://github.com/panlabs-tech/overpower/issues/84))


## [0.17.0] - 2026-08-14

### Added

- **`--from` alcança `--mcp`: a receita federada, no mesmo schema da embutida.** `install --mcp <slug> --from <url>` acha a receita em `.overpower/mcp/<slug>.toml` no repositório apontado — raiz do repo, subpasta ou a pasta da receita dão o mesmo resultado, e uma receita não encontrada recusa com **exit 3** sem o fallback rodar. `list --mcp <slug> --from <url>` mostra a receita sem instalar nada. O canal é o mesmo do `--skill`: exclusivo, sem cache, e o `git` roda de verdade contra o remoto apontado. ([#83](https://github.com/panlabs-tech/overpower/issues/83))


## [0.16.0] - 2026-08-14

### Added

- **Precondições de MCP: vocabulário fechado, e nenhum script de terceiro executa.** Uma receita
  pode declarar `[[preconditions]]` — `command_exists`, `env_set` ou `path_exists` — e o overpower
  checa antes de escrever, nunca invocando o que encontra. Uma precondição que falta recusa a
  linha inteira com **exit 3**, nomeando qual precondição e por quê, zero byte escrito; `--dry-run`
  roda a mesma checagem, para que o relatório não fale de uma máquina diferente da que instala de
  verdade. `instructions` chegou junto: a prosa que a receita carrega para o que não dá para
  automatizar sai impressa ao lado do plano, antes da confirmação. ([#82](https://github.com/panlabs-tech/overpower/issues/82))


## [0.15.0] - 2026-08-14

### Changed

- Numa linha que mistura `--skill`/`--ai-framework`/`--bundle` com `--mcp`, a recusa deixa de ser por linha inteira e passa a ser por runtime: só é recusado quem não tem destino em nenhuma das duas classes; quem tem destino numa e não na outra recebe o que pode e a tela nomeia o que ficou de fora. ([#100](https://github.com/panlabs-tech/overpower/issues/100))


## [0.14.0] - 2026-08-14

### Changed

- **`install --mcp <slug>` funciona pelo wizard, num terminal e sem `--runtime`.** O passo de runtime passa a conhecer a classe que a linha carrega: numa linha de MCP ele vira outro passo, sem o grupo universal travado, contando só os runtimes que recebem documento naquele escopo e rotulando cada opção pelo arquivo que vai receber o servidor — não pelo diretório de skill.

  **A validação sobe para antes da primeira tela.** Slug de MCP inexistente, slug que na verdade é de outra classe (`--mcp` nomeando um skill, por exemplo) e linha que mistura skill e MCP sem `--runtime` saem em exit 2 sem desenhar banner nem passo algum, em vez de custar o wizard inteiro para falhar no fim.

  **`vscode` ganha linha em `RUNTIMES`, sem destino de skill** (ADR 0018, que revisita e não repete a ADR 0017): é o que deixa o novo passo nomear `VS Code`. Pertencer à tabela deixou de provar destino de skill — `runtimes_in` passa a filtrar pelo campo, e a tabela cresce de 76 para 77 linhas. ([#97](https://github.com/panlabs-tech/overpower/issues/97))

### Fixed

- **`list --mcp <slug>` parou de pagar o produto cartesiano.** A tela mostrava um par por linha — cada runtime uma vez por escopo, seis linhas para três alvos — quando alvo e escopo são dois eixos e cabem em duas linhas, uma por eixo. Uma receita sem alvo nenhum continua dizendo isso.

  **O painel `installed` recupera a chave do enxerto.** A última tela, a que confirma o que já foi escrito, degradava um enxerto ao caminho do documento e jogava a chave fora; passa a imprimir `documento › chave`, como o plano e o portão já fazem — a única defesa do leitor sob sobrescrita incondicional.

  Os goldens de `list --mcp`, `summary` e `installed` passam a ser gravados com o que o produto realmente produz — alvos reais e uma variante com enxerto — em vez de um par construído à mão, que é o que deixou o produto cartesiano invisível em snapshot até agora. ([#98](https://github.com/panlabs-tech/overpower/issues/98))


## [0.13.0] - 2026-08-14

### Changed

- O help de `--runtime` passa a dizer que skill e MCP moram em tabelas separadas, e nem todo runtime está nas duas. ([#99](https://github.com/panlabs-tech/overpower/issues/99))


## [0.12.0] - 2026-08-14

### Added

- **`--global` escreve MCP no arquivo pessoal dos três alvos.** `install --mcp <servidor>
  --runtime claude-code|vscode|devin --global` aterrissa em `~/.claude.json`, no `mcp.json` do
  perfil de usuário do VS Code e no `mcp_config.json` de máquina do Devin. Os três de uma vez,
  porque o custo deste ticket não é dialeto — é **resolução de caminho**, e resolvê-la três vezes
  daria três meias soluções.

  **Um documento de máquina não é o de projeto sob outra raiz.** A linha da tabela passa a carregar
  a própria âncora, então quem decide a base é a tabela e não o argumento de escopo: `scope` escolhe
  a linha, a linha escolhe onde ela pendura. É o que faz um caminho de projeto continuar impossível
  de resolver contra a home, e vice-versa.

  **As 9 células resolvem, e são afirmáveis num runner só.** O perfil do VS Code é
  `%APPDATA%\Code\User` no Windows, `~/Library/Application Support/Code/User` no macOS e
  `$XDG_CONFIG_HOME/Code/User` no Linux; o Devin troca de lugar no Windows; o Claude Code fica na
  home nos três. `sys.platform` virou valor de `Environment` pelo mesmo motivo que `home` e
  `variables` já eram — *onde escrever* se decide a partir de fatos que chegam —, e `%APPDATA%`
  entrou no sandbox da suíte, que agora deriva as âncoras das **duas** tabelas.

  **O que ficou de fora ficou de fora por falta de fonte, não por esquecimento.** O perfil
  não-default do VS Code e a segunda cópia que uma sessão Remote-WSL/SSH mantém no servidor remoto
  não entram na tabela: a pesquisa registra que existem e que escrever no errado é **não-op
  silencioso**, e não registra caminho. Caminho que ninguém leu em fonte primária não vira linha.

  **O aviso de ativação cala em escopo de máquina — pela tabela.** `born_pending` é falso nas três
  linhas novas, e `pending_activation` pergunta à mesma linha que decidiu o arquivo. O servidor no
  arquivo pessoal é do próprio usuário; nada espera aprovação, e o CLI não aprendeu regra nova.

  **E o enxerto deixou de ser perguntado sobre sobrescrita.** `~/.claude.json` existe em toda
  máquina que já rodou o runtime, e ele carrega `userID`, `machineID` e o estado de onboarding —
  perguntar *"já existe, sobrescrevo?"* teria travado o caso ordinário para pedir permissão de
  **acrescentar** uma chave. Um enxerto não substitui arquivo: insere a chave e deixa os outros
  bytes onde estavam, formatação inclusive. ([#81](https://github.com/panlabs-tech/overpower/issues/81))


## [0.11.0] - 2026-08-14

### Added

- **O segundo alvo de MCP: `.devin/mcp_config.json`.** `install --mcp <servidor> --runtime devin`
  escreve `mcpServers.<slug>` no documento do projeto, e a receita não foi tocada para isso — a
  tabela ganhou uma linha e a regra 4 pagou por si. É o primeiro documento de graft que **não**
  mora na raiz do repositório, então o diretório nasce com ele.

  **A terceira grafia de um mesmo nome.** O slot vira `${env:VAR}` aqui e `${VAR}` no `.mcp.json`,
  a partir de uma receita que não carrega nenhuma das duas: nome e papel são dela, a grafia é do
  alvo. O `[server.env]` continua chegando literal dos dois lados, porque endereço de painel não
  é segredo. O discriminador também parte: `type` no Claude Code, `transport` no Devin — e **só em
  HTTP**, porque o fornecedor documenta os valores `"http"` e `"sse"` e infere stdio pelo `command`.
  Escrever um `"transport": "stdio"` que a doc não tem seria campo desconhecido num alvo cujo
  comportamento com campo desconhecido é dúvida aberta.

  **`sse` continua recusado na origem**, mesmo o Devin lendo. A recusa mora em `Transport`, na
  receita, e não no alvo: um alvo que engole o campo calado não pode ser quem decide.

  **E o aviso de ativação não aparece para ele.** ADR 0014 faz do aviso um requisito onde ele é
  verdade, e por isso mesmo silêncio onde não é: o fornecedor não documenta portão de confiança
  para esse arquivo, e inventar um seria afirmar um fato que ninguém aqui pôde observar. Numa linha
  com os dois runtimes, o aviso nomeia o `.mcp.json` e só ele.

  **A evidência desta linha é doc do fornecedor, não medição** — o binário `devin` não estava na
  máquina em que ela foi escrita, e as três dúvidas que só a medição fecha estão registradas em
  `docs/research/mcp-config-formats.md`. A mais cara delas: se `${env:}` alcança `env` ou só os
  campos de OAuth. Se não alcançar, a referência chega crua ao servidor e falha alto na primeira
  chamada — que ainda é o lado certo de errar, porque o outro é escrever o segredo num arquivo
  versionado com exit 0. ([#80](https://github.com/panlabs-tech/overpower/issues/80))


## [0.10.0] - 2026-08-14

### Added

- O VS Code entra como alvo de enxerto: `.vscode/mcp.json`, chave raiz `servers`, e o slot renderizado como `${input:<id>}` mais uma entrada em `inputs[]` marcada `password: true` — a única grafia do espaço medido em que o segredo fica no cofre do sistema operacional em vez de em texto puro. `--runtime vscode` passa a ser nomeável, ainda que o VS Code não tenha linha na tabela de skills. ([#79](https://github.com/panlabs-tech/overpower/issues/79))

### Fixed

- O enxerto passou a achar uma chave escrita com aspas simples. A busca só reconhecia a grafia com aspas duplas, e um falso "não achei" custa uma **duplicata**: a entrada era acrescentada ao lado da que devia substituir — um segundo `inputs`, ou o mesmo segredo perguntado duas vezes.
  Um documento que termina a última entrada com vírgula não ganha mais uma `,` órfã numa linha só. Em JSONC a vírgula final é idiomática, e o espaço antes da chave de fechamento pendura nela e não no último valor — movê-lo deixava para trás uma linha que ninguém escreveu. ([#79](https://github.com/panlabs-tech/overpower/issues/79))


## [0.9.0] - 2026-08-13

### Added

- **A receita passa a carregar segredo e configuração, e a diferença entre os dois é a coisa
  toda: slot é o que o overpower se recusa a escrever; `[server.env]` é o que ele escreve
  porque pode.** Um slot é declarado como **nome e papel** — nunca como valor e nunca como a
  grafia de um alvo —, e o que aterrissa no arquivo é a referência que o runtime expande:
  `"COOLIFY_ACCESS_TOKEN": "${COOLIFY_ACCESS_TOKEN}"` ao lado de `"COOLIFY_BASE_URL":
  "https://vps.panlabs.tech"`, este escrito literal. O endereço de um painel não é segredo, e
  tratá-lo como slot faria o servidor subir sem saber para onde falar.

  **Os três papéis — `env`, `header` e `bearer` — renderizam para o Claude Code**, e o `bearer`
  monta `Authorization: Bearer ${VAR}` **sem a palavra aparecer na receita**. É o que permitirá
  servir um alvo que monta o header sozinho — o `bearer_token_env_var` do Codex — a partir
  desta mesma declaração, sem campo novo.

  **Nenhum papel emite `${VAR:-default}`.** Não existe default no contrato, e a sintaxe é
  armadilha medida: ela é exclusiva do Claude Code, e nos outros dois runtimes que leem o mesmo
  `.mcp.json` a string chega **literal** ao processo do servidor — o arquivo parseia, a
  instalação sai verde, e a falha aparece na primeira chamada. Dois arquivos versionados desta
  organização carregam essa sintaxe hoje.

  **Papel e transporte se pareiam no leitor**, com erro nomeado: processo recebe variável,
  requisição recebe header, e o par que não existe é recusado **antes de qualquer
  renderização** — do mesmo jeito que papel fora do conjunto fechado e `header` sem o header
  que ele preenche.

  **E dois slots nunca preenchem o mesmo lugar.** A unicidade é do **lugar**, não do nome:
  dois slots `bearer` carregam variáveis diferentes e caem no mesmo `Authorization`, então
  uma tabela construída com os dois guardaria o último e perderia o primeiro — segredo
  sumido, com exit 0, num arquivo que ninguém relê. Vale para header em duas grafias
  (nome de campo HTTP é case-insensitive) e para nome declarado ao mesmo tempo como slot e
  como literal em `[server.env]`. Uma variável **pode** preencher dois lugares diferentes,
  porque aí não se perde nada. Uma receita que passa do leitor é uma receita que renderiza, e
  por isso o renderizador não tem ramo nenhum onde um segredo possa sumir calado.

  **Variável de slot ausente é aviso e exit 0.** Ela precisa existir quando o runtime sobe, e
  não quando o overpower roda — o ambiente do editor não é o deste shell. Mas o aviso sai,
  porque no Claude Code a variável ausente manda `${VAR}` **cru** na requisição, e o que a
  pessoa vê é um 401 longe da causa. O `--dry-run` avisa o mesmo, antes de escrever nada.

  **Três receitas embutidas entram, e nenhuma é inventada**: `hostinger-vps` (slot `env`),
  `coolify` (slot `env` mais `COOLIFY_BASE_URL` literal) e `github` (slot `bearer`) saem da
  configuração que quatro repositórios desta organização já mantêm à mão — a mesma que produziu
  cinco versões que discordam entre si. Todas **pinam versão exata**: `@latest` numa receita
  embutida faria o servidor mudar de comportamento sem ninguém ter mudado nada, e a versão em
  que ele mudou não ficaria escrita em lugar nenhum. ([#78](https://github.com/panlabs-tech/overpower/issues/78))


## [0.8.0] - 2026-08-13

### Added

- **O `list` conhece MCP: um bloco próprio no catálogo, e a receita inteira em `list --mcp
  <slug>`.** O `overpower list` passa a imprimir **quatro** blocos — os MCPs ao lado de AI
  Frameworks, skills e bundles —, para que a classe exista na tela sem ninguém precisar ler
  documentação. A entrada tem o mesmo tratamento visual das outras três: nome, descrição
  **inteira**, e as linhas que instalam e que abrem. Onde as outras dizem quanto pesam, a do
  MCP diz o **transporte**: a receita não aterrissa, então bytes e contagem de arquivos não
  são fatos sobre ela.

  **`overpower list --mcp cloudflare` mostra a receita inteira** — descrição nunca truncada,
  transporte, `url` ou `command`/`args`/`env`, e a linha de alvos. Todo rótulo menos o último
  é um **campo da receita**, grafado como o TOML o grafa; `targets` é o único sem campo por
  trás.

  **A linha de alvos é derivada, nunca declarada** (regra 4 do modelo). Ela é função de
  (transporte, papéis de slot, alvo), logo tabela em código: mudar a tabela muda a resposta
  **sem tocar na receita**, e uma receita que declarasse `targets` é recusada pelo leitor,
  por nome. Um alvo é um **par** — runtime *e* escopo —, porque o `claude-code` lê `.mcp.json`
  dentro do repositório e ainda não lê nada na máquina
  ([#81](https://github.com/panlabs-tech/overpower/issues/81)): a tela diz `claude-code ·
  project` e não promete a metade que não existe. Receita que alvo nenhum atende diz `none`
  em vez de mostrar uma linha vazia.

  Nome fora do catálogo sai **exit 2** com a lista fechada na mensagem, dois seletores na
  mesma linha saem 2 nomeando os dois, e sob pipe continua **zero** sequência ANSI. Nada
  truncado a 80 nem a 60 colunas, e as duas telas novas entram como snapshot nas duas
  larguras, sem cor. ([#77](https://github.com/panlabs-tech/overpower/issues/77))


## [0.7.0] - 2026-08-13

### Added

- **`install --mcp` escreve um servidor MCP dentro do arquivo do usuário, e o `git diff`
  mostra só o que ele escreveu.** `overpower install --mcp cloudflare --runtime claude-code`
  num repositório git enxerta `mcpServers.cloudflare` no `.mcp.json` da raiz e sai 0. É a
  **segunda operação de escrita** do modelo — a primeira classe que colide por **chave** e
  não por caminho —, e ela entra como ramo da fronteira de escrita que já existia:
  `WriteMode.GRAFT` ao lado de `COPY`, um escritor só.

  **O resto do documento chega byte a byte igual.** Comentário sobrevive, chave raiz
  desconhecida sobrevive, e um servidor que já estava lá **não é reformatado** — nem os
  `args` que ele mantinha numa linha. Isso custou uma dependência (`json-five`) e a
  proibição do `json.dumps` como escritor de enxerto, decidida na
  [ADR 0016](https://github.com/panlabs-tech/overpower/blob/main/docs/adr/0016-o-diff-aditivo-e-requisito.md):
  medido, reserializar no melhor caso possível já reflui um servidor que ninguém tocou, e
  aí o `git diff` deixa de responder o que a ferramenta fez. Indentação por tabs continua
  tabs, `CRLF` continua `CRLF`, e um comentário no fim do objeto sobrevive à vírgula que a
  inserção precisa acrescentar.

  **O plano nomeia arquivo e chave antes de confirmar** — `.mcp.json ›
  mcpServers.cloudflare ← claude-code` —, e essa linha é requisito e não ornamento: chave
  homônima é **sobrescrita** sem perguntar e sem `--force`
  ([ADR 0013](https://github.com/panlabs-tech/overpower/blob/main/docs/adr/0013-a-chave-alheia-e-sobrescrita.md)),
  então ela é a única defesa que o leitor tem. A identidade de três vias ganhou a metade
  que faltava: toda chave que o plano nomeou existe no documento depois, e nenhuma que ele
  não nomeou apareceu. **Arquivo de configuração já quebrado é recusado, nunca reparado**,
  com exit 3 — e o `--dry-run` devolve o mesmo 3, porque a checagem acontece antes do
  primeiro byte.

  **O servidor nasce desligado e o produto diz isso**
  ([ADR 0014](https://github.com/panlabs-tech/overpower/blob/main/docs/adr/0014-o-enxerto-nasce-desligado-e-o-produto-diz-isso.md)):
  no Claude Code um servidor vindo do `.mcp.json` nasce pendente de aprovação e **não
  conecta**, sem mensagem e sem exit code, então o comando avisa ao final — com exit 0,
  porque a escrita aconteceu e o que falta é ato do usuário. O aviso só sai onde é verdade.

  Nascem com isso o **leitor de receita** e o **renderizador**, os dois função pura sobre
  valores, e a **terceira raiz de catálogo**: `catalog/mcps/<slug>.toml`, um arquivo por
  MCP, descoberta por andar na árvore, na raiz que **nunca aterrissa** — porque o que
  aterrissa é o fragmento renderizado, não a receita. Transporte fora de `stdio`/`http` e
  campo que esta versão não renderiza são **erro nomeado no leitor**, nunca aceitação
  parcial. O primeiro corte tem **um alvo** (Claude Code, escopo de projeto) e **uma
  receita**, `cloudflare`, que não é inventada: é a configuração que três repositórios
  desta organização já mantêm à mão, em três cópias que por acaso concordam. ([#76](https://github.com/panlabs-tech/overpower/issues/76))


## [0.6.0] - 2026-08-13

### Changed

- **O sdist publicado deixa de ser o repositório inteiro.** `[tool.hatch.build.targets.sdist]`
  ganha uma linha — `include = ["src/"]` — e o `.tar.gz` sai de 172 arquivos e 424.699
  bytes para 105 e 266.086, **−37%**. O que sai é `tests/`, `docs/`, `.github/` e os
  dotfiles de ferramenta, e sai porque nada a jusante os lê: o wheel reconstruído a
  partir do sdist encolhido é **byte-idêntico** ao de hoje, 105 entradas e zero bytes
  diferentes. Oito arquivos entram de qualquer jeito — `pyproject.toml`, o readme, os
  `license-files`, o `.gitignore` e o `PKG-INFO` são forçados pelo `hatchling`,
  verificado —, o que garante que a atribuição PEP 639 não pode ser perdida por uma
  allowlist errada.

  O mecanismo é **allowlist e não denylist**, e é a escolha que fecha a classe: um
  `exclude` obriga a enumerar a ferramenta de amanhã; um `include` não deixa entrar o
  que ninguém declarou. Um portão novo, **P3**, roda no job `static` e reprova o sdist
  que carregue arquivo não rastreado pelo git ou que perca arquivo rastreado sob
  `src/` — sem custar build nenhum, lendo o `dist/` que o P2 já constrói. Ele existe
  para pegar a allowlist envelhecendo, e não o vazamento, que a CI nunca conseguiria
  ver.

  **Quem empacotava a partir do sdist para rodar a suíte passa a precisar do
  repositório**, e a divergência está registrada na
  [ADR 0013](https://github.com/panlabs-tech/overpower/blob/main/docs/adr/0013-o-sdist-declara-o-que-carrega.md). ([#71](https://github.com/panlabs-tech/overpower/issues/71))

### Fixed

- **O estado local do Claude Code sai do `.git/info/exclude` e entra no `.gitignore`.**
  O `info/exclude` é por clone e não viaja, e nenhuma ferramenta além do git o lê — o
  `hatchling` monta o sdist filtrando pelo `.gitignore`. O resultado medido: plantadas
  quatro sondas numa árvore suja, **as quatro entravam no sdist sem aparecer no `git
  status`**, entre elas `.claude/mailbox/` (mensagem trocada entre agentes) e
  `.claude/checkpoints/` (estado de sessão), que são conteúdo e não metadado. Nove
  linhas passam a viver ao lado do `.claude/worktrees/` que já estava lá.

  Nada disso chegou ao PyPI: os sdists publicados `0.1.0` e `0.5.0` têm **zero**
  entradas `.claude`, porque o release builda em runner limpo e o `actions/checkout`
  só materializa o que o git rastreia. O que estava exposto era o build da máquina do
  mantenedor, para o dia em que um `uv build && uv publish` saísse dali. ([#72](https://github.com/panlabs-tech/overpower/issues/72))


## [0.5.0] - 2026-08-12

### Changed

- `install --global` deixa de recusar duro (`DestinationExistsError`, exit 3) quando um destino já existe: num terminal real, sem `--force`, a mesma pergunta que já perguntava `Write these paths?` passa a nomear os paths em conflito e perguntar se deve sobrescrever — `Y` instala tudo e sobrescreve onde há conflito, `N` cancela sem escrever nada (exit `CANNOT_RUN`, 1, a mesma convenção que toda recusa interativa já usava). Fora de terminal, com `--yes`, ou sob `--dry-run` — que é relatório, nunca sessão — o comportamento continua idêntico ao de antes: recusa antes de qualquer tela, exit 3. `--force` continua sobrescrevendo em silêncio, em qualquer contexto. ([#69](https://github.com/panlabs-tech/overpower/issues/69))


## [0.4.0] - 2026-08-12

### Changed

- O comando sob cada entrada do `list` (`AI Frameworks`, `Bundles`, `Pool skills`) deixa de usar a mesma tinta cyan do nome do artefato acima dele — novo token `op.command` (`#5f819d`, o azul-acinzentado que já era o `qmark` do wizard) marca o comando como subordinado ao nome, sem virar ilegível. Os prompts do wizard `install` (`questionary`) ganham um `Style` próprio, harmonizado com o `THEME` do resto do produto: `qmark` e a moldura (rail, hints, grupo travado) na mesma tinta de `op.brand`/`op.dim`, a resposta selecionada e a linha destacada na mesma tinta de `op.key` — em vez do azul-acinzentado e do laranja que a biblioteca usava por padrão. A pergunta de escopo ganha uma linha em branco antes do hint de navegação, que estavam colados, e as opções mudam de "This repository"/"This machine (~/), every project" para "This project"/"Global". ([#67](https://github.com/panlabs-tech/overpower/issues/67))

### Removed

- A dica de atalho `alias op='overpower'` sai do banner. A linha misturava pt-BR ("atalho") com o resto do banner em en-US e, sem um segundo executável instalado para o alias (#58), não sobrava nada além de mais uma linha para o olho descartar. ([#67](https://github.com/panlabs-tech/overpower/issues/67))


## [0.3.0] - 2026-08-11

### Added

- Fora de repositório git o escopo passa a ser **relatado** em vez de decidido em silêncio: a sessão mostra `Where should this install write to? / This machine (~/) — outside a git repository` onde antes não havia etapa nenhuma. Cada runtime da lista passa a nomear a árvore que lê, como o `npx skills` faz — e a busca passa a casar o caminho junto com o nome. ([#65](https://github.com/panlabs-tech/overpower/issues/65))

### Changed

- O wizard de `install` passa a desenhar a dinâmica de sessão do `npx skills add`: moldura `┌`/`└`, trilho `│` entre etapas, marcas `◆`/`◇`/`●`, e a etapa respondida colapsando em pergunta sobre resposta. A lista de runtimes ganha viewport de 8 linhas com contador `↓ N mais` e rodapé de seleção viva; o grupo universal sai da lista e vira bloco estático que nomeia quatro e conta o resto. Medido a 80x24: a etapa mostrava **1** linha selecionável e passa a mostrar **8**. ([#65](https://github.com/panlabs-tech/overpower/issues/65))

### Fixed

- O portão de confirmação cabe na tela. Medido a 80x24, o plano detalhado tem 34 linhas contra as 24 do terminal, então as 11 primeiras — incluindo a linha que nomeia o que está sendo aceito — já tinham rolado quando `Write these paths?` aparecia. O portão passa a listar destinos; `--dry-run` e a saída sob cano mantêm a lista de artefatos inteira, e as duas são a mesma função a um flag de distância. ([#65](https://github.com/panlabs-tech/overpower/issues/65))


## [0.2.0] - 2026-08-11

### Added

- The banner teaches the keyboard shortcut: `atalho   alias op='overpower'`, under
  the tagline, on both gestures of discovery — a bare `overpower` and `overpower
  --help`, which now carries the banner too. It is gated on `isatty()` for the same
  reason the banner is, so a pipe and a file still get clean output. **No second
  executable is installed**: `[project.scripts]` still declares one command,
  because `op` is the binary of the 1Password CLI and a second entry point would
  shadow a credential tool out of a `~/.local/bin` that sits ahead of it on the
  `PATH` — with `uv` refusing the whole package if it noticed at all. Occupying the
  name is a decision for whoever knows their own machine. ([#58](https://github.com/panlabs-tech/overpower/issues/58))

### Changed

- The journey the catalog opens now closes: **`overpower list` prints the line that
  installs each item**, and that line, pasted back, works. Under every description
  sits the install command — plus the inspection command for an AI Framework and a
  bundle, the two units that carry something to open — bare, with no `$` and no
  label column, wrapping rather than truncating, and present under a pipe as well,
  because the banner is a courtesy and a command is a datum.

  **The wizard's trigger stops being the empty line and becomes the gap.** In a
  terminal, a line that does not add up to a plan — no selection, no runtime, or
  both — opens the wizard on exactly the steps the flags left open, in the order
  artifacts, scope, runtimes, confirmation. `install --ai-framework matt-pocock`
  asks scope and runtimes; `install --runtime cursor` asks artifacts; giving
  `--runtime` takes the scope question with it, because the set `--runtime` accepts
  is a function of the scope. `--from` no longer keeps the whole wizard away: only
  the artifacts step consults a catalog, and a `--from` line names `--skill` before
  anything is fetched, so that step never opens and the embedded catalog is never
  read. Without a TTY nothing changes — the same two refusals, the same exit 2.

  **The universal group is a locked section again, and its composition follows the
  scope.** It is shown as *always included* rather than as lines to tick, and it
  holds the 19 runtimes that read `.agents/skills` in project scope against the 6
  that read `~/.agents/skills` in global — which corrects a screen that used to
  announce the project path to 18 runtimes of which 12 land somewhere else. The
  lock is of the screen and never of the plan: `install --runtime claude-code` on
  the flag line still writes `.claude/skills/` and nothing else. The *Additional
  agents* list now filters as you type, matching in the middle of a word, which
  costs the `j`/`k` navigation keys because the library cannot offer both. ([#57](https://github.com/panlabs-tech/overpower/issues/57))
- The plan **names every artifact it is about to write**, instead of counting them.
  Between the head line of a selection and the places it lands, `install` now
  stacks the artifacts the same way `list --ai-framework` does — the type as the
  prefix, one per line, one shared function — so the last gate before 148 files
  land in a repository says *which* 25 skills those are without anyone leaving the
  screen. It is the same plan on all three ways in: `--dry-run`, the wizard's
  confirmation and a direct run. Fidelity to `list` was chosen over fitting on one
  screen: the `matt-pocock` plan goes from 8 lines to 34 and scrolls at 24 rows,
  and the measured alternatives all cost more — a three-column grid needs 91
  characters and a two-column one 62, so neither fits the widths this screen is
  recorded at, and a wrapped run of names fits but drops the type prefix that a
  framework of mixed types is read by. ([#58](https://github.com/panlabs-tech/overpower/issues/58))
- **Release cadence now follows implementation.** A new version comes out of every
  pull request that changes what goes inside the wheel, instead of out of somebody
  remembering to move a literal: a required check, `release-ready`, refuses the
  pull request without the bump and prints the computed level and the two commands
  in the failure itself. The level comes from the types of the fragments in
  `changelog.d/` — the same ones that assemble this file — so the version and the
  release notes cannot disagree. While the project is `0.x` a break does not
  promote the first digit, and reaching `1.0.0` stays an explicit act. There is a
  seventh fragment type, `breaking`, because Keep a Changelog has no section for a
  break and `changed` was carrying both meanings at once.

  This is the first version where that holds, and it exists because it did **not**
  hold before: after `v0.1.0`, three pull requests merged into `main` without a
  bump, the tagger found the tag already there, wrote a notice and went green all
  three times — nothing published, no error anywhere, and the only symptom was a
  `pip install --upgrade` that brought nothing back. The tagger now fails loudly in
  that case. The sections below are the work that had been dammed up behind it. ([#62](https://github.com/panlabs-tech/overpower/issues/62))

### Fixed

- An artifact name is no longer cropped on a narrow terminal. The stacked list of
  `list --ai-framework` — and now of the plan, which shares the same grid — used
  rich's default overflow, so at 40 columns it printed
  `skill improve-codebase-architec…`: a name nobody can type back into `--skill`.
  It folds across lines instead, at every width. Leaving `no_wrap` off was not
  enough and that was the trap — it lets rich *try* to wrap, and a name is a single
  unbreakable word, so what it did instead was crop. ([#58](https://github.com/panlabs-tech/overpower/issues/58))


## [0.1.0] - 2026-08-08

### Added

- The command line is born, and with it the frame the rest of v0.1.0 hangs off.
  `overpower` opens the banner and the help in a terminal, the help alone under a
  pipe, and exits 0 in both; `overpower --version` answers the version that
  arrived; `overpower list` shows the whole embedded catalog in three blocks — AI
  Frameworks, pool skills and bundles — each item with its name, its size, its file
  count and its description **whole**, never truncated, at 80 columns and at 60.
  The catalog comes from walking the content tree, so adding a skill is adding a
  directory: no path is registered anywhere, and a directory outside the closed set
  of type names is a named error carrying the offending path. The error model
  starts here too: a wrong flag exits 2, and an unhandled exception becomes an
  error panel and exit 1 — a traceback never reaches the user. ([#36](https://github.com/panlabs-tech/overpower/issues/36))
- `overpower list` gains the three screens that answer the question preceding an
  install — one per installable unit. `list --ai-framework matt-pocock` shows the
  artifacts **inside** it, stacked, with the **type of each one as its prefix**
  and their count on the head line, because a framework installs whole and *whole*
  has to be readable before it is accepted; `list --bundle api-python` shows
  exactly the pool artifacts the
  manifest names, in the order it names them; `list --skill <name>` shows the
  description **whole**, which is the extreme case at 517 characters and the
  reason none of the three truncates — all of them re-wrap inside the frame at 80
  columns and at 60, because a narrow terminal is where reading matters most. A
  name outside the catalog exits **2** with the closed list in the message: the
  list is closed, so the defect is in what was typed. ([#37](https://github.com/panlabs-tech/overpower/issues/37))
- `overpower install --skill <a>,<b> --runtime <x> --runtime <y>` writes curated
  pool skills into a repository. Comma and repeated flag are both accepted and
  both accumulate, there is no positional, and there is **no default runtime**:
  without a terminal and without `--runtime` the command exits 2, and a value
  outside the closed table exits 2 naming the whole set. A named runtime whose
  directory does not exist yet is created and written, never skipped. The command
  prints a plan first — every path it will write and **who reads each one**, so a
  selection that lands in one shared directory says so instead of promising a
  runtime — asks for confirmation in a terminal, and runs without asking anywhere
  else; `--yes` skips that confirmation and nothing else. `--dry-run` resolves
  everything, prints the same plan, mirrors the exit code and leaves nothing
  behind, not even an empty directory. Every landing is a **real copy**: under
  `core.symlinks=false`, which git records into the clone, a link becomes a text
  file and the equipment is broken for whoever cloned. Writing is unconditional
  and reinstalling replaces rather than overlays, so no file from a previous
  version survives; a failure part-way through leaves what it wrote and reports
  how far it got and where it stopped, with exit 1. What the plan announces, the
  real run announces and the disk carries are asserted to be the same set of
  paths, on all nine cells of the matrix. ([#38](https://github.com/panlabs-tech/overpower/issues/38))
- `overpower install` gains `--ai-framework` and `--bundle`, joining `--skill` as
  independent selectors that a single line may freely mix — both accept comma and
  repeated flag, accumulating, the same as `--skill` already does.
  `--ai-framework <name>` writes the AI Framework's whole body: rule 1 forbids a
  partial install, and there is no syntax to ask for a slice of one — a
  framework's own artifact is not addressable through `--skill`, since it never
  joined the pool. `--bundle <name>` expands to exactly the pool artifacts its
  manifest names, and never a framework (ADR 0002). Mixing all three produces
  **one** plan, in a fixed and documented order — framework, then bundle, then
  individual artifact. An intra-command collision, where two selectors would write
  the same destination, is not detected — it is decided: the order makes the
  individual artifact, the most specific unit, always the last write, so the
  content that survives a collided destination is the individual artifact's. ([#39](https://github.com/panlabs-tech/overpower/issues/39))
- `overpower install` now has a scope. Inside a git repository the default stays
  the repository, unchanged; **outside one, the command refuses and exits 2**
  unless `--global`/`-g` says explicitly to write under the home directory —
  "the git is the manifest" only holds where there is git, and nothing else on
  the machine would audit what a silent write left behind. `--global` needs no
  repository at all.

  In global scope every selection climbs a ladder: the **first destination in
  the runtime table's own order** receives a real copy, and every destination
  after it becomes a **relative symlink** pointing at that copy — relative, so
  the link survives `$HOME` moving and the machine being cloned. On Windows the
  same rung is a **junction**, created through `_winapi.CreateJunction`, which
  needs no privilege and works identically with or without it; the source
  directory is validated before the call, because the API itself accepts a file
  as target and creates unusable garbage in silence. Whenever a link or a
  junction cannot be created — a filesystem with no reparse points, a network
  share, an interpreter without parity — the write **degrades to a real copy
  instead**, and the command says so as a warning while still exiting 0: nothing
  is lost, the content is on disk either way.

  Two refusals are new, both exit 3 — a correct invocation whose answer is no,
  never a typo. A `--runtime` that names a value **in the table** but with no
  destination in the requested scope (`eve` and `promptscript` have none in
  global) is refused by name, distinct from a value outside the table entirely,
  which still exits 2. And in global scope, `--force`/`-f` is the one gate a
  project install never needed: a destination that **already exists** is
  refused unless `--force` says to overwrite it — global scope has no `git
  status` to reveal or undo a clobbered write, so nothing is written until the
  whole plan is known to be collision-free or the overwrite was asked for by
  name. Both refusals are detected before a single byte is written, and both
  mirror through `--dry-run` exactly as the rest of the exit-code table already
  does.

  The plan now carries **mode** alongside path, and the identity that ties the
  plan, the screen and the disk together grows with it: what the screen calls a
  link has to be a link on disk, in every scope, on every platform the writer
  runs on. ([#40](https://github.com/panlabs-tech/overpower/issues/40))
- `overpower install` typed bare in a terminal now opens a wizard instead of
  refusing with *"nothing to install"*. Four steps, in a fixed order: **artifacts,
  then scope, then runtimes, then confirmation** — the order is not aesthetic,
  the runtime probe depends on the scope already being known, so asking runtimes
  first would probe the wrong root. The runtime step always asks, even when
  detection pre-marks exactly one — pre-marking is a convenience, not a decision
  made on the user's behalf. The universal group (`.agents/skills`) is shown
  grouped and **never locked**: there is no canonical destination to lock in
  project scope, and in global scope which selection becomes canonical is a
  function of what gets picked, not a fact knowable before the pick. Its members
  are the **19** runtimes that read that path, read off the path itself, so the
  heading never gathers a runtime that lands somewhere else. In global
  scope the two runtimes with no destination there (`eve`, `promptscript`) do
  not appear on the screen at all — the wizard offers exactly what the runtime
  table would accept, never what the next step would refuse. There is no step
  asking symlink versus copy: that choice does not exist, scope alone decides it.

  There is **no state file**, in any scope. Pre-checking a runtime's box comes
  from probing the target root live: project scope probes the repository for an
  existing destination, global scope probes `~` directly, and a repository that
  carries no runtime directory at all falls back to probing `~` rather than
  pre-checking nothing.

  The wizard hands the rest of the program the same `Request` the flags build,
  so the selection logic downstream is unchanged and stays tested over values,
  never over keystrokes. Without a terminal, a bare invocation still exits 2
  without ever touching the prompt library — no prompt library degrades alone
  under no-TTY, so the check is the overpower's own, ahead of every call into it. ([#41](https://github.com/panlabs-tech/overpower/issues/41))
- `overpower install` gains `--from <url>`, which points `--skill` at **any GitHub
  repository, with no registration**: the vendored copy ages by construction, and
  this is the escape hatch that does not wait for a curation refresh. It is
  **exclusive** — with it, only the remote is consulted, which extinguishes the
  question of precedence between embedded and remote instead of answering it — and
  it holds for `--skill` only, because a skill is the one unit that exists in the
  market while a bundle and an AI Framework only exist in a repository that already
  knows the overpower. A line that names either of them alongside `--from` is
  refused by name, exit 2, before anything is fetched.

  **The URL is a search root, not an address.** The repository root, a subfolder
  and the skill's own folder give the same result, and the deepest one only buys a
  shorter walk. `tree/<ref>/<path>` pins a branch, a tag **or a full SHA** with no
  field of our own, so reproducibility comes free with the address someone pasted.
  The known limit is declared rather than papered over: a branch whose name
  contains a `/` cannot be told from a ref plus a path without asking the server,
  so the first segment is the ref.

  Obtention has **two paths and one search**. The primary is `git` as transport —
  `init`, `remote add`, `fetch --depth 1`, `checkout FETCH_HEAD` — reusing whatever
  credential the local `git` already has; the fallback is the **anonymous
  `codeload` tarball**, pure standard library, so that no third-party binary is a
  *requirement* (axiom 1, as amended by ADR 0007). Neither side asks for a
  credential of its own, and the subprocess runs under `LC_ALL=C` because the three
  obtention failures all exit 128 and only their stderr tells them apart.

  **The fallback fires on a failure to obtain, and never on "I did not find it"** —
  the live bug measured in #25, where it re-fetched a whole repository to return an
  identical answer. The two numbers are now distinct and both mirror through
  `--dry-run`: **exit 1** means the search root could not be obtained, and the
  transport's own error is passed through because it is the one that names the
  problem; **exit 3** means it was obtained, searched, and the answer is no —
  either the skill is not under the root, or more than one folder of that name is.

  The scratch is a temporary directory, removed in the `finally` even on failure,
  and **there is no cache**: remote content is fresh by decision. `--dry-run
  --from` resolves the remote exactly as the real run does and still writes
  nothing, because a dry run that does not fetch is a report about a different
  installation. **Zero new dependencies.** ([#42](https://github.com/panlabs-tech/overpower/issues/42))
- `overpower doctor` answers two questions in one output: how the terminal is,
  and how what was installed is. The terminal half reports **TTY, colour, width
  and `NO_COLOR`** — the four facts that explain a screen that came out strange
  without a round trip. The integrity half reads the **whole runtime table in both
  scopes**, because axiom 2 forbids a manifest in the target and the closed table
  is therefore the only thing that knows where equipment can be; that is also why
  there is no `--global`, since one flag switching between the halves would make
  it two outputs. Outside a git repository the command still answers, unlike
  `install`: the machine half is there and the terminal half never needed git.

  Three checks, and each one pays a hole nothing else closes. **`core.symlinks=false`
  breaking links** is the exact point where axiom 2 does not answer on its own —
  git auto-detects the capability and records it into the clone, a committed link
  checks out as an ordinary text file carrying its own target, and **`git status`
  stays clean**; the git lies, and `doctor` is what contradicts it. Both places the
  value can live are read, in git's own precedence order — the clone's own config
  and the user's — because measured on a machine where links do work, the user's
  config alone produces the identical broken checkout with the clone recording
  nothing about links at all. A linked worktree is followed to where its shared
  config actually lives. **A link that does not resolve** is invisible equipment: the
  listing shows the name and there is nothing behind it. **Copies of one artifact
  that disagree** is the payment of the debt taken on when project scope chose to
  copy instead of link — that decision accepted losing the single point of truth
  and named `doctor` as its mitigation.

  **Exit 3 when it found something, 0 when it did not**, which is what makes it a
  CI gate next to `--dry-run`: *"could not run"* and *"ran, and the answer is no"*
  have to be distinguishable. The whole answer is phrased in **writes** rather than
  in artifacts — one artifact occupies as many places as it landed in, and the
  screen counts both — so the graft of v0.2, where an artifact costs a second
  write possibly outside the repository, is a sum and not a rewrite. ([#43](https://github.com/panlabs-tech/overpower/issues/43))
- The vendored content ships inside the wheel, in two sibling roots with opposite
  invariants: `content/`, which lands whole in the target — the `matt-pocock` AI
  Framework and one pool skill, `panlabs-python-standards` — and `catalog/`, which
  never lands and carries only what the tree cannot know: the `api-python` bundle
  and one description line per framework. No path is written anywhere. Attribution
  travels in the package metadata, never in the target. ([#45](https://github.com/panlabs-tech/overpower/issues/45))

### Changed

- Everything the product says is English — the README that becomes the PyPI page,
  the package description, and everything the command prints. pt-BR stays in
  tickets, resolutions and ADRs. ([#14](https://github.com/panlabs-tech/overpower/issues/14))
- The `0.0.x` series ends. `0.1.0` is the first version that installs anything, and
  the notice saying the series is not the product leaves the README and the package
  docstring with it. The README **is** the PyPI page, so it now describes the
  surface that exists — the three commands, the three selectors, the runtime and
  scope flags, and the exit code table — and it states `@latest` as a **correctness
  requirement** rather than README style: `uvx` freezes the version on first use
  with **no TTL**, and by rule 5 the version of the overpower *is* the version of
  the catalog it embeds, so a bare `uvx overpower` serves a catalog that can never
  age out. The curation step is written down next to the four development commands,
  both halves of it — refreshing the vendored content against its upstream, and the
  end-to-end test against the real GitHub under `OVERPOWER_NETWORK_TESTS=1`, which
  runs in no CI job by decision. `Development Status` moves off `1 - Planning`,
  which is the same claim as the notice and would have outlived it on the sidebar
  of the page. ([#44](https://github.com/panlabs-tech/overpower/issues/44))


## [0.0.2] - 2026-08-05

### Fixed

- Publishing metadata pointed at a repository that answered 404 to anonymous
  callers. ([#24](https://github.com/panlabs-tech/overpower/issues/24))

## [0.0.1] - 2026-08-05

The `0.0.x` series is not the product. It reserves the name on PyPI and proves
the publishing pipeline end to end; it installs nothing.

### Added

- Name reserved on PyPI, published from GitHub Actions through a trusted
  publisher, with no credential stored anywhere.
  ([#13](https://github.com/panlabs-tech/overpower/issues/13))
- `overpower` reports the version that arrived, the interpreter that ran it, the
  platform and the payload that crossed — the four facts only a real execution
  can answer. ([#13](https://github.com/panlabs-tech/overpower/issues/13))
