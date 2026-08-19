---
title: Install
description: How to get overpower, the op shortcut that is deliberately not installed, and the flag that proves the package arrived whole.
---

# Install

There is nothing to install, in the usual sense, to try overpower once:

```bash
uvx overpower@latest install --skill panlabs-python-standards --runtime claude-code
```

`uvx` downloads the package into an ephemeral, isolated environment, runs it, and throws the environment away. Nothing is left on the machine except whatever overpower itself wrote — no global site-packages entry, no leftover virtualenv, nothing to uninstall later because you tried a flag once. This is the right way to run overpower from CI, from a one-off terminal, or from any context where "installed forever" is the wrong default.

If you reach for overpower often enough that typing `uvx overpower@latest` every time is friction, install it as a persistent tool instead:

```bash
uv tool install overpower
uv tool upgrade overpower
```

That puts an `overpower` executable on your `PATH`, resolved once instead of on every invocation — which means it no longer self-updates the way `@latest` does, and `uv tool upgrade` becomes something you run on purpose.

## The `op` shortcut you have to make yourself

Typing `overpower` in full, every time, is longer than most people want. The obvious fix is a shell alias:

```bash
alias op='overpower'
```

overpower does not create this alias for you, and does not ship an `op` executable — that is a deliberate omission, not an oversight. `op` is already the name of the [1Password CLI](https://developer.1password.com/docs/cli/), which lives at `/usr/local/bin/op` on a great many developer machines and typically sits ahead of `~/.local/bin` — where a `uv tool install` would put an overpower binary — on `PATH`. Shipping a second `op` would silently shadow a credential tool, and `uv` will in fact refuse the *entire* installation the moment it detects a name collision among tools it manages (`error: Executable already exists: op`) — so even the honest failure mode costs you the `overpower` command too, not just the alias.

Whether occupying `op` on your own machine is safe is something only you know — you know whether 1Password's CLI is there. That is why the decision is left to you, as a line you type once, rather than baked into what the package installs. If you already use 1Password's `op`, pick a name that does not collide:

```bash
alias opw='uvx overpower@latest'
```

Keep in mind an alias is a convenience of an interactive shell and nothing more — it does not expand under `sh -c`, which is how a Makefile target or many CI runners invoke a command, so `op` inside one of those contexts fails with "command not found" regardless of what your shell profile defines. That costs nothing in practice, because the line a Makefile, a CI workflow, or this site itself actually writes is the full `uvx overpower@latest …` anyway — the alias is a keyboard shortcut for you, typed by hand, never something scripts are meant to depend on.

## `--version` as proof the package arrived whole

```bash
uvx overpower@latest --version
```

`--version` reads the version from the package's own installed metadata, not from a string hardcoded somewhere in the source. Since the catalog is embedded in the same wheel as the code — see [why `@latest` is a correctness requirement](/) — the version number `--version` prints is also, by construction, the version of the catalog that came with it. It is the cheapest available check that what landed on the machine is what was supposed to land: no partial install, no stale cache masquerading as current, no ambiguity about which catalog you are about to install from.
