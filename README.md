# overpower

A CLI that installs curated **AI Frameworks** — named bodies of agent equipment
from a single upstream — into a repository or onto a machine.

```bash
uvx overpower@latest install --skill panlabs-python-standards --runtime claude-code
```

Three commands, and they answer three questions. `list` says what there is,
`install` writes it, `doctor` says whether what was written is still what was
written.

Typed bare in a terminal, `overpower` opens the banner and the help and exits 0,
and `overpower --help` says the same thing; under a pipe the banner stays behind
and the help goes through alone, so `grep` and a file get something readable. The
banner also teaches the keyboard shortcut — [`alias op='overpower'`](#the-op-shortcut),
which you type or do not — and it is behind the same gate. `overpower --version`
answers the version that arrived, read from the installed metadata rather than
from a constant — which is what makes it evidence that the package landed intact.

## Always `@latest`

`uvx` **freezes the version on first use, with no TTL.** Since the version of
overpower *is* the version of the catalog it embeds, a bare `uvx overpower`
serves a catalog that can never age out. `@latest` is a correctness requirement,
not README style.

## `list` — what there is

Bare, it prints the whole embedded catalog in three blocks:

```bash
uvx overpower@latest list
```

| block | what it holds | how it installs |
| --- | --- | --- |
| **AI Frameworks** | a body of equipment from one upstream | whole, never a slice of one |
| **Pool skills** | artifacts curated to stand alone | alone, by name |
| **Bundles** | a named set of pool artifacts | expands to exactly what its manifest names |

Every item arrives with its size, its file count and its description **whole** —
never truncated, at 80 columns and at 60, because the description is what the
decision to install is made on. Under each description sits **the line that
installs it**, and — for an AI Framework and a bundle, the two units that carry
something to open — the line that opens it:

```
╭─ Bundles  lists pool artifacts only ─────────────────────╮
│                                                          │
│  api-python                         229.0 KiB · 8 files  │
│    Equipment for working on a Python API.                │
│                                                          │
│      overpower install --bundle api-python               │
│      overpower list --bundle api-python                  │
│                                                          │
╰──────────────────────────────────────────────────────────╯
```

The line is **bare**: no `$` in front, which makes a selected line paste back
broken, and no label column, which does not fit — the words `install` and `list`
inside the command are the label. It wraps rather than truncates, because a
command cut at the terminal edge is a command nobody can type back, and it
**survives a pipe**: the banner is a courtesy and is gated on `isatty()`, but a
command is a datum, so `overpower list | grep <name>` hands back the line to
copy.

One selector opens one item, and each takes one name:

```bash
uvx overpower@latest list --ai-framework matt-pocock   # every artifact inside it, typed
uvx overpower@latest list --skill panlabs-python-standards
uvx overpower@latest list --bundle api-python
```

`--skill` and `--bundle` carry the same short forms here as on `install`, `-s`
and `-b`. Two selectors on one line is a question with two answers, and exits 2
naming both flags. A name outside the catalog exits 2 with the closed list in
the message: the list is closed, so the defect is in what was typed.

## `install` — write it

```bash
uvx overpower@latest install --ai-framework matt-pocock --runtime claude-code,cursor
```

**The three selectors mix freely on one line**, and each accepts a comma-separated
value, a repeated flag, or both — they accumulate either way:

| flag | short | unit |
| --- | --- | --- |
| `--ai-framework` | — | an AI Framework, installed whole |
| `--bundle` | `-b` | a bundle, expanded to the pool artifacts it names |
| `--skill` | `-s` | one pool skill |

`--ai-framework` has no short flag on purpose: `-f` is spoken for by `--force`,
and a letter that means one thing on one line and another elsewhere is worse than
typing the word.

A line that mixes all three produces **one** plan, in a fixed order — framework,
then bundle, then individual artifact. Where two selectors would write the same
destination the order decides it rather than an error: the individual artifact is
the most specific unit, so it is the last write and its content is what survives.

### Runtimes

`--runtime` takes the keys of a closed table of 76 runtimes and **has no
default**. A line that names something to install and no runtime to equip exits 2
rather than guessing; a key outside the table exits 2 naming the whole set. A
named runtime whose directory does not exist yet is created, never skipped.

Several runtimes read the same directory: nineteen of the seventy-six read
`.agents/skills`. When they do, the plan says so — it prints the path and **who
reads it**, so a selection that lands in one shared place says that, instead of
promising one installation per runtime.

**The plan names every artifact it is about to write**, one per line with its
type as the prefix — the same grid `list --ai-framework` draws, between the head
line of a selection and the places it lands. It is the last gate before the
write, so it says *which* ones rather than how many:

```
$ overpower install --skill panlabs-python-standards --runtime claude-code,cursor,codex --dry-run

╭─ plan ───────────────────────────────────────────────────────────────────────╮
│                                                                              │
│  panlabs-python-standards  1 skill                                           │
│                                                                              │
│    skill  panlabs-python-standards                                           │
│                                                                              │
│    .claude/skills/  ← claude-code                                   8 files  │
│    .agents/skills/  ← codex, cursor                                 8 files  │
│                                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
```

A framework is where that matters: `--ai-framework matt-pocock` is two words on
the line and 74 files on the disk, and the plan lists all 25 skills it carries
(elided here with `…`; on screen every one of them is printed, and nothing is
ever truncated).

```
╭─ plan ───────────────────────────────────────────────────────────────────────╮
│                                                                              │
│  matt-pocock  25 skills                                                      │
│                                                                              │
│    skill  ask-matt                                                           │
│    skill  code-review                                                        │
│     …                                                                        │
│    skill  writing-for-agents                                                 │
│                                                                              │
│    .claude/skills/  ← claude-code                                  74 files  │
│    .agents/skills/  ← cursor                                       74 files  │
│                                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
```

The same plan appears on all three ways in — `--dry-run`, the wizard's
confirmation and a direct run — because there is one plan screen and not three.

The wizard shows those nineteen as a locked section — `Universal
(.agents/skills)  always included  19 runtimes` — rather than as nineteen lines
to tick, because one pre-ticked line and one locked line differ by a tap of the
space bar, and what the second buys is seeing that a single path equips every
runtime under it at once. **In global scope the group is six**, not nineteen: only
`cline`, `dexto`, `kimi-code-cli`, `loaf`, `warp` and `zed` read
`~/.agents/skills`, while Codex reads `~/.codex/skills`, Cursor
`~/.cursor/skills` and Amp `~/.config/agents/skills`. A heading that named a
folder its members do not read would be the screen lying about the disk.

**The lock is of the screen and never of the plan.** The wizard puts the locked
keys into the request it builds, exactly like a key somebody ticked; the flag
stays literal, so `overpower install --runtime claude-code` writes
`.claude/skills/` and nothing else. The list of *Additional agents* filters as
you type, matching in the middle of a word — `dev` cuts it to two rows — which
costs the `j`/`k` navigation keys, because the library cannot offer both.

### The wizard opens for whatever the line is missing

**In a terminal, a line that does not add up to a plan opens a wizard** instead
of refusing — a missing selection, a missing runtime, or both. It opens only the
steps the flags left open, in a fixed order: artifacts, then scope, then
runtimes, then confirmation. The order is mechanical, not aesthetic — the runtime
step probes the target root, so it cannot be asked before the scope is known —
and what comes out is the same request the equivalent flag line would build.

| line, in a terminal, inside a git repository | steps that open |
| --- | --- |
| `install` | artifacts · scope · runtimes · plan |
| `install --ai-framework matt-pocock` | scope · runtimes · plan |
| `install --runtime cursor` | artifacts · plan |
| `install --bundle api-python --runtime cursor` | the plan, straight away |
| `install --from <url> --skill <name>` | scope · runtimes · plan |
| no TTY, no `--runtime` | none — exit 2 |

Giving `--runtime` takes the scope question with it, because the set `--runtime`
accepts is a function of the scope, so the scope step exists to scope the runtime
step. `--global` answers it outright; its *absence* is "did not say", never
"chose the project". The wizard is one gesture, not a question per absent flag.

`--from` no longer keeps the whole wizard away: only the **artifacts** step
consults a catalog, and a `--from` line names `--skill` before anything is
fetched, so that step never opens and the embedded catalog is never read.
`--yes` skips no step at all — it skips the final confirmation and nothing else.

### Scope

Inside a git repository the default is the repository. **Outside one a flag line
refuses, exit 2**, unless `--global`/`-g` says explicitly to write under the home
directory: *the git is the manifest* only holds where there is git, and nothing
else on the machine would audit what a silent write left behind. Where the wizard
asks the question it reaches the same explicitness from the other side — outside
a repository it does not ask a question that has one legal answer, and goes
global without the step. Where it does not ask — because `--runtime` was given —
the flag rule applies unchanged, and outside a repository the line exits 2.

In project scope every landing is a **real copy**. Under `core.symlinks=false` —
a value git detects and records into the clone — a committed link checks out as
an ordinary text file, and the equipment is broken for whoever cloned.

In global scope each selection climbs a ladder: the first destination in the
table's own order receives the copy, and every destination after it becomes a
**relative symlink** to it — relative, so the link survives `$HOME` moving. On
Windows the same rung is a junction, which needs no privilege. Where neither can
be created, the write **degrades to a real copy**, says so as a warning, and
still exits 0: nothing is lost either way.

`--force`/`-f` is a global-scope gate and nothing else. A destination that
already exists is refused, exit 3, unless it says to overwrite — global scope has
no `git status` to reveal or undo a clobbered write. Both that refusal and a
runtime with no destination in the requested scope (`eve` and `promptscript` have
none globally) are detected before a single byte is written.

### The plan comes first

Every run prints the plan — every path, and who reads each one — before writing
anything. In a terminal it then asks; `--yes`/`-y` skips **that confirmation and
nothing else**. Off a terminal it does not ask at all, so the same line runs
identically in CI.

`--dry-run` resolves everything, prints the same plan, mirrors the exit code and
leaves nothing behind, not even an empty directory.

### `--from` — any GitHub repository

```bash
uvx overpower@latest install --from https://github.com/owner/repo --skill some-skill --runtime codex
```

The vendored catalog ages by construction, and `--from` is the escape hatch that
does not wait for a curation refresh. It points `--skill` at **any GitHub
repository, with no registration**, and it is **exclusive**: with it, only the
remote is consulted, which extinguishes the question of precedence rather than
answering it. It holds for `--skill` alone — a skill is the one unit that exists
in the market, while a bundle and an AI Framework only exist in a repository that
already knows the overpower — and a line naming either of them alongside `--from`
is refused by name before anything is fetched.

**The URL is a search root, not an address.** The repository root, a subfolder,
or the skill's own folder all give the same result. `tree/<ref>/<path>` pins a
branch, a tag **or a full SHA**, so reproducibility comes free with the address
someone pasted.

Obtention uses the local `git` as transport and reuses whatever credential it
already has, falling back to the anonymous tarball — standard library only — so
no third-party binary is a requirement. There is no cache: remote content is
fresh by decision.

## `doctor` — is it still what it was

```bash
uvx overpower@latest doctor
```

Two halves in one output. The **terminal** half reports tty, colour, width and
`NO_COLOR` — the four facts that explain a screen that came out strange, without
a round trip. The **integrity** half reads the runtime table in both scopes,
because the target carries no manifest and the closed table is therefore the only
thing that knows where equipment can be. That is also why there is no
`--global` here: one flag switching between the halves would make it two outputs.
Outside a git repository it still answers, unlike `install`.

Three checks, and each pays a hole nothing else closes:

- **`core.symlinks=false` breaking links** — the case where `git status` stays
  clean while the equipment is a text file. The git lies, and `doctor` is what
  contradicts it. Both places the value can live are read, in git's own
  precedence order.
- **A link that does not resolve** — invisible equipment: the listing shows a
  name with nothing behind it.
- **Copies of one artifact that disagree** — the debt taken on when project scope
  chose to copy instead of link.

**Exit 3 when it found something, 0 when it did not**, which is what makes it
usable as a CI gate next to `--dry-run`.

## Exit codes

| code | meaning |
| --- | --- |
| `0` | did what was asked |
| `1` | could not run |
| `2` | you invoked me wrong |
| `3` | ran, and the answer is no |

The axis between **2** and **3** is *whose defect it is*, and it is what makes
both usable in a pipeline. A `--runtime` outside the table is **2**; a
`--runtime` in the table with no destination in the requested scope is **3**. A
`--from` whose search root could not be obtained is **1**, and the transport's
own error is passed through because it is the one that names the problem;
obtained, searched, and the skill is not there — or is there twice — is **3**.

A traceback never reaches the terminal: an unhandled exception becomes an error
panel and exits **1**, saying it is a bug in the overpower and not in what was
typed.

## The `op` shortcut

The banner teaches one line, and typing it is your call:

```bash
alias op='overpower'
```

**No executable named `op` is ever installed.** `[project.scripts]` declares one
command, `overpower`, and that is deliberate: `op` is the command of the
[1Password CLI](https://developer.1password.com/docs/cli/), which lives in
`/usr/local/bin` — and measured on a developer machine, `~/.local/bin` sits at
position **1** of the `PATH` against position **6** for it, so a second entry
point would shadow a credential tool with no warning at all. `uv` only detects a
collision between tools it manages itself, and when it does it refuses the
**whole** package (`error: Executable already exists: op`), so even the honest
failure costs you the `overpower` command too. Occupying the name is a decision
for whoever knows their own machine, so the product prints the line and installs
nothing. If you use 1Password, alias something else:

```bash
alias opw='uvx overpower@latest'
```

An alias is keyboard comfort and nothing more: it does not expand in a
non-interactive shell, so `sh -c op` — which is how a Makefile invokes — answers
`command not found`. That costs nothing, because the line a README, a Makefile
and a CI write is `uvx overpower@latest …` anyway.

## Development

Four commands, and they are the whole loop. There is no task runner, and the
absence is deliberate: `uv` already does what one would add.

```bash
uv run ruff format --check .          # formatting
uv run ruff check .                   # lint
uv run --group typecheck pyright      # types, strict
uv run pytest                         # tests
```

The same four run in CI, from the same lockfile, so "it passed locally" and "it
passed in CI" mean the same thing.

### Local hooks

```bash
lefthook install     # once per clone; worktrees inherit
```

The hook is the shortcut, not the gate — the gate is the ruleset on `main`, and
a ruleset has no `--no-verify`. `lefthook` and `gitleaks` are equipment of the
machine, not of the repository; a clone on a machine without them loses the
shortcut by design.

### Coverage

Ephemeral by decision: no threshold, no badge, nothing in `pyproject.toml`. One
command, for when the question is "what has no test at all":

```bash
uv run --with pytest-cov pytest --cov=src/overpower --cov-report=term-missing
```

### Screens

Recorded screens live in `tests/snapshots/`, one file per screen, at 80 and 60
columns, without colour. They render a fixture and not the shipped catalog, so
a content refresh does not rewrite them. Rewriting them is an explicit act:

```bash
uv run pytest --snapshot-update tests/test_screens.py
```

### Releasing

The version is a literal in `pyproject.toml`, moved by hand:

```bash
uv version --bump patch      # or minor / major
uv run towncrier build --version "$(uv version --short)"
```

Merging that into `main` is what publishes: the tagger workflow creates `v<X>`
and dispatches the release. A merge that does not move the version publishes
nothing.

## Curation

Refreshing the catalog is an **act, not a job**. A gate blocks what this
repository controls; what depends on a third party is verified here, by hand, on
purpose.

### Refreshing the vendored content

The trees under `src/overpower/content/` are vendored at a fixed upstream
reference, which `NOTICE` records per origin. A refresh is:

1. Read the upstream's own manifest at the new reference to get the set — for
   `matt-pocock`, the `skills` array of `.claude-plugin/plugin.json`, never the
   `version` field beside it, which has been measured standing still while the
   array moved.
2. Replace the tree, applying the curation transform: the slice excludes what the
   upstream declares unshipped, and the shape is the one the target discovers,
   because the transformation happens at curation and never in the product.
3. Update `NOTICE` — reference and commit per origin — and `licenses/` if the
   upstream licence file moved.
4. Run the four development commands, plus the network test below.
5. **Bump the version.** By rule 5 the version of the overpower *is* the version
   of the catalog, so a refresh nobody can install is not a refresh.

### Tests that touch the real GitHub

They exist, they are documented, and they run in **no** CI job — not on a pull
request and not on a release:

```bash
OVERPOWER_NETWORK_TESTS=1 uv run pytest -m network
```

With the variable set, the skip condition can no longer be satisfied — a network
test that gets renamed or lost turns red instead of disappearing in silence.

## Where the reasoning lives

Every position in this repository was decided in a ticket, and the ticket is
where the argument is. The map is
[Mapa: overpower v0.1.0 publicada no PyPI](https://github.com/panlabs-tech/overpower/issues/1).

| Document | Role |
| --- | --- |
| [`docs/agents/domain.md`](docs/agents/domain.md) | Vocabulary, model rules, curation criteria, axioms |
| [`docs/agents/workflow.md`](docs/agents/workflow.md) | Branch policy, gates, autonomous implementation mode |
| [`docs/agents/testing.md`](docs/agents/testing.md) | What is a double, what runs for real, how screens are asserted |
| [`docs/adr/`](docs/adr/) | The decisions that read as arbitrary until you know why |

## Licence

MIT. Attribution owed to vendored upstreams travels in [`NOTICE`](NOTICE), which
names each origin and the reference it was taken at, and in [`licenses/`](licenses/),
which carries their licence files verbatim. PEP 639 places both in
`dist-info/licenses/` — inside the wheel, never in your repository.
