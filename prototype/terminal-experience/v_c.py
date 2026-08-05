"""PROTOTYPE — variant C: DOCUMENTO.

No borders. Structure comes from horizontal rules, section headings and indentation
— the page, not the box. Two-line catalog entries (name on top, description dim
below) so the description never gets truncated. Reference points: `bun`, `cargo new`,
`gh repo view`, a well-set man page.

Bet: the catalog IS the product, so it should read like a document you scan, and a
60-column terminal should degrade by rewrapping rather than by truncating.
"""

from __future__ import annotations

import time

from rich.padding import Padding
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.rule import Rule
from rich.tree import Tree

from catalog import BUNDLES, COPY, FRAMEWORKS, MATT_POCOCK_SKILLS, SKILLS, VERSION, WRITTEN, err, human, out

NAME = "Documento"

# FIGlet `rectangles`, rendered once and hardcoded (#4: no pyfiglet in the wheel).
# 39 x 4 — chosen because it still fits the 60-column terminal the ticket asks about.
BANNER = r"""
 ___ _ _ ___ ___ ___ ___ _ _ _ ___ ___
| . | | | -_|  _| . | . | | | | -_|  _|
|___|\_/|___|_| |  _|___|_____|___|_|
                |_|
"""


def banner(lang: str) -> None:
    if not out.is_terminal or out.width < 42:
        # Narrow: the wordmark degrades to type, not to nothing.
        if out.is_terminal:
            out.print(f"[op.brand]overpower[/] [op.dim]{VERSION}[/]\n")
        return
    c = COPY[lang]
    out.print(f"[op.brand]{BANNER}[/]")
    out.print(f"  [op.dim]{c['tagline']}[/]   [op.dim]v{VERSION}[/]")
    out.print()


def _section(title: str, note: str) -> None:
    out.print(Rule(f"[op.brand]{title}[/] [op.dim]{note}[/]", align="left", style="op.dim"))
    out.print()


def _entries(items, lang: str) -> None:
    for it in items:
        desc = it.desc_pt if lang == "pt" else it.desc_en
        out.print(f"  [op.key]{it.name}[/]")
        # Padding, not a spaced f-string: a wrapped line has to keep the indent,
        # otherwise a narrow terminal dumps the continuation at column 0.
        out.print(Padding(f"[op.dim]{desc}[/]", (0, 0, 0, 4)))
        out.print(Padding(f"[op.dim]{it.origin} · {it.files} arq · {human(it.size)}[/]", (0, 0, 0, 4)))
        out.print()


def list_all(lang: str) -> None:
    c = COPY[lang]
    _section(c["frameworks"], f"— {c['frameworks_note']}")
    _entries(FRAMEWORKS, lang)
    _section(c["skills"], f"— {c['skills_note']}")
    _entries(SKILLS, lang)
    _section(c["bundles"], f"— {c['bundles_note']}")
    _entries(BUNDLES, lang)
    out.print(Rule(style="op.dim"))
    out.print(f"[op.dim]{c['hint_list']}[/] overpower list --ai-framework matt-pocock")


def list_one(lang: str) -> None:
    c = COPY[lang]
    fw = FRAMEWORKS[0]
    _section("matt-pocock", f"— {c['frameworks_note']}")
    out.print(f"  [op.dim]{fw.desc_pt if lang == 'pt' else fw.desc_en}[/]")
    out.print(f"  [op.dim]{fw.origin} · MIT · {fw.files} arq · {human(fw.size)}[/]")
    out.print()
    cols = 3
    width = max(len(s) for s in MATT_POCOCK_SKILLS) + 2
    for i in range(0, len(MATT_POCOCK_SKILLS), cols):
        row = "".join(s.ljust(width) for s in MATT_POCOCK_SKILLS[i : i + cols])
        out.print(f"  [op.key]{row.rstrip()}[/]")
    out.print()
    out.print(f"  [op.dim]{len(MATT_POCOCK_SKILLS)} {c['skills_word']}[/]")


def plan(lang: str, scope: str) -> None:
    c = COPY[lang]
    dest = "./.agents/" if scope == "project" else "~/.agents/"
    _section(c["plan"], "")
    out.print(f"  [op.key]matt-pocock[/]  [op.dim]{len(MATT_POCOCK_SKILLS)} {c['skills_word']}[/]")
    out.print(f"  [op.dim]{c['will_write']}[/] {len(WRITTEN)} {c['files']} [op.dim]{c['in_']}[/] {dest}")
    out.print(f"  [op.dim]{c['linked']} .claude/skills -> .agents/skills[/]")
    out.print()


def progress(lang: str) -> None:
    c = COPY[lang]
    with Progress(
        SpinnerColumn(),
        TextColumn("[op.dim]{task.description}[/]"),
        console=out,
        transient=True,
    ) as p:
        task = p.add_task("", total=len(WRITTEN))
        for f in WRITTEN:
            p.update(task, description=f"{c['installing']}  {f}")
            time.sleep(0.11)
            p.advance(task)


def summary(lang: str, scope: str) -> None:
    c = COPY[lang]
    root = "./.agents/skills" if scope == "project" else "~/.agents/skills"
    _section(c["done"], f"— {len(WRITTEN)} {c['wrote']}, 1 {c['linked']}")
    tree = Tree(f"[bold]{root}[/]", guide_style="op.dim")
    for f in WRITTEN:
        tree.add(f"[op.dim]{f.split('/')[-2]}/SKILL.md[/]")
    tree.add(f"[op.dim]... +{len(MATT_POCOCK_SKILLS) - len(WRITTEN)}[/]")
    tree.add(f"[op.dim].claude/skills -> .agents/skills[/]")
    out.print(tree)
    out.print()
    out.print(f"  [op.dim]{c['next']}[/]  [bold]{c['next_cmd']}[/]")
    out.print(f"        [op.dim]{c['next_hint']}[/]")


def err_collision(lang: str) -> None:
    c = COPY[lang]
    err.print(Rule(f"[op.err]{c['err_collision_t']}[/]", align="left", style="op.err"))
    err.print()
    err.print(f"  {c['err_collision_1']}")
    err.print()
    err.print(f"    [op.dim]matt-pocock[/]  ->  .agents/skills/grilling/")
    err.print(f"    [op.dim]grilling[/]     ->  .agents/skills/grilling/")
    err.print()
    err.print(f"  [op.dim]{c['err_collision_2']}[/]")
    err.print()


def err_symlink(lang: str) -> None:
    c = COPY[lang]
    err.print(Rule(f"[op.warn]{c['err_symlink_t']}[/]", align="left", style="op.warn"))
    err.print()
    err.print(f"  {c['err_symlink_1']}")
    err.print(f"  [op.dim]OSError: [WinError 1314] required privilege is not held[/]")
    err.print()
    err.print(f"  [op.dim]{c['err_symlink_2']}[/]")
    err.print()
