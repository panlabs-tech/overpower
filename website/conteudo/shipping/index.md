---
title: Shipping
description: The architecture — the modules, the flow between them, and two sibling roots with opposite invariants.
---

# Shipping

This page maps the codebase for someone about to change it: the modules, what each one is responsible for, and the path a single invocation takes through them. It also covers the two sibling content roots and why their invariants are opposites — one is vendored and must stay byte-identical to its source, the other is authored here — because most of the surprising rules in this repository descend from that split.

## The module map

Everything lives under `src/overpower/`, flat — there is no package-within-package, because the project is single-context.

| module | responsibility |
| --- | --- |
| `cli.py` | the command line: parsing, the `isatty()` gate, the exit codes, the top-level handler |
| `discovery.py` | the tree *is* the catalog — `list` and `install` discover artifacts by walking `content/pool/<type>/<name>/` and `content/frameworks/<name>/<type>/<name>/` |
| `packaged.py` | where the two sibling roots live inside the package |
| `scope.py` | whether `cwd` is inside a git repository — the one fact the default scope needs |
| `wizard.py` | the interactive wizard: a terminal, a line that does not add up to a plan, one `Request` out |
| `remote.py` | `--from <url>`: any GitHub repository as a search root, obtained two ways |
| `planning.py` | `Request → Plan`: the one place a destination is decided |
| `writing.py` | the one write boundary — it executes the plan and reads nothing else |
| `written.py` | the only file overpower writes about its own content — the catalog entries a tree cannot know on its own |
| `inspection.py` | what is on the disk of the target, and what is wrong with it — the `doctor` |
| `screens.py` | what the product draws to the terminal |
| `recipes.py` | TOML in, a `Recipe` out — the reader and validation for an MCP server declaration |
| `rendering.py` | `(Recipe, document) → the grafts to make` — a pure function over values |
| `grafting.py` | surgical insertion into a document that is not ours: text in, text out |
| `runtimes.py` | the runtime path table — where each AI runtime reads skills from, and the target of a graft |
| `jsonio.py` | the sanctioned way to reach the standard library's JSON reader, typed as `object` |
| `errors.py` | the one exception the product raises on purpose, and the seam the CLI catches |

## The flow of one invocation

`cli.py` parses the line and, in a terminal with a line that does not add up to a full request, hands the gaps to `wizard.py` — artifacts, then scope, then runtimes, then confirmation, in that order, because a later step can depend on an earlier one's answer. Either way, what comes out is the same `Request`.

For the embedded catalog, `discovery.py` and `packaged.py` answer what exists by walking `content/`; for `--from <url>`, `remote.py` answers the same question by obtaining a copy of a foreign repository — through `git` where it can, through an anonymous tarball where it must — and then discovering across that copy. `planning.py` turns the `Request` into a `Plan`: the one place a destination is decided, given an artifact, a runtime and a scope. For an MCP server the plan additionally passes through `recipes.py` and `rendering.py`, which turn a declared recipe into the concrete graft `grafting.py` will make.

Every write, whichever path produced the plan, passes through the single boundary in `writing.py`. `screens.py` renders what the terminal shows at each stage, and `written.py` is the one file the product writes describing its own catalog. `inspection.py` powers `doctor` by reading what actually landed on a target and comparing it against what the runtime table in `runtimes.py` says should be there.

## Two sibling roots, opposite invariants

Inside the package sit two content roots, siblings, and their invariants are opposites — most of the rules that read as arbitrary until you know why descend from this split:

**`src/overpower/content/`** carries the vendored trees — the pool of individually curated artifacts and the AI Frameworks. It **must land 100%**: every file tracked here has to reach the wheel byte-identical, because this is copied content, never generated, and a partial landing is a corrupted artifact nobody would notice at the point it happened. Two gates in CI guard exactly this — one confirms nothing under `content/` is hidden from git, the other confirms the wheel carries the same set the git tree carries.

**`src/overpower/catalog/`** is the opposite: a single file, `catalog.yaml`, that carries **only what the tree cannot know on its own** — bundle definitions, which have no directory of their own by construction, and one description line per AI Framework, which has no `SKILL.md` to read a description from. Nothing that a directory walk could answer lives here; a field that duplicated a path the filesystem already knows would be a second source of truth for a fact that has only one. It **must land 0%** relative to the wheel's tolerance for loss in the other direction: there is no dedicated gate for it, because losing it fails loudly rather than quietly — a bundle vanishes from `list`, and `install` answers that it does not know the name. What fails loudly does not need a gate; what fails silently is what the two `content/` gates exist to catch.

See [ADR 0006](https://github.com/panlabs-tech/overpower/blob/main/docs/adr/0006-a-arvore-e-o-catalogo.md) for the full argument, including the registry design that was built and rejected before this one. See [Curation](/shipping/curation) for how the vendored tree is refreshed, and [Releasing](/shipping/releasing) for how a change to either root reaches a release.
