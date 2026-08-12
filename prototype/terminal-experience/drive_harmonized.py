r"""PROTOTYPE — throwaway. Drive `install_harmonized.py` through a real PTY, keep colour.

`questionary` needs an actual terminal — a pipe raises `EOFError` (#4, measured,
same as this branch's own `drive.py`). So this forks a PTY, sends keystrokes, and
captures every frame — same technique as `drive.py`, with ONE correction:

**`drive.py`'s frame-cleaning regex throws SGR away with the rest of the CSI
noise.** It strips `\x1b\[[0-9;?]*[a-zA-Z]` wholesale, and `m` — the terminator
of every colour/bold/dim/italic code — is inside `[a-zA-Z]`. That is exactly
right for judging STRUCTURE (`drive.py`'s job, comparing six variants' shape)
and exactly wrong for judging COLOUR, which is this prototype's whole point.

The fix keeps the same job — drop cursor movement, erase-line, save/restore
cursor, scroll — but names the finals explicitly and leaves `m` out of the set,
so a colour code survives untouched:

    \x1b\[[0-9;?]*[ABCDEFGHJKSTfsu]

Frame boundaries are still `\x1b\[\d*J` (erase display) — that one is a
legitimate separator, not colour, so it stays exactly as `drive.py` had it.

The surviving SGR is then handed to `rich.text.Text.from_ansi()`, which decodes
real ANSI into a `Text` with real `Style` objects — colour, bold, dim, italic —
and THAT is what gets printed into a recording `Console` and exported to SVG.
"""

from __future__ import annotations

import os
import pty
import re
import select
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.text import Text

REPO_ROOT = os.environ.get("OVERPOWER_REPO", "/home/paninit/workspaces/panlabs-tech/overpower")
PROTO_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = Path(
    os.environ.get(
        "PROTO_RENDERS",
        "/tmp/claude-1000/-home-paninit-workspaces-panlabs-tech-overpower/"
        "f9d1ef5b-3756-44d2-aae7-2e3627627a36/scratchpad/overpower-proto-renders",
    )
)

# Two Enters: accept the default scope ("This project"), then accept whatever
# detection pre-checked on the runtimes step (real detection, this machine —
# `Claude Code` reads `.claude/skills` in this very repository).
#
# Measured: a down-arrow before the first Enter does NOT buy a clean extra
# frame — prompt_toolkit repaints an in-place pointer move by overwriting the
# same line count, with no erase between it and the first paint, so the two
# merge into one confusing frame under this capture technique (same
# limitation this branch's own `drive.py` has, just visible now that colour
# survives to show it). Enter alone still exercises every recoloured class at
# least once: `qmark`/`question`/hint-spacing/`pointer`+`highlighted` on the
# default row of the scope step, `answer` on its collapse, and — on the
# runtimes step — the patched `☑`/`☐` glyphs plus `selected` on whatever
# detection pre-checked.
KEYS = "\r\r"

env = dict(os.environ, COLUMNS="80", LINES="40", TERM="xterm-256color")

pid, fd = pty.fork()
if pid == 0:
    os.chdir(REPO_ROOT)
    python = os.path.join(REPO_ROOT, ".venv", "bin", "python3")
    os.execvpe(python, [python, os.path.join(PROTO_DIR, "install_harmonized.py")], env)

buf = b""
sent = 0
deadline = time.time() + 25
while time.time() < deadline:
    r, _, _ = select.select([fd], [], [], 0.4)
    if r:
        try:
            chunk = os.read(fd, 65536)
        except OSError:
            break
        if not chunk:
            break
        buf += chunk
    else:
        if sent < len(KEYS):
            # 1.5s and not drive.py's 0.5s: measured, the runtimes step builds
            # and paints a 57-choice list, and firing the next key the instant
            # the PTY goes quiet for 0.4s caught that paint still settling —
            # the checkbox's "asked" frame never got its own erase-delimited
            # boundary and merged invisibly into its own collapse.
            time.sleep(1.5)
            os.write(fd, KEYS[sent].encode())
            if KEYS[sent] == "\x1b":
                os.write(fd, KEYS[sent + 1 : sent + 3].encode())
                sent += 2
            sent += 1
        elif buf:
            time.sleep(0.6)
            r2, _, _ = select.select([fd], [], [], 0.4)
            if not r2:
                break

os.close(fd)
os.waitpid(pid, 0)

text = buf.decode("utf-8", "replace")

# Frame boundary: erase-display, same as drive.py. Not colour, safe to split on.
raw_frames = re.split(r"\x1b\[\d*J", text)

# The fix: preserve every SGR (`...m`) code; drop only the cursor-control finals.
_STRIP = re.compile(r"\x1b\[[0-9;?]*[ABCDEFGHJKSTfsu]")

clean_frames: list[str] = []
for frame in raw_frames:
    frame = _STRIP.sub("", frame)
    frame = frame.replace("\r\n", "\n")
    # A bare \r (redraw-in-place, no newline) still means "back to column 0";
    # keep it as a newline for line splitting, same normalisation drive.py did.
    frame = frame.replace("\r", "\n")
    lines = [line.rstrip() for line in frame.split("\n")]
    frame = "\n".join(lines)
    frame = re.sub(r"\n{3,}", "\n\n", frame).strip("\n")
    if frame.strip():
        clean_frames.append(frame)

print(f"{len(clean_frames)} frame(s) captured", file=sys.stderr)
for i, f in enumerate(clean_frames):
    print(f"----- frame {i} -----", file=sys.stderr)
    print(f, file=sys.stderr)

# --------------------------------------------------------------------------- #
# reconvert: real ANSI -> real rich.Text -> one recording Console -> one SVG
# --------------------------------------------------------------------------- #

# Keep only the frames that actually carry one of the two questions — this
# drops frame 0 (terminal mode-setup escapes, no visible text) and whatever
# trails the session once each `.ask()` returns (a plain `print`, not part of
# the wizard UI).
SCOPE_Q = "Where should this install write to?"
RUNTIME_Q = "Which runtimes should read this equipment?"
prompt_frames = [f for f in clean_frames if SCOPE_Q in f or RUNTIME_Q in f]
if len(prompt_frames) < 4:  # pragma: no cover — diagnostic aid if the capture ever misses one
    print(f"WARNING: expected 4 prompt frames, got {len(prompt_frames)}", file=sys.stderr)
LABELS = [
    "1 — scope: asked (pointer on the default)",
    "2 — scope: answered",
    "3 — runtimes: asked (☑/☐, locked group, pointer)",
    "4 — runtimes: answered",
]
labelled = list(zip(LABELS, prompt_frames, strict=False))

console = Console(record=True, width=90, force_terminal=True, color_system="truecolor")
for label, frame in labelled:
    console.rule(f"[dim]{label}[/]", style="dim")
    console.print(Text.from_ansi(frame))
    console.print()

OUT_DIR.mkdir(parents=True, exist_ok=True)
out_path = OUT_DIR / "install_harmonized.svg"
console.save_svg(str(out_path), title="install — scope, harmonized")
print(f"wrote {out_path}", file=sys.stderr)
