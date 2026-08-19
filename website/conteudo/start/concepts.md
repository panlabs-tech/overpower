---
title: Concepts
description: The vocabulary — AI Framework, pool skill, bundle, recipe, slot, precondition, runtime, scope, provenance.
---

# Concepts

The rest of this site uses these terms without pausing to redefine them. This page is where that definition lives.

## The three installable units

overpower's model has exactly three units you can ask for, and they are not levels of one hierarchy — you pick among them, not up or down a ladder.

**Artifact** is the atom: a single skill, command, agent, or MCP server, curated on its own. An artifact lives in the **pool**, installs by itself, and is the only kind of thing a bundle is allowed to name.

**AI Framework** is a self-contained body of equipment from a single upstream source — Matt Pocock's skill collection is the one this package currently vendors. A framework installs **whole**, never as a slice; its artifacts live inside the framework's own context, not in the pool, and cannot be requested individually. The name you type at `--ai-framework` is overpower's own name for the framework, which is not always the name of the upstream it came from — the origin is recorded in `NOTICE`, a file the product itself never reads.

**Bundle** is a named collection of pool artifacts assembled for one context of work — `api-python` is the one this package ships today. A bundle carries no content of its own: it is a manifest that points at artifact names, and expands into exactly what that manifest lists.

## Where content comes from

**Pool** is the set of individually curated artifacts, organized by type — the source both a direct `--skill` install and every bundle draw from.

**Catalog** is everything overpower knows how to install — artifacts, frameworks, and bundles together. It is curated, not open, and it is not a registry in the usual sense: the embedded catalog *is* the artifact tree inside the package, discovered by walking the filesystem rather than read from an index file.

**Recipe** is the logical declaration of one MCP server — its transport, how to reach it, its slots, its preconditions. A recipe never lands on disk as a file; what lands is the fragment rendered from it into a document you already own. One recipe file exists per server, and the same recipe schema is used whether the server came from the embedded catalog or from `--from`.

**Provenance** is where a piece of content came from — the origin and the way it was obtained, embedded in the package or fetched remotely. It describes the catalog's own history, never the target it lands in.

## The vocabulary of the MCP graft

**Slot** is where a secret belongs in a recipe, declared as a **name and a role** — `env`, `header`, or `bearer` — and never as a value. A slot is exactly what overpower refuses to write to disk; everything else a recipe declares, it writes because it can.

**Precondition** is a check a recipe can name, from a closed vocabulary overpower itself implements: does a given command exist, is a given variable set, does a given path exist. A recipe only ever names *what* to check — the code that performs the check is always overpower's own, never something fetched and executed from wherever the recipe came from.

## What decides where things land

**Runtime** is the tool that consumes what overpower installs — Claude Code, Cursor, Codex, Copilot, Devin, and many more. Each runtime has its own path convention and, for grafts, its own configuration format. See [Targets](/targets/) for the full table.

**Scope** is which of two places overpower writes to: the current repository, or the current machine (selected with `--global`). The two scopes are not symmetric — a repository write can rely on `git status` to reveal or undo a mistake, a machine write cannot, and the rules each command follows differ accordingly.

The catalog tree itself is the map these terms describe — `content/pool/`, `content/frameworks/`, the bundle and framework entries in `catalog.yaml` — and this page is only the legend for reading it.
