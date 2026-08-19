---
title: "--from"
description: Any GitHub repository as a search root, and how a tree path pins a branch, a tag, or a commit.
---

# --from

```bash
uvx overpower@latest install --from https://github.com/owner/repo --skill some-skill --runtime codex
```

The catalog embedded in overpower ages by construction — it is fixed at the version you have installed, and refreshing it means waiting for a new curation pass. `--from` is the escape hatch that does not wait: it points at **any GitHub repository, with no registration step**, and reads from there instead of the embedded catalog.

`--from` is **exclusive**. Once it is on the line, only the remote repository is consulted — the embedded catalog is not searched at all, and not merged with the remote either. That settles the question of precedence between the two by removing it rather than answering it.

`--from` reaches **three of the four units** on both `install` and `list`: `--skill`, `--mcp`, and `--bundle`. Bare — with no selector at all — it answers the question before the name: *what does this repository offer?* The one flag it refuses is `--ai-framework`, and that refusal is a decision rather than a missing feature: an AI Framework is a folder of overpower's own package, so there is nothing in someone else's repository for the flag to name. A line pairing the two is refused by name, before anything is fetched over the network.

`--from` is also the axis that separates a market MCP server from a homegrown one — there is no other axis for that distinction. The embedded recipe for a server lives at `catalog/mcps/<slug>.toml` inside the package; a federated one lives at `.overpower/mcp/<slug>.toml` inside whatever repository `--from` points at, discovered by the same search rule described below. Both use the identical recipe schema.

## The federated bundle

```bash
uvx overpower@latest install --from https://github.com/owner/repo --bundle api-python --runtime codex
```

A **bundle** is a named composition — *"to work in this context, install these artifacts"* — and a repository federates one by writing `.overpower/catalog.yaml` at its root:

```yaml
bundles:
  api-python:
    description: Everything needed to work on the Python API.
    items:
      - fastapi-conventions
      - pytest-fixtures
```

That file is read by the **same reader** that reads the catalog overpower ships, so a malformed manifest is refused naming the same field on both sides and there is no second validator anywhere to disagree with the first. `items` are **names**, never paths, resolved against the skills that same repository offers under `skills/` — they reach neither the embedded catalog nor a third repository. A name that does not resolve exits `3` and says which name, so the problem goes back to whoever wrote the manifest.

The manifest is **optional**. A repository that has never written one keeps its skills listed and installable; its `list --from` simply omits the bundles section. `.overpower/` deliberately carries two formats — `catalog.yaml` for the manifest and `mcp/<slug>.toml` for recipes — because it is a namespace rather than a format.

Unlike `--skill` and `--mcp`, `--bundle` does **not** treat the URL as a search root: the manifest is read from the repository root, and a subfolder in the URL does not interfere. What a repository composes is a property of the repository, not of the path you pasted — a vendored dependency's own `.overpower/catalog.yaml` speaks for its own repository, never for this one.

## The URL is a search root, not an address

```bash
uvx overpower@latest install --from https://github.com/owner/repo/tree/main/some/subfolder --skill some-skill --runtime codex
```

The repository root, a subfolder inside it, or the skill's own folder directly all resolve to the same result — overpower searches from wherever the URL points, rather than expecting an exact path to the artifact. Appending `tree/<ref>/<path>` to the URL pins a specific branch, a tag, **or a full commit SHA** — pinning a SHA is what makes a `--from` install fully reproducible, since the address someone pasted into an issue or a chat is then guaranteed to resolve to the same content every time.

## Obtaining the content

overpower uses your local `git` installation as the transport, and reuses whatever credentials it already has configured — so a private repository you can already clone works here too, with no separate authentication step. If `git` itself is unavailable, it falls back to fetching an anonymous tarball using only the Python standard library, so no third-party binary becomes a hard requirement either way.

There is **no cache**. Every `--from` run fetches fresh, by decision — remote content changes on someone else's schedule, and a locally cached copy would silently defeat the entire reason `--from` exists.

## What changes about the plan

Content installed via `--from` still goes through the same plan, the same confirmation, and the same `--dry-run` mirror as content from the embedded catalog — the write mechanics do not change. What changes is [provenance](/start/concepts): the plan and the resulting install record that this artifact came from a specific remote repository at a specific reference, rather than from the version of overpower you ran.
