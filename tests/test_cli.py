"""Terminal citizenship and the error model: the frame every later ticket uses.

Two shapes of test, and the split is not taste.

**In process**, through `cli.main([...])`, for what the environment cannot move:
exit codes, and that an unhandled exception becomes a panel instead of a stack.

**In a subprocess**, for the two properties that are *about* the environment —
zero ANSI under a pipe, and the banner gated on `isatty()`. They cannot be
answered in process: `typer` reads `FORCE_COLOR`, `PY_COLORS` and
`GITHUB_ACTIONS` **at import time** to decide whether to force a terminal, and
both this machine and the CI runner set one of them. A child with a scrubbed
environment and a real pipe on its stdout is the only honest measurement, and it
is also the closest thing to what the user actually runs.
"""

from __future__ import annotations

import io
import os
import subprocess
import sys
from importlib import metadata
from typing import TYPE_CHECKING

import pytest
from rich.console import Console

from overpower import cli
from overpower.errors import OverpowerError
from overpower.screens import THEME

if TYPE_CHECKING:
    from collections.abc import Sequence

RUN = "import sys; from overpower.cli import main; sys.exit(main())"
"""The console script, one line: `project.scripts` is `overpower.cli:main`."""

FORCED_COLOUR = ("FORCE_COLOR", "PY_COLORS", "CLICOLOR_FORCE", "GITHUB_ACTIONS", "TERM")
"""Everything that tells rich or typer to emit colour into something that is not a
terminal. Scrubbed in the child so the pipe is the only thing left to answer."""


def piped(*argv: str) -> subprocess.CompletedProcess[bytes]:
    """Run the command the way a user pipes it: a real child, a real pipe.

    The output is read as **bytes**, and that is the assertion's own unit — the
    criterion is *zero `ESC` bytes*. It is also the only way to read it at all on
    Windows: measured on the matrix, a pipe there takes the locale encoding, so
    the child writes cp1252 and rich swaps the box characters for ASCII
    (`ConsoleOptions.ascii_only`). The screen degrades and stays ANSI-free, which
    is the property; decoding it as UTF-8 is what breaks.
    """
    environment = {key: value for key, value in os.environ.items() if key not in FORCED_COLOUR}
    environment["COLUMNS"] = "80"
    return subprocess.run(  # noqa: S603 — the argv is this interpreter and literals
        [sys.executable, "-c", RUN, *argv],
        capture_output=True,
        env=environment,
        check=False,
    )


def output_of(capsys: pytest.CaptureFixture[str], argv: Sequence[str]) -> tuple[int, str]:
    code = cli.main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out + captured.err


# --------------------------------------------------------------------------- #
# the surface
# --------------------------------------------------------------------------- #


def test_a_bare_invocation_prints_the_help_and_exits_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Exit 0 by deliberate override: a bare name is not a usage error."""
    code, output = output_of(capsys, [])

    assert code == 0
    assert "Usage" in output


def test_the_version_flag_prints_the_version_that_arrived(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Rule 5: the version of the overpower *is* the version of the catalog."""
    code, output = output_of(capsys, ["--version"])

    assert code == 0
    assert metadata.version("overpower") in output


def test_an_unknown_flag_exits_two(capsys: pytest.CaptureFixture[str]) -> None:
    """2 is *you invoked me wrong* — the defect is on the caller's side."""
    code, _ = output_of(capsys, ["--nope"])

    assert code == 2


@pytest.mark.parametrize(
    ("terminal", "expected"),
    [pytest.param(True, True, id="tty"), pytest.param(False, False, id="pipe")],
)
def test_the_banner_follows_the_terminal_and_nothing_else(
    monkeypatch: pytest.MonkeyPatch, *, terminal: bool, expected: bool
) -> None:
    """The gate is `isatty()`, asserted in both directions rather than one.

    The child process below proves the pipe half against the real binary; this
    one proves the other half, which no pipe can show.
    """
    sink = io.StringIO()
    monkeypatch.setattr(
        cli,
        "_out",
        Console(file=sink, theme=THEME, width=80, force_terminal=terminal, highlight=False),
    )

    assert cli.main(["list"]) == 0

    assert ("_____" in sink.getvalue()) is expected


def test_the_list_command_shows_the_three_blocks(capsys: pytest.CaptureFixture[str]) -> None:
    code, output = output_of(capsys, ["list"])

    assert code == 0
    assert "AI Frameworks" in output
    assert "Pool skills" in output
    assert "Bundles" in output


# --------------------------------------------------------------------------- #
# the error model
# --------------------------------------------------------------------------- #


def test_an_unhandled_exception_exits_one_without_a_traceback(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A rich traceback in the terminal leaks library internals to the user."""

    def explode(*_: object, **__: object) -> object:
        message = "the disk went away"
        raise RuntimeError(message)

    monkeypatch.setattr(cli, "load_catalog", explode)

    code, output = output_of(capsys, ["list"])

    assert code == 1
    assert "Traceback" not in output
    assert "the disk went away" in output


def test_a_named_failure_exits_one_and_says_what_it_found(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode(*_: object, **__: object) -> object:
        message = "unknown artifact type directory: /content/pool/sklls"
        raise OverpowerError(message)

    monkeypatch.setattr(cli, "load_catalog", explode)

    code, output = output_of(capsys, ["list"])

    assert code == 1
    assert "/content/pool/sklls" in output
    assert "RuntimeError" not in output


def test_a_path_with_brackets_reaches_the_panel_whole(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The message names the wrong path, so the path cannot be re-read as markup.

    Measured: as markup, `/tmp/[wip]/pool/sklls` renders `/tmp//pool/sklls` —
    the segment that names the defect is the segment that disappears.
    """

    def explode(*_: object, **__: object) -> object:
        message = "unknown artifact type directory: /tmp/[wip]/pool/sklls"
        raise OverpowerError(message)

    monkeypatch.setattr(cli, "load_catalog", explode)

    code, output = output_of(capsys, ["list"])

    assert code == 1
    assert "[wip]" in output


def test_a_message_that_looks_like_a_closing_tag_does_not_escape_the_handler(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Measured: `[/2024]` raises `MarkupError` *from inside* the handler."""

    def explode(*_: object, **__: object) -> object:
        message = "no description in the frontmatter of /tmp/c/[/2024]/SKILL.md"
        raise OverpowerError(message)

    monkeypatch.setattr(cli, "load_catalog", explode)

    code, output = output_of(capsys, ["list"])

    assert code == 1
    assert "[/2024]" in output


def test_an_interrupt_exits_one(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ctrl-C is *could not run*, and it is not a crash report."""

    def interrupt(*_: object, **__: object) -> object:
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "load_catalog", interrupt)

    code, output = output_of(capsys, ["list"])

    assert code == 1
    assert "Traceback" not in output


def test_the_exit_codes_are_the_four_the_model_declares() -> None:
    """The table is born whole even though v0.1.0 only exercises part of it."""
    assert [code.value for code in cli.ExitCode] == [0, 1, 2, 3]


# --------------------------------------------------------------------------- #
# terminal citizenship, measured in a child
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "argv",
    [pytest.param([], id="bare"), pytest.param(["list"], id="list")],
)
def test_piped_output_carries_no_ansi(argv: list[str]) -> None:
    """Measured in #12: the three piped captures carry zero `ESC` bytes."""
    result = piped(*argv)

    assert result.returncode == 0
    assert b"\x1b" not in result.stdout
    assert b"\x1b" not in result.stderr


def test_the_banner_is_suppressed_without_a_tty() -> None:
    result = piped()

    assert result.returncode == 0
    assert b"_____" not in result.stdout


def test_the_list_screen_survives_a_pipe_whole() -> None:
    """A screen conducted to a file has to stay readable on the other end.

    Only the ASCII of it is asserted, because the encoding of the rest is the
    pipe's to choose — the truncation property lives next door in
    `test_screens.py`, at both widths, where it is not an encoding question.
    """
    result = piped("list")

    assert result.returncode == 0
    assert b"AI Frameworks" in result.stdout
    assert b"panlabs-python-standards" in result.stdout
