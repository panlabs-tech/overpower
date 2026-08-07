# overpower

A CLI that installs curated **AI Frameworks** — named bodies of agent equipment
from a single upstream — into a repository or onto a machine.

```bash
uvx overpower@latest
```

> **The `0.0.x` series is not the product.** It exists to reserve the name on
> PyPI and to prove the publishing pipeline end to end. It installs nothing: it
> prints the version that arrived, the interpreter that ran it and the payload
> that crossed. The first usable version is `v0.1.0`.

## Always `@latest`

`uvx` **freezes the version on first use, with no TTL.** Since the version of
overpower *is* the version of the catalogue it embeds, a bare `uvx overpower`
silently serves a stale catalogue forever. `@latest` is a correctness
requirement, not README style.

## The `op` alias collides

`op` is the command of the [1Password CLI](https://developer.1password.com/docs/cli/).
Aliasing `op=overpower` shadows it. If you use both, pick another alias — this
is written down rather than left to be discovered:

```bash
alias opw='uvx overpower@latest'
```

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
columns, without colour. Rewriting them is an explicit act:

```bash
uv run pytest --snapshot-update tests/test_screens.py
```

### Tests that touch the real GitHub

They exist, they are documented, and they run in **no** CI job — not on a pull
request and not on a release. A gate blocks what this repository controls; what
depends on a third party is an act of curation. They are part of the curation
step, next to refreshing the vendored content:

```bash
OVERPOWER_NETWORK_TESTS=1 uv run pytest -m network
```

With the variable set, the skip condition can no longer be satisfied — a network
test that gets renamed or lost turns red instead of disappearing in silence.

### Releasing

The version is a literal in `pyproject.toml`, moved by hand:

```bash
uv version --bump patch      # or minor / major
uv run towncrier build --version "$(uv version --short)"
```

Merging that into `main` is what publishes: the tagger workflow creates `v<X>`
and dispatches the release. A merge that does not move the version publishes
nothing.

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
PEP 639 places in `dist-info/licenses/` — inside the wheel, never in your
repository.
