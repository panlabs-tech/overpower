"""PROTOTYPE — throwaway. Three treatments for the command lines under a `list` entry.

Built for the 2026-08-12 grilling session on visual improvements — not a ticket,
not production code. Lives in this branch's worktree only; nothing under
`src/overpower/` was touched to build it.

**Fact measured**, `src/overpower/screens.py` (main, ~line 63-82 and ~1050-1065):
`THEME` sets `op.key = "cyan"`, and that ONE token colours both the artifact
name on the head line (`_entry`, `head.add_row(Text(name, style="op.key"), ...)`)
and every command line under it (`_commands`, `stacked.add_row(Text(command,
style="op.key"))`). The command borrows the exact ink that is supposed to name
the artifact — nothing distinguishes "what this is" from "what to type".

**Decided criterion for this prototype** (not open here — arbitrated by the
product owner before this file was written): the command has to read as
clearly SUBORDINATE to the artifact name — weaker is fine, illegible is not.

**Technique**: `overpower.screens._commands` — the one function `_entry()`
calls to draw the command lines — is monkeypatched per variant. Everything
around it (`_block`, `_entry`, the Panel, the padding, the real `THEME`) is
the unmodified product code, imported, not reimplemented. `overpower.screens`
is resolved off the MAIN repo's `src/`, not off this old branch's stale copy
(this worktree predates `screens.py`/`wizard.py`/`discovery.py` entirely —
ticket #12 is what produced them). The path is an env var and not a bare
hardcode for the same reason `drive.py`'s own history records
(`e970dab`..`6d98239`): a hardcoded path breaks the day someone runs this from
a different worktree.

Run it:
    OVERPOWER_SRC=/path/to/overpower/src \
    /path/to/overpower/.venv/bin/python3 prototype/terminal-experience/list_command_style.py

Default `OVERPOWER_SRC` and `PROTO_RENDERS` below match the machine this was
built on; override both env vars on any other machine.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_SRC = os.environ.get("OVERPOWER_SRC", "/home/paninit/workspaces/panlabs-tech/overpower/src")
if REPO_SRC not in sys.path:
    sys.path.insert(0, REPO_SRC)

from rich.console import Console  # noqa: E402
from rich.table import Table  # noqa: E402
from rich.text import Text  # noqa: E402

import overpower.screens as screens  # noqa: E402 — the real product module, imported whole

OUT_DIR = Path(
    os.environ.get("PROTO_RENDERS", str(Path(__file__).resolve().parent / "renders"))
)

# Real numbers, measured 2026-08-12 by loading the embedded catalog with
# `overpower.discovery.load_catalog(content_root(), catalog_file())` on the
# machine this was built on. Not illustrative.
_NAME = "matt-pocock"
_FILES = 74
_SIZE = 204_143
_DESCRIPTION = (
    "Matt Pocock's agent skills for real engineering: grilling, spec and "
    "ticket flows, TDD, code review, domain modelling and more."
)
# The exact two lines `catalog_screen()` prints for a framework entry — built
# with the real `_install`/`_inspect` helpers, so a typo in the flag spelling
# would show up here exactly as it would on the real screen.
_COMMANDS = (
    screens._install(screens.AI_FRAMEWORK_FLAG, _NAME),  # noqa: SLF001 — the real, private helper
    screens._inspect(screens.AI_FRAMEWORK_FLAG, _NAME),  # noqa: SLF001
)


def _commands_dim(commands: object) -> object:
    """Variant A — `op.dim`: the same grey the rest of the screen already uses for a note."""
    stacked = Table.grid()
    stacked.add_column(overflow="fold")
    for command in commands:
        stacked.add_row(Text(command, style="op.dim"))
    return stacked


def _commands_dim_italic(commands: object) -> object:
    """Variant B — `dim italic`: the same grey, plus a second, unrelated signal (slant)."""
    stacked = Table.grid()
    stacked.add_column(overflow="fold")
    for command in commands:
        stacked.add_row(Text(command, style="dim italic"))
    return stacked


def _commands_family_blue(commands: object) -> object:
    """Variant C — `#5f819d`: questionary's own `qmark` blue-grey, unmodified in this project.

    Chosen over a named Rich grey (e.g. `grey62`) specifically to test whether
    this hex is a ready-made "family" ink that could unify this screen with the
    wizard's qmark — which already renders in exactly this colour today,
    `questionary.constants.DEFAULT_STYLE`, no override.
    """
    stacked = Table.grid()
    stacked.add_column(overflow="fold")
    for command in commands:
        stacked.add_row(Text(command, style="#5f819d"))
    return stacked


VARIANTS = (
    ("a_dim", "Variant A — op.dim", _commands_dim),
    ("b_dim_italic", "Variant B — dim italic", _commands_dim_italic),
    ("c_family_blue", "Variant C — #5f819d (questionary qmark blue)", _commands_family_blue),
)


def render(tag: str, title: str, patched_commands: object) -> Path:
    """One variant: patch `screens._commands`, draw the REAL `_block`/`_entry`, export SVG."""
    screens._commands = patched_commands  # noqa: SLF001 — the seam this prototype tests
    entry = screens._entry(  # noqa: SLF001
        _NAME, _SIZE, _FILES, _DESCRIPTION, commands=_COMMANDS
    )
    block = screens._block("AI Frameworks", "installs whole", [entry])  # noqa: SLF001

    console = Console(
        record=True,
        theme=screens.THEME,
        width=80,
        highlight=False,
        force_terminal=True,
        color_system="truecolor",
    )
    console.print(block)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"list_command_{tag}.svg"
    console.save_svg(str(path), title=title)
    return path


if __name__ == "__main__":
    for tag, title, fn in VARIANTS:
        written = render(tag, title, fn)
        print(f"wrote {written}")
