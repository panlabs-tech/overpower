---
title: Reference
description: The catalog as it stands today — one AI Framework, one bundle, one pool skill, four MCP servers.
---

# Reference

This is what ships inside the package right now, in this release. The catalog is embedded, not fetched, so this list describes exactly the version you have installed — a newer release may carry more, but this page describes today's.

## AI Frameworks — 1

**`matt-pocock`** — Matt Pocock's agent skills for real engineering: grilling, spec and ticket flows, TDD, code review, domain modelling, and more. 25 skills, 74 files, installed whole with `--ai-framework matt-pocock`.

## Bundles — 1

**`api-python`** — Equipment for working on a Python API. 8 files. Currently names one pool artifact: `panlabs-python-standards`. Installed with `--bundle api-python`, or its contents can be requested individually through `--skill`.

## Pool skills — 1

**`panlabs-python-standards`** — A reference standard for Python backend work: contracts and ports, code composition and shape, module topology, the error model, testing doctrine, and machine-configuration discipline. Written for a use-case-shaped service, it settles the recurring questions of that shape — where a file belongs, what an error returns, what counts as a real dependency versus a fake one, what a passing test is actually allowed to assert. Installed with `--skill panlabs-python-standards`.

## MCP servers — 4

| Server | Transport | What it does |
| --- | --- | --- |
| `cloudflare` | HTTP | Cloudflare's remote MCP server. Authorises in the browser on first use — no secret is ever written to the configuration file. |
| `coolify` | stdio | Coolify's API server, run as a local process. Deploys and inspects the applications, databases, and servers of a Coolify panel; the panel address is written as configuration, the access token is only ever referenced. |
| `github` | HTTP | GitHub's remote MCP server. Reads and writes issues, pull requests, and workflows in whatever repositories your personal access token can see. |
| `hostinger-vps` | stdio | Hostinger's API server, run as a local process. Manages VPS instances, DNS records, and domains through the Hostinger API, authorised with an API token that has to be present in the runtime's own environment. |

Run `list` for the live version of this page — the same four blocks, with every description printed in full and the exact command that installs each item.
