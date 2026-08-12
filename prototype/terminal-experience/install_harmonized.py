"""PROTOTYPE — throwaway. The `install` wizard's scope step, harmonized.

Built for the 2026-08-12 grilling session on visual improvements — not a
ticket, not production code. Nothing under `src/overpower/` is touched; the
real `overpower.wizard` module is imported and patched IN MEMORY, the same way
`list_command_style.py` patches `overpower.screens` for the other prototype.

**Facts measured**, `src/overpower/wizard.py` (main):
- no `questionary.Style` is built anywhere in this project today — every
  prompt inherits `questionary.constants.DEFAULT_STYLE` unmodified. `qmark` is
  `fg:#5f819d` (a blue-grey), `answer` is `fg:#FF9D00 bold` (orange), and
  `question`/`separator`/`disabled`/`instruction` carry no colour at all.
- the scope choices are `questionary.Choice("This repository", ...)` and
  `questionary.Choice("This machine (~/), every project", ...)`, ~line 285-286.
- the hint line (`_SELECT_HINT`) is drawn by `_hint_block()`, ~line 415-427,
  and hangs directly under the question with no blank line between them.
- the checkbox indicators are the library defaults, `INDICATOR_SELECTED = "●"`
  / `INDICATOR_UNSELECTED = "○"`, `questionary/constants.py`.

**Decided already** (not open in this file): the harmonized colours below,
"This project" / "Global" for the two choices, and a blank rail line between
the question and its hint. The checkbox glyph was tried as `☑`/`☐` and
**rejected** on live review — reverted to the library default `●`/`○` here,
so this file no longer patches `questionary.prompts.common` at all.

**Correction, same live review**: the first cut of this file's `main()` did
NOT call the real orchestrator (`wizard.run_wizard`) between steps — it used
its own bare `console.print(f"scope: {scope} -> {root}")` and, after
runtimes, a raw dump of every chosen runtime key. Neither exists in the real
product: `run_wizard` (`wizard.py:193-199`) prints exactly one styled
`noted()` line between the scope and runtimes steps, and nothing at all
after runtimes. The crowding reported on live review was largely this
prototype's own debug scaffolding sitting where the real, already-considered
`noted()` line belongs — fixed below by calling the same line the real
orchestrator calls, and deleting the runtimes dump outright.

## Why this is a near-verbatim copy of `ask_scope`, not a call to it

`ask_scope`'s choice text and the absence of a `style=` kwarg are string/call
literals inside its body — there is no seam to patch them from outside
without editing the file. Everything else IS the real, unmodified machinery,
reused rather than re-drawn: `wizard._railed` (the custom rail layout),
`wizard._QMARK`, `wizard._SELECT_HINT`, `wizard._NO_SELECT_INSTRUCTION`,
`wizard._SCOPE_QUESTION`, and `overpower.screens.railed`/`stepped`. Only
`wizard._hint_block` is patched — with the one-line spacing fix described
above, at the exact seam wizard.py already calls it through — and the
`questionary.select(...)` call itself is duplicated because that is the one
piece that cannot be reached any other way.

The checkbox glyphs are patched on `questionary.prompts.common`, not on
`questionary.constants`: `common.py` does `from questionary.constants import
INDICATOR_SELECTED`, which binds the value into `common`'s own namespace at
import time. Rebinding `questionary.constants.INDICATOR_SELECTED` afterwards
would not reach it — this is the exact trap this branch's own README records
for `questionary.constants.YES`/`NO` (see git history, Passo 7).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_SRC = os.environ.get("OVERPOWER_SRC", "/home/paninit/workspaces/panlabs-tech/overpower/src")
if REPO_SRC not in sys.path:
    sys.path.insert(0, REPO_SRC)

import questionary  # noqa: E402
from rich.console import Console  # noqa: E402

import overpower.wizard as wizard  # noqa: E402 — the real product module, patched in memory only
from overpower.runtimes import Environment, Scope  # noqa: E402
from overpower.scope import git_root  # noqa: E402
from overpower.screens import RAIL, THEME, noted, railed, stepped  # noqa: E402

# --------------------------------------------------------------------------- #
# the harmonized Style — DEFAULT_STYLE with exactly the classes this ticket named
# --------------------------------------------------------------------------- #

HARMONIZED_STYLE = questionary.Style(
    [
        # op.brand ("bold magenta") in place of the library's blue-grey.
        # `ansimagenta`/`ansicyan`, not a raw hex: prompt_toolkit writes these
        # as the BASIC SGR codes (`\x1b[35m`/`\x1b[36m`), the same codes Rich's
        # own "magenta"/"cyan" resolve from — so this is the closest a
        # questionary Style can get to literally sharing ink with `op.brand`
        # and `op.key`, rather than merely approximating their hex.
        ("qmark", "fg:ansimagenta bold"),
        # op.brand's own weight is bold; adding it here is not a proportion
        # decision, it is copying the token.
        # unchanged — decision: the question is the main element, it stays
        # exactly as prominent as it is today.
        ("question", "bold"),
        # op.key ("cyan") in place of the library's orange. Kept bold, as the
        # default answer already was — only the colour moves.
        ("answer", "fg:ansicyan bold"),
        # op.key. The default is "" (no colour at all) — today the arrow glyph
        # in front of the highlighted row is undyed.
        ("pointer", "fg:ansicyan"),
        # Not named in the four bullet points, but required to make "the
        # highlighted option" actually read in op.key: `pointer` colours only
        # the `»` glyph (`common.py::_get_choice_tokens`), the row's OWN text
        # uses a separate, undocumented class, `highlighted`, that
        # DEFAULT_STYLE never defines at all (falls back to no colour).
        # Left uncoloured, only the arrow would move — the row it points at
        # would still read in the terminal's default ink.
        ("highlighted", "fg:ansicyan"),
        # op.key. Governs a TICKED row's text in `checkbox` — does not appear
        # on the scope screen (a `select`), captured here for completeness of
        # the Style and exercised only if the checkbox screen is captured too.
        ("selected", "fg:ansicyan"),
        # op.dim. `"dim"` and not a grey hex: it is the real SGR-2 (faint)
        # attribute, the exact one `screens.THEME["op.dim"]` resolves to
        # ("dim", no colour) — the closest available match to "the dim ANSI
        # the rest of the project already uses", because it IS that attribute,
        # not an approximation of its colour.
        ("separator", "dim"),
        ("disabled", "dim"),
        ("instruction", "dim"),
    ]
)

# --------------------------------------------------------------------------- #
# checkbox glyphs — reverted. `●`/`○`, the library default, untouched.
# --------------------------------------------------------------------------- #

# --------------------------------------------------------------------------- #
# spacing — one blank rail line between the question and its hint
# --------------------------------------------------------------------------- #


def _hint_block_spaced(hint: str):
    """`wizard._hint_block`, plus the blank rail line the ticket asked for."""

    def block():
        return [
            ("class:separator", f"{RAIL}\n"),
            ("class:instruction", f"{RAIL}  {hint}"),
        ]

    return block


wizard._hint_block = _hint_block_spaced  # noqa: SLF001 — the real function, patched in memory


# --------------------------------------------------------------------------- #
# ask_scope, harmonized — see the module docstring for why this is a near-copy
# --------------------------------------------------------------------------- #


def ask_scope_harmonized(cwd: Path, environment: Environment, console: Console):
    """`wizard.ask_scope`, unchanged in every mechanic but the three named diffs."""
    if git_root(cwd) is None:  # pragma: no cover — this prototype always runs inside a repo
        console.print(
            stepped(wizard._SCOPE_QUESTION, "This machine (~/) — outside a git repository")  # noqa: SLF001
        )
        return Scope.GLOBAL, environment.home
    console.print(railed())
    with wizard._railed(  # noqa: SLF001
        header=wizard._hint_block(wizard._SELECT_HINT), footer=False  # noqa: SLF001
    ):
        picked = questionary.select(
            wizard._SCOPE_QUESTION,  # noqa: SLF001 — unchanged copy, not part of this ticket
            choices=[
                # Renamed, decided: "This repository" / "This machine (~/),
                # every project" -> "This project" / "Global".
                questionary.Choice("This project", value=Scope.PROJECT),
                questionary.Choice("Global", value=Scope.GLOBAL),
            ],
            qmark=wizard._QMARK,  # noqa: SLF001
            instruction=wizard._NO_SELECT_INSTRUCTION,  # noqa: SLF001
            style=HARMONIZED_STYLE,
        ).ask()
    if picked is None:
        return None
    return picked, (cwd if picked is Scope.PROJECT else environment.home)


def ask_runtimes_harmonized(scope: Scope, root: Path, environment: Environment):
    """`wizard.ask_runtimes`, unchanged but for `style=` and the patched checkbox glyphs.

    No renamed copy or added `--global`/`--project` text touches this step —
    the ticket named only the scope choices and the checkbox glyphs, and the
    glyphs are already patched globally (module-level, see above). This
    function exists at all for the same reason `ask_scope_harmonized` does:
    `style=` is a kwarg the real call does not pass, so reaching it means
    duplicating the call.
    """
    choices = wizard.runtime_choices(scope, wizard.detected_runtimes(scope, root, environment))
    with wizard._railed(header=wizard.locked_block(scope)):  # noqa: SLF001
        picked = questionary.checkbox(
            wizard._RUNTIME_QUESTION,  # noqa: SLF001
            choices=choices,
            qmark=wizard._QMARK,  # noqa: SLF001
            instruction=wizard._NO_INSTRUCTION,  # noqa: SLF001
            use_search_filter=True,
            use_jk_keys=False,
            style=HARMONIZED_STYLE,
        ).ask()
    if picked is None:
        return None
    chosen = tuple(picked)
    included = {*(r.key for r in wizard.universal_runtimes(scope)), *chosen}
    return tuple(r.key for r in wizard.runtimes_in(scope) if r.key in included)


def main() -> None:
    cwd = Path.cwd()
    environment = Environment.from_process()
    console = Console(theme=THEME, highlight=False)
    answered = ask_scope_harmonized(cwd, environment, console)
    if answered is None:
        console.print("[op.warn]aborted[/]")
        return
    scope, root = answered

    if os.environ.get("PROTO_SKIP_RUNTIMES"):
        return
    # The real orchestrator's own line between steps — `wizard.py:193-199` —
    # not a debug print. Nothing prints after runtimes in the real flow either
    # (the wizard moves on to the plan/confirmation screen, out of scope
    # here), so this prototype prints nothing after `ask_runtimes_harmonized`
    # returns.
    console.print(noted(f"{len(wizard.runtimes_in(scope))} runtimes read this scope"))
    chosen = ask_runtimes_harmonized(scope, root, environment)
    if chosen is None:
        console.print("[op.warn]aborted[/]")
        return


if __name__ == "__main__":
    main()
