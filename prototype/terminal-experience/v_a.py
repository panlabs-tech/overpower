"""PROTOTYPE — variant A: PAINEL.

Everything is framed. Bordered tables, panels around the plan, panel around the
summary, panel around the error. Big 5-line banner. Reference points: `npm doctor`,
`vercel`, `gh` at its most decorated.

Bet: the declared requirement is visual impact, so lean into rich all the way.
"""

from __future__ import annotations

import time

from rich import box
from rich.align import Align
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.tree import Tree

from catalog import BUNDLES, COPY, FRAMEWORKS, MATT_POCOCK_SKILLS, SKILLS, VERSION, WRITTEN, err, human, out

NAME = "Painel"

# FIGlet `standard`, rendered once and hardcoded (#4: no pyfiglet in the wheel).
# 7-bit ASCII: survives legacy cmd.exe and any codepage. 50 cols x 5 lines — the
# footprint measured in #8.
BANNER = r"""
  _____   _____ _ __ _ __   _____      _____ _ __
 / _ \ \ / / _ \ '__| '_ \ / _ \ \ /\ / / _ \ '__|
| (_) \ V /  __/ |  | |_) | (_) \ V  V /  __/ |
 \___/ \_/ \___|_|  | .__/ \___/ \_/\_/ \___|_|
                    |_|
"""


def banner(lang: str) -> None:
    if not out.is_terminal or out.width < 50:
        return
    c = COPY[lang]
    out.print(BANNER, style="op.brand", highlight=False)
    out.print(f"  [op.dim]{c['tagline']} · v{VERSION}[/]\n")


def _table(title: str, note: str, items, lang: str) -> Table:
    c = COPY[lang]
    t = Table(
        title=f"[op.brand]{title}[/]  [op.dim]({note})[/]",
        title_justify="left",
        box=box.SIMPLE_HEAVY,
        header_style="op.dim",
        expand=True,
        pad_edge=False,
    )
    # Four columns do not fit in 80 with real names (`prompt-engineering-patterns`
    # is 27 chars). Origin folds into the description as a dim suffix.
    t.add_column(c["col_name"], style="op.key", no_wrap=True)
    t.add_column(f"{c['col_desc']} · {c['col_origin']}", ratio=1)
    t.add_column(c["col_size"], justify="right", no_wrap=True)
    for it in items:
        desc = it.desc_pt if lang == "pt" else it.desc_en
        t.add_row(it.name, f"{desc}  [op.dim]{it.origin}[/]", human(it.size))
    return t


def list_all(lang: str) -> None:
    c = COPY[lang]
    out.print(_table(c["frameworks"], c["frameworks_note"], FRAMEWORKS, lang))
    out.print(_table(c["skills"], c["skills_note"], SKILLS, lang))
    out.print(_table(c["bundles"], c["bundles_note"], BUNDLES, lang))
    out.print(
        Panel(
            f"[op.dim]{c['hint_list']}[/] overpower list --ai-framework matt-pocock\n"
            f"[op.dim]{c['hint_install']}[/]  overpower install --ai-framework matt-pocock",
            box=box.ROUNDED,
            border_style="op.dim",
        )
    )


def list_one(lang: str) -> None:
    c = COPY[lang]
    fw = FRAMEWORKS[0]
    grid = Table.grid(padding=(0, 3))
    for i in range(0, len(MATT_POCOCK_SKILLS), 3):
        grid.add_row(*[f"[op.key]{s}[/]" for s in MATT_POCOCK_SKILLS[i : i + 3]])
    out.print(
        Panel(
            grid,
            title=f"[op.brand]matt-pocock[/] [op.dim]— {len(MATT_POCOCK_SKILLS)} {c['skills_word']}, "
            f"{fw.files} {c['col_files']}, {human(fw.size)}[/]",
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
            f"[op.key]matt-pocock[/]  [op.dim]({len(MATT_POCOCK_SKILLS)} {c['skills_word']})[/]\n"
            f"{c['will_write']} [bold]{len(WRITTEN)}[/] {c['files']} {c['in_']} [bold]{dest}[/]\n"
            f"[op.dim]+ {c['linked']} .claude/skills -> .agents/skills[/]",
            title=f"[op.brand]{c['plan']}[/]",
            box=box.ROUNDED,
            border_style="op.brand",
            padding=(1, 2),
        )
    )


def progress(lang: str) -> None:
    c = COPY[lang]
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None),
        TextColumn("[op.dim]{task.completed}/{task.total}[/]"),
        console=out,
        transient=True,
    ) as p:
        task = p.add_task(f"{c['installing']} matt-pocock", total=len(WRITTEN))
        for _ in WRITTEN:
            time.sleep(0.09)
            p.advance(task)


def summary(lang: str, scope: str) -> None:
    c = COPY[lang]
    root = "./.agents/skills" if scope == "project" else "~/.agents/skills"
    tree = Tree(f"[bold]{root}[/]")
    for f in WRITTEN:
        tree.add(f"[op.dim]{f.split('/')[-2]}/SKILL.md[/]")
    tree.add(f"[op.dim]... +{len(MATT_POCOCK_SKILLS) - len(WRITTEN)}[/]")
    tree.add(f"[bold].claude/skills[/] [op.dim]-> .agents/skills[/]")

    out.print(
        Panel(
            tree,
            title=f"[op.ok]{c['done']}[/] [op.dim]— {len(WRITTEN)} {c['wrote']}, 1 {c['linked']}[/]",
            box=box.ROUNDED,
            border_style="op.ok",
            padding=(1, 2),
        )
    )
    out.print(f"[op.dim]{c['next']}:[/] [bold]{c['next_cmd']}[/]  [op.dim]{c['next_hint']}[/]")


def err_collision(lang: str) -> None:
    c = COPY[lang]
    err.print(
        Panel(
            c["err_collision_b"],
            title=f"[op.err]{c['err_collision_t']}[/]",
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
            box=box.ROUNDED,
            border_style="op.warn",
            padding=(1, 2),
        )
    )
