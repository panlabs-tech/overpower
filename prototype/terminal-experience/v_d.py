"""PROTOTYPE — variant D: IMPACTO.

Impact first, because that is a declared project requirement (#8). Everything is
framed, the banner is the big one, colour carries meaning — and the single measured
defect of variant A is fixed: catalog entries are two-line blocks INSIDE the frame,
so nothing truncates at any width.

A's presence, C's information integrity.
"""

from __future__ import annotations

import time

from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.tree import Tree

from catalog import BUNDLES, COPY, FRAMEWORKS, MATT_POCOCK_SKILLS, SKILLS, VERSION, WRITTEN, err, human, out

NAME = "Impacto"

# FIGlet `standard`, 50 x 5 — the footprint #8 measured. The biggest of the set.
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


def _entry(it, lang: str):
    """Two lines inside the frame. Never truncates — that was A's only real defect."""
    desc = it.desc_pt if lang == "pt" else it.desc_en
    t = Table.grid(padding=(0, 1), expand=True)
    t.add_column(ratio=1)
    t.add_column(justify="right", no_wrap=True, style="op.key")
    t.add_row(f"[bold]{it.name}[/]", human(it.size))
    t.add_row(f"[op.dim]{desc}[/]", "")
    t.add_row(f"[op.dim]{it.origin} · {it.files} arq[/]", "")
    return t


def _panel(title: str, note: str, items, lang: str, hero: bool = False):
    body = []
    for i, it in enumerate(items):
        if i:
            body.append("")
        body.append(_entry(it, lang))
    return Panel(
        Group(*body),
        title=f"[op.brand]{title}[/]  [op.dim]{note}[/]",
        title_align="left",
        box=box.HEAVY if hero else box.ROUNDED,
        border_style="op.brand" if hero else "op.dim",
        padding=(1, 2),
    )


def list_all(lang: str) -> None:
    c = COPY[lang]
    out.print(_panel(c["frameworks"], c["frameworks_note"], FRAMEWORKS, lang, hero=True))
    out.print(_panel(c["skills"], c["skills_note"], SKILLS, lang))
    out.print(_panel(c["bundles"], c["bundles_note"], BUNDLES, lang))
    out.print(f"[op.dim]{c['hint_list']}[/] [op.key]overpower list --ai-framework matt-pocock[/]")


def list_one(lang: str) -> None:
    c = COPY[lang]
    fw = FRAMEWORKS[0]
    # Column count follows the terminal. Three columns clip `setup-matt-pocock-skills`
    # below ~72, and clipping a name the user has to type back is the one truncation
    # that actually costs something.
    cols = 3 if out.width >= 72 else 2
    grid = Table.grid(padding=(0, 3))
    for i in range(0, len(MATT_POCOCK_SKILLS), cols):
        grid.add_row(*[f"[op.key]{s}[/]" for s in MATT_POCOCK_SKILLS[i : i + cols]])
    out.print(
        Panel(
            grid,
            title=f"[op.brand]matt-pocock[/] [op.dim]— {len(MATT_POCOCK_SKILLS)} {c['skills_word']} · "
            f"{fw.files} arq · {human(fw.size)}[/]",
            title_align="left",
            subtitle=f"[op.dim]{fw.origin} · MIT · {c['frameworks_note']}[/]",
            box=box.HEAVY,
            border_style="op.brand",
            padding=(1, 2),
        )
    )


def plan(lang: str, scope: str) -> None:
    c = COPY[lang]
    dest = "./.agents/" if scope == "project" else "~/.agents/"
    out.print(
        Panel(
            f"[bold]matt-pocock[/]  [op.dim]{len(MATT_POCOCK_SKILLS)} {c['skills_word']}[/]\n"
            f"{c['will_write']} [op.key]{len(WRITTEN)}[/] {c['files']} {c['in_']} [op.key]{dest}[/]\n"
            f"[op.dim]+ {c['linked']} .claude/skills -> .agents/skills[/]",
            title=f"[op.brand]{c['plan']}[/]",
            title_align="left",
            box=box.HEAVY,
            border_style="op.brand",
            padding=(1, 2),
        )
    )


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
        task = p.add_task(f"{c['installing']} [bold]matt-pocock[/]", total=len(WRITTEN))
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
    tree.add(f"[bold].claude/skills[/] [op.dim]-> .agents/skills[/]")
    out.print(
        Panel(
            tree,
            title=f"[op.ok]{c['done']}[/]  [op.dim]{len(WRITTEN)} {c['wrote']} · 1 {c['linked']}[/]",
            title_align="left",
            subtitle=f"[op.dim]{c['next']}: [/][op.key]{c['next_cmd']}[/]",
            box=box.HEAVY,
            border_style="op.ok",
            padding=(1, 2),
        )
    )


def err_collision(lang: str) -> None:
    c = COPY[lang]
    err.print(
        Panel(
            c["err_collision_b"],
            title=f"[op.err]{c['err_collision_t']}[/]",
            title_align="left",
            box=box.HEAVY,
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
