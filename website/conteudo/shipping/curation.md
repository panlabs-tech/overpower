---
title: Curation
description: How vendored content is refreshed, and what earns a place in the catalog.
---

# Curation

This page covers the two questions that decide what overpower carries: how content vendored from upstream is refreshed without drifting, and what a candidate has to be before it earns a place in the catalog. It states the criterion explicitly, including the kinds of thing that are deliberately refused.

## Refreshing is deliberately an act, not automation

Refreshing the catalog is something a person does by hand, on purpose — not a scheduled job. A gate blocks what this repository controls; what depends on a third party is verified here, by hand, because automating a check against someone else's repository would put a third party's availability and stability inside this project's CI, which was measured unstable and rejected for exactly that reason (see [Tests](/development/tests) for where the same reasoning shows up as "the network never enters a gate").

A refresh follows a fixed sequence:

1. **Read the upstream's own manifest** at the new reference to get the set of what it offers — for `mattpocock/skills`, the `skills` array of `.claude-plugin/plugin.json`, and specifically never the `version` field beside it, which was measured standing still while the array itself moved.
2. **Replace the tree**, applying the curation transform. If what lands is not the versioned tree verbatim, the transformation happens at curation time and the vendored output is what ships — the product itself stays a straight copy, never a transformer.
3. **Update `NOTICE`** — the reference and the commit, per origin — and `licenses/` if the upstream's licence file moved.
4. **Run the four development commands** (see [Development](/development/)), plus the one network test below.
5. **Bump the version.** The version of overpower *is* the version of the catalog it embeds, so a refresh nobody can install is not a refresh. This step is no longer something to remember: `src/overpower/content/` is inside the wheel, so [`release-ready`](/shipping/releasing) refuses the pull request until the bump happens.

## The one test that touches the real GitHub

It exists, it is documented, and it runs in **no** CI job — not on a pull request, not on a release:

```bash
OVERPOWER_NETWORK_TESTS=1 uv run pytest -m network
```

With the variable set, the test's skip condition can no longer be satisfied, so a network test that gets renamed or lost turns red instead of silently vanishing. Run it as part of a refresh, alongside the four development commands — it is a curation step, not a gate.

## What earns a place in the catalog

Three gates decide whether a candidate becomes an AI Framework, and the first one that fails ends the evaluation:

1. **Legal (a veto).** The content has to be redistributable inside the wheel. Anything not MIT requires a composed SPDX expression in the metadata — otherwise the package would misrepresent itself to exactly the audience deciding whether it clears a corporate licence allow-list.
2. **Self-contained.** What lands has to work without tooling overpower cannot guarantee on the target. Failing here is not "this framework was rejected" — it is "this is not an AI Framework under this model," because being self-contained is identity, not a quality bar to clear.
3. **Transformation happens at curation.** If what ships is not the tree exactly as versioned upstream, the transformation happens during curation, with the transformed output vendored — the product itself never transforms content at install time.

The criterion lives in the curator's judgement, not in a field on the catalog: a field that recorded "this passed" would just be a constant, since the catalog only ever contains things that already passed.

A pool artifact — a skill, a command, an agent, standing alone rather than bundled into a framework — is curated more freely, under two of the same clauses: the same legal veto, and the same requirement that the artifact works without tooling overpower cannot guarantee on the target. A pool artifact whose text tells the reader to invoke another one is still admitted on its own, because nothing in this model creates a dependency between artifacts — it simply arrives alone if it is requested alone. And a framework's legal veto does not propagate down to an individual atom pulled from it: provenance is a property of the body, not of the atom, and the target never carries attribution regardless.

Writing inside a file the user already owns does not, on its own, disqualify anything — a graft (an MCP server, for instance) is a legitimate class in this model. What has actually failed this criterion in practice was tooling: a candidate was rejected because its landed content required Node ≥22 and its hooks embedded the absolute path of the binary on the machine that installed it — a self-containment failure, not a licensing one.

The tooling clause reads differently for a graft, and without that distinction the whole class would be stillborn: nearly every stdio MCP server is launched through `uvx`, `npx` or `docker`, and a literal reading of "no required tooling" would reject all of them. What differs is what actually lands. A copy lands **content that only works with that tooling**, and its absence is this project's own defect, discovered by the user after the fact. A graft lands a **declaration**, and the tooling belongs to the server, not to something overpower brought along — so the recipe declares what it needs as a precondition, and overpower checks that precondition before writing, refusing with exit `3` and naming what is missing rather than writing something broken. What still fails this gate is a requirement the recipe never declared.

See [Shipping](/shipping/) for where curated content lands inside the package, and [Releasing](/shipping/releasing) for how a refresh becomes a published version.
