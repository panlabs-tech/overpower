---
title: Screens
description: How a screen is tested — structure in the gate, one snapshot per screen.
---

# Screens

This page covers the terminal output as a tested surface: what a snapshot captures, which screens have one, and how to update a snapshot deliberately rather than by accident. It draws the line between what the gate asserts about structure and what the snapshot pins about appearance, and says which failures mean the screen changed and which mean the test did.

## What a snapshot is

Recorded screens live in `tests/snapshots/`, one plain-text file per screen, captured at 80 and 60 columns, without colour. Each one renders a **fixture**, not the shipped catalog, so a content refresh — a skill added, a description reworded upstream — does not rewrite screens that have nothing to do with content.

A snapshot is taken from the rendered console (`Console(record=True).export_text()`), never from the raw stream of bytes a terminal would receive. Those two are not the same thing: the raw stream also carries the transient progress bar's cursor-control sequences — clear line, move up, hide and show cursor — which describe an animation, not the screen a person actually sees at the end. Recording bytes would pin the animation; recording the rendered console pins the result.

Colour is never recorded into a snapshot. It is asserted structurally instead — see below — because gravure records exactly what colour looked like today, and this project's whole reason for splitting structure from appearance was measuring that colour changes should not be able to break a test.

## Structure lives in the gate, appearance lives in the snapshot

A full-session recording is a diff nobody reads: a small, deliberate visual adjustment can touch half the bytes of a long capture, and a real regression can hide inside that noise. Splitting the work in two is what keeps both cheap:

**The gate asserts structure** — properties with meaning, that a border or a spacing tweak has no business touching:

- piped output carries no ANSI codes at all;
- the banner is suppressed when there is no TTY;
- no description is truncated at either 80 or 60 columns;
- no rendered line exceeds the terminal width;
- every path in the plan is also in the rendered output.

**The snapshot pins appearance** — one file per screen, so a redesign that touches one screen shows up as a change to exactly one file, and a reviewer can see precisely what an aesthetic pass had licence to touch.

## Updating a snapshot

Rewriting a snapshot is an explicit act, never a side effect of running the suite:

```bash
uv run pytest --snapshot-update tests/test_screens.py
```

Run it only when a screen changed on purpose. If the diff after updating touches a screen you did not mean to change, that is the signal the change had a wider blast radius than intended — chase it before committing the new snapshot.

## The comparator has no dependency

There is no snapshot plugin in this project. The comparator is small and lives in `tests/support/snapshots.py`, alongside `--snapshot-update`, which is declared in `conftest.py`. One dev dependency less, and the update path stays something you read in the test file rather than something a plugin does for you behind the scenes.

## What is not a snapshot

The wizard's own selection screen — the list `questionary` draws for choosing artifacts — is largely not this project's to record: the lines a person picks from are drawn by `questionary`'s own `InquirerControl`, and recording someone else's rendering pins someone else's future change. What *is* this project's own drawing — the locked block, the viewport, the counter, the footer around that list — is asserted structurally instead: question, static block, viewport, counter and footer all have to fit within a real terminal's height, and the viewport itself can never fall below a floor of visible rows. Alongside that arithmetic, one PTY test proves that the surrounding chrome reaches a real terminal at all — the same split used everywhere else on this page: the PTY test proves the wiring, never the pixels.

See [Tests](/development/tests) for the rest of the testing doctrine, and [Development](/development/) for the loop these tests run inside.
