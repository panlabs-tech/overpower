"""What the product draws. Variant **F — Herdada · bloco**, locked in #12.

Thin frames, a 7-bit 50 x 5 ASCII banner, artifact names in cyan, the
description **indented under the name**, a blank line between categories and a
coloured block heading. The prototype that produced it is in the history of
`prototype/terminal-experience/`; what survived into the product is this file.

Every screen here is a **renderable**, never a print. That is what lets the test
doctrine record a screen instead of a byte stream: the snapshot is
`Console(record=True).export_text()` of exactly these objects, so an output path
that bypassed them would be an output path no snapshot can see.

Two positions of #36 change what the prototype drew, and both are subtractions:

- **the `list` does not show origin.** The `NOTICE` of the wheel is curation
  text the program never reads — it travels in the package metadata under
  PEP 639, which is exactly what keeps it off every screen and out of the
  target (ADR 0003);
- with the origin gone, its line held only the file count, so the count joins the
  size on the head line — *name, size and file count*, and the description whole
  underneath.

**Everything that comes off disk is rendered as `Text`, never as markup.** A
description is data: it is read from a `SKILL.md` this repository does not own,
so a `[bold]` inside it has to arrive on screen as those seven characters.

The catalog screen and the three detail screens are **one function apart**, and
that is deliberate: `_entry` draws an item the same way wherever it appears, and
a detail screen is that entry plus what the item carries. The block heading is
what says which of the four screens is on: `AI Frameworks` against `AI
Framework`, `Bundles` against `Bundle`. A second layout for the same item would
be a second place for the truncation rule to be forgotten.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import TYPE_CHECKING, assert_never

from rich import box
from rich.console import Group
from rich.padding import Padding
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from overpower.discovery import Artifact
from overpower.inspection import DanglingLink, Divergence, LinkTurnedText
from overpower.planning import DirectoryTree, DocumentKey, WriteMode
from overpower.recipes import Recipe

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from pathlib import Path

    from rich.console import Console, ConsoleOptions, RenderableType, RenderResult

    from overpower.discovery import Bundle, Catalog, Framework
    from overpower.inspection import Diagnosis, Finding, Terminal
    from overpower.planning import Carried, Destination, Landing, Plan, Selection

THEME = Theme(
    {
        "op.brand": "bold magenta",
        # The block heading of `list`. Same ink as the brand today and a separate
        # name on purpose: the palette is the entry someone will want to move
        # first, and `op.key` is taken — it is the artifact name, which has to
        # read as a different rank.
        #
        # `not dim` is load-bearing rather than decoration. Measured in #12: rich
        # composes a Panel's `border_style` into its title, so with the thin dim
        # border the heading renders `ESC[1;2;35m` — bold DIM magenta — and the
        # emphasis the thick border used to carry is lost twice over.
        "op.section": "bold magenta not dim",
        "op.ok": "bold green",
        "op.warn": "bold yellow",
        "op.err": "bold red",
        "op.dim": "dim",
        "op.key": "cyan",
        # The command line under a `list` entry. Split from `op.key` on purpose
        # (#67): both used to render in cyan, so the command borrowed the exact
        # ink that named the artifact above it, and with several commands on
        # screen the artifact name stopped standing out. `#5f819d` is not a new
        # colour to the terminal session — it is `questionary`'s own default
        # `qmark` blue-grey (`wizard.py`'s prompts already render it), reused
        # here rather than invented so the command reads as ink the eye already
        # treats as "structure", not "content".
        "op.command": "#5f819d",
    }
)

BANNER = r"""
  _____   _____ _ __ _ __   _____      _____ _ __
 / _ \ \ / / _ \ '__| '_ \ / _ \ \ /\ / / _ \ '__|
| (_) \ V /  __/ |  | |_) | (_) \ V  V /  __/ |
 \___/ \_/ \___|_|  | .__/ \___/ \_/\_/ \___|_|
                    |_|
"""
"""FIGlet `standard`, 50 x 5, and 7-bit on purpose: it has to survive any terminal."""

BANNER_WIDTH = 50
"""Below this the art does not fit, and a wrapped banner is worse than no banner."""

TAGLINE = "installs curated agent equipment"

PROGRAM = "overpower"
"""The command someone types, and therefore the first word of every line `list` prints.

It lives in the screens and not in `overpower.cli` — which imports it back, and
declares its own command with it — for one reason: the line printed here has to
be a line the shell answers to, and two spellings of one word is exactly how
those two stop being the same string.
"""

AI_FRAMEWORK_FLAG = "--ai-framework"
BUNDLE_FLAG = "--bundle"
SKILL_FLAG = "--skill"
MCP_FLAG = "--mcp"
"""The four selectors, spelled once for the screen that prints them and the CLI
that declares them.

Same reasoning as `PROGRAM`, and the reason it is not laboured differently: a
printed command is a promise that the flag inside it exists, so a rename that
moved only the `typer.Option` would leave the catalog printing a line that no
longer parses — green, because nothing compares two literals.

`--skill` is the pool selector and not the artifact's own type: it is the only
one v0.1.0 ships, and the day a command lands in the pool the CLI grows the flag
before this line can name it.
"""


class Mark(StrEnum):
    """The five punctuation marks of a session, named rather than spelled.

    A name and not the glyph itself because the glyph is **two** glyphs: the
    ASCII fallback is chosen at render time off `ConsoleOptions.ascii_only`, the
    same switch `_PlanScreen` already reads for its arrow, and for the same
    measured reason — `│` is not encodable in cp1252, which is what a pipe on
    Windows takes.
    """

    OPEN = "open"
    DONE = "done"
    ACTIVE = "active"
    NOTE = "note"
    CLOSE = "close"


_MARKS = MappingProxyType(
    {Mark.OPEN: "┌", Mark.DONE: "◇", Mark.ACTIVE: "◆", Mark.NOTE: "●", Mark.CLOSE: "└"}
)
"""The session vocabulary of `npx skills`, adopted whole (#65)."""

_ASCII_MARKS = MappingProxyType(
    {Mark.OPEN: "+", Mark.DONE: "-", Mark.ACTIVE: ">", Mark.NOTE: "*", Mark.CLOSE: "+"}
)
"""The same five where the console cannot carry the first five."""

RAIL = "│"
"""The vertical that connects every step, and the whole of what makes it read as one gesture."""

_ASCII_RAIL = "|"

ACTIVE_MARK = _MARKS[Mark.ACTIVE]
DONE_MARK = _MARKS[Mark.DONE]
CLOSE_MARK = _MARKS[Mark.CLOSE]
"""The three the wizard needs as plain strings.

`prompt_toolkit` draws its own screen and takes `(style, text)` pairs, not
renderables, so the marks it needs cannot arrive as `Mark` members. There is no
ASCII fallback on this path and none is needed: `questionary` requires a real
terminal — a pipe raises `EOFError` — so the cp1252-under-a-pipe case that
`_SessionLine` guards against cannot reach these three.
"""

_MARK_STYLE = MappingProxyType(
    {
        Mark.OPEN: "op.brand",
        Mark.DONE: "op.ok",
        Mark.ACTIVE: "op.brand",
        Mark.NOTE: "op.key",
        Mark.CLOSE: "op.brand",
    }
)
"""Ink per rank. The palette is ours; the structure is the one that was adopted."""

_KIB = 1024
_MIB = 1024 * 1024

_READERS_SHOWN = 3
"""How many runtimes a plan line names before it counts the rest.

Three and a `(+N)`, which is the shape the prototype settled on: enough to
recognise the place, short enough that the line still fits at 60 columns next to
the path it belongs to.
"""


@dataclass(frozen=True)
class _Glyphs:
    """The two marks a plan line is drawn with, in what this console can encode.

    Measured: neither `←` nor `›` can be encoded in cp1252, which is what a pipe
    on Windows takes, and rich writes text straight to the file — so a hard-coded
    pair raises `UnicodeEncodeError` out of the middle of the screen, on the
    three Windows cells only. `ascii_only` is the same switch rich itself reads
    to swap the box characters, and it is read off the console about to draw
    rather than off the platform, so a UTF-8 pipe on Windows keeps both.
    """

    arrow: str
    """`place ← who reads it`."""

    into: str
    """`document › key inside it` — the graft's own separator.

    One spelling of *"a key inside a document"*, shared with the `doctor`: two
    would be two ways to write the one thing a reader has to recognise across
    both screens.
    """

    @classmethod
    def of(cls, options: ConsoleOptions) -> _Glyphs:
        """The pair this console can carry."""
        if options.ascii_only:
            return cls(arrow="<-", into=">")
        return cls(arrow="←", into="›")


def banner(version: str, width: int) -> RenderableType:
    """The opening screen: the art, the tagline, and the version.

    Whether it is *shown* is not decided here — it is a terminal question, and
    the CLI gates it on `isatty()`.
    """
    if width < BANNER_WIDTH:
        return Text.assemble(("overpower ", "op.brand"), (version, "op.dim"))
    return Group(
        Text(BANNER, style="op.brand"),
        Text.assemble("  ", (TAGLINE, "op.dim"), "   ", (f"v{version}", "op.key")),
    )


@dataclass(frozen=True)
class _SessionLine:
    """One punctuated line of the session, assembled at render time for its glyphs.

    The lead rail is part of the line and not the caller's to remember, and that
    is the whole reason this is a type: the rhythm of `npx skills` is that
    **every** step is preceded by a rail, and a caller that had to print one
    between steps is a caller that will forget one between two of them.
    """

    mark: Mark
    text: str
    answer: str | None = None
    lead: bool = True

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        """The mark, the text, and the answer under it — in glyphs this console can carry."""
        del console
        marks = _ASCII_MARKS if options.ascii_only else _MARKS
        rail = _ASCII_RAIL if options.ascii_only else RAIL
        if self.lead:
            yield Text(rail, style="op.dim")
        yield _hanging(Text(marks[self.mark], style=_MARK_STYLE[self.mark]), Text(self.text))
        if self.answer is not None:
            yield _hanging(Text(rail, style="op.dim"), Text(self.answer, style="op.key"))


def _hanging(mark: Text, body: Text) -> RenderableType:
    """A mark and its text, where a wrapped line keeps the indent of the first.

    A two-column grid and never `Text.assemble` with spaces, for the reason
    `_entry` gives for its `Padding`: measured at 60 columns, the sign-off is
    76 characters and wraps, and assembled as one string its continuation lands
    at column 0 — under the rail rather than beside it, which reads as a line
    that fell out of the session.
    """
    line = Table.grid(padding=(0, 2))
    line.add_column(no_wrap=True)
    line.add_column(overflow="fold")
    line.add_row(mark, body)
    return line


def opened(title: str) -> RenderableType:
    """`┌   overpower install` — the session begins, and nothing precedes it."""
    return _SessionLine(Mark.OPEN, title, lead=False)


def noted(text: str) -> RenderableType:
    """`●  selected: matt-pocock — 25 skills` — a fact the session establishes on the way."""
    return _SessionLine(Mark.NOTE, text)


def stepped(label: str, answer: str) -> RenderableType:
    """`◇  label` over `│  answer` — a step that was settled without being asked.

    The same shape `questionary` collapses to once answered, drawn here for the
    steps that never open: outside a git repository the scope has one legal
    answer, and ADR 0008 wants that explicit rather than silent, so it is
    *reported* rather than *asked*.
    """
    return _SessionLine(Mark.DONE, label, answer=answer)


def closed(text: str) -> RenderableType:
    """`└  Done!  …` — the session ends, and the rail stops."""
    return _SessionLine(Mark.CLOSE, text)


def railed() -> RenderableType:
    """A bare rail, for the gap between a prompt and what follows it."""
    return _RailLine()


@dataclass(frozen=True)
class _RailLine:
    """One rail character, in whichever of the two the console can encode."""

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        """Just the rail."""
        del console
        yield Text(_ASCII_RAIL if options.ascii_only else RAIL, style="op.dim")


@dataclass(frozen=True)
class _RailPanel:
    """A panel that hangs off the rail instead of floating beside it.

    `rich`'s own `Panel` cannot draw this shape: it owns all four corners, and
    what this needs is a **title line that starts with the session mark** and a
    bottom-left that is a tee rather than a corner — which is what says the
    frame is inside the session and not a sibling of it. Thirty lines of segment
    assembly buys the one property the whole repaint exists for, so it is drawn
    here rather than approximated with a `Panel` whose corners say otherwise.
    """

    title: str
    body: RenderableType

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        """Title line, body inside the rail, and a tee that closes it back onto the rail."""
        marks = _ASCII_MARKS if options.ascii_only else _MARKS
        rail = _ASCII_RAIL if options.ascii_only else RAIL
        horizontal, corner, tee = ("-", "+", "+") if options.ascii_only else ("─", "╮", "├")

        width = options.max_width
        # Two of padding either side of the body, a rail on the left and a border
        # on the right. `max` keeps a very narrow terminal from computing a
        # negative width, which `render_lines` would raise on.
        inner = max(1, width - 6)
        lines = console.render_lines(self.body, options.update(width=inner), pad=True)

        head = f"{marks[Mark.DONE]}  {self.title} "
        yield Text.assemble(
            (marks[Mark.DONE], _MARK_STYLE[Mark.DONE]),
            f"  {self.title} ",
            (horizontal * max(0, width - len(head) - 1), "op.dim"),
            (corner, "op.dim"),
        )
        yield _bordered(Text(""), rail, inner)
        for line in lines:
            body = Text("").join(Text(segment.text, style=segment.style or "") for segment in line)
            yield _bordered(body, rail, inner)
        yield _bordered(Text(""), rail, inner)
        foot = "+" if options.ascii_only else "╯"
        yield Text.assemble(
            (tee, "op.dim"), (horizontal * max(0, width - 2), "op.dim"), (foot, "op.dim")
        )


def _bordered(line: Text, rail: str, inner: int) -> Text:
    """One body line, between the rail and the right border."""
    padded = line.copy()
    padded.pad_right(max(0, inner - padded.cell_len))
    return Text.assemble((rail, "op.dim"), "  ", padded, "  ", (rail, "op.dim"))


def catalog_screen(catalog: Catalog) -> RenderableType:
    """The whole catalog: three blocks, with a blank line between them.

    Three and not one grid, because the three units are not levels of a
    hierarchy — a framework, a pool artifact and a bundle are chosen
    independently, and a single table would rank them.
    """
    blocks = (
        _block(
            "AI Frameworks",
            "installs whole",
            [
                _entry(
                    framework.name,
                    framework.size,
                    framework.files,
                    framework.description,
                    commands=(
                        _install(AI_FRAMEWORK_FLAG, framework.name),
                        _inspect(AI_FRAMEWORK_FLAG, framework.name),
                    ),
                )
                for framework in catalog.frameworks
            ],
        ),
        _block(
            "Pool skills",
            "installs alone",
            [
                _entry(
                    artifact.name,
                    artifact.size,
                    artifact.files,
                    artifact.description,
                    commands=(_install(SKILL_FLAG, artifact.name),),
                )
                for artifact in catalog.pool
            ],
        ),
        _block(
            "Bundles",
            "lists pool artifacts only",
            [
                _entry(
                    bundle.name,
                    bundle.size,
                    bundle.files,
                    bundle.description,
                    commands=(
                        _install(BUNDLE_FLAG, bundle.name),
                        _inspect(BUNDLE_FLAG, bundle.name),
                    ),
                )
                for bundle in catalog.bundles
            ],
        ),
    )
    return Group(*_spaced(blocks))


def framework_screen(framework: Framework) -> RenderableType:
    """One AI Framework: what it weighs, what it says, and what is inside it.

    The artifacts are **stacked, with the type of each one as its prefix**, and
    the type is read off the tree rather than assumed: an AI Framework may mix
    skill, command, hook and MCP. A framework installs *whole* (rule 1), so
    whoever is about to accept one has to be able to read what *"whole"* means
    before accepting it — which is also why the list is stacked instead of
    columnar. A grid of names has to change its column count with the terminal
    width to stop clipping the longest name; a stacked list clips at no width.
    """
    return _block(
        "AI Framework",
        "installs whole",
        [
            _entry(
                framework.name,
                framework.size,
                framework.files,
                framework.description,
                contents=framework.artifacts,
                # Only the line that installs. Printing `list --ai-framework
                # matt-pocock` inside the output of that very command is a no-op.
                commands=(_install(AI_FRAMEWORK_FLAG, framework.name),),
            )
        ],
    )


def bundle_screen(bundle: Bundle) -> RenderableType:
    """One bundle: the pool artifacts its manifest names, and nothing else.

    In the order the manifest wrote them, never sorted — a bundle is a curated
    composition, and the order is part of what was curated.
    """
    return _block(
        "Bundle",
        "lists pool artifacts only",
        [
            _entry(
                bundle.name,
                bundle.size,
                bundle.files,
                bundle.description,
                contents=bundle.artifacts,
                commands=(_install(BUNDLE_FLAG, bundle.name),),
            )
        ],
    )


def artifact_screen(artifact: Artifact) -> RenderableType:
    """One pool artifact: its description **whole**, which is the whole screen.

    It is the extreme case of the rule the catalog screen already obeys — the
    maximum measured across the promoted skills is 517 characters — and the
    reason it is a screen of its own is that a description read in halves is a
    description someone has to go and look up elsewhere.

    The heading is driven by the artifact's own type, because the pool is not a
    pool of skills by definition: `--skill` is the only selector v0.1.0 ships,
    and the day a command lands in the tree this screen already says so.
    """
    return _block(
        f"Pool {artifact.type}",
        "installs alone",
        [
            _entry(
                artifact.name,
                artifact.size,
                artifact.files,
                artifact.description,
                commands=(_install(SKILL_FLAG, artifact.name),),
            )
        ],
    )


def plan_screen(plan: Plan) -> RenderableType:
    """Everything the plan will write, before a single byte of it is written.

    It draws a `Landing` as what a `Landing` is — a path and everyone who reads
    it — and the argument for that shape lives on the type, in
    `overpower.planning`, so it is stated once.
    """
    return _PlanScreen(plan)


@dataclass(frozen=True)
class _PlanScreen:
    """The plan panel, assembled at render time because one glyph depends on the encoding.

    Measured: `←` cannot be encoded in cp1252, which is what a pipe on Windows
    takes, and rich writes text straight to the file — so a hard-coded arrow
    raises `UnicodeEncodeError` out of the middle of the screen, on the three
    Windows cells only. `ascii_only` is the same switch rich itself uses to swap
    the box characters for ASCII, and it is read off the console that is about
    to draw rather than off the platform, so a UTF-8 pipe on Windows keeps the
    arrow and a cp1252 one does not.
    """

    plan: Plan

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        """Draw the panel with the marks this console can carry."""
        del console
        yield _plan_panel(self.plan, _Glyphs.of(options))


def doctor_screen(diagnosis: Diagnosis) -> RenderableType:
    """Two questions in one output: how the terminal is, and how what landed is.

    Two blocks and not one, for the reason the catalog screen has three: they
    answer different questions, and a single frame would rank the environment
    against the integrity when the whole point of `doctor` is that either one
    alone leaves a person guessing.
    """
    return _DoctorScreen(diagnosis)


@dataclass(frozen=True)
class _DoctorScreen:
    """The `doctor` output, assembled at render time for the arrow of `_PlanScreen`.

    Same measurement, same switch: `←` is not encodable in cp1252, which is what
    a pipe on Windows takes, and this screen points at a link's target on exactly
    the cells where that matters most.
    """

    diagnosis: Diagnosis

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        """Draw both blocks with the marks this console can carry."""
        del console
        glyphs = _Glyphs.of(options)
        yield Group(
            *_spaced(
                (
                    _terminal_block(self.diagnosis.terminal),
                    _integrity_block(self.diagnosis, glyphs),
                )
            )
        )


@dataclass(frozen=True)
class _Roots:
    """The two places a `doctor` path can be shortened against, and how.

    A type rather than two parameters travelling together through three call
    levels: the screen reports both scopes in one output, so *"which root does
    this path belong to"* is one question asked at every path, and the answer
    reads better next to the data than passed alongside it.
    """

    repository: Path | None
    home: Path

    def shorten(self, path: Path) -> str:
        """The repository first, then the home, then not at all.

        `/` separators on every platform, deliberately, as on the plan: the
        runtime table spells its paths that way, `git status` prints them that
        way on Windows too, and a screen whose separator changes with the
        platform cannot be recorded once for the nine cells.

        A place under neither root is shown whole, because it is not a detail
        the reader can reconstruct — that is the second write of a graft.
        """
        if self.repository is not None and path.is_relative_to(self.repository):
            return path.relative_to(self.repository).as_posix()
        if path.is_relative_to(self.home):
            return f"~/{path.relative_to(self.home).as_posix()}"
        return path.as_posix()


def _terminal_block(terminal: Terminal) -> Panel:
    """The four facts a strange-looking screen is explained by."""
    facts = Table.grid(padding=(0, 2))
    facts.add_column()
    facts.add_column(overflow="fold")
    rows = (
        ("tty", "yes" if terminal.tty else "no"),
        ("colour", terminal.colour),
        ("width", f"{terminal.width} {_plural('column', terminal.width)}"),
        ("NO_COLOR", _no_color(terminal.no_color)),
    )
    for label, value in rows:
        facts.add_row(Text(label, style="op.dim"), Text(value, style="op.key"))
    return _block("terminal", "how this screen is set up", [facts])


def _no_color(value: str | None) -> str:
    """`NO_COLOR` is presence-based, so *set to nothing* is not the same as *unset*."""
    if value is None:
        return "unset"
    return value if value.strip() else 'set to ""'


def _integrity_block(diagnosis: Diagnosis, glyphs: _Glyphs) -> Panel:
    """What landed, counted, and everything wrong with it.

    The count line says **artifacts and places**, two numbers and never one: an
    artifact occupies as many places as runtimes were equipped, and a screen
    that printed a single number would be the screen assuming one artifact costs
    one write — the shape `domain.md` locks against for the graft.
    """
    counted = Text(
        f"{diagnosis.artifacts} {_plural('artifact', diagnosis.artifacts)}"
        f" · {len(diagnosis.landed)} {_plural('place', len(diagnosis.landed))}",
        style="op.dim",
    )
    roots = _Roots(repository=diagnosis.root, home=diagnosis.home)
    found: list[RenderableType] = [
        _finding(finding, roots, glyphs) for finding in diagnosis.findings
    ]
    if not found:
        found = [Text("no findings", style="op.ok")]
    return _block("integrity", "what is installed", [counted, *found])


def _finding(finding: Finding, roots: _Roots, glyphs: _Glyphs) -> RenderableType:
    """One thing that is wrong: what class it is, and every path that carries it."""
    arrow = glyphs.arrow
    match finding:
        case DanglingLink(destination, points_at):
            place = _located(destination, roots, glyphs)
            pointed = "" if points_at is None else f"  {arrow} {points_at}"
            return _flagged("dangling link", [f"{place}{pointed}"])
        case LinkTurnedText(destination, inside, points_at):
            place = _located(destination, roots, glyphs)
            relative = _under(inside, destination.path)
            return _flagged("link became a text file", [f"{place}  {relative} {arrow} {points_at}"])
        case Divergence(name, _, destinations):
            places = [_located(destination, roots, glyphs) for destination in destinations]
            return _flagged(f"copies of `{name}` differ", places)
        case _ as unreachable:
            assert_never(unreachable)


def _flagged(headline: str, places: Sequence[str]) -> RenderableType:
    """A finding: the class in warning ink, the paths indented under it.

    Indented with `Padding` and never with spaces in the string, for the reason
    `_entry` uses it: a path long enough to wrap has to keep its indent, and a
    narrow terminal is exactly where a path is long enough to wrap.
    """
    stacked = Table.grid()
    # `fold`, as on the plan: a truncated path is the one thing a diagnosis may
    # not print, because the path is the whole of what the reader has to act on.
    stacked.add_column(overflow="fold")
    for place in places:
        stacked.add_row(Text(place, style="op.dim"))
    return Group(Text(headline, style="op.warn"), Padding(stacked, (0, 0, 0, 2)))


def _located(destination: Destination, roots: _Roots, glyphs: _Glyphs) -> str:
    """Where a write is, said the shortest way that still names it unambiguously.

    The two forms of a destination read differently on purpose: a folder earns a
    trailing separator, and a document plus a key inside it is spelled with the
    key attached. v0.1.0 produces only the first, and the second is here because
    a report that could only spell a folder would be one v0.2 has to replace
    rather than extend.
    """
    shown = roots.shorten(destination.path)
    match destination:
        case DirectoryTree():
            return f"{shown}/"
        case DocumentKey(_, key):
            return f"{shown} {glyphs.into} {key}"
        case _ as unreachable:
            assert_never(unreachable)


def _under(path: Path, base: Path) -> str:
    """A file named against the write it was found in, so the line stays readable."""
    if path.is_relative_to(base):
        return path.relative_to(base).as_posix()
    return path.as_posix()  # pragma: no cover — the walk starts at the destination


def error_panel(body: Text) -> Panel:
    """A failure as a panel, which is the whole reason the top handler exists.

    The body is a `Text` and the type is the guard, not a preference. An error
    message carries paths and exception text, both of which routinely contain
    `[`: measured, a path of `/tmp/[wip]/pool/sklls` printed as markup renders
    `/tmp//pool/sklls` — the wrong path silently loses the segment that names it
    — and `/tmp/[/2024]/SKILL.md` raises `MarkupError` *out of* the handler,
    which is the traceback the handler exists to prevent.
    """
    return Panel(
        body,
        title="[op.err]error[/]",
        title_align="left",
        box=box.ROUNDED,
        border_style="op.err",
        padding=(1, 2),
    )


def human(size: int) -> str:
    """Bytes the way the research reported them: `948 B`, `6.8 KiB`, `1.02 MiB`."""
    if size < _KIB:
        return f"{size} B"
    if size < _MIB:
        return f"{size / _KIB:.1f} KiB"
    return f"{size / _MIB:.2f} MiB"


def summary_screen(plan: Plan) -> RenderableType:
    """The **gate**: the same plan, said as destinations rather than as artifacts.

    Measured, and this is what reopens the position written on `_planned`
    (#65): the detailed plan is **34 lines** at 80 columns, and a terminal is
    24, so at the moment `Write these paths?` appears the first **11** have
    scrolled — including the head line that names what is being accepted and how
    much of it. Fidelity to `list` was chosen there "over fitting on one
    screen", on the argument that a gate has to be readable whole; the
    measurement says that at the default size it was readable *not at all*.

    So the gate takes the shape `npx skills` gives it — source, count, and one
    line per destination with who reads it — and the artifact list stays where
    it can be read at leisure: `--dry-run` and `list`. **It is the same
    function** underneath, one flag apart, which is what keeps the truncation
    rule in one place; that invariant was the real reason `_planned` was single,
    and it is now structural rather than remembered.
    """
    return _SummaryScreen(plan)


@dataclass(frozen=True)
class _SummaryScreen:
    """The gate panel, assembled at render time for the arrow of `_PlanScreen`."""

    plan: Plan

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        """Draw the compact plan inside a frame that hangs off the rail."""
        del console
        glyphs = _Glyphs.of(options)
        yield _RailPanel(
            "summary",
            Group(
                *_spaced(
                    [
                        _planned(selection, self.plan.root, glyphs, detailed=False)
                        for selection in self.plan.selections
                    ]
                )
            ),
        )


def installed_screen(plan: Plan, writes: int, files: int) -> RenderableType:
    """What landed, counted, and the places it landed in — the closing frame.

    `npx skills` closes with a panel and a sign-off, and the reason it reads as
    finished rather than as stopped is that the panel names **what** landed and
    the line names **what to do next**. What this replaces is a bare
    `installed 50 writes · 148 files`, which is the count with neither.
    """
    return _InstalledScreen(plan, writes, files)


@dataclass(frozen=True)
class _InstalledScreen:
    """The closing panel, assembled at render time for the arrow."""

    plan: Plan
    writes: int
    files: int

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        """One group per selection: its name, its weight, and where it went."""
        del console
        tick = "v" if options.ascii_only else "✓"
        arrow = "<-" if options.ascii_only else "←"
        blocks: list[RenderableType] = []
        for selection in self.plan.selections:
            places = Table.grid()
            places.add_column(overflow="fold")
            for landing in selection.landings:
                places.add_row(Text(_shown(self.plan.root, landing), style="op.dim"))
            blocks.append(
                Group(
                    Text.assemble(
                        (tick, "op.ok"),
                        " ",
                        (selection.name, "op.key"),
                        "  ",
                        (_carries(selection.artifacts), "op.dim"),
                    ),
                    Padding(places, (0, 0, 0, 2)),
                )
            )
        del arrow
        counted = Text(
            f"{self.writes} {_plural('write', self.writes)}"
            f" · {self.files} {_plural('file', self.files)}",
            style="op.dim",
        )
        yield _RailPanel("installed", Group(*_spaced([*blocks, counted])))


def _plan_panel(plan: Plan, glyphs: _Glyphs) -> Panel:
    """One block, and inside it one group per thing that was asked for."""
    return Panel(
        Group(
            *_spaced(
                [
                    _planned(selection, plan.root, glyphs, detailed=True)
                    for selection in plan.selections
                ]
            )
        ),
        title="[op.section]plan[/]",
        title_align="left",
        box=box.ROUNDED,
        border_style="op.dim",
        padding=(1, 2),
    )


def _planned(
    selection: Selection, root: Path, glyphs: _Glyphs, *, detailed: bool
) -> RenderableType:
    """What one selection brings, **named artifact by artifact**, and every place it lands.

    The stacked list is `_contents` — the same function the detail screens of
    `list` draw, and the same one on purpose (#58): a screen that summarised
    *"25 skills"* would ask someone to accept a set they have to leave the
    screen to read. The measured alternatives all cost more than they saved — a
    three-column grid needs 91 characters and a two-column one 62, so neither
    fits the widths this screen is recorded at, and a wrapped run of names fits
    but drops the type prefix that a framework of mixed types is read by.

    **`detailed` is where #65 revised #58, and the revision is one clause
    wide.** #58 chose fidelity to `list` *over fitting on one screen*, on the
    argument that the plan is the last gate before 148 files land in a
    repository that is not ours and a gate has to be readable whole. The
    measurement that reopened it: at 80x24 — the default terminal — the detailed
    plan of `matt-pocock` is 34 lines, so by the time `Write these paths?`
    appeared its first **11** had scrolled, including the head line naming what
    was being accepted. Fidelity had not bought a readable gate; it had bought
    an unreadable one.

    So the argument survives and its conclusion moves: the **gate** takes the
    short form, and the artifact list stays wherever there is no screen to fit —
    `--dry-run`, and any run whose output goes down a pipe. Both come out of
    **this function**, one flag apart, which is what keeps the truncation rule
    in one place; that invariant was the real content of *"there is one plan
    function"*, and it is now structural rather than remembered.

    It is drawn for **every** selection, including a pool skill that carries one
    artifact of its own name. The repetition is the rule staying one rule: the
    head line names what was *asked for* and the row names what *lands*, and the
    two coincide only by accident of the pool. A screen that hid the row when the
    names matched would be a second shape of plan, and the reason there is one
    plan function at all is that `--dry-run`, the wizard's confirmation and a
    direct run must not be able to disagree.
    """
    places = Table.grid(padding=(0, 1), expand=True)
    # `fold`, never the default `ellipsis`: a truncated path is the one thing
    # this screen may not do, and a narrow terminal is where it would happen.
    places.add_column(ratio=1, overflow="fold")
    places.add_column(justify="right", no_wrap=True)
    for landing in selection.landings:
        for line, counted in _place_rows(landing, root, glyphs):
            places.add_row(line, counted)
    head = Text.assemble(
        (selection.name, "op.key"), "  ", (_carries(selection.artifacts), "op.dim")
    )
    if not detailed:
        # The gate: head line and destinations, no artifact list. One blank line
        # keeps the two ranks apart the way the detailed form does with two.
        return Group(head, "", Padding(places, (0, 0, 0, 2)))
    return Group(
        head,
        Padding(_contents(selection.artifacts), (1, 0, 1, 2)),
        Padding(places, (0, 0, 0, 2)),
    )


def _place_rows(landing: Landing, root: Path, glyphs: _Glyphs) -> Iterable[tuple[Text, Text]]:
    """The rows one landing draws: **one per folder, one per key**.

    The two forms of a destination read differently because they *are*
    different: a copy lands in a folder and costs files, a graft lands in a key
    inside a document that is already there and costs no path at all. Naming the
    document alone would hide the only line that says which key is about to be
    replaced, which under unconditional overwriting (ADR 0013) is the whole of
    the reader's defence.
    """
    if landing.folder:
        yield (
            Text.assemble(
                _shown(root, landing),
                "  ",
                (glyphs.arrow, "op.dim"),
                " ",
                (_readers(landing.readers), "op.dim"),
                *_mode_suffix(landing.mode),
            ),
            Text(f"{landing.files} {_plural('file', landing.files)}", style="op.dim"),
        )
        return
    for key in landing.keys:
        yield (
            Text.assemble(
                _shown(root, landing),
                " ",
                (glyphs.into, "op.dim"),
                " ",
                (key, "op.key"),
                "  ",
                (glyphs.arrow, "op.dim"),
                " ",
                (_readers(landing.readers), "op.dim"),
            ),
            Text("1 key", style="op.dim"),
        )


def _mode_suffix(mode: WriteMode) -> tuple[tuple[str, str], ...]:
    """`  · link` or `  · junction` after the readers, nothing for a real copy.

    Project scope is copy-only and this renders nothing there, so no snapshot
    that predates the global scope moves. What it buys is the other half of the
    central assertion (https://github.com/panlabs-tech/overpower/issues/40): the
    plan now carries mode as well as path, so what the screen *calls* a link has
    something on screen to check against what is actually on disk.
    """
    if mode is WriteMode.COPY:
        return ()
    return ((f"  · {mode}", "op.dim"),)


def _shown(root: Path, landing: Landing) -> str:
    """The place, as the plan names it: relative to the target, with `/` separators.

    `/` on every platform, deliberately. The runtime table spells its paths that
    way, `git status` prints them that way on Windows too, and a screen whose
    separator changes with the platform cannot be recorded once for the nine
    cells of the matrix.

    A place *outside* the target is shown whole, because it is not a detail the
    reader can reconstruct — that is the second write of a graft, which lands
    outside the repository.
    """
    inside = landing.place.is_relative_to(root)
    shown = landing.place.relative_to(root).as_posix() if inside else landing.place.as_posix()
    return f"{shown}/" if landing.folder else shown


def _readers(keys: Sequence[str]) -> str:
    """`cursor, codex, github-copilot (+16)` — who reads the place, and how many more."""
    rest = len(keys) - _READERS_SHOWN
    shown = ", ".join(keys[:_READERS_SHOWN])
    return f"{shown} (+{rest})" if rest > 0 else shown


def _carries(artifacts: Sequence[Carried]) -> str:
    """`22 skills`, or `4 artifacts` when a selection mixes types.

    A framework may mix skill, command and agent — the type comes from the tree
    (rule 8) — so the noun is data and not a constant.
    """
    kinds = {_kind(item) for item in artifacts}
    noun = next(iter(kinds)) if len(kinds) == 1 else "artifact"
    return f"{len(artifacts)} {_plural(noun, len(artifacts))}"


def _kind(item: Carried) -> str:
    """What one carried thing is called on screen.

    An artifact answers with the type its folder gave it; a recipe answers `mcp
    server`, which is what it is — the noun is not `mcp`, because what lands is
    a server and the protocol is not the thing being installed.
    """
    match item:
        case Artifact():
            return str(item.type)
        case Recipe():
            return "mcp server"
        case _ as unreachable:
            assert_never(unreachable)


def _block(title: str, note: str, entries: Sequence[RenderableType]) -> Panel:
    """One category, framed. Colour carries the rank; the border stays thin."""
    return Panel(
        Group(*_spaced(entries)),
        title=f"[op.section]{title}[/]  [op.dim]{note}[/]",
        title_align="left",
        box=box.ROUNDED,
        border_style="op.dim",
        padding=(1, 2),
    )


def _install(flag: str, name: str) -> str:
    """The line that installs one item, exactly as it has to be typed back."""
    return f"{PROGRAM} install {flag} {name}"


def _inspect(flag: str, name: str) -> str:
    """The line that opens one item — only the two units that carry something to open."""
    return f"{PROGRAM} list {flag} {name}"


def _entry(  # noqa: PLR0913 — the four facts of an item plus the two blocks that hang under it.
    # The four do travel together, and `Artifact`, `Framework` and `Bundle` each carry them —
    # but as three types with no declared kinship and with `files`/`size` a field on one and a
    # property on the others, so unifying them means a `Protocol` invented for this one call.
    # The clump is real and the cure costs more than it; taken knowingly, not missed.
    name: str,
    size: int,
    files: int,
    description: str,
    *,
    contents: Sequence[Artifact] = (),
    commands: Sequence[str] = (),
) -> RenderableType:
    """Name and weight on the head line, the whole description indented under it.

    `commands` is what closes the journey the catalog opens: the lines to copy,
    a blank line under the description and indented one step past it. **Bare** —
    no `$` and no label column, both measured and refused. A `$` makes the
    selected line paste back broken; a label column does not fit, because at 60
    columns the panel body is 54 characters and `overpower install --skill
    panlabs-python-standards` indented already occupies exactly that. The words
    `install` and `list` inside the command are the label.

    `contents` is what turns the same entry into a detail screen: the artifacts
    the item carries, stacked with a blank line between. An item that carries
    none — a pool artifact — renders exactly as it does on the catalog screen,
    which is the point of it being one function.
    """
    head = Table.grid(padding=(0, 1), expand=True)
    head.add_column(ratio=1)
    head.add_column(justify="right", no_wrap=True)
    head.add_row(
        Text(name, style="op.key"), Text(_weight(size, files, len(contents)), style="op.dim")
    )
    body: list[RenderableType] = [
        head,
        # `Padding`, and never a spaced string: a wrapped line has to keep the
        # indent, otherwise a narrow terminal dumps the continuation at column 0
        # — and the continuation is where a 517-character description lives.
        Padding(Text(description, style="op.dim"), (0, 0, 0, 2)),
    ]
    if commands:
        body.append(Padding(_commands(commands), (1, 0, 0, 4)))
    if contents:
        body.append(Padding(_contents(contents), (1, 0, 0, 2)))
    return Group(*body)


def _commands(commands: Sequence[str]) -> RenderableType:
    """The lines to copy, one per row, folded rather than cut.

    `fold`, never the default `ellipsis`, for the same reason a planned path
    folds: a truncated command is a command nobody can type back, and that is
    the whole of what these lines are for.

    They are **not** gated on being in a terminal, unlike the banner: the banner
    is a courtesy and a command is a datum, so `overpower list | grep <name>` has
    to hand back the line to copy.
    """
    stacked = Table.grid()
    stacked.add_column(overflow="fold")
    for command in commands:
        stacked.add_row(Text(command, style="op.command"))
    return stacked


def _contents(artifacts: Sequence[Carried]) -> RenderableType:
    """The artifacts an item carries, one per line, type first.

    The type column is dim and the name is cyan, so a line reads as *what kind*
    then *which one* without either rank being carried by colour alone.

    **`fold` on both columns, never the default `ellipsis`.** Measured at 40
    columns before it was set: the plan printed `skill improve-codebase-archite…`
    — a name that cannot be typed back into `--skill`, which is the one thing
    this grid may not do. Leaving `no_wrap` off is not enough, and that is the
    trap: it lets rich *try* to wrap, and a name is a single unbreakable word, so
    what it does instead is crop. `fold` is what breaks the word across lines
    rather than cutting it, and it is the same call the plan's own path column
    already makes for the same reason.

    **One function, two screens.** `list` draws it for the content of an item and
    the plan draws it for what a selection will write (#58), and they are the
    same grid because the plan is checked against `list` by whoever reads both —
    two grids would be two places for the truncation rule to be forgotten, which
    is the same argument that keeps the four `list` screens one `_entry` apart.
    The measurement above is what that buys: one word fixed both screens.
    """
    stacked = Table.grid(padding=(0, 2))
    stacked.add_column(overflow="fold")
    stacked.add_column(overflow="fold")
    for artifact in artifacts:
        stacked.add_row(Text(_kind(artifact), style="op.dim"), Text(artifact.name, style="op.key"))
    return stacked


def _weight(size: int, files: int, artifacts: int = 0) -> str:
    """What an item costs, in the order someone reads it: how many, then how big.

    The count of artifacts leads on a detail screen and is absent on the catalog
    screen, and that is what the screen is *for*: a framework installs whole, so
    the number that says how much *whole* is has to be readable without counting
    the rows. It is `artifacts` and not `skills` because a framework may mix
    skill, command, hook and MCP, and the head line cannot claim a type the
    stacked list below it may contradict.
    """
    counted = f"{artifacts} {_plural('artifact', artifacts)} · " if artifacts else ""
    return f"{counted}{human(size)} · {files} {_plural('file', files)}"


def _plural(word: str, count: int) -> str:
    return word if count == 1 else f"{word}s"


def _spaced(renderables: Iterable[RenderableType]) -> list[RenderableType]:
    """The respiro: a blank line between siblings, and none at the edges."""
    spaced: list[RenderableType] = []
    for index, renderable in enumerate(renderables):
        if index:
            spaced.append("")
        spaced.append(renderable)
    return spaced
