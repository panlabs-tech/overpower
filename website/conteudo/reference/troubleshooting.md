---
title: Troubleshooting
description: The common refusals, what each one means, and what to do about it.
---

# Troubleshooting

This page is organized by the message you actually saw, quoted as overpower prints it, so you can find your line by matching text rather than by guessing the internal cause first. Wherever a message names a specific value — the runtime you typed, the scope, a path — it is marked here as ‹placeholder› rather than filled in, since the real message names whatever you actually gave it.

### `not inside a git repository: pass --global to write under the home directory`

You ran `install` outside a git repository without `--global`. Project scope requires a repository to write into — the rule this product follows is that git is the manifest of what got installed, and that only holds where git exists. Either run the command inside a repository, or add `--global` to write under your home directory instead. Exit `2`.

### `unknown runtime ‹key›; the table is: ‹every known key›`

The value you gave `--runtime` is not in the closed table at all — not a typo of scope, an actual miss. The message lists every valid key because there is no partial match or `--dir` escape hatch to fall back on; see [Targets](/targets/) for the full table with what each one reads. Exit `2`.

### `‹key› has no destination in ‹scope› scope; install in the repository instead of the machine`

The runtime key you gave is real, but it has no destination in the scope you asked for — this happens for `eve` and `promptscript` under `--global`, since neither declares a global destination. The value was valid, the flag was valid; what does not exist is that specific pairing. Drop `--global`, or pick a different runtime. Exit `3`.

### `unknown skill ‹name›; the pool is: ‹every known skill›`

The name you gave `--skill` is not in the pool. The message prints the whole pool because it is small enough to read in full — check it against [Reference](/reference/) for what is actually installable today. Exit `2`.

### `list shows one item at a time, and got ‹every flag you gave›`

More than one selector was given to `list` on the same line — `--skill` and `--bundle` together, for instance. `list` answers about exactly one item; naming two is a question with two answers, and the command will not silently pick one for you. Drop all but one selector. Exit `2`.

### `‹name› is not an MCP server in this catalog; it is named under ‹the flag it actually belongs to›`

You gave a real catalog name to the wrong selector — for example, passing a skill's name to `--mcp`. The message names the flag the value actually belongs under, so the fix is usually moving one word rather than looking anything up. Exit `2`.

### `already exists, use --force to overwrite: ‹the colliding paths›`

In global scope, off a terminal (or under `--yes` / `--dry-run`), a destination that already has content there is refused rather than silently replaced — global scope has no `git status` to reveal or undo an overwrite the way project scope does. Add `--force` if overwriting is what you actually want, or run interactively and answer the confirmation prompt instead. Exit `3`.

### `‹path› is not ours to repair, and it is broken: ‹what is wrong with it›`

The MCP configuration file overpower would graft into already fails to parse, for a reason of its own — invalid JSON, most commonly. overpower will not repair a file it does not own; fix the file by hand first, then re-run the install. Exit `3`.

### `--from ‹url› is not a GitHub repository URL: ‹the specific rule it broke›`

The value given to `--from` failed one of a few checks before any network call was made: it may not point at `github.com` at all, it may be missing either the owner or the repository segment, a path below the repository may not follow the `tree/<ref>/<path>` shape GitHub itself uses, or it may contain a `.` or `..` path segment, which is never part of a real GitHub URL. Fix the URL to match a real repository address. Exit `2`.
