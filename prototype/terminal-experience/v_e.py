"""PROTOTYPE — variant E: HERDADA (linha).

Built from the dev's validation pass over A/B/C/D. Base is D, with the four
adjustments he asked for, plus his summary line: "herdar `list` da variante B".

    borda fina        box.HEAVY -> box.ROUNDED everywhere. Colour still carries
                      meaning (brand / ok / warn / err); thickness no longer does.
    respiro           blank line between category groups.
    nome em cyan      `op.key`, plain — the exact treatment C used, not D's bold.
    identação         info line indented under the name.
    list da B         one row per artifact, columns aligned across every group.

E and F share this whole file except `list_all`. That is the ONE screen where the
two readings of the feedback diverge, so it is the only thing worth comparing.

E's bet: B's density. One line per artifact, one aligned grid for the whole
catalog, so sizes are comparable down the column. The description gets whatever
column is left and WRAPS inside it — B truncated there, and truncating the
description of a catalog is losing the catalog.
"""

from __future__ import annotations

import time

from rich import box
from rich.console import Group
from rich.padding import Padding
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.tree import Tree

from catalog import BUNDLES, COPY, FRAMEWORKS, MATT_POCOCK_SKILLS, SKILLS, VERSION, WRITTEN, err, human, out

NAME = "Herdada · linha"

# FIGlet `standard`, 50 x 5 — unchanged from D. The banner was not criticised,
# and it is what pays the declared impact requirement of #8.
BANNER = r"""
  _____   _____ _ __ _ __   _____      _____ _ __
 / _ \ \ / / _ \ '__| '_ \ / _ \ \ /\ / / _ \ '__|
| (_) \ V /  __/ |  | |_) | (_) \ V  V /  __/ |
 \___/ \_/ \___|_|  | .__/ \___/ \_/\_/ \___|_|
                    |_|
"""


def banner(lang: str) -> None:
    if not out.is_terminal:
        return
    c = COPY[lang]
    if out.width < 50:
        out.print(f"[op.brand]overpower[/] [op.dim]{VERSION}[/]\n")
        return
    out.print(BANNER, style="op.brand", highlight=False)
    out.print(f"  [op.dim]{c['tagline']}[/]   [op.key]v{VERSION}[/]\n")


def frame(body, title: str, style: str = "op.brand", subtitle: str | None = None) -> Panel:
    """The one frame helper. ROUNDED, never HEAVY — the thickness was the
    complaint, and it was carrying no information the colour did not already."""
    return Panel(
        body,
        title=title,
        title_align="left",
        subtitle=subtitle,
        subtitle_align="left" if subtitle else None,
        box=box.ROUNDED,
        border_style=style,
        padding=(1, 2),
    )


# --------------------------------------------------------------------------- #
# list — E's version: one grid, one row per artifact
# --------------------------------------------------------------------------- #


def list_all(lang: str) -> None:
    c = COPY[lang]
    # No column-level style: it would paint the group headers and the blank
    # separator rows too, and the header has to read as a different rank from
    # the artifact names. Style goes per cell.
    t = Table.grid(padding=(0, 2), expand=True)
    t.add_column(no_wrap=True)                    # name
    t.add_column(justify="right", no_wrap=True)   # size
    t.add_column(ratio=1)                         # description — WRAPS

    groups = (
        (c["frameworks"], c["frameworks_note"], FRAMEWORKS),
        (c["skills"], c["skills_note"], SKILLS),
        (c["bundles"], c["bundles_note"], BUNDLES),
    )
    for i, (title, note, items) in enumerate(groups):
        if i:
            t.add_row("", "", "")  # the respiro between categories
        # Header note lands over the description column, so the group heading
        # never widens the name column and the grid stays aligned end to end.
        t.add_row(f"[bold]{title}[/]", "", f"[op.dim]{note}[/]")
        for it in items:
            desc = it.desc_pt if lang == "pt" else it.desc_en
            t.add_row(f"[op.key]{it.name}[/]", f"[op.dim]{human(it.size)}[/]", f"[op.dim]{desc}[/]")

    out.print(frame(t, f"[op.brand]{c['catalog']}[/]"))
    out.print()
    out.print(f"[op.dim]{c['hint_list']}[/] [op.key]overpower list --ai-framework matt-pocock[/]")


# --------------------------------------------------------------------------- #
# every other screen — shared by E and F
# --------------------------------------------------------------------------- #


def list_one(lang: str) -> None:
    c = COPY[lang]
    fw = FRAMEWORKS[0]
    # Column count follows the terminal: three columns clip
    # `setup-matt-pocock-skills` below ~72, and clipping a name the user has to
    # type back is the one truncation that actually costs something.
    cols = 3 if out.width >= 72 else 2
    grid = Table.grid(padding=(0, 3))
    for i in range(0, len(MATT_POCOCK_SKILLS), cols):
        grid.add_row(*[f"[op.key]{s}[/]" for s in MATT_POCOCK_SKILLS[i : i + cols]])
    out.print(
        frame(
            grid,
            title=f"[op.key]matt-pocock[/] [op.dim]— {len(MATT_POCOCK_SKILLS)} {c['skills_word']} · "
            f"{fw.files} {c['col_files']} · {human(fw.size)}[/]",
            subtitle=f"[op.dim]{fw.origin} · MIT · {c['frameworks_note']}[/]",
        )
    )


def plan(lang: str, scope: str) -> None:
    c = COPY[lang]
    dest = "./.agents/" if scope == "project" else "~/.agents/"
    body = Group(
        f"[op.key]matt-pocock[/]  [op.dim]{len(MATT_POCOCK_SKILLS)} {c['skills_word']}[/]",
        Padding(
            f"[op.dim]{c['will_write']}[/] [bold]{len(WRITTEN)}[/] [op.dim]{c['files']} {c['in_']}[/] "
            f"[bold]{dest}[/]",
            (0, 0, 0, 2),
        ),
        Padding(f"[op.dim]+ {c['linked']} .claude/skills -> .agents/skills[/]", (0, 0, 0, 2)),
    )
    out.print(frame(body, f"[op.brand]{c['plan']}[/]"))


def progress(lang: str) -> None:
    c = COPY[lang]
    with Progress(
        SpinnerColumn(style="op.brand"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None, complete_style="op.brand", finished_style="op.ok"),
        TextColumn("[op.dim]{task.completed}/{task.total}[/]"),
        console=out,
        transient=True,
    ) as p:
        task = p.add_task(f"{c['installing']} [op.key]matt-pocock[/]", total=len(WRITTEN))
        for _ in WRITTEN:
            time.sleep(0.09)
            p.advance(task)


def summary(lang: str, scope: str) -> None:
    c = COPY[lang]
    root = "./.agents/skills" if scope == "project" else "~/.agents/skills"
    tree = Tree(f"[bold]{root}[/]", guide_style="op.dim")
    for f in WRITTEN:
        tree.add(f"[op.dim]{f.split('/')[-2]}/SKILL.md[/]")
    tree.add(f"[op.dim]... +{len(MATT_POCOCK_SKILLS) - len(WRITTEN)}[/]")
    tree.add("[op.key].claude/skills[/] [op.dim]-> .agents/skills[/]")
    out.print(
        frame(
            tree,
            title=f"[op.ok]{c['done']}[/]  [op.dim]{len(WRITTEN)} {c['wrote']} · 1 {c['linked']}[/]",
            style="op.ok",
            subtitle=f"[op.dim]{c['next']}: [/][op.key]{c['next_cmd']}[/]",
        )
    )


def err_collision(lang: str) -> None:
    c = COPY[lang]
    err.print(
        Panel(
            c["err_collision_b"],
            title=f"[op.err]{c['err_collision_t']}[/]",
            title_align="left",
            box=box.ROUNDED,
            border_style="op.err",
            padding=(1, 2),
        )
    )


def err_symlink(lang: str) -> None:
    c = COPY[lang]
    err.print(
        Panel(
            c["err_symlink_b"],
            title=f"[op.warn]{c['err_symlink_t']}[/]",
            title_align="left",
            box=box.ROUNDED,
            border_style="op.warn",
            padding=(1, 2),
        )
    )
