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
