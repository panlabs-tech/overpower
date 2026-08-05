"""PROTOTYPE — variant B: LINHA.

No boxes anywhere. Everything is a line. Aligned columns without borders, a status
glyph per line, errors in the rustc/cargo shape (`error:` then `help:`). One-line
wordmark instead of a banner. Reference points: `uv`, `cargo`, `apt`, `ruff`.

Bet: this thing is going to live in CI logs and in READMEs; density and greppability
beat decoration, and it looks the same whether or not it has a terminal.
"""

from __future__ import annotations

import time

from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from catalog import BUNDLES, COPY, FRAMEWORKS, MATT_POCOCK_SKILLS, SKILLS, VERSION, WRITTEN, err, human, out

NAME = "Linha"


def banner(lang: str) -> None:
    """No ASCII art. The wordmark is one line, and it carries data."""
    if not out.is_terminal:
        return
    n_fw, n_sk, n_bd = len(FRAMEWORKS), len(SKILLS), len(BUNDLES)
    fw = "framework" if n_fw == 1 else "frameworks"
    bd = "bundle" if n_bd == 1 else "bundles"
    out.print(
        f"[op.brand]overpower[/] [op.dim]{VERSION}[/]  "
        f"[op.dim]{n_fw} {fw} · {n_sk} skills · {n_bd} {bd}[/]"
    )
    out.print()


def list_all(lang: str) -> None:
    """ONE grid for every row. Columns that do not align across the type groups
    defeat the entire bet of this variant."""
    # `framework` + `prompt-engineering-patterns` + size + description is 103 chars
    # of content — it does not fit 80. The type tag pays: two letters, not nine.
    c = COPY[lang]
    t = Table.grid(padding=(0, 2), expand=True)
    t.add_column(style="op.dim", no_wrap=True, width=2)  # type tag
    t.add_column(style="op.key", no_wrap=True)  # name
    t.add_column(justify="right", style="op.dim", no_wrap=True)  # size
    t.add_column(overflow="ellipsis", no_wrap=True, ratio=1)  # desc

    for tag, items in (("fw", FRAMEWORKS), ("sk", SKILLS), ("bd", BUNDLES)):
        for it in items:
            desc = it.desc_pt if lang == "pt" else it.desc_en
            t.add_row(tag, it.name, human(it.size), f"[op.dim]{desc}[/]")
    out.print(t)
    out.print()
    out.print(f"[op.dim]{c['hint_list']}[/] overpower list --ai-framework matt-pocock")


def list_one(lang: str) -> None:
    c = COPY[lang]
    fw = FRAMEWORKS[0]
    out.print(
        f"[op.key]matt-pocock[/]  [op.dim]{fw.origin} · MIT · {fw.files} {c['col_files']} · "
        f"{human(fw.size)} · {c['frameworks_note']}[/]"
    )
    out.print()
    for s in MATT_POCOCK_SKILLS:
        out.print(f"  [op.dim]skill[/]  {s}")
    out.print()
    out.print(f"[op.dim]{len(MATT_POCOCK_SKILLS)} {c['skills_word']}[/]")


def plan(lang: str, scope: str) -> None:
    c = COPY[lang]
    dest = "./.agents/" if scope == "project" else "~/.agents/"
    out.print(
        f"[op.brand]{c['plan']}[/]  matt-pocock -> [bold]{dest}[/]  "
        f"[op.dim]{len(WRITTEN)} {c['files']} + 1 {c['linked']}[/]"
    )


def progress(lang: str) -> None:
    """One line per file, and they stay. This is the log, not an animation."""
    c = COPY[lang]
    if not out.is_terminal:
        for f in WRITTEN:
            out.print(f"   + {f}")
        return
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=out,
        transient=True,
    ) as p:
        task = p.add_task(f"{c['installing']}", total=len(WRITTEN))
        for f in WRITTEN:
            time.sleep(0.09)
            p.advance(task)
            p.console.print(f"   [op.ok]+[/] [op.dim]{f}[/]")


def summary(lang: str, scope: str) -> None:
    c = COPY[lang]
    dest = "./.agents/skills" if scope == "project" else "~/.agents/skills"
    more = len(MATT_POCOCK_SKILLS) - len(WRITTEN)
    if more:
        out.print(f"   [op.dim]+ ... +{more}[/]")
    out.print(f"   [op.ok]+[/] [op.dim].claude/skills -> .agents/skills[/]")
    out.print()
    out.print(
        f"[op.ok]{c['done']}[/]  {len(WRITTEN)} {c['wrote']}, 1 {c['linked']}, {dest}"
    )
    out.print(f"[op.dim]{c['next']}: {c['next_cmd']} — {c['next_hint']}[/]")


def err_collision(lang: str) -> None:
    c = COPY[lang]
    err.print(f"[op.err]{c['err_collision_t']}:[/] {c['err_collision_1']}")
    err.print(f"  [op.dim]matt-pocock  ->[/] .agents/skills/grilling/")
    err.print(f"  [op.dim]grilling     ->[/] .agents/skills/grilling/")
    err.print(f"[op.key]help:[/] {c['err_collision_2']}")


def err_symlink(lang: str) -> None:
    c = COPY[lang]
    err.print(f"[op.warn]{c['err_symlink_t']}:[/] {c['err_symlink_1']}")
    err.print(f"  [op.dim]OSError: [WinError 1314] required privilege is not held[/]")
    err.print(f"[op.key]help:[/] {c['err_symlink_2']}")
