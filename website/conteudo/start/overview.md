---
title: overpower
description: What overpower is, the three questions its three commands answer, and why the version you pin is the catalog you get.
slug: /
---

# overpower

overpower is a CLI that installs curated agent equipment — skills, MCP servers, and whole frameworks of them — into a repository or onto a machine. It does not scaffold, it does not generate, and it does not ask an LLM anything. It copies files a curator already decided are worth having, and it grafts configuration a runtime already knows how to read.

```bash
uvx overpower@latest install --skill panlabs-python-standards --runtime claude-code
```

## Three commands, three questions

Every invocation of overpower answers one of exactly three questions.

| Command | Question | Answer |
| --- | --- | --- |
| `list` | What is there? | The catalog, or the whole content of one item in it. |
| `install` | Write it. | A plan, printed before anything touches disk, then the write itself. |
| `doctor` | Is it still what it was? | A report on the terminal and on the integrity of what was installed. |

Typed bare, `overpower` prints a banner and the top-level help, and exits `0`; `overpower --help` prints the same help. Under a pipe the banner is dropped and only the help goes through, so a `grep` or a redirect to a file gets something worth reading. `overpower --version` answers with the version that actually arrived, read from the package's own installed metadata rather than from a constant baked in at import time — which is what makes it evidence the package landed intact, not just a string somewhere in the source.

## Always `@latest`

The catalog overpower installs from is not fetched over the network at install time or at run time. It is **embedded in the package** — the trees under `content/` ship inside the wheel, and `list` reads them by walking the filesystem, not by calling out anywhere. That single fact has a consequence that is easy to miss: **the version of overpower *is* the version of the catalog it carries.** There is no separate "catalog version" to track, and no way to get a newer catalog without getting a newer overpower.

`uvx` complicates this in one specific way. Run as `uvx overpower`, without a version pin, `uvx` resolves the latest release the first time it is invoked in an environment and then **caches that resolution with no time-to-live** — a bare `uvx overpower` today and the same bare `uvx overpower` in six months can silently run the exact same build, and therefore serve the exact same catalog, unless something else forces a re-resolution. A catalog that never ages would be a curiosity; a catalog whose staleness is invisible is a defect.

`@latest` is what breaks that cache on every invocation:

```bash
uvx overpower@latest list
```

This is why every example on this site, and the one line this project asks you to actually type, pins `@latest` explicitly. It is not house style copied from some other README — it is the one spelling that keeps "the catalog I get" equal to "the catalog that exists," every time the command runs.

## Where to go next

[Install](/start/install) covers getting overpower onto a machine, including the one shortcut it deliberately does not create for you. [Concepts](/start/concepts) is the vocabulary the rest of this site leans on without re-explaining. [Commands](/commands/) starts the walkthrough of the three commands themselves, beginning with what is true of every invocation before you reach any single one of them.
