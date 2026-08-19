---
title: install
description: Selectors, the plan shown before any write, the confirmation, and the wizard that opens when the line does not close a plan.
---

# install

```bash
uvx overpower@latest install --ai-framework matt-pocock --runtime claude-code,cursor
```

Four selectors name what to write:

| Flag | Short | Unit |
| --- | --- | --- |
| `--ai-framework` | — | an AI Framework, installed whole |
| `--bundle` | `-b` | a bundle, expanded into the pool artifacts it names |
| `--skill` | `-s` | one pool skill |
| `--mcp` | — | one MCP server, grafted into the runtime's own configuration |

They mix freely on one line, and each accepts a comma-separated value, a repeated flag, or both — see [Commands](/commands/) for how a mixed line resolves into one plan, in one fixed order. `--ai-framework` has no short form on purpose: `-f` is already `--force` on this same command, and a letter that means one thing here and another thing on `list` is worse than the extra keystrokes. `--mcp` has none either, because it is already short enough that a flag would not save anything worth having.

## `--runtime` — who receives it

```bash
overpower install --skill panlabs-python-standards --runtime claude-code,cursor,codex
```

`--runtime` takes keys from a closed table of 77 runtimes and has **no default**. A line that names something to install but no runtime to equip refuses, exit `2`, rather than guessing; a key outside the table refuses the same way, naming the whole set. The full table, what each runtime reads, and how the two scopes differ live on [Targets](/targets/).

## The plan comes before every write

Every run prints the plan — every destination path, and which runtime reads it — before writing a single byte:

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

The plan grid is where several runtimes sharing one destination becomes visible — `.agents/skills/` above receives both `codex` and `cursor` in one write, rather than promising a separate install per runtime. An AI Framework makes the same point at a larger scale: `--ai-framework matt-pocock` is two words on the command line and 74 files on disk, and the plan lists every one of the 25 skills it carries:

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

On screen every skill is printed — the `…` above is a limit of this page, not of the product, which never truncates a plan. The same plan screen appears whichever of the three ways you reach it: `--dry-run`, the wizard's own confirmation step, and a direct run all print the identical grid, because there is one plan and not three.

## The flags that change the contract

| Flag | Short | What it gives up |
| --- | --- | --- |
| `--dry-run` | — | resolves everything, prints the plan, mirrors the real exit code, and writes nothing — not even an empty directory |
| `--yes` | `-y` | skips the confirmation prompt, and nothing else |
| `--force` | `-f` | overwrites an existing global-scope destination without asking; has no effect in project scope, where there is no such question to begin with |
| `--global` | `-g` | writes under the home directory instead of the current repository |

In a terminal, after the plan, `install` asks for confirmation before writing; `--yes` is the flag that skips exactly that question and nothing further. Off a terminal — in CI, in a script — it never asks at all, so the same line behaves identically whether a human is watching or not.

## Scope, briefly

Inside a git repository the default scope is the repository itself. Outside one, a plain flag line refuses, exit `2`, unless `--global` says explicitly to write under the home directory instead — the rule is that git is the manifest of what was installed, and that only holds where git exists. `--force` belongs to global scope alone: project scope has `git status` to reveal or undo a mistake, global scope does not, so an existing destination there is refused rather than silently overwritten unless `--force` says otherwise. The full mechanics — the project-scope real copy, the global-scope symlink ladder, and what happens when neither can be created — are on [Targets](/targets/).

## MCP is a graft, not a copy

The first three selectors — framework, bundle, skill — **copy**: a file or folder appears that was not there, and `git status` shows something new. `--mcp` **grafts**: a key appears inside a document you already own, and `git diff` shows a change to a file of yours instead of a new one. The mechanics of that graft — how the plan names the exact key, why the rest of the document survives byte for byte, and how a secret is kept out of it entirely — are their own page: [MCP servers](/targets/mcp).

## The wizard opens for whatever the line is missing

In a terminal, a line that does not add up to a complete plan opens a wizard instead of simply refusing — triggered by a missing selection, a missing runtime, or both at once. It only opens the steps the flags on your line left open, always in the same fixed order: artifacts, then scope, then runtimes, then the final plan and confirmation. That order is mechanical rather than aesthetic — the runtime step has to know the scope before it can check which destinations exist, so scope can never come after it.

| Line typed, in a terminal, inside a git repository | Steps that open |
| --- | --- |
| `install` | artifacts · scope · runtimes · plan |
| `install --ai-framework matt-pocock` | scope · runtimes · plan |
| `install --runtime cursor` | artifacts · plan |
| `install --bundle api-python --runtime cursor` | the plan, straight away |
| `install --from <url> --skill <name>` | scope · runtimes · plan |
| no TTY, no `--runtime` | none — exit `2` |

Giving `--runtime` on the line takes the scope question with it, since which runtime keys are valid is itself a function of scope — answering runtime implicitly answers scope. `--global` answers the scope step outright, and its *absence* only ever means "not stated," never "the project was chosen." `--from` keeps most of the wizard open — only the artifacts step consults a catalog, and a `--from` line already names `--skill` before anything is fetched, so that one step alone is skipped, and the embedded catalog is never touched. `--yes` skips no wizard step at all: it only skips the final confirmation, exactly as it does off the wizard.

The wizard is not a fourth command. Whatever it collects — ticked artifacts, a chosen scope, selected runtimes — becomes exactly the same request object a hand-typed flag line would have built, and the plan it shows before writing is the identical screen `--dry-run` prints.
