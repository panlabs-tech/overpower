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
from typing import TYPE_CHECKING, assert_never

from rich import box
from rich.console import Group
from rich.padding import Padding
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from overpower.inspection import DanglingLink, Divergence, LinkTurnedText
from overpower.planning import DirectoryTree, DocumentKey, WriteMode

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from pathlib import Path

    from rich.console import Console, ConsoleOptions, RenderableType, RenderResult

    from overpower.discovery import Artifact, ArtifactType, Bundle, Catalog, Framework
    from overpower.inspection import Diagnosis, Finding, Terminal
    from overpower.planning import Destination, Landing, Plan, Selection

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

_KIB = 1024
_MIB = 1024 * 1024

_READERS_SHOWN = 3
"""How many runtimes a plan line names before it counts the rest.

Three and a `(+N)`, which is the shape the prototype settled on: enough to
recognise the place, short enough that the line still fits at 60 columns next to
the path it belongs to.
"""


def banner(version: str, width: int) -> RenderableType:
    """The opening screen: the art, the tagline and the version that arrived.

    Whether it is *shown* is not decided here — it is a terminal question, and
    the CLI gates it on `isatty()`.
    """
    if width < BANNER_WIDTH:
        return Text.assemble(("overpower ", "op.brand"), (version, "op.dim"), "\n")
    return Group(
        Text(BANNER, style="op.brand"),
        Text.assemble("  ", (TAGLINE, "op.dim"), "   ", (f"v{version}", "op.key"), "\n"),
    )


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
                _entry(framework.name, framework.size, framework.files, framework.description)
                for framework in catalog.frameworks
            ],
        ),
        _block(
            "Pool skills",
            "installs alone",
            [
                _entry(artifact.name, artifact.size, artifact.files, artifact.description)
                for artifact in catalog.pool
            ],
        ),
        _block(
            "Bundles",
            "lists pool artifacts only",
            [
                _entry(bundle.name, bundle.size, bundle.files, bundle.description)
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
                framework.artifacts,
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
        [_entry(bundle.name, bundle.size, bundle.files, bundle.description, bundle.artifacts)],
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
        [_entry(artifact.name, artifact.size, artifact.files, artifact.description)],
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
        """Draw the panel with the arrow this console can carry."""
        del console
        yield _plan_panel(self.plan, "<-" if options.ascii_only else "←")


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
        """Draw both blocks with the arrow this console can carry."""
        del console
        arrow = "<-" if options.ascii_only else "←"
        yield Group(
            *_spaced(
                (
                    _terminal_block(self.diagnosis.terminal),
                    _integrity_block(self.diagnosis, arrow),
                )
            )
        )


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


def _integrity_block(diagnosis: Diagnosis, arrow: str) -> Panel:
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
    found: list[RenderableType] = [
        _finding(finding, diagnosis, arrow) for finding in diagnosis.findings
    ]
    if not found:
        found = [Text("no findings", style="op.ok")]
    return _block("integrity", "what is installed", [counted, *found])


def _finding(finding: Finding, diagnosis: Diagnosis, arrow: str) -> RenderableType:
    """One thing that is wrong: what class it is, and every path that carries it."""
    match finding:
        case DanglingLink(destination, points_at):
            place = _located(destination, diagnosis)
            pointed = "" if points_at is None else f"  {arrow} {points_at}"
            return _flagged("dangling link", [f"{place}{pointed}"])
        case LinkTurnedText(destination, inside, points_at):
            place = _located(destination, diagnosis)
            relative = _inside(inside, destination)
            return _flagged("link became a text file", [f"{place}  {relative} {arrow} {points_at}"])
        case Divergence(name, _, destinations):
            places = [_located(destination, diagnosis) for destination in destinations]
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


def _located(destination: Destination, diagnosis: Diagnosis) -> str:
    """Where a write is, said the shortest way that still names it unambiguously.

    Relative to the repository when it is in one, `~/…` when it is on the
    machine, absolute when it is neither — because `doctor` reports both scopes
    in one output and the two roots have to be told apart at a glance. A place
    outside both is shown whole, which is the second write of a graft.
    """
    shown = _relative_to_a_root(destination.path, diagnosis)
    match destination:
        case DirectoryTree():
            return f"{shown}/"
        case DocumentKey(_, key):
            return f"{shown}#{key}"
        case _ as unreachable:
            assert_never(unreachable)


def _relative_to_a_root(path: Path, diagnosis: Diagnosis) -> str:
    """The path against the repository first, then the home, then not at all."""
    root = diagnosis.root
    if root is not None and path.is_relative_to(root):
        return path.relative_to(root).as_posix()
    if path.is_relative_to(diagnosis.home):
        return f"~/{path.relative_to(diagnosis.home).as_posix()}"
    return path.as_posix()


def _inside(path: Path, destination: Destination) -> str:
    """A file named against the write it was found in, so the line stays readable."""
    if path.is_relative_to(destination.path):
        return path.relative_to(destination.path).as_posix()
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


def _plan_panel(plan: Plan, arrow: str) -> Panel:
    """One block, and inside it one group per thing that was asked for."""
    return Panel(
        Group(*_spaced([_planned(selection, plan.root, arrow) for selection in plan.selections])),
        title="[op.section]plan[/]",
        title_align="left",
        box=box.ROUNDED,
        border_style="op.dim",
        padding=(1, 2),
    )


def _planned(selection: Selection, root: Path, arrow: str) -> RenderableType:
    """What one selection brings, and every place it lands."""
    places = Table.grid(padding=(0, 1), expand=True)
    # `fold`, never the default `ellipsis`: a truncated path is the one thing
    # this screen may not do, and a narrow terminal is where it would happen.
    places.add_column(ratio=1, overflow="fold")
    places.add_column(justify="right", no_wrap=True)
    for landing in selection.landings:
        places.add_row(
            Text.assemble(
                _shown(root, landing),
                "  ",
                (arrow, "op.dim"),
                " ",
                (_readers(landing.readers), "op.dim"),
                *_mode_suffix(landing.mode),
            ),
            Text(f"{landing.files} {_plural('file', landing.files)}", style="op.dim"),
        )
    return Group(
        Text.assemble((selection.name, "op.key"), "  ", (_carries(selection.artifacts), "op.dim")),
        Padding(places, (0, 0, 0, 2)),
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


def _carries(artifacts: Sequence[ArtifactType]) -> str:
    """`22 skills`, or `4 artifacts` when a selection mixes types.

    A framework may mix skill, command and agent — the type comes from the tree
    (rule 8) — so the noun is data and not a constant.
    """
    kinds = set(artifacts)
    noun = str(next(iter(kinds))) if len(kinds) == 1 else "artifact"
    return f"{len(artifacts)} {_plural(noun, len(artifacts))}"


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


def _entry(
    name: str,
    size: int,
    files: int,
    description: str,
    contents: Sequence[Artifact] = (),
) -> RenderableType:
    """Name and weight on the head line, the whole description indented under it.

    `contents` is what turns the same entry into a detail screen: the artifacts
    the item carries, stacked under the description with a blank line between.
    An item that carries none — a pool artifact — renders exactly as it does on
    the catalog screen, which is the point of it being one function.
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
    if contents:
        body.append(Padding(_contents(contents), (1, 0, 0, 2)))
    return Group(*body)


def _contents(artifacts: Sequence[Artifact]) -> RenderableType:
    """The artifacts an item carries, one per line, type first.

    The type column is dim and the name is cyan, so a line reads as *what kind*
    then *which one* without either rank being carried by colour alone. Neither
    column is `no_wrap`: a name longer than the terminal has to wrap, because a
    clipped name is a name that cannot be typed back into `install`.
    """
    stacked = Table.grid(padding=(0, 2))
    stacked.add_column()
    stacked.add_column()
    for artifact in artifacts:
        stacked.add_row(Text(artifact.type, style="op.dim"), Text(artifact.name, style="op.key"))
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
