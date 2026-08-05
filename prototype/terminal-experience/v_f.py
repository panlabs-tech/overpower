"""PROTOTYPE — variant F: HERDADA (bloco).

Identical to E in every screen except `list`. Same soft frames, same cyan names,
same indentation, same copy — the diff is one function, on purpose, because that
is the only place the dev's feedback admits two readings:

    "gostei do título em cyan e da identação entre título e descrição" (da C)
    "herdar list da variante B"                                       (da B)

C's indentation needs the description on its OWN line under the name. B's list
needs the description on the SAME line as the name. Both cannot hold at once, so
E takes B's reading and F takes C's.

F's bet: one soft panel per category with a blank line between them (the respiro
he asked for), and each artifact as name + size, then the description indented
under it, then origin and file count. Nothing truncates and nothing wraps into a
narrow column — the description gets the full width of the frame.
"""

from __future__ import annotations

from rich.console import Group
from rich.padding import Padding
from rich.table import Table

from catalog import BUNDLES, COPY, FRAMEWORKS, SKILLS, human, out

# Every screen but `list` comes from E, unchanged. Importing them keeps the two
# variants honest: any difference you see IS the list decision.
from v_e import (  # noqa: F401
    BANNER,
    banner,
    err_collision,
    err_symlink,
    frame,
    list_one,
    plan,
    progress,
    summary,
)

NAME = "Herdada · bloco"


def _entry(it, lang: str):
    """Name and size on the top line, everything else indented under it."""
    c = COPY[lang]
    desc = it.desc_pt if lang == "pt" else it.desc_en
    head = Table.grid(padding=(0, 1), expand=True)
    head.add_column(ratio=1)
    head.add_column(justify="right", no_wrap=True, style="op.dim")
    head.add_row(f"[op.key]{it.name}[/]", human(it.size))
    return Group(
        head,
        # Padding, not a spaced f-string: a wrapped line has to keep the indent,
        # otherwise a narrow terminal dumps the continuation at column 0.
        Padding(f"[op.dim]{desc}[/]", (0, 0, 0, 2)),
        Padding(f"[op.dim]{it.origin} · {it.files} {c['col_files']}[/]", (0, 0, 0, 2)),
    )


def _panel(title: str, note: str, items, lang: str):
    body = []
    for i, it in enumerate(items):
        if i:
            body.append("")
        body.append(_entry(it, lang))
    return frame(Group(*body), f"[bold]{title}[/]  [op.dim]{note}[/]", style="op.dim")


def list_all(lang: str) -> None:
    c = COPY[lang]
    groups = (
        (c["frameworks"], c["frameworks_note"], FRAMEWORKS),
        (c["skills"], c["skills_note"], SKILLS),
        (c["bundles"], c["bundles_note"], BUNDLES),
    )
    for i, (title, note, items) in enumerate(groups):
        if i:
            out.print()  # the respiro between categories
        out.print(_panel(title, note, items, lang))
    out.print()
    out.print(f"[op.dim]{c['hint_list']}[/] [op.key]overpower list --ai-framework matt-pocock[/]")
