---
title: MCP servers
description: The graft — one key inside a file that is yours, secrets never written, and targets derived rather than declared.
---

# MCP servers

Every other artifact overpower installs **copies**: a file or a directory appears that was not there before, and `git status` shows it as new. An MCP server **grafts**: one key appears inside a configuration document you already own and already edit yourself, and `git diff` shows a change to your file rather than a new one.

```bash
uvx overpower@latest install --mcp cloudflare --runtime claude-code
```

Because the destination is somebody else's file — yours, not overpower's — three things follow from that, and all three are guarantees, not incidental behaviour.

**The plan names the file and the key, not just the file.** The last line before the write reads something like `.mcp.json › mcpServers.cloudflare ← claude-code` — the exact key about to be added or replaced, inside the exact document it lands in.

**The rest of the document survives byte for byte.** Comments are preserved, root keys the tool knows nothing about are preserved, and a server that was already present is not reformatted — not even reflowing its `args` array onto one line. Writing the whole file back out through a generic JSON serialiser would reflow it regardless of whether anything meaningful changed, and `git diff` would stop answering what the tool actually did versus what happened to be nearby.

**A server of the same name is overwritten, without asking and without `--force`** — the same rule a colliding path follows for a copied artifact. A configuration file that is *already* broken, on the other hand, is **refused, never repaired**: editing a file that is not overpower's, on the tool's own initiative, is not something an install is allowed to do. See [Troubleshooting](/reference/troubleshooting) for what that refusal looks like.

Where the runtime itself holds a freshly-written server back from actually connecting, the command says so. In Claude Code, a server written into `.mcp.json` is born pending approval and stays inert until you approve it there, so the install prints that warning naming the file — still at exit `0`, because the write itself succeeded and what remains is a step that belongs to you. Devin documents no equivalent gate for `.devin/mcp_config.json`, so nothing is printed for it: a warning that fired on every target regardless of whether it applied would be a warning nobody reads.

## `--global` writes your personal file instead

```bash
uvx overpower@latest install --mcp cloudflare --runtime claude-code --global
```

`--global` writes to one personal file per target instead of a repository one — `~/.claude.json` for Claude Code, the VS Code user profile (a different path per operating system), or Devin's machine-level configuration. That file is yours in a stronger sense than a repository file: `~/.claude.json`, for instance, also carries your user ID and onboarding state. Nothing else in it is touched, and — because a graft never replaces a whole file, only adds a key — there is no approval gate either: a server written into your own personal file is one you have already implicitly approved by having written it yourself.

## The secret is never written; the address is

A recipe declares a secret as a **slot** — a name and a role, never a value and never a specific spelling. What actually lands in the configuration file is the reference the runtime itself expands at connection time, not the secret:

```jsonc
"coolify": {
  "type": "stdio",
  "command": "npx",
  "args": ["-y", "@masonator/coolify-mcp@2.12.0"],
  "env": {
    "COOLIFY_BASE_URL": "https://vps.panlabs.tech",   // configuration, written
    "COOLIFY_ACCESS_TOKEN": "${COOLIFY_ACCESS_TOKEN}" // a secret, referenced
  }
}
```

Those two lines are the whole distinction: **a slot is what overpower refuses to write, and everything else in `env` is what it writes because it can.** An address like a base URL is not a secret, and treating it like one would only leave the server unable to find what it is supposed to talk to.

Three slot roles exist: `env`, `header`, and `bearer`. A `bearer` slot is rendered as `Authorization: Bearer ${VAR}` without the recipe itself ever having to spell that string out. No reference ever carries a default value — `${VAR:-fallback}` syntax is understood by exactly one runtime, and in every other runtime reading the very same `.mcp.json`, that whole expression is treated as a literal string instead of an interpolation, so the file still parses, the install still reports success, and the failure only surfaces the first time the server actually tries to start. If a slot's variable is not set at install time, the command says so and still exits `0` — the variable only has to exist when the runtime itself starts, and that is neither this shell nor this moment.

## Targets are derived, never declared

`list --mcp` prints a `targets` line for every recipe, but there is no `targets` field anywhere in the recipe file itself:

```
╭─ MCP server  grafts into the runtime's config ───────────╮
│                                                          │
│  cloudflare                                        http  │
│    Cloudflare's remote MCP server, over streamable       │
│    HTTP. It carries no secret in the file: the           │
│    connection authorises in the browser the first time   │
│    an agent uses it, so nothing here has to be filled     │
│    in before the server works.                            │
│                                                          │
│      overpower install --mcp cloudflare                  │
│                                                          │
│    url      https://mcp.cloudflare.com/mcp               │
│    targets  claude-code · project                        │
│             devin · project                              │
│                                                          │
╰──────────────────────────────────────────────────────────╯
```

Which pairs of runtime and scope a given recipe can actually serve is computed from its transport and the roles of its slots against a table in code, and printed fresh every time — never written down as a static field in the recipe. A declared field would go stale silently the day a runtime gained the capability to receive that server; a derived one cannot, because it is recomputed from the current table on every read. `claude-code` above shows only its project half because that is the half it actually has for this recipe — the same runtime can have no destination at all for a different server, or in the other scope, and `list` reports exactly that rather than a guess.
