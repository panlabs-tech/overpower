"""The wizard: a terminal, a line that does not add up to a plan, one `Request` out.

Artifacts, then scope, then runtimes, then confirmation
(https://github.com/panlabs-tech/overpower/issues/41). The order is not
aesthetic: the runtime probe depends on scope — project probes the target
repository, global probes `~` — so asking runtimes before scope would probe
the wrong root (ADR 0008). Confirmation is the fourth step and needs no code
here: it is the same plan screen and the same `y`/`n` the flag path already
draws, once this module hands `overpower.cli` the same `Request` type the
flags would have built.

**The trigger is the gap and not the empty line**
(https://github.com/panlabs-tech/overpower/issues/57): a line missing a
selection *or* a runtime opens the wizard, and the wizard opens only the steps
that line left open. `install --ai-framework matt-pocock` therefore asks scope
and runtimes and never artifacts, which is what makes the command the catalog
prints a command that works when it is pasted back.

Each `ask_*` function is the seam: one `questionary` call, `.ask()`ed, and
nothing else around it. Flow tests stub it directly — it supplies indirect
input, it does not emulate `questionary`'s own behaviour, so it is a Stub and
the house ruler excludes Stub from contract testing by name
(`docs/agents/testing.md`, §7). Public rather than underscored, the way
`overpower.runtimes.runtimes_in` is: what a test calls directly cannot also be
private, under `pyright --strict`. What proves the wiring down to the real
library is the one PTY test next to this module's tests, POSIX only.

## The screen this draws, and why it is not `questionary`'s

Measured at 80x24 — the default terminal — before #65: the runtime step showed
**one** selectable row. The 19 locked rows, their two separators and a
two-line hint filled 23 of the 24 lines, so the row detection had pre-ticked
was below the fold and nothing on screen said 55 more existed. The cause is in
the library: `questionary.prompts.common.create_inquirer_layout` builds the
list as `Window(ic)` with **no height**, so every row renders and the terminal
scrolls.

`_rail_layout` replaces that one function. Three things move, and each is
measured against `npx skills add`, whose choreography #65 adopted:

- **the locked group leaves the scrollable control** and becomes static text.
  It is what makes the viewport spendable on rows that can actually be chosen —
  inside the control it ate the window and the count went from 1 row to 2;
- **the list gets a viewport** of `VIEWPORT` rows plus a live `↓ N more`, so
  the step is self-contained at 24 rows whatever the table grows to;
- **the rail runs down the left of everything**, drawn as a `VSplit` column
  beside the control rather than as a prefix on each row — `_get_choice_tokens`
  has no hook for a prefix, and a `VSplit` needs none.

The coupling is **one module attribute**, resolved at call time by
`checkbox.py` and `select.py` (`common.create_inquirer_layout(...)`), so
replacing it is a supported shape rather than a patch of a bound import. If a
future `questionary` changes the layout contract this raises at render, which
is loud; the CLI stack is pinned deliberately (#4) for exactly that reason.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from typing import TYPE_CHECKING, Any

import questionary
from prompt_toolkit.filters import Always, Condition, IsDone
from prompt_toolkit.layout import ConditionalContainer, HSplit, Layout, VSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.dimension import LayoutDimension
from prompt_toolkit.shortcuts.prompt import PromptSession
from questionary.prompts import common

from overpower.runtimes import (
    RUNTIMES_BY_KEY,
    Scope,
    detected_mcp_runtimes,
    detected_runtimes,
    mcp_document_of,
    mcp_runtimes_in,
    runtimes_in,
    universal_place,
    universal_runtimes,
)
from overpower.scope import git_root
from overpower.screens import (
    ACTIVE_MARK,
    CLOSE_MARK,
    DONE_MARK,
    RAIL,
    noted,
    railed,
    stepped,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from pathlib import Path

    from prompt_toolkit.formatted_text import StyleAndTextTuples
    from questionary.prompts.common import InquirerControl
    from rich.console import Console

    from overpower.discovery import Catalog
    from overpower.planning import Request
    from overpower.runtimes import Environment, Runtime

ALWAYS_INCLUDED = "always included"
"""What the locked section says of itself, on its heading and on every row of it.

One string and not two, because the heading and the row are the same claim seen
from two distances, and a screen that spelled it twice could spell it two ways.
"""

VIEWPORT = 8
"""Rows of the choosable list kept on screen at once.

Public, like `ALWAYS_INCLUDED` and for the same reason: the height budget of
the step is asserted directly against it, and what a test names cannot also be
private under `pyright --strict`.

Eight, which is what `npx skills add` shows, and it is a budget rather than a
taste: at 24 rows the step spends 2 on the question, 7 on the locked block, 2
on the section heading and the search, 1 on the counter, 2 on the footer and 1
on the closing rail. Eight is what is left, and it is what makes the step fit
whatever the runtime table grows to.
"""

LOCKED_SHOWN = 4
"""Members of the universal group named before the rest are counted.

Public for the reason `VIEWPORT` is: the bound on the static block is asserted
against it rather than against a number typed twice.

Four and a `…and N more`, the shape `npx skills` uses. Naming all 19 is what
cost the step its viewport: the group is **informative**, so it has to be
recognisable, not exhaustive — and what it is informative *about* is the one
path under it, which the heading names.
"""

_SELECTED_SHOWN = 3
"""Names on the live footer before it counts the rest, as `_READERS_SHOWN` does on a plan."""


def run_wizard(  # noqa: PLR0913 — the five the steps need, plus the console they narrate on
    asked: Request,
    catalog: Catalog | None,
    environment: Environment,
    cwd: Path,
    scoped: tuple[Scope, Path] | None,
    *,
    console: Console,
) -> tuple[Request, Path] | None:
    """`asked` with its gaps filled, or `None` when the user backs out of any step.

    **Gaps, not steps** (https://github.com/panlabs-tech/overpower/issues/57):
    what the flags already fixed is not asked again, and what they did not is
    asked in the order #18 locked — artifacts, scope, runtimes, confirmation.
    `catalog` is `None` exactly when the artifacts step cannot open, and
    `scoped` is `None` exactly when the scope step is the caller's to ask;
    both are decided in `overpower.cli`, which is where the flags are.

    It **replaces into the request it was handed** rather than building a new
    one, and that is what keeps `--dry-run`, `--force` and `--yes` — which are
    not wizard steps — travelling through untouched. What comes out is
    indistinguishable from what the equivalent flag line would have built,
    which is what lets the selection logic be tested over values instead of
    over keystrokes.

    `.ask()` answers `None` on interruption — the same gesture `_confirmed()`
    already treats as a decline — and that meaning is threaded through here
    unchanged: backing out of any one step abandons the whole wizard rather
    than resuming at the previous one, which is the same all-or-nothing shape
    the final confirmation already has.

    `console` is what the session is narrated on, and it is passed rather than
    owned: `overpower.cli` holds the one console the whole program prints
    through (`T20` forbids `print`), and a second one here would be a second
    place for the theme and the width to be decided.
    """
    ai_frameworks, bundles, skills = asked.ai_frameworks, asked.bundles, asked.skills
    # `asked.mcps` is a selection like the other three, so a line that names one
    # has already answered this step — the wizard opens the gaps and not the
    # steps. What it does *not* yet do is offer MCP servers to pick from inside
    # it, which is https://github.com/panlabs-tech/overpower/issues/85. The
    # runtime step below already knows which class the line carries (#97): a
    # mixed line never reaches here — `overpower.cli` refuses it before the
    # wizard opens — so `asked.mcps` truthy here means the whole line is graft.
    if not (ai_frameworks or bundles or skills or asked.mcps):
        if catalog is None:  # pragma: no cover — `overpower.cli` decides the two together
            message = "the artifacts step opened with no catalog to read"
            raise AssertionError(message)
        console.print(noted(_counted(catalog)))
        picked = ask_artifacts(catalog)
        if picked is None:
            return None
        ai_frameworks, bundles, skills = picked

    if scoped is None:
        answered = ask_scope(cwd, environment, console)
        if answered is None:
            return None
        scope, root = answered
    else:
        scope, root = scoped

    runtimes = asked.runtimes
    if not runtimes:
        if asked.mcps:
            console.print(
                noted(f"{len(mcp_runtimes_in(scope))} runtimes take an MCP server in this scope")
            )
            chosen = ask_mcp_runtimes(scope, root, environment)
        else:
            console.print(noted(f"{len(runtimes_in(scope))} runtimes read this scope"))
            chosen = ask_runtimes(scope, root, environment)
        if chosen is None:
            return None
        runtimes = chosen

    return (
        replace(
            asked,
            ai_frameworks=ai_frameworks,
            bundles=bundles,
            skills=skills,
            runtimes=runtimes,
            scope=scope,
        ),
        root,
    )


def ask_artifacts(
    catalog: Catalog,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]] | None:
    """What to install — the three independent units, one flat multi-select.

    Empty is a legal answer here: an empty pick lands on the same
    `NothingSelectedError` the flag path already raises, once `plan_for` sees
    the `Request` this step feeds — one place names that defect, reached by
    two doors.
    """
    choices = artifact_choices(catalog)
    with _railed(header=_hint_block(_HINT)):
        picked = questionary.checkbox(
            "What should this install bring?",
            choices=choices,
            qmark=_QMARK,
            instruction=_NO_INSTRUCTION,
            style=QUESTIONARY_STYLE,
        ).ask()
    if picked is None:
        return None
    return (
        tuple(name for kind, name in picked if kind == "framework"),
        tuple(name for kind, name in picked if kind == "bundle"),
        tuple(name for kind, name in picked if kind == "skill"),
    )


def artifact_choices(catalog: Catalog) -> list[questionary.Separator | questionary.Choice]:
    """One flat list, grouped the way the catalog screen already groups the same three units.

    A group with nothing in it prints no heading: an empty bundle list is a
    real catalog shape, not a defect this screen exists to name.
    """
    groups = (
        ("AI Frameworks", tuple(("framework", framework.name) for framework in catalog.frameworks)),
        ("Bundles", tuple(("bundle", bundle.name) for bundle in catalog.bundles)),
        ("Pool skills", tuple(("skill", artifact.name) for artifact in catalog.pool)),
    )
    choices: list[questionary.Separator | questionary.Choice] = []
    for title, entries in groups:
        if not entries:
            continue
        choices.append(questionary.Separator(_section(title)))
        choices.extend(questionary.Choice(name, value=(kind, name)) for kind, name in entries)
    return choices


def ask_scope(cwd: Path, environment: Environment, console: Console) -> tuple[Scope, Path] | None:
    """Project or the machine — and outside a repository there is only one legal answer.

    Offering `Project` with nowhere to write would be the anti-pattern ADR
    0008 and ADR 0009 already refuse one layer further down: a screen that
    names what the next step cannot honour. Outside a repository the flag
    path already demands `--global` explicitly (`OutsideRepositoryError`); the
    wizard's equivalent of that explicitness is not asking a question that has
    only one legal answer, rather than asking it and disabling the other one.

    **It is reported rather than skipped** (#65). Before, the one legal answer
    was taken in silence and the session showed nothing at all where a step
    belonged — so the person could not tell that scope had been decided, let
    alone how. Now it collapses to the same two lines an answered step
    collapses to, with the reason on it.
    """
    if git_root(cwd) is None:
        console.print(stepped(_SCOPE_QUESTION, "Global — outside a git repository"))
        return Scope.GLOBAL, environment.home
    console.print(railed())
    with _railed(header=_hint_block(_SELECT_HINT), footer=False):
        picked = questionary.select(
            _SCOPE_QUESTION,
            choices=[
                questionary.Choice("This project", value=Scope.PROJECT),
                questionary.Choice("Global", value=Scope.GLOBAL),
            ],
            qmark=_QMARK,
            instruction=_NO_SELECT_INSTRUCTION,
            style=QUESTIONARY_STYLE,
        ).ask()
    if picked is None:
        return None
    return picked, (cwd if picked is Scope.PROJECT else environment.home)


def ask_runtimes(scope: Scope, root: Path, environment: Environment) -> tuple[str, ...] | None:
    """Which runtimes read this equipment — the locked group, plus whatever is picked.

    Asked even when detection pre-marks exactly one runtime: pre-marking is a
    convenience, not a decision made on the user's behalf, and a single
    detected runtime is exactly the case where a silent default would be
    loneliest.

    **The lock is of the screen, not of the plan** (ADR 0011): the keys of the
    universal group travel in the `Request` this step feeds, exactly like a key
    somebody ticked, so `overpower install --runtime claude-code` on the flag
    line still writes `.claude/skills/` and nothing else. A lock that were a
    planning rule would make that flag write two trees, and the flag would stop
    saying what it does.

    The union is taken over the **scoped table's order** and through a set, so
    the answer is deterministic and names nothing twice — which matters because
    a locked line can still come back in the pick: `questionary` moves the
    pointer to the top of the filtered list when a search character arrives,
    and the top of a filtered list may be a disabled row.

    **The locked group is no longer among the choices** (#65): it is drawn as
    static text above the list, which is where `npx skills` draws it and what
    frees the viewport for rows that can be chosen. Nothing about the answer
    moves — the union below is computed off `universal_runtimes(scope)` exactly
    as before, so ADR 0011 holds whatever the screen does.
    """
    choices = runtime_choices(scope, detected_runtimes(scope, root, environment))
    with _railed(header=locked_block(scope)):
        picked = questionary.checkbox(
            _RUNTIME_QUESTION,
            choices=choices,
            qmark=_QMARK,
            instruction=_NO_INSTRUCTION,
            # The search is what makes a 76-row list navigable: measured on
            # questionary 2.1.1, `dev` reduces it to 2 rows, `copilot` to 1 and
            # `claude` to 1, against 22 lines visible at 80x24. It costs two things,
            # both fixed in the library and both taken knowingly.
            #
            # `j`/`k` stop navigating — `ValueError: Cannot use j/k keys with prefix
            # filter search, since j/k can be part of the prefix.` The arrow keys and
            # the Emacs pair survive, and `j`/`k` are a binding this project never
            # committed to.
            #
            # And **the filter is of the list, not of one section**: `Separator`
            # subclasses `Choice`, so a search hides the group headings along with
            # whatever missed. It cannot be scoped from here — but since #65 the
            # locked rows are not in the list at all, so what a search can hide is
            # only the one heading over rows that are all choosable.
            use_search_filter=True,
            use_jk_keys=False,
            style=QUESTIONARY_STYLE,
        ).ask()
    if picked is None:
        return None
    chosen: tuple[str, ...] = tuple(picked)
    included = {*(runtime.key for runtime in universal_runtimes(scope)), *chosen}
    return tuple(runtime.key for runtime in runtimes_in(scope) if runtime.key in included)


def runtime_choices(scope: Scope, detected: frozenset[str]) -> list[questionary.Choice]:
    """The runtimes of this scope that are a real choice — the universal group excluded.

    `runtimes_in(scope)` is the one implementation of *the skills half*, so global
    scope never offers the two runtimes with no destination there, and `vscode`
    is never among them either (ADR 0018): it has a row in the table now, but no
    `project_dir` for `runtimes_in` to find. What the universal group of **that**
    scope holds — 19 rows in project, 6 in global — is drawn by `locked_block`
    instead, above the list rather than in it.

    **This list is the skills half only.** Since #97 the runtime step knows
    which class the line carries and calls `mcp_runtime_choices` for the other
    one — a mixed line never reaches either, refused by `overpower.cli` before
    the wizard opens — so a target this list omits is never one the next step
    would have accepted.

    The split is #65's, and it is measured rather than tidy: inside the list the
    19 locked rows filled the terminal and left **one** choosable row visible;
    outside it they cost 6 static lines and leave eight.
    """
    included = {runtime.key for runtime in universal_runtimes(scope)}
    return [
        _choice(runtime, scope, detected)
        for runtime in runtimes_in(scope)
        if runtime.key not in included
    ]


def ask_mcp_runtimes(scope: Scope, root: Path, environment: Environment) -> tuple[str, ...] | None:
    """Which runtimes should receive this server — the graft class's own step (#97).

    Not `ask_runtimes` filtered: the two classes disagree about the whole shape
    of the step, not only about which rows are offered. There is no universal
    group to lock — ADR 0011's group is a fact of the skills class, a path every
    member shares, and the graft class has no such path — so every row here is a
    real choice and the step draws no static block above the list. And a row is
    labelled by the **file** it writes, not by a directory: `.vscode/mcp.json`
    is what tells the reader apart from `.mcp.json`, where a shared directory
    name like `.agents/skills` tells the skills step's reader apart.
    """
    choices = mcp_runtime_choices(scope, detected_mcp_runtimes(scope, root, environment))
    with _railed(header=_hint_block(_HINT)):
        picked = questionary.checkbox(
            _MCP_RUNTIME_QUESTION,
            choices=choices,
            qmark=_QMARK,
            instruction=_NO_INSTRUCTION,
            use_search_filter=True,
            use_jk_keys=False,
            style=QUESTIONARY_STYLE,
        ).ask()
    if picked is None:
        return None
    chosen = set(picked)
    return tuple(key for key in mcp_runtimes_in(scope) if key in chosen)


def mcp_runtime_choices(scope: Scope, detected: frozenset[str]) -> list[questionary.Choice]:
    """Every runtime that can receive a server in this scope — no group excluded.

    `mcp_runtimes_in(scope)` is the whole set the class offers here, unlike the
    skills half where the universal group is drawn separately: the graft class
    has nothing in common to draw that way, so every key returned is a choice.
    """
    return [_mcp_choice(key, scope, detected) for key in mcp_runtimes_in(scope)]


def _mcp_choice(key: str, scope: Scope, detected: frozenset[str]) -> questionary.Choice:
    """One graft target, labelled by the file it writes and pre-checked by detection."""
    document = mcp_document_of(key, scope)
    if document is None:  # pragma: no cover — `key` comes straight off `mcp_runtimes_in(scope)`
        message = f"`{key}` has no MCP document in {scope}, despite `mcp_runtimes_in`"
        raise AssertionError(message)
    return questionary.Choice(
        f"{RUNTIMES_BY_KEY[key].display_name} ({document.relative})",
        value=key,
        checked=key in detected,
    )


def locked_block(scope: Scope) -> Callable[[], StyleAndTextTuples]:
    """The universal group as static text: the place, the lock, the count, four names.

    The heading carries the place, the lock and the count, because that is the
    whole of what the section buys: a pre-ticked line and a locked line differ
    by one tap of the space bar, and what the second one buys is the reader
    understanding, without counting boxes, that one path equips every runtime
    under it at once — which is also why the count is on the heading and not
    left to be counted.

    Four names and a remainder rather than all of them (`LOCKED_SHOWN`): the
    section is informative, and what it informs about is the single path in its
    heading. Naming all 19 is what cost the step its viewport before #65.

    It returns a **callable** because that is what `FormattedTextControl` takes,
    and because the block is recomputed on every redraw — which is what keeps it
    correct if the terminal is resized mid-prompt.
    """
    locked = universal_runtimes(scope)
    place = universal_place(scope)

    def block() -> StyleAndTextTuples:
        heading = f"Universal ({place})  {ALWAYS_INCLUDED}  {len(locked)} runtimes"
        rows: StyleAndTextTuples = [("class:separator", f"{RAIL}  {_section(heading)}\n")]
        rows.extend(
            ("class:disabled", f"{RAIL}    • {runtime.display_name}\n")
            for runtime in locked[:LOCKED_SHOWN]
        )
        remaining = len(locked) - LOCKED_SHOWN
        if remaining > 0:
            rows.append(("class:disabled", f"{RAIL}    …and {remaining} more\n"))
        rows.append(("class:separator", f"{RAIL}\n"))
        rows.append(("class:separator", f"{RAIL}  {_section('Additional agents')}\n"))
        rows.append(("class:instruction", f"{RAIL}  {_HINT}"))
        return rows

    return block


def _hint_block(hint: str) -> Callable[[], StyleAndTextTuples]:
    """A header that is only the hint, for the two steps with no locked group over them.

    On its own rail line rather than trailing the question, which is where
    `questionary` puts it and where it wrapped: measured at 80 columns, the
    runtime question plus the default hint ran to 103 characters and broke
    `enter confirm` across two lines inside a fixed-height window.

    **A blank rail line separates it from the question above** (#67): with the
    hint on the very next line, the question and its navigation hint read as
    one crowded block. `locked_block()` is unchanged — its own hint follows a
    heading it just drew, not a question, so the two read as one group
    already and were never reported as crowded.
    """

    def block() -> StyleAndTextTuples:
        return [
            ("class:separator", f"{RAIL}\n"),
            ("class:instruction", f"{RAIL}  {hint}"),
        ]

    return block


def _choice(runtime: Runtime, scope: Scope, detected: frozenset[str]) -> questionary.Choice:
    """One runtime that is a real choice, pre-checked by detection.

    The place travels on the title, as `npx skills` puts it there: the plan
    names paths and never runtime names (ADR 0008), so a row that showed only
    *"Cursor"* would be the one screen in the flow that hid the thing every
    other screen is written in.

    It is the **declared relative** place and not the resolved one, which is a
    deliberate shortening: a global row resolves through an anchor that may be
    `$XDG_CONFIG_HOME`, and a row 80 characters wide is a row that wraps inside
    an eight-line viewport. What the reader needs here is which tree it is; the
    plan, one step later, prints the path that will actually be written.
    """
    return questionary.Choice(
        f"{runtime.display_name} ({_place_of(runtime, scope)})",
        value=runtime.key,
        checked=runtime.key in detected,
    )


def _place_of(runtime: Runtime, scope: Scope) -> str:
    """The tree this runtime reads in this scope, relative and unanchored."""
    if scope is Scope.PROJECT:
        return runtime.project_dir.relative if runtime.project_dir else "—"
    return f"~/{runtime.global_dir.relative}" if runtime.global_dir else "—"


def _section(title: str) -> str:
    """`── title ──────` — a heading that reads as a rule with a word on it."""
    filled = f"── {title} "
    return filled + "─" * max(3, _SECTION_WIDTH - len(filled))


_SECTION_WIDTH = 62
"""What a heading rule is padded to, so `── Additional agents ─────` reads as a rule.

Padded rather than measured against the terminal: the rule lives inside a
`prompt_toolkit` control, which is drawn before the width is known here, and a
heading that stops three characters short at 80 columns costs nothing while a
heading that overruns at 60 costs a wrapped line inside a fixed-height window.
"""

QUESTIONARY_STYLE = questionary.Style(
    [
        # `qmark` shipped as the library's own default blue-grey
        # (`fg:#5f819d`), unrelated to the rest of the product's palette.
        # `ansimagenta`, not a raw hex: `prompt_toolkit` writes the eight ANSI
        # names as the basic SGR codes (`\x1b[35m` here), the same codes
        # Rich's own "magenta" resolves from — the closest a `questionary`
        # `Style` gets to literally sharing ink with `op.brand`, rather than
        # merely approximating its hex.
        ("qmark", "fg:ansimagenta bold"),
        # Unchanged from the library default — the question is meaning, not
        # frame, and stays exactly as prominent as it already was.
        ("question", "bold"),
        # `op.key`'s ink, in place of the library default `fg:#FF9D00 bold`
        # (orange), for the text that carries meaning: the picked answer, and
        # the row a select's pointer sits on. `highlighted`/`selected` are the
        # classes that colour that row's own text — `pointer` alone only
        # reaches the `»` glyph in front of it (`questionary.prompts.common`).
        ("answer", "fg:ansicyan bold"),
        ("pointer", "fg:ansicyan"),
        ("highlighted", "fg:ansicyan"),
        ("selected", "fg:ansicyan"),
        # `op.dim`'s own attribute — SGR-2, faint — in place of the library's
        # default of no styling at all, for the frame around that meaning: the
        # rail, the locked rows, the navigation hint.
        ("separator", "dim"),
        ("disabled", "dim"),
        ("instruction", "dim"),
    ]
)
"""The prompts' palette, harmonized with `screens.THEME` (#67).

Built once, module level, and passed to every `questionary` prompt in the
CLI — `cli._confirmed()` imports this rather than building its own, so no
prompt is left in the library's own colours.
"""

_QMARK = f"{ACTIVE_MARK} "
"""Two spaces before the question, because `questionary` writes one of its own.

The rich lines of the session put two after their mark, and a step that used one
would be the only line of the flow that did not sit on the same column.
"""

_SCOPE_QUESTION = "Where should this install write to?"
_RUNTIME_QUESTION = "Which runtimes should read this equipment?"
_MCP_RUNTIME_QUESTION = "Which runtimes should receive this server?"
_HINT = "↑↓ move · space select · enter confirm"
_SELECT_HINT = "↑↓ move · enter confirm"
_NO_INSTRUCTION = ""
"""What suppresses `questionary`'s own hint on a checkbox — it tests `is not None`."""

_NO_SELECT_INSTRUCTION = " "
"""The same for a select, which tests truthiness instead, so empty falls back to the default."""


@contextmanager
def _railed(
    *, header: Callable[[], StyleAndTextTuples] | None = None, footer: bool = True
) -> Generator[None]:
    """Install the railed layout for the duration of one prompt, then put back what was there.

    A context manager and not a module-level assignment, because the three
    steps need three different headers and one global replacement could only
    carry one. Restoring in `finally` is what keeps a `KeyboardInterrupt` out
    of the next prompt's layout.
    """
    original = common.create_inquirer_layout
    common.create_inquirer_layout = _builder(header, footer=footer)
    try:
        yield
    finally:
        common.create_inquirer_layout = original


def _counted(catalog: Catalog) -> str:
    """`31 artifacts available` — what the catalog step is about to offer."""
    total = len(catalog.frameworks) + len(catalog.bundles) + len(catalog.pool)
    plural = "artifact" if total == 1 else "artifacts"
    return f"{total} {plural} available"


def _builder(
    header: Callable[[], StyleAndTextTuples] | None, *, footer: bool
) -> Callable[..., Layout]:
    """A `create_inquirer_layout` that closes over this prompt's static header."""

    def build(
        ic: InquirerControl,
        get_prompt_tokens: Callable[[], StyleAndTextTuples],
        **kwargs: Any,  # noqa: ANN401 — questionary's own pass-through into the layout
    ) -> Layout:
        return _rail_layout(ic, get_prompt_tokens, header, footer=footer, **kwargs)

    return build


def _rail_layout(
    ic: InquirerControl,
    get_prompt_tokens: Callable[[], StyleAndTextTuples],
    header: Callable[[], StyleAndTextTuples] | None,
    *,
    footer: bool,
    **kwargs: Any,  # noqa: ANN401 — questionary's own pass-through into the layout
) -> Layout:
    """`questionary`'s layout with a rail down it, a viewport, a counter and a footer.

    It mirrors `questionary.prompts.common.create_inquirer_layout` and departs
    from it in exactly the four places #65 measured. The two attribute
    assignments it inlines are what that function calls
    `_fix_unecessary_blank_lines` for — copied rather than called so the only
    thing this module depends on is the public name it replaces.
    """
    session: PromptSession[str] = PromptSession(
        _collapsing(ic, get_prompt_tokens), reserve_space_for_menu=0, **kwargs
    )
    for window in session.layout.find_all_windows():
        content = window.content
        if isinstance(content, BufferControl) and content.buffer.name == "DEFAULT_BUFFER":
            # Keeps the main window as small as possible, which is what stops a
            # blank line appearing under every selection.
            window.dont_extend_height = Always()
            window.always_hide_cursor = Always()

    @Condition
    def searching() -> bool:
        return ic.get_search_string_tokens() is not None

    @Condition
    def unanswered() -> bool:
        return not ic.is_answered

    parts: list[Any] = [session.layout.container]
    if header is not None:
        parts.append(
            ConditionalContainer(
                # `dont_extend_height` is what keeps a short step short: without
                # it this `Window` claims the rows the list did not use, and the
                # two-row scope step drew six blank lines between its hint and
                # its choices.
                Window(FormattedTextControl(header), dont_extend_height=True),
                filter=unanswered,
            )
        )
    parts.append(
        ConditionalContainer(
            VSplit(
                [
                    Window(
                        width=LayoutDimension.exact(1),
                        content=FormattedTextControl(
                            lambda: [("class:separator", _rail_column(ic))]
                        ),
                        dont_extend_height=True,
                    ),
                    Window(ic, height=_viewport_of(ic), dont_extend_height=True),
                ]
            ),
            filter=~IsDone(),
        )
    )
    parts.append(
        ConditionalContainer(
            Window(
                height=LayoutDimension.exact(1),
                content=FormattedTextControl(lambda: _counter(ic)),
            ),
            filter=~IsDone(),
        )
    )
    parts.append(
        ConditionalContainer(
            Window(
                height=LayoutDimension.exact(2),
                content=FormattedTextControl(_searching(ic)),
            ),
            filter=searching & ~IsDone(),
        )
    )
    if footer:
        parts.append(
            ConditionalContainer(
                Window(
                    height=LayoutDimension.exact(3),
                    content=FormattedTextControl(lambda: _footer(ic)),
                ),
                filter=~IsDone(),
            )
        )
    else:
        parts.append(
            ConditionalContainer(
                Window(
                    height=LayoutDimension.exact(1),
                    content=FormattedTextControl(lambda: [("class:separator", CLOSE_MARK)]),
                ),
                filter=~IsDone(),
            )
        )
    return Layout(HSplit(parts))


def _viewport_of(ic: InquirerControl) -> Callable[[], LayoutDimension]:
    """The height of the list: as tall as it needs, never taller than `VIEWPORT`.

    A callable and not a constant `Dimension`, for two reasons that are the same
    reason. A bare `Dimension(max=n)` leaves `preferred` at the maximum, so the
    two-row scope step reserved eight and drew six blank lines under its
    choices; and the row count is not fixed anyway — a search character filters
    the list, so the height has to be recomputed on the redraw that filtering
    triggers.
    """

    def height() -> LayoutDimension:
        rows = max(1, len(ic.choices))
        return LayoutDimension(min=1, max=VIEWPORT, preferred=min(VIEWPORT, rows))

    return height


def _searching(ic: InquirerControl) -> Callable[[], StyleAndTextTuples]:
    """What the reader has typed so far, or nothing — never `questionary`'s `None`.

    The library answers `None` when no search is running, and `None` is not
    formatted text; the original layout leaned on the `ConditionalContainer`
    never rendering it, which is true and untyped. Normalising here is what lets
    the whole module stay clean under `pyright --strict`.
    """

    def tokens() -> StyleAndTextTuples:
        found = ic.get_search_string_tokens()
        collected: StyleAndTextTuples = []
        if found is not None:
            collected.extend(found)
        return collected

    return tokens


def _rail_column(ic: InquirerControl) -> str:
    """One rail per row the control actually draws, never more.

    Measured: a fixed `VIEWPORT` column left the two-row scope step trailing
    six bare rails under it, which reads as a list that lost its rows rather
    than as a list with two.
    """
    return "\n".join(RAIL for _ in range(min(VIEWPORT, len(ic.choices))))


def _counter(ic: InquirerControl) -> StyleAndTextTuples:
    """`↓ N more` — how much of the list is below the viewport, live.

    Counted off `ic.choices` and not off the list this prompt was built with,
    because those two differ the moment a search character arrives: the counter
    has to shrink with the filter, or it would announce rows the filter has
    already hidden.
    """
    selectable = sum(1 for choice in ic.choices if not isinstance(choice, questionary.Separator))
    hidden = max(0, selectable - VIEWPORT)
    if not hidden:
        return [("class:separator", RAIL)]
    return [("class:separator", f"{RAIL}  ↓ {hidden} more")]


def _footer(ic: InquirerControl) -> StyleAndTextTuples:
    """`Selected: …` — what is ticked right now, named rather than counted.

    Named because a count is exactly what the reader cannot check: `npx skills`
    prints the names and a remainder, and that is what lets someone confirm they
    ticked what they meant to without leaving the prompt.
    """
    picked = [_titled(choice) for choice in ic.get_selected_values()]
    shown = ", ".join(picked[:_SELECTED_SHOWN])
    rest = len(picked) - _SELECTED_SHOWN
    body = f"{shown} +{rest} more" if rest > 0 else shown
    return [
        ("class:separator", f"{RAIL}\n"),
        ("class:separator", f"{RAIL}  Selected: "),
        ("class:answer", f"{body or 'nothing yet'}\n"),
        ("class:separator", CLOSE_MARK),
    ]


def _collapsing(
    ic: InquirerControl, original: Callable[[], StyleAndTextTuples]
) -> Callable[[], StyleAndTextTuples]:
    """Wrap the prompt line so an answered step collapses the way `npx skills` collapses one.

    `questionary` answers `? Question [a, b]` on one crowded line, or
    `done (7 selections)` — a count where the reader wanted the names. The
    session grammar wants two lines: the mark and the question, then the answer
    on the rail under it. Both halves are rebuilt from `ic`, which is the only
    object that knows what was picked.

    The first two tokens of `get_prompt_tokens` are the mark and the question in
    both `select.py` and `checkbox.py`, and they are stable across the answered
    flag — which is what lets the question be read off the original rather than
    threaded in from the call site.
    """

    def tokens() -> StyleAndTextTuples:
        raw = original()
        if not ic.is_answered:
            return raw
        question = raw[1][1].strip() if len(raw) > 1 else ""
        return [
            ("class:qmark", DONE_MARK),
            ("class:question", f"  {question}"),
            ("class:text", f"\n{RAIL}  "),
            ("class:answer", _answer(ic)),
        ]

    return tokens


def _answer(ic: InquirerControl) -> str:
    """What the step settled on, in names — one for a select, all of them for a checkbox."""
    selected = ic.get_selected_values()
    if selected:
        return ", ".join(_titled(choice) for choice in selected)
    return _titled(ic.get_pointed_at())


def _titled(choice: questionary.Choice) -> str:
    """A choice's title as a plain string, whichever of the two shapes it carries."""
    title = choice.title
    if isinstance(title, list):
        return "".join(fragment[1] for fragment in title)
    return str(title)
