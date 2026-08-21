#!/bin/sh
# The documentation sweep trigger. It does NOT sweep: it launches whoever
# sweeps, and returns.
#
# The documentation of this project left here in #151 and lives in
# `panlabs-docs`. What left along with it was the coupling: before, changing
# behaviour and changing the page that describes it was the same PR. This
# script puts the coupling back from outside, without bringing the
# documentation back here.
#
# THIS SCRIPT IS NOT A GATE, AND THAT IS A REQUIREMENT. It blocks no commit, no
# push, no merge, and it is in no job's `needs`. It exits 0 on every path,
# including the error ones. What enforces is the gate of the OTHER repository,
# over the `main` of the other repository, and the `lefthook.yml` here records
# why that split is the design and not a loosening.
#
# MARKER-GATED, in the shape of `~/.claude/hooks/context-economy-injector.py`:
# with no sibling on disk, no skill inside it, or no `claude` on `PATH`, it
# exits silently. A machine that has only this repository feels no difference,
# and the file can be versioned without imposing anything on anyone.
#
# THE TRIGGER CONDITION IS THE PIN, NOT THE VERSION. This script cannot compare
# releases, and must not: it asks the other repository's `npm run pino --
# --verificar` whether there is debt. That makes it idempotent (a pull that
# brings nothing launches nothing) and makes the sweep coalesce by itself,
# because the pin is a cursor: three accumulated releases become a single
# sweep.
#
# The codes the pin returns, and there are three of them on purpose:
#   0  up to date                 nothing to do
#   1  behind                     launch
#   2  could not ask (network)    do NOT launch; try again on the next pull

set -eu

SIBLING="${OVERPOWER_DOCS_REPO:-$(CDPATH= cd -- "$(dirname -- "$0")/../../panlabs-docs" 2>/dev/null && pwd || true)}"
[ -n "${SIBLING:-}" ] || exit 0
[ -d "$SIBLING/.git" ] || exit 0

SKILL="$SIBLING/.claude/skills/varredura-overpower/SKILL.md"
[ -f "$SKILL" ] || exit 0

command -v claude >/dev/null 2>&1 || exit 0
command -v npm    >/dev/null 2>&1 || exit 0

# `post-merge` fires on any `git pull`, including on a working branch. Only
# `main` carries a published release.
[ "$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '')" = "main" ] || exit 0

# One sweep at a time. The other repository does not accept two PRs open at
# once: its gate 4 pins the page count, and two PRs adding one page each pass
# on their own and break together after the merge.
#
# `mkdir` is the atomic lock of POSIX; `-p` does not serve, because it succeeds
# when the directory already exists, which is exactly the case that has to
# fail.
LOCK="${XDG_STATE_HOME:-$HOME/.local/state}/overpower/docs-update.lock"
mkdir -p "$(dirname "$LOCK")"
if ! mkdir "$LOCK" 2>/dev/null; then
  # A lock left by a session that died cannot silence the trigger forever. Half
  # an hour is generous for a sweep and short for a crash.
  if [ -n "$(find "$LOCK" -maxdepth 0 -mmin +30 2>/dev/null)" ]; then
    rmdir "$LOCK" 2>/dev/null || true
    mkdir "$LOCK" 2>/dev/null || exit 0
  else
    exit 0
  fi
fi

# FROM HERE ON EVERYTHING IS DETACHED, AND THE ORDER MATTERS.
#
# Asking the pin is an HTTP call: up to three attempts of ten seconds, measured
# at 1.05 s with PyPI answering well. Doing it here, before detaching, would
# put thirty seconds of network inside `git pull` in the worst case. The rule
# of this repository is that nothing here blocks, so whoever asks is the
# outside process, not the hook.
#
# What the hook does synchronously is only the guards above, all local:
# measured at 0.00 s off `main` and with no sibling.
#
# `--dangerously-skip-permissions` is not carelessness: this process is
# detached and has no terminal, so a permission prompt would have no one to ask
# and would hang forever. What limits the damage is not the permission of the
# agent, it is the ruleset on the `main` of the other repository: empty
# `bypass_actors` and the `gate` check required. Nothing lands there without a
# green PR, including what comes from here.
#
# `setsid` releases the process from the process group of `git`, so that
# closing the terminal where `git pull` ran does not kill it along. With no
# `setsid` on the machine, `nohup` covers the essential.
LOG="${XDG_STATE_HOME:-$HOME/.local/state}/overpower/docs-update.log"

LAUNCHER="nohup"
command -v setsid >/dev/null 2>&1 && LAUNCHER="setsid"

$LAUNCHER sh -c '
  SIBLING="$1"; LOG="$2"; LOCK="$3"
  # The lock is released on every exit path, including the error ones. A leaked
  # lock would silence the trigger for thirty minutes with nobody knowing why.
  trap "rmdir \"$LOCK\" 2>/dev/null || true" EXIT INT TERM

  cd "$SIBLING" || exit 0

  # `pino` and `--verificar` are the interface of the sibling repository, not
  # ours, so they are spelled the way that repository spells them.
  PIN=0
  npm run --silent pino -- --verificar >/dev/null 2>&1 || PIN=$?

  # 0 up to date, 1 behind, 2 could not ask. Only 1 orders a sweep.
  [ "$PIN" -eq 1 ] || exit 0

  printf "\n=== %s — pin behind, sweeping ===\n" "$(date -Iseconds)" >> "$LOG"
  # The prompt stays in Portuguese because it is copy addressed to a
  # Portuguese-language skill in the sibling repository, and what it has to
  # match is the description of that skill.
  claude -p "varre a documentação do overpower" \
         --dangerously-skip-permissions >> "$LOG" 2>&1
  printf "=== %s — sweep finished (exit code %s) ===\n" "$(date -Iseconds)" "$?" >> "$LOG"
' _ "$SIBLING" "$LOG" "$LOCK" >/dev/null 2>&1 &

exit 0
