# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "typer>=0.27",
#   "rich>=15",
#   "questionary>=2.1",
#   "prompt-toolkit>=3.0.53",
# ]
# ///
"""PROTOTYPE — overpower terminal experience. Ticket #12. THROWAWAY.

Four variants of the same six screens, switchable with -V/--variant:

    A  Painel      everything framed, catalog as a bordered table
    B  Linha       no boxes, one line per thing — cargo/uv shape
    C  Documento   rules and indentation as structure — no borders
    D  Impacto     A's frames, but catalog entries as blocks so nothing truncates

Second axis, the other open decision this ticket owns: --lang pt|en (product voice).

Run it:
    uv run op.py all                 # every screen, variant D, English — the decision
    uv run op.py -V a all            # variant A
    uv run op.py --lang pt all       # the pt-BR copy that lost

Degradation checks the ticket asks for:
    uv run op.py all | cat           # under a pipe
    NO_COLOR=1 uv run op.py all
    COLUMNS=60 uv run op.py all
"""

from __future__ import annotations

import os
import sys
from typing import IO

import typer

import v_a
import v_b
import v_c
import v_d
from catalog import COPY, MATT_POCOCK_SKILLS, WRITTEN, err, out

VARIANTS = {"a": v_a, "b": v_b, "c": v_c, "d": v_d}

app = typer.Typer(add_completion=False, rich_markup_mode="rich", invoke_without_command=True)

# Defaults are the decision this ticket landed on: variant D, English copy.
# A, B and C stay runnable — they are the evidence for why D won.
_state: dict[str, str] = {"variant": "d", "lang": "en"}


def ui():
    return VARIANTS[_state["variant"]]


def lang() -> str:
    return _state["lang"]


def footer() -> None:
    """The switcher. Deliberately ugly so it reads as scaffolding, not design."""
    if not out.is_terminal:
        return
    v = _state["variant"]
    nxt = {"a": "b", "b": "c", "c": "d", "d": "a"}[v]
    out.print()
    out.print(
        f"[reverse] PROTOTYPE [/] variant [bold]{v.upper()}[/] — {ui().NAME} · "
        f"lang={_state['lang']} · next: [bold]-V {nxt}[/]",
        style="op.dim",
    )


# --------------------------------------------------------------------------- #


@app.callback()
def main(
    ctx: typer.Context,
    variant: str = typer.Option("d", "--variant", "-V", help="a | b | c | d"),
    lang_: str = typer.Option("en", "--lang", help="pt | en"),
    width: int = typer.Option(None, "--width", "-w", help="force terminal width, e.g. 60"),
) -> None:
    _state["variant"] = variant.lower()
    _state["lang"] = lang_.lower()
    if width:
        # Public setter on rich's Console. More reliable than COLUMNS, which the
        # shell owns and resets.
        out.width = width
        err.width = width
    if ctx.invoked_subcommand is None:
        ui().banner(lang())
        out.print(ctx.get_help())
        raise typer.Exit(0)


@app.command("list")
def list_cmd(
    ai_framework: str = typer.Option(None, "--ai-framework"),
) -> None:
    """The catalog."""
    ui().banner(lang())
    if ai_framework:
        ui().list_one(lang())
    else:
        ui().list_all(lang())
    footer()


@app.command("install")
def install(
    ai_framework: str = typer.Option(None, "--ai-framework"),
    skill: str = typer.Option(None, "--skill", "-s"),
    global_: bool = typer.Option(False, "--global", "-g"),
    yes: bool = typer.Option(False, "--yes", "-y"),
    force: bool = typer.Option(False, "--force", "-f"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Install. Bare + TTY = wizard."""
    c = COPY[lang()]
    ui().banner(lang())
    scope = "global" if global_ else "project"

    # The collision case #8 named: matt-pocock brings `grilling`, the pool has one too.
    if ai_framework and skill and "grilling" in skill and not force:
        ui().err_collision(lang())
        raise typer.Exit(code=3)

    if _can_ask(yes) and not ai_framework and not skill:
        import questionary  # late import: only this branch pays prompt_toolkit

        what = questionary.select(
            c["q_what"],
            choices=[
                "matt-pocock              (AI Framework, 22 skills)",
                "panlabs-python-standards (skill)",
                "api-python               (bundle)",
            ],
        ).ask()
        if what is None:
            err.print(f"[op.warn]{c['aborted']}[/]")
            raise typer.Exit(code=130)
        where = questionary.select(c["q_where"], choices=[c["opt_project"], c["opt_global"]]).ask()
        if where is None:
            err.print(f"[op.warn]{c['aborted']}[/]")
            raise typer.Exit(code=130)
        scope = "global" if where.strip().startswith(("global", "machine", "maquina")) else "project"

        ui().plan(lang(), scope)
        if not questionary.confirm(c["q_confirm"], default=True).ask():
            err.print(f"[op.warn]{c['aborted']}[/]")
            raise typer.Exit(code=130)
    else:
        ui().plan(lang(), scope)

    if dry_run:
        footer()
        raise typer.Exit(0)

    ui().progress(lang())
    ui().summary(lang(), scope)
    footer()


@app.command("boom")
def boom(kind: str = typer.Argument("symlink", help="symlink | collision")) -> None:
    """The two error screens, in isolation."""
    ui().banner(lang())
    if kind == "collision":
        ui().err_collision(lang())
        footer()
        raise typer.Exit(3)
    ui().err_symlink(lang())
    footer()
    raise typer.Exit(0)


@app.command("all")
def all_screens() -> None:
    """Every screen, back to back. This is the flip-through."""
    ui().banner(lang())
    _hdr("1 · list")
    ui().list_all(lang())
    _hdr("2 · list --ai-framework matt-pocock")
    ui().list_one(lang())
    _hdr("3 · install (plan)")
    ui().plan(lang(), "project")
    _hdr("4 · install (progress + summary)")
    ui().progress(lang())
    ui().summary(lang(), "project")
    _hdr("5 · collision  (exit 3)")
    ui().err_collision(lang())
    _hdr("6 · symlink unavailable  (warning, exit 0)")
    ui().err_symlink(lang())
    footer()


SCREENS = {
    "list": lambda m, lg: m.list_all(lg),
    "detail": lambda m, lg: m.list_one(lg),
    "plan": lambda m, lg: m.plan(lg, "project"),
    "summary": lambda m, lg: m.summary(lg, "project"),
    "collision": lambda m, lg: m.err_collision(lg),
    "symlink": lambda m, lg: m.err_symlink(lg),
    "banner": lambda m, lg: m.banner(lg),
}


@app.command("compare")
def compare(
    screen: str = typer.Argument("list", help=" | ".join(SCREENS)),
) -> None:
    """The SAME screen in all four variants, back to back. This is the comparison."""
    if screen not in SCREENS:
        raise typer.BadParameter(f"unknown screen. pick one of: {', '.join(SCREENS)}")
    draw = SCREENS[screen]
    for key in ("a", "b", "c", "d"):
        mod = VARIANTS[key]
        out.print()
        out.rule(f"[bold]{key.upper()}[/] — {mod.NAME}   [dim]{screen}[/]", style="dim")
        out.print()
        # `banner` self-suppresses without a TTY; every other screen renders anywhere.
        draw(mod, lang())
    out.print()
    out.rule("[dim]end — same screen, four treatments[/]", style="dim")


def _hdr(t: str) -> None:
    out.print()
    out.print(f"[reverse dim] {t} [/]")
    out.print()


def _tty(stream: IO[str] | None) -> bool:
    return stream is not None and stream.isatty()


def _can_ask(yes: bool) -> bool:
    if yes or os.environ.get("CI") == "true":
        return False
    return _tty(sys.stdin) and _tty(sys.stdout)


if __name__ == "__main__":
    app()
