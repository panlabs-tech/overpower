---
title: Development
description: The four-command loop, and the local hooks that guard every commit.
---

# Development

This page covers the working loop for contributing to overpower: getting the environment, and the four commands you run over and over — install, lint, typecheck, test. It also covers the hooks that run without being asked — lefthook, commitlint, gitleaks — what each one rejects, and how to see what a hook saw when it rejects you.

## The loop

There is no task runner, and the absence is deliberate: `uv` already does what one would add. Four commands are the whole loop:

```bash
uv run ruff format --check .          # formatting
uv run ruff check .                   # lint
uv run --group typecheck pyright      # types, strict
uv run pytest                         # tests
```

The same four run in CI, from the same lockfile, so "it passed locally" and "it passed in CI" mean the same thing — there is no second local path that could drift from what the pipeline installs.

`pyright` runs `strict`, against the floor Python (`3.12`), never the version your own interpreter happens to be. `pytest` runs the whole suite, on every platform in the matrix — there is no marker for "slow" and no tier that runs on one OS only, because what the suite tests is disk behaviour, and disk behaviour is exactly what diverges between platforms. See [Tests](/development/tests) for why.

Coverage is a diagnostic, not a gate: no threshold lives in `pyproject.toml`, no badge, nothing in CI. When the question is "what has no test at all," run it by hand:

```bash
uv run --with pytest-cov pytest --cov=src/overpower --cov-report=term-missing
```

## Local hooks

```bash
lefthook install     # once per clone; worktrees inherit
```

Arm this once per clone. A worktree does not need its own `lefthook install`: it shares `.git/hooks` with the clone that owns it.

**The hook is the shortcut, not the gate.** The gate is the ruleset on `main`, and a ruleset has no `--no-verify` — the lists of who can bypass it are empty, including for the repository's owner. What the hook buys is speed: it catches the cheap error cheaply, before a push pays for a CI job whose fixed overhead alone costs more than the check.

Two hooks run, at two different moments:

**`pre-commit`**, over the staged set, in parallel:

- `ruff format --check` on staged `.py` files — a hook that reformatted mid-commit would leave the index different from what you reviewed.
- `ruff check` on staged `.py` files.
- a check that nothing under `src/overpower/content/` is hidden from git — the cheap half of the pair of gates that keep the vendored content tree honest. A subject-less run (the directory does not exist, or git tracks nothing under it) is treated as failure, not as a vacuous pass.
- `gitleaks`, over the staged diff — the last moment where blocking a secret is still cheap. Once a commit exists the secret is already in local history, and removing it is a rewrite rather than a fix.

**`commit-msg`**: `commitlint`, checking Conventional Commits with a lower-case subject.

`lefthook`, `gitleaks` and the tooling `commitlint` needs are equipment of the machine, not of the repository — a clone on a machine without them loses the shortcut by design, and still meets the same gate on the pull request.

When a hook rejects a commit, it prints the failing command's own output straight to the terminal, at the moment of the rejection — there is no separate log to go find. A `ruff` failure shows the `ruff` diagnostic; a `gitleaks` failure shows the match it found; a `commitlint` failure shows which rule the subject broke. Fix what it names and commit again.

See [Tests](/development/tests) for the testing doctrine and [Screens](/development/screens) for how the terminal output is tested. See [Releasing](/shipping/releasing) for what stands between a passing local hook and a published version.
