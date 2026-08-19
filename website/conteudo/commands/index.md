---
title: Commands
description: The shape of the line — selectors mix freely, and the plan always runs in the same order.
---

# Commands

Before any single command, two things hold across all of them.

## Selectors compose

`--ai-framework`, `--bundle`, `--skill`, and `--mcp` are **selectors** — flags that name what a line is about. Every one of them accepts a comma-separated value, a repeated flag, or both, and they accumulate rather than override:

```bash
overpower install --skill one-skill --skill another-skill --bundle api-python,another-bundle
```

Mixing selectors of different kinds on a single `install` line is the normal case, not an edge case — `--ai-framework matt-pocock --skill some-other-skill --mcp cloudflare` is one ordinary invocation, not three commands stitched together. `list` is the one place this does not hold: it answers about a single item, so more than one selector on a `list` line is a question with two answers, and the command refuses rather than silently picking one.

## The plan runs in one fixed order

When a line resolves to writes across more than one unit — a framework and an individual skill on the same `install`, say — the writes always happen in the same order: **framework, then bundle, then individual artifact, then MCP server.** This is not the order you typed the flags in; it is fixed regardless of how the line reads.

The order matters most where two selections would land on the same destination. Rather than raising an error for that overlap, the fixed order decides it: the most specific unit is written last, so its content is what survives on disk. An individual artifact is more specific than a bundle, which is more specific than a framework — so if a framework and a directly named artifact both happen to touch the same path, the direct artifact wins, because it is written after.

Continue to [`list`](/commands/list), [`install`](/commands/install), or [`doctor`](/commands/doctor) for what each command does on its own.
