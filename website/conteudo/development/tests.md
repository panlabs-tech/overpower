---
title: Tests
description: The doctrine — the disk is real, one suite runs whole across nine cells, and the network never enters a gate.
---

# Tests

This page covers how overpower is tested and why that shape was chosen: the disk is real rather than mocked, there is one suite rather than a fast tier and a slow tier, and it runs whole across the nine cells of the matrix. It covers git running for real against a local remote, the rule that the network never enters a gate, and the three-way identity that decides whether a written artifact is the artifact that was meant.

| question | answer |
| --- | --- |
| filesystem double | **does not exist** — `tmp_path`, always |
| `git` behind `--from` | **real subprocess, against a local remote** |
| the real GitHub | **outside every gate** — a curation act, opt in with `OVERPOWER_NETWORK_TESTS=1` |
| plan × screen × disk | one assertion, the **three-way identity**, across all 9 cells |
| visual output | **structure in the gate**; one snapshot **per screen**, no colour, at 80 and 60 columns |
| interactive selection | the seam is a **stub**; one PTY test proves the wiring, POSIX only |
| coverage | ephemeral diagnostic, **nothing** in `pyproject.toml` |

## The disk is real

`tmp_path`, always. No `FakeFileSystem`, no port, no `mock_open`, no environment gate on a write test. A double that does not implement a real symlink and a real junction stays green exactly where the product breaks — and every write path has to exercise three concrete traps: removing a symlinked destination without writing through it, removing a junction with the predicate that actually recognises one (`os.path.islink()` is `False` for a junction, and `shutil.rmtree()` refuses it anyway — Windows only, keyed on `sys.platform`, never on an environment variable), and installing over a previous version without leaving a stale file behind, because an overlay copy that does not sync first lets yesterday's file survive and read as installed.

That third case is what ties write semantics to the three-way identity below: if the disk has to equal the plan, the destination of a planned write has to end up **equal to the source**, not overlaid on it.

## One suite, and it runs whole across the nine cells

There is no "runs on one platform only" category, and no `slow` marker. Splitting the suite does not buy time — measured, the fixed overhead of standing up a job is comparable to the whole battery — and what gets tested here is disk behaviour, which is precisely what diverges between the nine cells (three operating systems × three Python versions). A test that genuinely cannot run on a platform is keyed by `sys.platform`, never by an environment variable, so the exclusion cannot be silently forgotten out of a workflow file.

Three absences are recorded as **known**, not as coverage: the no-symlink-privilege case on Windows is not reproducible on hosted CI, because the runner image turns on Developer Mode; PyPy has no `CreateJunction`, and is not in the matrix; and building a `questionary` prompt does not run on the Windows cells, because the construction raises `NoConsoleScreenBufferError` in a process with no console screen buffer — which is what a `pytest` child on the hosted runner is, even though a real Windows terminal has the buffer and the product path is unaffected.

## `git` runs for real, and the remote is local

The primary path is `init` + `remote add` + `fetch --depth 1 origin <ref>` + `checkout FETCH_HEAD`, with an anonymous tarball as fallback. That is subprocess and network — and the cut separates the two: **the subprocess runs, the network does not.**

Against a local repository standing in for the remote, a branch, a tag and a full SHA all resolve; a ref that does not exist or a remote that does not exist both fail with `git`'s own exit code `128` and its own message text, reproduced byte for byte against a local remote. The honest limit is that fetching an arbitrary SHA also depends on the *server* allowing it (`uploadpack.allowAnySHA1InWant`), and only a real GitHub exercises that half.

| layer | double | where |
| --- | --- | --- |
| deciding to fall back | **stub** of the obtainer, returning the outcome | gate |
| primary `git` | **none** — real subprocess, local remote, in `tmp_path` | gate, all 9 cells |
| fallback decompression | **none** — real `tarfile` over a `.tar.gz` built in `tmp_path` | gate |
| fallback HTTP | **stub** of `urlopen` (200, 404, timeout) | gate |
| finding `SKILL.md` | **none** — real `os.walk` over `tmp_path` | gate, all 9 cells |
| the real GitHub | **none**, and **outside the gate** | curation |

The one assertion this doctrine bought with a live measurement: a search that finds nothing must not fall back — obtention failure falls back and exits `1` if the fallback also fails; obtained, searched, not found exits `3`, and the fallback is never invoked.

## The network never enters a gate

Whatever depends on a third party is verified by hand, at curation time, never by automation on a pull request or a release. The end-to-end test against the real upstream repository exists, is documented, and runs in no CI job:

```bash
OVERPOWER_NETWORK_TESTS=1 uv run pytest -m network
```

With the variable set, the skip condition can no longer be satisfied — a network test that gets renamed or lost turns red instead of quietly disappearing. The gate is its own, named marker, never the generic `CI` variable every runner sets.

## The three-way identity

A `--dry-run` has to mirror not just the exit code of a real run, but its content: the set of paths a dry run announces, the set a real run announces, and the set actually found on disk after the real run all have to be the *same* set. That single assertion proves three properties at once, and it runs across all nine cells, because the property most likely to break by platform — path separators, `Path` vs. `PurePosixPath`, a filesystem that ignores case — is exactly the kind of bug that passes green on a single cell.

The identity also drives the design, not just the test: the writer consumes the plan and nothing beyond it. A writer that recomputes a path could diverge from what the screen promised, and no later test would close that gap.

## Visual output: structure in the gate, snapshot per screen

Colour does not break a test; layout does — a full-session snapshot is a diff nobody reads, and a real regression hiding inside a 50%-changed file is invisible. One file per screen fixes the granularity problem: a redesign that touches one screen shows up as a change to one file, and a reviewer sees exactly what an aesthetic pass had licence to touch.

**In the gate, structure** — properties that carry meaning and must never regress, none of which break on a border tweak: piped output carries no ANSI at all, the banner is suppressed without a TTY, no description is truncated at 80 or 60 columns, no rendered line exceeds the terminal width, every planned path appears in the rendered plan.

**Outside the gate, as bytes, a snapshot** — one file per screen, at 80 and 60 columns, without colour, of the rendered console (never of the raw byte stream, which also records the transient progress animation rather than the final screen). The comparator is small and home-grown, with an explicit update path:

```bash
uv run pytest --snapshot-update tests/test_screens.py
```

See [Screens](/development/screens) for the mechanics of what gets captured.

## The wizard's seam is a stub, and it does not get a contract test

What the interactive wizard hands to the rest of the program is a request — artifacts, scope, runtimes. The flow tests inject that request through a thin seam; selection logic is tested against values, not against keystrokes. That seam does not emulate `questionary`'s behaviour, it supplies indirect input — it is a stub, and a stub does not owe a contract test. What proves the wiring itself is one PTY test, sending real keys and asserting on the request that comes out, never on pixels; it is POSIX-only, because the `pty` module does not exist on Windows, and that absence is declared rather than silently missing.

## Coverage

An ephemeral diagnostic, nothing more: no threshold in the gate, nothing in the dev dependencies, no badge. One documented command answers "what has no test at all" when someone asks it:

```bash
uv run --with pytest-cov pytest --cov=src/overpower --cov-report=term-missing
```

Mutation testing is a trigger, not something adopted up front — it would enter if a bug ever escaped with a green suite, aimed at the specific deterministic code involved, never as a gate.
