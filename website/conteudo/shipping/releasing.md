---
title: Releasing
description: towncrier, the bump as an act of the author, and why publishing is merging.
---

# Releasing

This page covers how a change becomes a release: the changelog fragment every pull request carries, towncrier assembling them, and the version bump as a deliberate act of the author rather than a computed one. It explains the consequence that publishing is merging — a merge that changes the version tags and releases, a merge that does not publishes nothing — and lists the gates that stand between a branch and that merge.

## Publishing is merging

A merge into `main` that moves the version in `pyproject.toml` creates the tag and dispatches the release; a merge that does not move it publishes nothing. There is no separate "cut a release" step to remember or forget — the version in the file that lands on `main` is the whole decision.

## The changelog fragment

Every pull request that changes behaviour drops one fragment into `changelog.d/`, named `<issue>.<type>.md`, where `<type>` is one of `breaking`, `added`, `changed`, `deprecated`, `removed`, `fixed`, `security`. Entries in `CHANGELOG.md` are never written by hand — a release assembles the fragments:

```bash
uv run towncrier build --version "$(uv version --short)"
```

The issue number in the filename comes along for free, which is what turns the changelog into a navigable index back to the decisions behind it. `breaking` is a section Keep a Changelog itself has no room for, and it exists because without it `changed` would carry two incompatible kinds of thing under one label — a cosmetic change and one that breaks every caller read identically, and only one of those needs to be found first by someone scanning a release.

## The bump is an act of the author, and the gate is what teaches it

Moving the version is not left to memory or discipline: `release-ready`, a required check alongside `gate`, refuses a pull request that changes what lands in the wheel without also moving the version — and its failure message prints the level it calculated and the two commands to run:

```bash
uv version --bump <patch|minor|major>                      # moves pyproject.toml + uv.lock
uv run towncrier build --version "$(uv version --short)"    # consumes changelog.d/
```

`release-ready` only fires when a pull request touches the **wheel** trigger — `src/`, `README.md`, `NOTICE`, `LICENSE`, `licenses/`, or the `[project]` table of `pyproject.toml`. A pull request confined to `docs/`, `tests/`, `.github/`, or a `[tool.*]` table merges without publishing anything, because none of that reaches a user who installs the package.

The level itself is not a judgement call — it is read from the *types* of the fragments sitting in `changelog.d/`, the same fragments that build the changelog:

| fragment type | level while `0.x` | level at `≥ 1.0` |
| --- | --- | --- |
| `breaking` · `removed` | minor | major |
| `added` · `changed` · `deprecated` | minor | minor |
| `fixed` · `security` | patch | patch |

While the project is `0.x`, a break does not promote the first digit — that is Semantic Versioning §4 read literally: nothing is stable yet, so nothing can break stability. Reaching `1.0.0` stays a deliberate act of its own: a pull request that sets `uv version 1.0.0` passes, because the check enforces a **floor**, never equality. Bumping higher than the fragments strictly require is always allowed; bumping lower than they require is refused.

The full argument — the three designs that were tried and rejected, and the measurements behind each one — is in [ADR 0012](https://github.com/ThiagoPanini/overpower/blob/main/docs/adr/0012-o-bump-e-ato-do-autor-e-o-portao-o-ensina.md).

## Two gates, two different remedies

`gate` and `release-ready` are both required checks on `main`, and they are kept deliberately separate rather than merged into one: `gate` means *the code is sound*, `release-ready` means *merging this publishes*. The two failures have different fixes, and one name per remedy is what lets a contributor — human or an agent working autonomously — act correctly on the first read of a red check, without first having to work out which of two unrelated problems it is pointing at.

Nothing entering `main` skips this. There is no bypass list — not even for the repository's owner — because a bot pushing on the author's own credentials would otherwise make "bypass" and "pushing as the agent" the same door.

See [Shipping](/shipping/) for the two sibling content roots that make up most of what the wheel trigger watches, and [Curation](/shipping/curation) for the refresh procedure that always ends with the bump described here.
