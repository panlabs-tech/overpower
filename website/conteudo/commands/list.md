---
title: list
description: The four blocks of the catalog, the line that installs each item, and the selectors that narrow the output.
---

# list

Run bare, `list` prints the whole embedded catalog in four blocks:

```bash
uvx overpower@latest list
```

| Block | What it holds | How it installs |
| --- | --- | --- |
| **AI Frameworks** | a self-contained body of equipment from one upstream | whole, never a slice of one |
| **Pool skills** | artifacts curated to stand alone | alone, by name |
| **Bundles** | a named set of pool artifacts | expands to exactly what its manifest names |
| **MCP servers** | a recipe for a server, not a folder | grafts one key into the runtime's own config |

Every entry prints with its size, its file count, and its description **in full** — never truncated, rendered at both 80 and 60 columns, because the description is the thing the decision to install is actually made on. Under each description sits the line that installs it, and — for an AI Framework and a bundle, the two units that carry something worth opening — the line that opens it too:

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

That command line is deliberately bare: no `$` prompt in front — which would make a selected line paste back broken — and no label column, because none fits; the words `install` and `list` inside the command already are the label. It wraps rather than truncates, since a command cut off at the terminal edge is a command nobody can type back correctly, and it survives being piped: the banner is a courtesy gated on `isatty()`, but a command is data, so `overpower list | grep <name>` still hands back a usable line.

An MCP server has no size — it never lands as a file on disk, so where a size would sit, `list` prints the **transport** instead, which is what actually says how the server is reached.

## Narrowing to one item

One selector opens exactly one item, and each takes a single name:

```bash
uvx overpower@latest list --ai-framework matt-pocock   # every artifact inside it, printed in full
uvx overpower@latest list --skill panlabs-python-standards
uvx overpower@latest list --bundle api-python
uvx overpower@latest list --mcp cloudflare
```

`--skill` and `--bundle` carry the same short forms `install` uses, `-s` and `-b`. `--mcp` has no short form, because it is already three letters and a short flag would not save enough to be worth spending. `--ai-framework` also has no short form — `-f` is reserved for `--force` on `install`, and a letter meaning one thing on one command and something else on another is worse than typing the word.

Two selectors on one `list` line is a question with two answers, and the command refuses, exit `2`, naming both flags it was given. A name that is not in the catalog also exits `2`, with the whole closed list printed in the message — the catalog is closed, so a miss is always a defect in what was typed.

## `list --mcp` — the recipe in full

A recipe is the logical declaration of a server, and this is the screen it is judged on before it ever gets wired into an agent:

```
╭─ MCP server  grafts into the runtime's config ───────────╮
│                                                          │
│  cloudflare                                        http  │
│    Cloudflare's remote MCP server, over streamable       │
│    HTTP. It carries no secret in the file: the           │
│    connection authorises in the browser the first time   │
│    an agent uses it, so nothing here has to be filled    │
│    in before the server works.                           │
│                                                          │
│      overpower install --mcp cloudflare                  │
│                                                          │
│    url      https://mcp.cloudflare.com/mcp               │
│    targets  claude-code · project                        │
│             devin · project                              │
│                                                          │
╰──────────────────────────────────────────────────────────╯
```

Every label but the last one is a field of the recipe itself, spelled the way the underlying TOML spells it — `url` for an HTTP server, or `command`, `args`, and `env` for a stdio one. `targets` is the exception: there is no `targets` field anywhere in the recipe. Which pairs of runtime and scope a given server can actually serve is **derived**, computed from the transport and the roles of its slots against a table in code, never declared by hand in the recipe — a declared field would go stale in silence the day a runtime gained the capability, leaving the recipe lying about itself. See [MCP servers](/targets/mcp) for how that derivation works.

Each target printed is a **pair**: a runtime and the scope it reads that server in. `claude-code` here shows only its project half, because it is the half that exists — the same runtime may read nothing at all in global scope for a given server. A recipe that no target can serve at all prints `none` rather than an empty line.

## `list --from` — previewing what someone else's repository offers

```bash
uvx overpower@latest list --from https://github.com/owner/repo
uvx overpower@latest list --mcp coolify --from https://github.com/owner/repo
uvx overpower@latest list --bundle api-python --from https://github.com/owner/repo
```

Bare, `list --from` prints that repository's **showcase**: the skills under `skills/`, the recipes under `.overpower/mcp/`, and the bundles declared in `.overpower/catalog.yaml`. Each of those three also takes a selector, so a single item can be read whole before anything is installed. Every command the showcase prints carries the `--from` back, because an item read this way is not in the embedded catalog and the line without it would be answered by a different catalog.

The one flag `--from` refuses on `list` is `--ai-framework`, and the refusal is a statement about the model rather than a queue position: a framework is a folder of the overpower's own wheel, so there is nothing in someone else's repository for the flag to name. That line exits `2` before anything is fetched.

The three selectors do not read the URL the same way. `--skill` and `--mcp` treat it as a **search root** — the repository, a subfolder, or the artifact's own folder all reach the same result. `--bundle` and the bare showcase are **anchored** at the repository root, so the URL's subfolder narrows nothing: what a repository offers, and what it composes, are properties of the repository rather than of the path you happened to paste. See [--from](/targets/from) for the URL forms it accepts and how a `tree/<ref>/<path>` segment pins a branch, a tag, or a commit.

A bundle names skills of that same repository and reaches nowhere else — not the embedded catalog, not a third repository. A name it lists that the repository does not offer exits `3` and says which name, so the report goes to whoever wrote the manifest instead of turning into guesswork.
