"""The command line: parsing, the `isatty()` gate, the exit codes, the top handler.

This is the frame every later ticket hangs off, and it replaces the probe of the
`0.0.x` series whole — that one printed four facts and exited 0 with no parsing
at all, which was the right shape for proving a publishing pipeline and the wrong
shape for a product.

**Every byte the product prints leaves through a `rich` console**, never through
`print`, and `T20` in `pyproject.toml` is what keeps that true. The reason is
testability before looks: the snapshot doctrine records a rendered screen, so an
output path that bypasses the console is an output path no snapshot can see.

**The top-level handler is mandatory.** An unhandled exception exits 1 dumping a
rich traceback into the terminal, and shipping that leaks library internals to
whoever typed the command. Exit 1 costs the conversion of an exception into an
error panel, and this module is where that conversion lives — which is also why
`pretty_exceptions_enable` is off: that feature is the defect, not the cure.

The code table is born whole even though v0.1.0 only exercises part of it, and
the axis between **2** and **3** is *whose defect it is*. The `except` order in
`main` is where that axis is decided, and it is the only place: a
`BadInvocationError` is caught before its base class and answers **2**.

`list` is where the selectors first appear — `--ai-framework` with no short flag
because `-f` belongs to `--force`, plus `--skill`/`-s` and `--bundle`/`-b`. Here
each takes **one** name, because `list` answers about one item; the accumulating
form that `install` needs is a different question and arrives with it.
"""

from __future__ import annotations

from enum import IntEnum
from importlib import metadata
from typing import TYPE_CHECKING, Annotated

import typer
from rich.console import Console
from rich.text import Text

from overpower.discovery import load_catalog
from overpower.errors import BadInvocationError, OverpowerError
from overpower.packaged import catalog_file, content_root
from overpower.screens import (
    THEME,
    artifact_screen,
    banner,
    bundle_screen,
    catalog_screen,
    error_panel,
    framework_screen,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rich.console import RenderableType

    from overpower.discovery import Catalog

PROGRAM = "overpower"

ABORTED = 130
"""What Ctrl-C costs before it reaches here — the shell's `128 + SIGINT`.

Read in `typer/core.py` of typer 0.27.1 and measured: typer's own `main`
overrides click's and turns `KeyboardInterrupt` into `Exit(130)`, where click
alone would have raised `Abort` and exited **1**. The model of the map puts
Ctrl-C under **1**, *could not run*, so the number is translated once, here,
rather than leaking a fifth code into a table that declares four. No command of
ours exits 130 for any other reason, so the translation cannot swallow a real
answer.
"""

_out = Console(theme=THEME, highlight=False)
_err = Console(theme=THEME, highlight=False, stderr=True)


class ExitCode(IntEnum):
    """What the shell reads back, and what each number promises.

    | code | meaning |
    | --- | --- |
    | 0 | did what was asked |
    | 1 | could not run |
    | 2 | you invoked me wrong |
    | 3 | ran, and the answer is no |

    `3` is the only one that costs code, and it is what makes `--dry-run` and
    `doctor` usable as a CI gate: *"could not compute the plan"* and *"computed
    it, and the answer is no"* have to be distinguishable, or a pipeline cannot
    tell whether to alert the team or try again.
    """

    OK = 0
    CANNOT_RUN = 1
    BAD_INVOCATION = 2
    REFUSED = 3


class TooManySelectorsError(BadInvocationError):
    """More than one selector on a `list` line, which has no single answer.

    `list` bare is the whole catalog and `list --<unit> <name>` is the content of
    **one** item; two selectors would be a question with two answers. Answering
    one of them silently is the class of defect this product exists not to commit
    — the screen says one thing and the result is another — so the command
    refuses and names every flag it was given.

    It lives here and not in the discovery because it is not about the catalog:
    the names may both be perfectly good, and it is the *line* that is wrong.
    """

    def __init__(self, flags: Sequence[str]) -> None:
        """Name every flag that was given, so the line can be cut in one edit."""
        self.flags = tuple(flags)
        given = " and ".join(self.flags)
        super().__init__(f"`list` shows one item at a time, and got {given}")


app = typer.Typer(
    name=PROGRAM,
    add_completion=False,
    # A bare `overpower` is not a usage error: it opens the banner and the help
    # and exits 0, by deliberate override.
    invoke_without_command=True,
    no_args_is_help=False,
    # The rich traceback is exactly what the error model forbids.
    pretty_exceptions_enable=False,
    help="Installs curated AI Frameworks into a repository or onto a machine.",
)


@app.callback()
def root(
    ctx: typer.Context,
    *,
    version: Annotated[
        bool, typer.Option("--version", help="Print the version that arrived and exit.")
    ] = False,
) -> None:
    """Open the banner and the help, or answer `--version`."""
    if version:
        # Rule 5: the version of the overpower *is* the version of the catalog it
        # embeds, so this one line is what `uvx overpower@0.1.0` pins.
        _out.print(Text.assemble((PROGRAM, "op.brand"), " ", _version()))
        raise typer.Exit(ExitCode.OK)

    if ctx.invoked_subcommand is None:
        _print_banner()
        # Typer's rich formatter prints the help to its own rich console and
        # returns nothing; the plain formatter returns the text instead. Both
        # paths are honoured, so the help does not depend on which is active.
        rendered = ctx.get_help()
        if rendered:
            _out.print(rendered)
        raise typer.Exit(ExitCode.OK)


@app.command("list")
def list_catalog(
    *,
    ai_framework: Annotated[
        str | None,
        typer.Option(
            "--ai-framework",
            metavar="NAME",
            # No short flag, and the reason is `--force`: `-f` is spoken for by
            # the mode flag of `install`, and a selector that means `--force` on
            # one line and `--ai-framework` on another is worse than typing it.
            help="Show the artifacts inside one AI Framework.",
        ),
    ] = None,
    skill: Annotated[
        str | None,
        typer.Option("--skill", "-s", metavar="NAME", help="Show one pool skill, whole."),
    ] = None,
    bundle: Annotated[
        str | None,
        typer.Option("--bundle", "-b", metavar="NAME", help="Show what one bundle names."),
    ] = None,
) -> None:
    """Show the catalog, or the content of one item of it."""
    catalog = load_catalog(content_root(), catalog_file())
    # Resolved before the banner: a name outside the catalog exits 2, and a
    # banner already on screen would be the product answering before it knew.
    screen = _listed(catalog, ai_framework=ai_framework, skill=skill, bundle=bundle)
    _print_banner()
    _out.print(screen)


def _listed(
    catalog: Catalog, *, ai_framework: str | None, skill: str | None, bundle: str | None
) -> RenderableType:
    """The screen the flags asked for: the whole catalog, or one item of it."""
    given = (("--ai-framework", ai_framework), ("--skill", skill), ("--bundle", bundle))
    selected = [flag for flag, name in given if name is not None]
    if len(selected) > 1:
        raise TooManySelectorsError(selected)

    if ai_framework is not None:
        return framework_screen(catalog.framework(ai_framework))
    if skill is not None:
        return artifact_screen(catalog.artifact(skill))
    if bundle is not None:
        return bundle_screen(catalog.bundle(bundle))
    return catalog_screen(catalog)


def main(argv: Sequence[str] | None = None) -> int:
    """The console script, and the only place an exception stops being one.

    `argv` exists for the tests: the entry point calls it with nothing and click
    reads `sys.argv`.
    """
    try:
        app(args=None if argv is None else list(argv), prog_name=PROGRAM)
    except SystemExit as stopped:
        # The framework's own exits: `--help` and `--version` at 0, a usage error
        # at 2, and Ctrl-C at 130, which `_code` translates. The number is read
        # off the exception and never re-derived here.
        return _code(stopped.code)
    except BadInvocationError as wrong:
        # Before the base class on purpose: this `except` order *is* the axis
        # between 1 and 2, and it is the only place the two are told apart.
        return _failed(str(wrong), ExitCode.BAD_INVOCATION)
    except OverpowerError as failure:
        return _failed(str(failure))
    except Exception as bug:  # noqa: BLE001 — the top handler catches everything by design
        return _failed(f"{type(bug).__name__}: {bug}", unexpected=True)
    return ExitCode.OK


def _print_banner() -> None:
    """The banner is a terminal courtesy, so it is gated on being in one.

    Under a pipe there is no banner and no ANSI: the output has to stay readable
    on the other end, which is where `grep` and a file are.
    """
    if not _out.is_terminal:
        return
    _out.print(banner(_version(), _out.width))


def _failed(message: str, code: ExitCode = ExitCode.CANNOT_RUN, *, unexpected: bool = False) -> int:
    """The panel, and the last place a message is still a message.

    `Text`, never markup: the message carries paths and exception text, and both
    routinely contain `[`. Measured, as markup a path of `/tmp/[wip]/pool/sklls`
    renders `/tmp//pool/sklls` — the *wrong path*, which is the one thing the
    message exists to name — and `/tmp/[/2024]/SKILL.md` raises `MarkupError`
    from inside the handler, which is how a traceback escapes the one function
    written to stop it.
    """
    body = Text(message)
    if unexpected:
        body = Text.assemble(
            body,
            "\n\n",
            ("This is a bug in the overpower, not in what you typed.", "op.dim"),
        )
    _err.print(error_panel(body))
    return code


def _code(code: int | str | None) -> int:
    """Whatever `SystemExit` carried, as a number the shell can read."""
    if code is None:
        return ExitCode.OK
    if code == ABORTED:
        return ExitCode.CANNOT_RUN
    if isinstance(code, int):
        return code
    return _failed(code)


def _version() -> str:
    """The version that arrived, read from installed metadata and not a constant.

    Reading the metadata is what proves the `dist-info` travelled intact; a
    literal here would answer even when nothing was installed.
    """
    try:
        return metadata.version("overpower")
    except metadata.PackageNotFoundError:  # pragma: no cover — installed in every cell
        return "uninstalled (running from source)"
