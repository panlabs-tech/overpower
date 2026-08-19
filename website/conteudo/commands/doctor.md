---
title: doctor
description: What doctor checks, why it answers both scopes in one output, and what exit code 3 means.
---

# doctor

```bash
uvx overpower@latest doctor
```

`doctor` answers one question: is what was written still what was written? It reports two halves in a single output.

The **terminal** half reports four facts — whether a TTY is attached, what colour system was detected, the terminal width, and whether `NO_COLOR` is set — the exact set of facts that explains a screen that came out looking wrong, without needing a round trip to ask. The **integrity** half reads the runtime table in both project and machine scope and checks what it finds against what was actually installed. It reads both scopes because a target carries no manifest of its own — the closed runtime table is the only thing that knows where equipment can possibly be, so there is no way to check "just one scope" that would mean anything.

That two-scopes-at-once design is also why `doctor` has **no `--global` flag** — a flag that switched between reporting the repository and reporting the machine would turn one report into two, and the whole point is that both answers arrive together. Unlike `install`, running outside a git repository is not a refusal here either: `doctor` still answers, and simply reports nothing for the project half it cannot find.

## Three checks, three separate failure modes

- **`core.symlinks=false` breaking links.** This is the case where `git status` reports a clean tree while the equipment on disk is actually a plain text file — a symlink that got checked out literally because the clone disabled symlink support. `doctor` reads both places that setting can live, in git's own precedence order, and is the thing that catches what git itself will not tell you.
- **A link that does not resolve.** Equipment that is invisible in the worst way: the artifact appears in a listing, but nothing is actually behind the name.
- **Copies of one artifact that disagree.** The debt taken on specifically by project scope's choice to write a real copy rather than a symlink — two on-disk copies of what should be the same artifact, drifted apart.

Each of the three closes a hole none of the others catch, which is why all three run on every invocation rather than being optional checks.

## Exit code 3, and why that makes `doctor` usable as a gate

`doctor` exits `3` when it found a problem, and `0` when it did not — never `1` for an unhealthy result, because an unhealthy result is not a crash: the command ran correctly and computed a real, negative answer. That distinction is what lets `doctor` sit in CI right next to `install --dry-run` as a gate — a script can tell "the check ran and failed" apart from "the check itself broke" by exit code alone, without parsing output. See [Exit codes](/reference/exit-codes) for the full table.
