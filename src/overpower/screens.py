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

from typing import TYPE_CHECKING

from rich import box
from rich.console import Group
from rich.padding import Padding
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from rich.console import RenderableType

    from overpower.discovery import Artifact, Bundle, Catalog, Framework

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
    head.add_row(Text(name, style="op.key"), Text(_weight(size, files), style="op.dim"))
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


def _weight(size: int, files: int) -> str:
    return f"{human(size)} · {files} file{'' if files == 1 else 's'}"


def _spaced(renderables: Iterable[RenderableType]) -> list[RenderableType]:
    """The respiro: a blank line between siblings, and none at the edges."""
    spaced: list[RenderableType] = []
    for index, renderable in enumerate(renderables):
        if index:
            spaced.append("")
        spaced.append(renderable)
    return spaced
