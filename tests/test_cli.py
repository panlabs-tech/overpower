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
import shlex
import subprocess
import sys
from dataclasses import replace
from importlib import metadata
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Protocol

import pytest
from rich.console import Console

from overpower import cli, remote, wizard
from overpower.discovery import load_catalog
from overpower.errors import OverpowerError
from overpower.packaged import catalog_file, content_root
from overpower.planning import Request
from overpower.runtimes import Scope
from overpower.screens import THEME
from tests.support import git_remote, project

if TYPE_CHECKING:
    from collections.abc import Sequence

    from overpower.discovery import Catalog
    from overpower.runtimes import Environment

    CaptureFixture = pytest.CaptureFixture[str]

    class Wizard(Protocol):
        """The shape `overpower.cli` calls: the request as the flags left it in, the
        same request with its gaps filled out.

        A `Protocol` and not a `Callable[...]` alias because `console` is
        keyword-only, which the alias form cannot spell — and it is keyword-only
        because the five before it are the steps and it is not one of them.

        The five are positional-only (`/`), which is what a `Callable[...]`
        alias gave for free: a stub is free to underscore the parameters it
        ignores, and without the marker `pyright` reads `_catalog` against
        `catalog` as a mismatch rather than as an unused argument.
        """

        def __call__(  # noqa: PLR0913 — one per parameter of the seam it describes
            self,
            asked: Request,
            catalog: Catalog | None,
            environment: Environment,
            cwd: Path,
            scoped: tuple[Scope, Path] | None,
            /,
            *,
            console: Console,
        ) -> tuple[Request, Path]: ...


RUN = "import sys; from overpower.cli import main; sys.exit(main())"
"""The console script, one line: `project.scripts` is `overpower.cli:main`."""

FORCED_COLOUR = ("FORCE_COLOR", "PY_COLORS", "CLICOLOR_FORCE", "GITHUB_ACTIONS", "TERM")
"""Everything that tells rich or typer to emit colour into something that is not a
terminal. Scrubbed in the child so the pipe is the only thing left to answer."""


def piped(*argv: str, sandbox: Path | None = None) -> subprocess.CompletedProcess[bytes]:
    """Run the command the way a user pipes it: a real child, a real pipe.

    The output is read as **bytes**, and that is the assertion's own unit — the
    criterion is *zero `ESC` bytes*. It is also the only way to read it at all on
    Windows: measured on the matrix, a pipe there takes the locale encoding, so
    the child writes cp1252 and rich swaps the box characters for ASCII
    (`ConsoleOptions.ascii_only`). The screen degrades and stays ANSI-free, which
    is the property; decoding it as UTF-8 is what breaks.

    `sandbox` moves the child's working directory *and* its home, and it is not
    a convenience: `doctor` reads both scopes off the machine, so a child left in
    the real environment would report the developer's own equipment — and could
    exit 3 on it, turning a property about ANSI bytes into a test of whose
    laptop ran it.
    """
    environment = {key: value for key, value in os.environ.items() if key not in FORCED_COLOUR}
    environment["COLUMNS"] = "80"
    if sandbox is not None:
        environment.update(HOME=str(sandbox), USERPROFILE=str(sandbox))
        for anchor in project.ANCHORS:
            environment.pop(anchor, None)
    return subprocess.run(  # noqa: S603 — the argv is this interpreter and literals
        [sys.executable, "-c", RUN, *argv],
        capture_output=True,
        cwd=None if sandbox is None else sandbox,
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


def test_the_package_installs_exactly_one_executable() -> None:
    """#58: no second entry point is installed for the `op` shell alias someone types themselves.

    `op` is the binary of the 1Password CLI, so a second `[project.scripts]`
    entry would shadow a credential tool with no warning at all — measured once,
    at the time #58 decided the product would never claim the name. What this
    asserts is the consequence, read off the **installed metadata** rather than
    off `pyproject.toml` — the reason `_version` reads it there: what ships is
    what the `dist-info` says, not what the source declares.
    """
    entry_points = metadata.distribution("overpower").entry_points

    installed = [point.name for point in entry_points if point.group == "console_scripts"]
    assert installed == ["overpower"]


def test_the_list_command_shows_the_four_blocks(capsys: pytest.CaptureFixture[str]) -> None:
    """Four units, four blocks — the MCP server has to exist on screen to be found.

    Whoever has never read the documentation learns the class exists from the
    catalog itself, which is what the block buys
    (https://github.com/panlabs-tech/overpower/issues/77).
    """
    code, output = output_of(capsys, ["list"])

    assert code == 0
    assert "AI Frameworks" in output
    assert "Pool skills" in output
    assert "Bundles" in output
    assert "MCP servers" in output


def test_the_runtime_help_names_the_two_tables(capsys: pytest.CaptureFixture[str]) -> None:
    """ADR 0017 split skill and MCP into separate runtime tables; the help text still
    read as if `--runtime` picked from one — the asymmetry only surfaced as a refusal.
    """
    code, output = output_of(capsys, ["install", "--help"])

    assert code == 0
    assert "not every runtime" in output


def test_the_install_help_still_fits_eighty_columns() -> None:
    result = piped("install", "--help")

    assert result.returncode == 0
    lines = result.stdout.decode().splitlines()
    assert [line for line in lines if len(line) > 80] == []


# --------------------------------------------------------------------------- #
# the content of one item
# --------------------------------------------------------------------------- #


def test_the_framework_screen_lists_what_is_inside_it(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A framework installs whole, so *whole* has to be readable before accepting.

    Both names are read off the catalog rather than typed in: the promoted set is
    re-read from upstream at every curation refresh — it has already gone from 22
    to 25 — and a test that names one of its members turns a curation move into a
    red build.
    """
    # given
    framework = load_catalog(content_root(), catalog_file()).frameworks[0]

    code, output = output_of(capsys, ["list", "--ai-framework", framework.name])

    assert code == 0
    assert framework.artifacts[0].name in output
    assert "Pool skills" not in output


def test_the_bundle_screen_names_the_pool_artifacts_of_the_manifest(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, output = output_of(capsys, ["list", "--bundle", "api-python"])

    assert code == 0
    assert "panlabs-python-standards" in output
    assert "AI Frameworks" not in output


def test_the_skill_screen_shows_one_pool_skill_and_not_the_catalog(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The wiring, here; that the description arrives *whole* is a screen property.

    It is asserted next door in `test_screens.py`, at 80 and at 60 columns, over
    the rendered screen — the only place the frame and the re-wrapping can be
    undone. Through `capsys` the same text arrives interleaved with borders and,
    depending on the machine, with escape sequences, so asserting it here would
    be asserting the capture.
    """
    described = load_catalog(content_root(), catalog_file()).pool[0]

    code, output = output_of(capsys, ["list", "--skill", described.name])

    assert code == 0
    assert described.name in output
    assert "AI Frameworks" not in output
    assert "Bundles" not in output


def test_the_mcp_screen_shows_one_recipe_and_not_the_catalog(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The wiring, and the one line of it that is derived rather than read.

    That the description arrives whole and that the rows are laid out at both
    widths is a screen property, asserted next door in `test_screens.py`. What
    only this seam can answer is that the targets and scopes lines the user sees
    are the ones the **product** computes off its own table — a screen drawn
    with a fixture could agree with itself all the way to a wrong answer.
    """
    catalog = load_catalog(content_root(), catalog_file())
    recipe = catalog.mcps[0]

    code, output = output_of(capsys, ["list", "--mcp", recipe.name])

    assert code == 0
    assert recipe.name in output
    joined = project.joined(output)
    assert "claude-code" in joined
    assert "devin" in joined
    assert "project, global" in joined
    assert "AI Frameworks" not in output
    assert "Bundles" not in output


@pytest.mark.parametrize(
    ("argv", "listed"),
    [
        pytest.param(["list", "--ai-framework", "matt-pocok"], "matt-pocock", id="ai-framework"),
        pytest.param(["list", "--skill", "grillin"], "panlabs-python-standards", id="skill"),
        pytest.param(["list", "--bundle", "api-pythn"], "api-python", id="bundle"),
        pytest.param(["list", "--mcp", "cloudflar"], "cloudflare", id="mcp"),
    ],
)
def test_a_name_outside_the_catalog_exits_two_naming_the_closed_list(
    capsys: pytest.CaptureFixture[str], argv: list[str], listed: str
) -> None:
    """The list is closed, so a name that is not on it is the caller's defect."""
    code, output = output_of(capsys, argv)

    assert code == 2
    assert listed in output


@pytest.mark.parametrize(
    ("argv", "flags"),
    [
        pytest.param(
            ["list", "--skill", "grilling", "--bundle", "api-python"],
            ("--skill", "--bundle"),
            id="skill-and-bundle",
        ),
        pytest.param(
            ["list", "--mcp", "cloudflare", "--skill", "grilling"],
            ("--skill", "--mcp"),
            id="mcp-and-skill",
        ),
    ],
)
def test_two_selectors_on_one_line_exit_two(
    capsys: pytest.CaptureFixture[str], argv: list[str], flags: tuple[str, ...]
) -> None:
    """`list` answers about one item, so two selectors have no single answer."""
    code, output = output_of(capsys, argv)

    assert code == 2
    for flag in flags:
        assert flag in output


def test_two_selectors_are_refused_before_the_catalog_is_read(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The defect is in the line, so the answer cannot depend on the tree.

    With the order the other way round a broken content tree would answer **1** —
    *could not run* — to a question whose real answer is **2**, and the two codes
    exist precisely so a pipeline can tell *"alert the team"* from *"fix the
    line"*.
    """

    def explode(*_: object, **__: object) -> object:
        message = "unknown artifact type directory: /content/pool/sklls"
        raise OverpowerError(message)

    monkeypatch.setattr(cli, "load_catalog", explode)

    code, _ = output_of(capsys, ["list", "--skill", "grilling", "--bundle", "api-python"])

    assert code == 2


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
    [
        pytest.param([], id="bare"),
        pytest.param(["--help"], id="help"),
        pytest.param(["list"], id="list"),
        pytest.param(["list", "--ai-framework", "matt-pocock"], id="list-framework"),
        pytest.param(["list", "--mcp", "cloudflare"], id="list-mcp"),
    ],
)
def test_piped_output_carries_no_ansi(argv: list[str]) -> None:
    """Measured in #12: the three piped captures carry zero `ESC` bytes.

    `--help` joined them with #58, which is when it started going through the
    banner at all: the root help is now formatted by a group that draws one, so
    the gesture that used to be pure click output is a gesture this property has
    to cover.
    """
    result = piped(*argv)

    assert result.returncode == 0
    assert b"\x1b" not in result.stdout
    assert b"\x1b" not in result.stderr


def test_the_banner_is_suppressed_without_a_tty() -> None:
    result = piped()

    assert result.returncode == 0
    assert b"_____" not in result.stdout


def test_the_doctor_screen_carries_no_ansi_under_a_pipe(tmp_path: Path) -> None:
    """The one command a pipeline reads on purpose, so the pipe half is measured.

    A sandbox rather than the repository this suite runs in: `doctor` reports the
    machine as well, and pointing the child at the developer's home would make
    the exit code depend on what they happen to have installed.
    """
    result = piped("doctor", sandbox=tmp_path)

    assert result.returncode == 0
    assert b"\x1b" not in result.stdout
    assert b"\x1b" not in result.stderr
    assert b"integrity" in result.stdout


def test_a_doctor_that_found_something_pipes_exit_three_and_still_no_ansi(
    tmp_path: Path,
) -> None:
    """The finding screen is the one with warm ink on it, so it is the one to pipe.

    A healthy run has nothing styled `op.warn`, so asserting zero `ESC` on it
    alone would leave the branch that actually reaches for colour unmeasured.
    Two copies of one name in two global runtime paths is the cheapest way to
    build a finding without installing anything — and the exit code travels
    through a real child, which is how a pipeline reads it.
    """
    # given
    for place, content in ((".claude/skills", "one"), (".cursor/skills", "two")):
        skill = tmp_path / place / "alpha"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(content, encoding="utf-8", newline="\n")

    result = piped("doctor", sandbox=tmp_path)

    assert result.returncode == 3
    assert b"\x1b" not in result.stdout
    assert b"\x1b" not in result.stderr
    assert b"differ" in result.stdout


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


def test_the_lines_to_copy_survive_a_pipe() -> None:
    """The banner is a courtesy and is gated on `isatty()`; a command is a datum.

    `overpower list | grep <name>` has to hand back the line to type, so the two
    are asserted against the same child: the art is gone and the commands are
    not.
    """
    catalog = load_catalog(content_root(), catalog_file())

    result = piped("list")

    assert result.returncode == 0
    assert b"_____" not in result.stdout
    assert b"overpower install --skill panlabs-python-standards" in result.stdout
    for framework in catalog.frameworks:
        assert f"overpower install --ai-framework {framework.name}".encode() in result.stdout
        assert f"overpower list --ai-framework {framework.name}".encode() in result.stdout
    for recipe in catalog.mcps:
        assert f"overpower install --mcp {recipe.name}".encode() in result.stdout
        assert f"overpower list --mcp {recipe.name}".encode() in result.stdout


# --------------------------------------------------------------------------- #
# the install surface: the confirmation, and the two flags that steer past it
# --------------------------------------------------------------------------- #


def test_the_confirmation_is_asked_in_a_terminal_and_declining_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """Confirmation before any byte, and a decline is *could not run*, like Ctrl-C.

    Only the seam is stubbed. What it stands in for is a `questionary` prompt,
    and the ruler excludes a Stub from contract testing by name: it supplies
    indirect input, it does not emulate the library.
    """
    # given
    project.catalog_of(tmp_path, monkeypatch, "alpha")
    root = project.target(tmp_path, monkeypatch)
    project.terminal(monkeypatch)
    monkeypatch.setattr(cli, "_confirmed", lambda: False)

    code, _ = project.run(capsys, "install", "--skill", "alpha", "--runtime", "claude-code")

    assert code == 1
    assert list(root.iterdir()) == []


# --------------------------------------------------------------------------- #
# #69: a terminal turns #40's hard refusal into a question
# --------------------------------------------------------------------------- #


def test_a_conflict_in_a_terminal_asks_instead_of_refusing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """Global scope, a terminal, no `--force`: yes overwrites instead of exit 3."""

    def confirm_overwrite(_conflicts: Sequence[Path]) -> bool:
        return True

    # given
    project.catalog_of(tmp_path, monkeypatch, "alpha")
    project.target(tmp_path, monkeypatch)
    project.terminal(monkeypatch)
    existing = tmp_path / project.CLAUDE / "alpha"
    existing.mkdir(parents=True)
    (existing / "stale.md").write_text("from before\n", encoding="utf-8")
    monkeypatch.setattr(cli, "_confirmed_overwrite", confirm_overwrite)

    code, _ = project.run(
        capsys, "install", "--skill", "alpha", "--runtime", "claude-code", "--global"
    )

    assert code == 0
    assert not (existing / "stale.md").exists()
    assert (existing / "SKILL.md").is_file()


def test_declining_the_overwrite_prompt_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """No is no — the same exit as declining the plain confirmation, a human said stop."""

    def confirm_overwrite(_conflicts: Sequence[Path]) -> bool:
        return False

    # given
    project.catalog_of(tmp_path, monkeypatch, "alpha")
    project.target(tmp_path, monkeypatch)
    project.terminal(monkeypatch)
    existing = tmp_path / project.CLAUDE / "alpha"
    existing.mkdir(parents=True)
    (existing / "stale.md").write_text("from before\n", encoding="utf-8")
    monkeypatch.setattr(cli, "_confirmed_overwrite", confirm_overwrite)

    code, _ = project.run(
        capsys, "install", "--skill", "alpha", "--runtime", "claude-code", "--global"
    )

    assert code == 1
    assert (existing / "stale.md").is_file()


def test_the_overwrite_prompt_replaces_the_plain_one_and_names_the_conflict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """One prompt, not two, and it is told which path it would clobber."""
    # given
    project.catalog_of(tmp_path, monkeypatch, "alpha")
    project.target(tmp_path, monkeypatch)
    project.terminal(monkeypatch)
    existing = tmp_path / project.CLAUDE / "alpha"
    existing.mkdir(parents=True)
    (existing / "stale.md").write_text("from before\n", encoding="utf-8")
    plain_asked: list[str] = []
    overwrite_asked: list[Sequence[Path]] = []

    def confirm_overwrite(conflicts: Sequence[Path]) -> bool:
        overwrite_asked.append(conflicts)
        return True

    monkeypatch.setattr(cli, "_confirmed", lambda: bool(plain_asked.append("asked")))
    monkeypatch.setattr(cli, "_confirmed_overwrite", confirm_overwrite)

    code, _ = project.run(
        capsys, "install", "--skill", "alpha", "--runtime", "claude-code", "--global"
    )

    assert code == 0
    assert plain_asked == []
    assert overwrite_asked == [(existing,)]


def test_dry_run_in_a_terminal_still_refuses_without_asking(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """`--dry-run` is a report, never a session — a terminal does not turn it into one."""
    # given
    project.catalog_of(tmp_path, monkeypatch, "alpha")
    project.target(tmp_path, monkeypatch)
    project.terminal(monkeypatch)
    existing = tmp_path / project.CLAUDE / "alpha"
    existing.mkdir(parents=True)
    asked: list[str] = []

    def confirm_overwrite(_conflicts: Sequence[Path]) -> bool:
        asked.append("asked")
        return True

    monkeypatch.setattr(cli, "_confirmed_overwrite", confirm_overwrite)

    code, output = project.run(
        capsys,
        "install",
        "--skill",
        "alpha",
        "--runtime",
        "claude-code",
        "--global",
        "--dry-run",
    )

    assert code == 3
    assert asked == []
    assert "--force" in project.joined(output)


def test_the_plan_names_its_artifacts_on_all_three_ways_in(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """#58, as #65 revised it: one plan, two lengths, and neither may lose a path.

    #58 asserted the **artifact list** on all three ways in, on the argument
    that a gate has to be readable whole. #65 measured that argument false at
    the terminal it was written for: at 80x24 the detailed plan is 34 lines, so
    by the time `Write these paths?` appeared the first **11** had scrolled —
    including the head line naming what was being accepted. A gate nobody can
    read whole is not a gate.

    So the two screens split by **length and never by content**: `--dry-run`
    keeps the artifact list, because the audit may never say less than the run
    it audits and it is read off a pipe where scrolling costs nothing; the gate
    speaks in destinations, which is the shape `npx skills` gives it. They stay
    one function one flag apart (`_planned(..., detailed=)`), and what is
    asserted here is the seam that matters: **no path may be on one and off
    another**.

    A framework, because it is the case the list exists for: `--ai-framework fw`
    is two words on the line and two artifacts on the disk, and the names of
    those two appear nowhere else in what was typed.
    """

    def picked_framework(
        _catalog: Catalog,
    ) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
        return (("fw",), (), (), ())

    def project_scope(
        cwd: Path, _environment: Environment, _console: Console, *, sourced: bool = False
    ) -> tuple[Scope, Path]:
        del sourced
        return Scope.PROJECT, cwd

    def fixed_runtimes(_scope: Scope, _root: Path, _environment: Environment) -> tuple[str, ...]:
        return ("claude-code",)

    # given
    project.catalog_of(tmp_path, monkeypatch, frameworks={"fw": ["fa", "fb"]})
    project.target(tmp_path, monkeypatch)
    project.terminal(monkeypatch)
    monkeypatch.setattr(wizard, "ask_artifacts", picked_framework)
    monkeypatch.setattr(wizard, "ask_scope", project_scope)
    monkeypatch.setattr(wizard, "ask_runtimes", fixed_runtimes)
    monkeypatch.setattr(cli, "_confirmed", lambda: False)
    selectors = ("install", "--ai-framework", "fw", "--runtime", "claude-code")

    dry_code, dry_out = project.run(capsys, *selectors, "--dry-run")
    wizard_code, wizard_out = project.run(capsys, "install")
    real_code, real_out = project.run(capsys, *selectors, "--yes")

    assert (dry_code, wizard_code, real_code) == (0, 1, 0)
    # the audit names every artifact, and nothing else has to
    audited = project.joined(dry_out)
    assert "skill fa" in audited
    assert "skill fb" in audited
    # and every path is on all three, which is the half that may never split
    for output in (dry_out, wizard_out, real_out):
        assert f"{project.CLAUDE}/" in project.joined(output)


def test_yes_skips_the_confirmation_and_nothing_else(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """Choosing between the repository and `~/` is not a yes-or-no question."""
    # given
    asked: list[str] = []
    project.catalog_of(tmp_path, monkeypatch, "alpha")
    root = project.target(tmp_path, monkeypatch)
    project.terminal(monkeypatch)
    monkeypatch.setattr(cli, "_confirmed", lambda: bool(asked.append("asked")))

    code, _ = project.run(
        capsys, "install", "--skill", "alpha", "--runtime", "claude-code", "--yes"
    )

    assert code == 0
    assert asked == []
    assert (root / project.CLAUDE / "alpha" / "SKILL.md").is_file()


@pytest.mark.parametrize(
    "extra",
    [pytest.param((), id="without --yes"), pytest.param(("--yes",), id="with --yes")],
)
def test_without_a_terminal_the_command_runs_and_yes_is_a_no_op(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: CaptureFixture,
    extra: tuple[str, ...],
) -> None:
    """v0.1.0 removes nothing: it stands next to `pip`, not next to `apt-get`.

    The same line therefore runs identically in a terminal and in CI.
    """
    # given
    asked: list[str] = []
    project.catalog_of(tmp_path, monkeypatch, "alpha")
    root = project.target(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "_confirmed", lambda: bool(asked.append("asked")))

    code, _ = project.run(capsys, "install", "--skill", "alpha", "--runtime", "claude-code", *extra)

    assert code == 0
    assert asked == []
    assert (root / project.CLAUDE / "alpha" / "SKILL.md").is_file()


def test_the_dry_run_mirrors_the_exit_code_of_the_real_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The whole reason `--dry-run` works as a CI gate: the number has to agree.

    Asserted on a refusal and not only on a clean plan, because a dry run that
    answered 0 where the real run answers 2 would pass a pipeline that is about
    to fail.
    """
    # given
    project.catalog_of(tmp_path, monkeypatch, "alpha")
    root = project.target(tmp_path, monkeypatch)
    selectors = ("install", "--skill", "alpha", "--runtime", "cursr")

    dry_code, _ = project.run(capsys, *selectors, "--dry-run")
    real_code, _ = project.run(capsys, *selectors)

    assert dry_code == real_code == 2
    assert list(root.iterdir()) == []


# --------------------------------------------------------------------------- #
# the graft: `--mcp`, and the warning ADR 0014 makes a requirement
# --------------------------------------------------------------------------- #

MCP_URL = "https://mcp.cloudflare.com/mcp"


def test_installing_an_mcp_warns_that_it_is_born_pending_approval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """ADR 0014: the product does not turn the server on, and it says so.

    Measured in #17: a server coming from `.mcp.json` is born `⏸ Pending
    approval` in Claude Code and **does not connect** — no message, no exit code,
    no sign in a normal session. Without this line the product ships exactly that
    failure: file written, exit 0, tool absent.

    Exit **0**, because the write happened and was correct; what is missing is
    the user's act.
    """
    # given
    project.catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": MCP_URL})
    root = project.target(tmp_path, monkeypatch)

    code, output = project.run(capsys, "install", "--mcp", "cloudflare", "--runtime", "claude-code")

    assert code == 0
    joined = project.joined(output)
    assert "pending approval" in joined
    assert ".mcp.json" in joined
    assert "approve" in joined
    assert (root / ".mcp.json").is_file()


def test_a_run_that_grafts_nothing_says_nothing_about_approval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """A warning that appears everywhere is a warning nobody reads (ADR 0014)."""
    # given
    project.catalog_of(tmp_path, monkeypatch, "alpha", mcps={"cloudflare": MCP_URL})
    project.target(tmp_path, monkeypatch)

    code, output = project.run(capsys, "install", "--skill", "alpha", "--runtime", "claude-code")

    assert code == 0
    assert "pending approval" not in project.joined(output)


def test_a_graft_into_vscode_says_nothing_about_approval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The warning is true of one target and is not printed at the other (ADR 0014).

    `born_pending` is a column of the document table because it is a fact of the
    pair (runtime, scope): a server in `.mcp.json` is born `⏸ Pending approval`
    in Claude Code, and one in `.vscode/mcp.json` is not — what VS Code gates is
    Workspace Trust, which is a fact of the **folder** and not of the server, so
    a per-graft line about it would be a warning that appears everywhere.

    Asserted with a slotted recipe on purpose: this is the run with the most to
    say at exit 0 — two keys land — and the approval line still is not one of the
    things it says.
    """
    # given
    project.catalog_of(tmp_path, monkeypatch, mcps={"panel": project.SLOTTED})
    root = project.target(tmp_path, monkeypatch)

    code, output = project.run(capsys, "install", "--mcp", "panel", "--runtime", "vscode")

    assert code == 0
    joined = project.joined(output)
    assert "pending approval" not in joined
    assert "approve" not in joined
    assert (root / ".vscode" / "mcp.json").is_file()


def test_a_server_and_its_prompt_in_one_document_are_counted_as_one_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """#75, on the pair the spec names: *"the two are one write of the plan"*.

    A VS Code slot lands the server under `servers` and the prompt it refers to
    under `inputs` — two keys, one document — and the spec says why they count
    as one: *"because they land in the same place"*. That place is the landing,
    and `_graft_landing` already opens by saying it draws exactly one however
    many keys fall in it. The **files** half was already collapsed on that
    reading; the writes half counted keys.

    The unit is the landing rather than the `Write` object, and the federated
    case below is what fixes which: the spec calls clone-plus-graft two writes,
    and that is two landings as well as two objects, so it agrees with either
    reading and settles nothing. This line is the only one that discriminates.
    """
    # given
    project.catalog_of(tmp_path, monkeypatch, mcps={"panel": project.SLOTTED})
    root = project.target(tmp_path, monkeypatch)

    code, output = project.run(capsys, "install", "--mcp", "panel", "--runtime", "vscode")

    assert code == 0
    assert "1 write · 1 file" in project.joined(output)
    assert (root / ".vscode" / "mcp.json").is_file()


def test_several_servers_landing_in_one_document_are_counted_as_one_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The contract `overpower.planning` states in its own words, on the case that broke it.

    *"One for the first graft into a document. **Zero for a second graft into the
    same one**"* — and "the same one" is the same **document**. Three servers
    asked for in one line land in one `.vscode/mcp.json`, so two of the three are
    second grafts into the same one; the count restarted per selection and said
    three, where `git status` shows one file.

    Each of the three carries a slot, so this is also the multi-key case: nine
    keys, three servers, one document, and the honest answer to both questions
    is the number of documents.
    """
    # given
    project.catalog_of(
        tmp_path,
        monkeypatch,
        mcps={"panel": project.SLOTTED, "second": project.SLOTTED, "third": project.SLOTTED},
    )
    root = project.target(tmp_path, monkeypatch)

    code, output = project.run(
        capsys, "install", "--mcp", "panel,second,third", "--runtime", "vscode"
    )

    assert code == 0
    assert [entry.name for entry in (root / ".vscode").iterdir()] == ["mcp.json"]
    assert "3 writes · 1 file" in project.joined(output)


def test_one_server_in_two_runtimes_still_counts_the_two_documents_it_landed_in(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The half the two fixes above must not eat: distinct documents still count.

    The rule is *one per document*, not *one per run*. Collapsing by document
    and collapsing to one are the same edit if nobody asserts the difference.
    """
    # given
    project.catalog_of(tmp_path, monkeypatch, mcps={"panel": project.SLOTTED})
    root = project.target(tmp_path, monkeypatch)

    code, output = project.run(
        capsys, "install", "--mcp", "panel", "--runtime", "claude-code,vscode"
    )

    assert code == 0
    assert (root / ".mcp.json").is_file()
    assert (root / ".vscode" / "mcp.json").is_file()
    assert "2 writes · 2 files" in project.joined(output)


def test_a_vscode_slot_is_not_a_variable_the_shell_has_to_export(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The other warning that is true of one target and false at the other.

    `${VAR}` is read out of the runtime's own process, so an absent variable is a
    measured failure at the far end and the line earns itself. `${input:<id>}` is
    read out of a prompt and the OS keychain: nothing looks the variable up, so
    telling somebody to export it is an instruction that does nothing — a warning
    nobody can act on, which is a warning nobody reads.

    The variable is deliberately left unset, which is the state that produces the
    line at the other target.
    """
    # given
    project.catalog_of(tmp_path, monkeypatch, mcps={"panel": project.SLOTTED})
    monkeypatch.delenv(project.SLOT_VARIABLE, raising=False)
    project.target(tmp_path, monkeypatch)

    code, output = project.run(capsys, "install", "--mcp", "panel", "--runtime", "vscode")

    assert code == 0
    assert "not set here" not in project.joined(output)
    assert project.SLOT_VARIABLE not in project.joined(output)


def test_a_line_that_lands_in_both_kinds_of_document_still_names_the_variable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """One target reads the environment, so the warning stands for the whole line.

    The suppression above is about a plan where *nothing* will ever look the
    variable up. Name Claude Code alongside VS Code and one of the two documents
    really does read it — so silence would be the false half this time.
    """
    # given
    project.catalog_of(tmp_path, monkeypatch, mcps={"panel": project.SLOTTED})
    monkeypatch.delenv(project.SLOT_VARIABLE, raising=False)
    project.target(tmp_path, monkeypatch)

    code, output = project.run(
        capsys, "install", "--mcp", "panel", "--runtime", "claude-code,vscode"
    )

    assert code == 0
    assert "not set here" in project.joined(output)
    assert project.SLOT_VARIABLE in project.joined(output)


def test_a_graft_only_runtime_receives_the_server_and_skips_the_skill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """Issue #100: `vscode` renders MCP and reads no skills, and keeps the half it can serve.

    A runtime with a row on one of the two tables a mixed line carries is not
    stranded by the other lacking a row for it — `vscode` gets the server, the
    skill is skipped, and the screen names it instead of the whole line dying
    for `vscode`'s gap on the other axis.
    """
    # given
    project.catalog_of(tmp_path, monkeypatch, "alpha", mcps={"panel": project.SLOTTED})
    root = project.target(tmp_path, monkeypatch)

    code, output = project.run(
        capsys, "install", "--skill", "alpha", "--mcp", "panel", "--runtime", "vscode"
    )

    assert code == 0
    assert (root / ".vscode" / "mcp.json").is_file()
    assert list(root.iterdir()) == [root / ".vscode"]
    assert "no skills destination" in project.joined(output)


def test_a_target_with_no_documented_gate_gets_no_warning_invented_for_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """ADR 0014 makes the warning a requirement **where it is true**, and no wider.

    The vendor documents no approval step for `.devin/mcp_config.json`, and the
    research says in as many words that *absence in the documentation is not an
    assertion of absence* — Codex did not document `trust_level` either. Since
    written, that slice moved from doc-grade to measured: `devin mcp
    list`/`get`/`add` read and write the project file with no login and no
    trust prompt, in a directory the binary had never seen before
    (`docs/research/mcp-config-formats.md` § Medição 2026-08-14). Whether a gate
    exists further downstream, at the point a live session spawns the server
    process, stayed unmeasured — that path requires an account. So the honest
    move is still neither warning nor reassurance: the product says what it
    knows, and about this target it knows only that it wrote the file.

    A warning printed here anyway would be a fact asserted about a runtime nobody
    ran, and it would spend the credibility of the line that is measured next
    door — *"a warning that appears everywhere is a warning nobody reads"*.
    """
    # given
    project.catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": MCP_URL})
    root = project.target(tmp_path, monkeypatch)

    code, output = project.run(capsys, "install", "--mcp", "cloudflare", "--runtime", "devin")

    assert code == 0
    assert "pending approval" not in project.joined(output)
    assert (root / ".devin" / "mcp_config.json").is_file()


def test_one_line_over_two_targets_warns_only_for_the_one_that_is_born_pending(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The warning is a fact of the pair, not of the run — and now there is a run that shows it.

    Both documents are written, both are named on the plan, and exactly one of
    them is named **by the warning**. A warning attached to the command rather
    than to the pair would carry both paths and send the reader looking for a gate
    that is not documented to exist.

    So the assertion is on the sentence and not on the path: `mcp_config.json`
    appears on this screen, as a destination, which is exactly right.
    """
    # given
    project.catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": MCP_URL})
    root = project.target(tmp_path, monkeypatch)

    code, output = project.run(
        capsys, "install", "--mcp", "cloudflare", "--runtime", "claude-code,devin"
    )

    assert code == 0
    joined = project.joined(output)
    warned = "is written, and the server does not connect"
    assert ".devin/mcp_config.json" in joined
    assert f".mcp.json {warned}" in joined
    assert f"mcp_config.json {warned}" not in joined
    assert (root / ".devin" / "mcp_config.json").is_file()


MACHINE_FILE_NAMES = {
    "claude-code": ".claude.json",
    "vscode": "mcp.json",
    "devin": "mcp_config.json",
}
"""The file name each target reads on the machine — the directory is per system.

The name and not the whole path, because the path is what
`tests/test_runtimes.py` asserts across all nine cells; here the question is
whether the CLI landed in the machine document at all rather than in the
project one, and the two never share a name.
"""


@pytest.mark.parametrize(
    ("key", "document"), MACHINE_FILE_NAMES.items(), ids=list(MACHINE_FILE_NAMES)
)
def test_a_machine_scope_graft_lands_in_the_personal_file_of_its_target(
    key: str, document: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """`--global` writes the user's own file for each of the three targets (#81).

    The repository is asserted empty in the same breath: a machine install that
    also touched the tree would be the divergence between what the screen says
    and what lands that ADR 0008 exists to refuse.
    """
    # given
    project.catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": MCP_URL})
    root = project.target(tmp_path, monkeypatch)

    code, output = project.run(
        capsys, "install", "--mcp", "cloudflare", "--runtime", key, "--global"
    )

    assert code == 0
    assert document in project.joined(output)
    written = [path for path in tmp_path.rglob(document) if path.is_file()]
    assert len(written) == 1
    assert "cloudflare" in written[0].read_text(encoding="utf-8")
    assert list(root.iterdir()) == []


@pytest.mark.parametrize("key", MACHINE_FILE_NAMES, ids=list(MACHINE_FILE_NAMES))
def test_a_machine_scope_graft_says_nothing_about_pending_approval(
    key: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The server in the personal file is the user's own, so nothing waits (#81).

    The exact inverse of the project-scope Claude Code case above, and it falls
    out of the table rather than out of a branch in the CLI: `born_pending` is a
    column of the pair (runtime, scope), and `pending_activation` reads the same
    row that decided the file.
    """
    # given
    project.catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": MCP_URL})
    project.target(tmp_path, monkeypatch)

    code, output = project.run(
        capsys, "install", "--mcp", "cloudflare", "--runtime", key, "--global"
    )

    assert code == 0
    assert "pending approval" not in project.joined(output)


PERSONAL_FILE = """\
{
  "userID": "97e2a3c0",
  "machineID": "b41f",
  "hasCompletedOnboarding": true,
  "theme": "dark"
}
"""
"""A `~/.claude.json` shaped like the real one: identity, onboarding, preferences.

Two spaces of indent and a trailing newline, so the assertion covers formatting
and not only content — the additive diff of ADR 0016 is what has to survive here.
"""


def test_a_machine_graft_touches_nothing_else_in_the_personal_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """#81: `~/.claude.json` carries the user's identity, and a graft is additive.

    Asserted as *"every byte before the closing brace survives verbatim"* rather
    than as a set of key lookups: what a re-serialising writer destroys first is
    the shape — indentation, key order, the trailing newline — and a reader that
    parsed both sides back into dicts would call that a pass. The single
    permitted change is the comma JSON requires after what used to be the last
    entry.
    """
    # given
    project.catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": MCP_URL})
    project.target(tmp_path, monkeypatch)
    personal = tmp_path / ".claude.json"
    personal.write_text(PERSONAL_FILE, encoding="utf-8")

    code, _ = project.run(
        capsys, "install", "--mcp", "cloudflare", "--runtime", "claude-code", "--global"
    )

    assert code == 0
    after = personal.read_text(encoding="utf-8")
    untouched = PERSONAL_FILE[: PERSONAL_FILE.index("\n}")]
    assert after.startswith(untouched + ",\n")
    assert '"mcpServers"' in after
    assert "cloudflare" in after
    assert after.endswith("}\n")


def test_the_dry_run_of_a_graft_names_the_key_and_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """A report that named different keys from the run it describes is worth nothing."""
    # given
    project.catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": MCP_URL})
    root = project.target(tmp_path, monkeypatch)

    code, output = project.run(
        capsys, "install", "--mcp", "cloudflare", "--runtime", "claude-code", "--dry-run"
    )

    assert code == 0
    assert "mcpServers.cloudflare" in project.joined(output)
    assert list(root.iterdir()) == []


def test_an_mcp_name_outside_the_catalog_exits_two(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """A typo is the caller's defect, and the closed list is small enough to print."""
    # given
    project.catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": MCP_URL})
    root = project.target(tmp_path, monkeypatch)

    code, output = project.run(capsys, "install", "--mcp", "cloudfare", "--runtime", "claude-code")

    assert code == 2
    assert "cloudflare" in project.joined(output)
    assert list(root.iterdir()) == []


def test_from_with_an_ai_framework_is_the_one_unit_that_stays_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The last unit off the list, and it is a decision rather than an adjournment.

    `--mcp` joined `--skill` in #83 and `--bundle` in #137; an AI Framework does
    not follow, because it stopped being a unit that *could*. It is a folder of
    the overpower's own wheel, so there is nothing in a third-party repository
    for the flag to name — which is why the message says the unit does not exist
    remotely rather than promising a later ticket.

    Refused for the *line*, so it needs neither a git repository nor a network to
    be told.
    """
    # given
    project.catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": MCP_URL})
    project.target(tmp_path, monkeypatch)

    code, output = project.run(
        capsys,
        *("install", "--from", "https://github.com/owner/repo"),
        *("--ai-framework", "matt-pocock", "--runtime", "claude-code"),
    )

    assert code == 2
    assert "--ai-framework" in project.joined(output)
    assert "does not exist" in project.joined(output)


def test_a_line_that_mixes_a_skill_and_a_server_writes_both(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The line is the manifest, and the manifest cannot be two lines."""
    # given
    project.catalog_of(tmp_path, monkeypatch, "alpha", mcps={"cloudflare": MCP_URL})
    root = project.target(tmp_path, monkeypatch)

    code, _ = project.run(
        capsys,
        *("install", "--skill", "alpha", "--mcp", "cloudflare"),
        *("--runtime", "claude-code"),
    )

    assert code == 0
    assert (root / project.CLAUDE / "alpha" / "SKILL.md").is_file()
    assert "mcpServers.cloudflare" in project.document_keys(root / ".mcp.json")


# --------------------------------------------------------------------------- #
# #84: [source] clones code to the machine, and restricts the scope
# --------------------------------------------------------------------------- #

SOURCED = """\
description = "A server with code of its own."
transport = "stdio"

[source]
url = "https://github.com/example/homegrown-mcp"

[server]
command = "uv"
args = ["run", "--project", "{source}", "server.py"]
"""


def test_a_sourced_recipe_clones_to_the_machine_and_resolves_the_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """#84: the clone lands under `--global`, and `{source}` points at where it landed."""
    # given
    project.catalog_of(tmp_path, monkeypatch)
    project.custom_recipe(tmp_path, "homegrown", SOURCED)
    home = tmp_path / "home"
    project.at_home(monkeypatch, home)
    monkeypatch.setattr(cli, "_out", project.pinned(tty=False))
    local = git_remote.build(tmp_path / "origin", {"server.py": "print('hi')\n"})
    monkeypatch.setattr(remote, "fetch_with_git", git_remote.instead_of_github(local))

    code, _ = project.run(
        capsys, "install", "--mcp", "homegrown", "--runtime", "claude-code", "--global"
    )

    assert code == 0
    destination = home / ".overpower" / "mcp" / "homegrown"
    assert (destination / "server.py").read_text(encoding="utf-8") == "print('hi')\n"
    document = project.parsed(home / ".claude.json")
    assert document["mcpServers"] == {
        "homegrown": {
            "type": "stdio",
            "command": "uv",
            "args": ["run", "--project", str(destination), "server.py"],
        }
    }


def test_a_clone_and_a_graft_are_two_writes_because_they_are_two_places(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The half that fixes the unit, from #75: *"a federated MCP costs two writes"*.

    Collapsing a server and its prompt into one write and collapsing *everything*
    into one are the same edit if nobody asserts the difference. Here the two
    writes land in two different places — a folder on the machine and a key in a
    document — so nothing collapses, and the count stays two.

    That is also why this line settles which unit the spec meant and the
    federated case alone could not: two landings **and** two write objects agree
    on 2, so it reads the same under either. The VS Code pair is the case where
    they disagree.
    """
    # given
    project.catalog_of(tmp_path, monkeypatch)
    project.custom_recipe(tmp_path, "homegrown", SOURCED)
    home = tmp_path / "home"
    project.at_home(monkeypatch, home)
    monkeypatch.setattr(cli, "_out", project.pinned(tty=False))
    local = git_remote.build(tmp_path / "origin", {"server.py": "print('hi')\n"})
    monkeypatch.setattr(remote, "fetch_with_git", git_remote.instead_of_github(local))

    code, output = project.run(
        capsys, "install", "--mcp", "homegrown", "--runtime", "claude-code", "--global"
    )

    assert code == 0
    assert "2 writes" in project.joined(output)


def test_a_sourced_recipe_in_project_scope_is_refused_naming_the_fix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """ADR 0015: the absolute path of the clone must not enter a committed manifest.

    Refused before any obtention, since the answer is already known from the
    scope alone — the assertion on `called` is what proves that, not just the
    exit code.
    """
    # given
    project.catalog_of(tmp_path, monkeypatch)
    project.custom_recipe(tmp_path, "homegrown", SOURCED)
    root = project.target(tmp_path, monkeypatch)
    called: list[str] = []

    def fetch(url: str, _ref: str, into: Path) -> Path:
        called.append(url)
        return into

    monkeypatch.setattr(remote, "fetch_with_git", fetch)

    code, output = project.run(capsys, "install", "--mcp", "homegrown", "--runtime", "claude-code")

    assert code == 3
    joined = project.joined(output)
    assert "homegrown" in joined
    assert "--global" in joined
    assert list(root.iterdir()) == []
    assert called == []


def test_a_dry_run_obtains_the_clone_but_lands_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The same promise `--from` makes: a dry run resolves exactly what the real run would."""
    # given
    project.catalog_of(tmp_path, monkeypatch)
    project.custom_recipe(tmp_path, "homegrown", SOURCED)
    home = tmp_path / "home"
    project.at_home(monkeypatch, home)
    monkeypatch.setattr(cli, "_out", project.pinned(tty=False))
    obtained: list[str] = []
    planted = git_remote.planting({"server.py": "print('hi')\n"})

    def fetch(url: str, ref: str, into: Path) -> Path:
        obtained.append(url)
        return planted(url, ref, into)

    monkeypatch.setattr(remote, "fetch_with_git", fetch)

    code, output = project.run(
        capsys,
        "install",
        "--mcp",
        "homegrown",
        "--runtime",
        "claude-code",
        "--global",
        "--dry-run",
    )

    assert code == 0
    assert obtained
    assert "homegrown" in project.joined(output)
    assert not (home / ".overpower" / "mcp" / "homegrown").exists()
    assert not (home / ".claude.json").exists()


def test_reinstalling_a_sourced_recipe_re_clones_without_force(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """ADR 0015: re-cloned unconditionally — the existing-destination gate never asks."""
    # given
    project.catalog_of(tmp_path, monkeypatch)
    project.custom_recipe(tmp_path, "homegrown", SOURCED)
    home = tmp_path / "home"
    project.at_home(monkeypatch, home)
    monkeypatch.setattr(cli, "_out", project.pinned(tty=False))
    local = git_remote.build(tmp_path / "origin", {"server.py": "print('hi')\n"})
    monkeypatch.setattr(remote, "fetch_with_git", git_remote.instead_of_github(local))
    selectors = ("install", "--mcp", "homegrown", "--runtime", "claude-code", "--global")

    first_code, _ = project.run(capsys, *selectors)
    second_code, _ = project.run(capsys, *selectors)

    assert first_code == 0
    assert second_code == 0
    assert (home / ".overpower" / "mcp" / "homegrown" / "server.py").is_file()


# --------------------------------------------------------------------------- #
# #97: the validation boundary moves up — before the wizard's first screen
# --------------------------------------------------------------------------- #


def test_a_line_with_skill_and_mcp_without_runtime_exits_two(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """Two classes, no `--runtime` to split them: name the runtimes, or split the line."""
    # given
    project.catalog_of(tmp_path, monkeypatch, "alpha", mcps={"cloudflare": MCP_URL})
    root = project.target(tmp_path, monkeypatch)

    code, output = project.run(capsys, "install", "--skill", "alpha", "--mcp", "cloudflare")

    assert code == 2
    joined = project.joined(output)
    assert "--runtime" in joined
    assert "separate" in joined
    assert list(root.iterdir()) == []


def test_a_line_with_skill_and_mcp_without_runtime_in_a_terminal_never_opens_the_wizard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The same refusal, and in a terminal it fires before any screen is drawn (#97).

    Absence of the banner is the seam: a terminal session that reached
    `run_wizard` would have printed it first (`_print_banner()` runs before the
    wizard opens), so its absence is what proves no screen was drawn — the same
    assertion `test_the_banner_is_suppressed_without_a_tty` makes for the pipe
    case. `run_wizard` is stubbed to fail loudly besides, so a refusal that
    slipped would not hang the suite on a prompt with no real terminal behind it.
    """
    # given
    project.catalog_of(tmp_path, monkeypatch, "alpha", mcps={"cloudflare": MCP_URL})
    project.target(tmp_path, monkeypatch)
    project.terminal(monkeypatch)
    monkeypatch.setattr(cli, "run_wizard", _never_called)

    code, output = project.run(capsys, "install", "--skill", "alpha", "--mcp", "cloudflare")

    assert code == 2
    assert "_____" not in output
    assert "--runtime" in project.joined(output)


def test_an_mcp_name_outside_the_catalog_in_a_terminal_exits_two_before_the_wizard_opens(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The same typo the flag path already caught, now caught before the wizard asks anything.

    Absence of the banner is the seam, for the reason the sibling test above
    gives; `run_wizard` is stubbed besides, so a refusal that slipped fails
    loudly instead of hanging on a prompt with no real terminal behind it.
    """
    # given
    project.catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": MCP_URL})
    root = project.target(tmp_path, monkeypatch)
    project.terminal(monkeypatch)
    monkeypatch.setattr(cli, "run_wizard", _never_called)

    code, output = project.run(capsys, "install", "--mcp", "cloudfare")

    assert code == 2
    assert "_____" not in output
    assert "cloudflare" in project.joined(output)
    assert list(root.iterdir()) == []


def test_an_mcp_name_that_is_actually_a_skill_says_which_flag_serves(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """A closer typo than *unknown*: the name is real, just filed under another flag."""
    # given
    project.catalog_of(tmp_path, monkeypatch, "alpha", mcps={"cloudflare": MCP_URL})
    root = project.target(tmp_path, monkeypatch)

    code, output = project.run(capsys, "install", "--mcp", "alpha", "--runtime", "claude-code")

    assert code == 2
    joined = project.joined(output)
    assert "alpha" in joined
    assert "--skill" in joined
    assert list(root.iterdir()) == []


def test_install_mcp_without_runtime_in_a_terminal_writes_and_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The acceptance criterion #97 exists for: the wizard covers the graft class too."""
    # given
    project.catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": MCP_URL})
    root = project.target(tmp_path, monkeypatch)
    project.terminal(monkeypatch)
    request = Request(mcps=("cloudflare",), runtimes=("claude-code",), scope=Scope.PROJECT)
    monkeypatch.setattr(cli, "run_wizard", _stub_wizard(request, root))

    code, _ = project.run(capsys, "install", "--mcp", "cloudflare", "--yes")

    assert code == 0
    assert (root / ".mcp.json").is_file()


def test_install_mcp_without_runtime_in_a_terminal_writes_and_exits_zero_in_global_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The same acceptance criterion, the other scope."""
    # given
    project.catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": MCP_URL})
    root = project.target(tmp_path, monkeypatch)
    project.terminal(monkeypatch)
    request = Request(mcps=("cloudflare",), runtimes=("claude-code",), scope=Scope.GLOBAL)
    monkeypatch.setattr(cli, "run_wizard", _stub_wizard(request, tmp_path))

    code, _ = project.run(capsys, "install", "--mcp", "cloudflare", "--global", "--yes")

    assert code == 0
    assert (tmp_path / ".claude.json").is_file()
    assert list(root.iterdir()) == []


def test_a_slot_whose_variable_is_not_set_warns_and_still_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The variable has to exist when the runtime starts, not when the overpower runs.

    So it is a warning and not a refusal: the file is correct, and the person may
    well export the variable afterwards — or have it in the editor's environment
    and not in this shell, which is an environment we cannot see from here.

    It is a warning and not silence because of what Claude Code does with an
    absent variable: measured against a local listener, `Bearer ${NAO_EXISTE}`
    went out **literally** on the request, so the server answers 401 and the
    cause is nowhere near.
    """
    # given
    project.catalog_of(tmp_path, monkeypatch, mcps={"coolify": project.SLOTTED})
    root = project.target(tmp_path, monkeypatch)
    monkeypatch.delenv(project.SLOT_VARIABLE, raising=False)

    code, output = project.run(capsys, "install", "--mcp", "coolify", "--runtime", "claude-code")

    assert code == 0
    joined = project.joined(output)
    assert project.SLOT_VARIABLE in joined
    assert "not set" in joined
    assert (root / ".mcp.json").is_file()


def test_a_slot_whose_variable_is_set_is_not_warned_about(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """A warning that appears when there is nothing to fix is a warning nobody reads."""
    # given
    project.catalog_of(tmp_path, monkeypatch, mcps={"coolify": project.SLOTTED})
    project.target(tmp_path, monkeypatch)
    monkeypatch.setenv(project.SLOT_VARIABLE, "SUPER-SECRET-42")

    code, output = project.run(capsys, "install", "--mcp", "coolify", "--runtime", "claude-code")

    assert code == 0
    joined = project.joined(output)
    assert "not set" not in joined
    assert "SUPER-SECRET-42" not in joined


def test_the_dry_run_warns_about_the_same_variable_the_real_run_does(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """`--dry-run` resolves everything, so it knows this before anything is written."""
    # given
    project.catalog_of(tmp_path, monkeypatch, mcps={"github": project.BEARER})
    root = project.target(tmp_path, monkeypatch)
    monkeypatch.delenv(project.SLOT_VARIABLE, raising=False)

    code, output = project.run(
        capsys, "install", "--mcp", "github", "--runtime", "claude-code", "--dry-run"
    )

    assert code == 0
    assert project.SLOT_VARIABLE in project.joined(output)
    assert list(root.iterdir()) == []


def test_a_run_with_no_slot_to_fill_says_nothing_about_a_variable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """Cloudflare authorises in the browser: there is no variable, so there is no line."""
    # given
    project.catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": MCP_URL})
    project.target(tmp_path, monkeypatch)

    code, output = project.run(capsys, "install", "--mcp", "cloudflare", "--runtime", "claude-code")

    assert code == 0
    assert "not set" not in project.joined(output)


# --------------------------------------------------------------------------- #
# #82: preconditions — a closed vocabulary, checked, never run
# --------------------------------------------------------------------------- #

PRECONDITION_VARIABLE = "OP_PRECONDITION_VAR"


def _precondition_recipe(check: str, value: str, *, instructions: str | None = None) -> str:
    """A minimal stdio recipe carrying one `[[preconditions]]` entry.

    `value` is a TOML **literal** string (single-quoted): a Windows path
    carries backslashes, and a basic string would read those as escapes.
    """
    lines: list[str] = []
    if instructions is not None:
        lines.append(f'instructions = "{instructions}"')
    lines += [
        'description = "A server with a precondition."',
        'transport = "stdio"',
        "",
        "[server]",
        'command = "uvx"',
        "",
        "[[preconditions]]",
        f'check = "{check}"',
        f"value = '{value}'",
        "",
    ]
    return "\n".join(lines)


def test_a_failed_precondition_refuses_before_the_first_byte_naming_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """Exit **3**: the invocation was correct, and this machine does not meet it."""
    # given
    project.catalog_of(tmp_path, monkeypatch)
    root = project.target(tmp_path, monkeypatch)
    project.custom_recipe(
        tmp_path, "toolserver", _precondition_recipe("env_set", PRECONDITION_VARIABLE)
    )
    monkeypatch.delenv(PRECONDITION_VARIABLE, raising=False)

    code, output = project.run(capsys, "install", "--mcp", "toolserver", "--runtime", "claude-code")

    assert code == 3
    joined = project.joined(output)
    assert PRECONDITION_VARIABLE in joined
    assert "toolserver" in joined
    assert list(root.iterdir()) == []


def test_an_env_set_precondition_that_is_met_installs_normally(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    # given
    project.catalog_of(tmp_path, monkeypatch)
    root = project.target(tmp_path, monkeypatch)
    project.custom_recipe(
        tmp_path, "toolserver", _precondition_recipe("env_set", PRECONDITION_VARIABLE)
    )
    monkeypatch.setenv(PRECONDITION_VARIABLE, "1")

    code, _ = project.run(capsys, "install", "--mcp", "toolserver", "--runtime", "claude-code")

    assert code == 0
    assert (root / ".mcp.json").is_file()


def test_a_path_exists_precondition_that_is_unmet_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    # given
    project.catalog_of(tmp_path, monkeypatch)
    root = project.target(tmp_path, monkeypatch)
    missing = tmp_path / "does-not-exist"
    project.custom_recipe(tmp_path, "toolserver", _precondition_recipe("path_exists", str(missing)))

    code, output = project.run(capsys, "install", "--mcp", "toolserver", "--runtime", "claude-code")

    assert code == 3
    # Not the full path: `tmp_path` runs long enough on some CI runners (macOS,
    # Windows) that the panel folds it mid-character, and `project.joined`
    # reconstructs a fold as a space — corrupting an unbroken path substring.
    joined = project.joined(output)
    assert missing.name in joined
    assert "path_exists" in joined
    assert list(root.iterdir()) == []


def test_a_path_exists_precondition_that_is_met_installs_normally(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    # given
    project.catalog_of(tmp_path, monkeypatch)
    root = project.target(tmp_path, monkeypatch)
    present = tmp_path / "socket"
    present.write_text("", encoding="utf-8")
    project.custom_recipe(tmp_path, "toolserver", _precondition_recipe("path_exists", str(present)))

    code, _ = project.run(capsys, "install", "--mcp", "toolserver", "--runtime", "claude-code")

    assert code == 0
    assert (root / ".mcp.json").is_file()


def test_a_command_exists_precondition_that_is_met_installs_normally(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """`sys.executable` is the one binary every test run is guaranteed to have."""
    # given
    project.catalog_of(tmp_path, monkeypatch)
    root = project.target(tmp_path, monkeypatch)
    executable = Path(sys.executable)
    monkeypatch.setenv("PATH", f"{executable.parent}{os.pathsep}{os.environ.get('PATH', '')}")
    project.custom_recipe(
        tmp_path, "toolserver", _precondition_recipe("command_exists", executable.name)
    )

    code, _ = project.run(capsys, "install", "--mcp", "toolserver", "--runtime", "claude-code")

    assert code == 0
    assert (root / ".mcp.json").is_file()


def test_the_dry_run_of_a_failed_precondition_mirrors_the_exit_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """`--dry-run` checks preconditions too, or it is a report about a different run."""
    # given
    project.catalog_of(tmp_path, monkeypatch)
    root = project.target(tmp_path, monkeypatch)
    project.custom_recipe(
        tmp_path, "toolserver", _precondition_recipe("env_set", PRECONDITION_VARIABLE)
    )
    monkeypatch.delenv(PRECONDITION_VARIABLE, raising=False)
    selectors = ("install", "--mcp", "toolserver", "--runtime", "claude-code")

    dry_code, _ = project.run(capsys, *selectors, "--dry-run")
    real_code, _ = project.run(capsys, *selectors)

    assert dry_code == real_code == 3
    assert list(root.iterdir()) == []


def test_the_plan_prints_the_recipes_prose_instructions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """What the overpower cannot automate — printed where the human still reads."""
    # given
    project.catalog_of(tmp_path, monkeypatch)
    project.target(tmp_path, monkeypatch)
    project.custom_recipe(
        tmp_path,
        "toolserver",
        _precondition_recipe(
            "env_set", PRECONDITION_VARIABLE, instructions="ask the platform team for the token"
        ),
    )
    monkeypatch.setenv(PRECONDITION_VARIABLE, "1")

    code, output = project.run(
        capsys, "install", "--mcp", "toolserver", "--runtime", "claude-code", "--dry-run"
    )

    assert code == 0
    assert "ask the platform team for the token" in project.joined(output)


def test_the_real_run_prints_instructions_too_before_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """Not only the report — the same line reads them before the write happens."""
    # given
    project.catalog_of(tmp_path, monkeypatch)
    project.target(tmp_path, monkeypatch)
    project.custom_recipe(
        tmp_path,
        "toolserver",
        _precondition_recipe(
            "env_set", PRECONDITION_VARIABLE, instructions="ask the platform team for the token"
        ),
    )
    monkeypatch.setenv(PRECONDITION_VARIABLE, "1")

    code, output = project.run(capsys, "install", "--mcp", "toolserver", "--runtime", "claude-code")

    assert code == 0
    assert "ask the platform team for the token" in project.joined(output)


def test_a_malicious_precondition_value_is_never_executed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """Asserted, not promised: `command_exists` walks `PATH`, it never runs a shell.

    A `;` and a second command in the value are what a script-injection attempt
    through this field would look like. `shutil.which` treats the whole string
    as one literal filename, so refusal happens for the ordinary reason — no
    file has that name — and nothing beside it ever runs.
    """
    # given
    project.catalog_of(tmp_path, monkeypatch)
    root = project.target(tmp_path, monkeypatch)
    marker = tmp_path / "pwned"
    project.custom_recipe(
        tmp_path, "toolserver", _precondition_recipe("command_exists", f"true; touch {marker}")
    )

    code, _ = project.run(capsys, "install", "--mcp", "toolserver", "--runtime", "claude-code")

    assert code == 3
    assert not marker.exists()
    assert list(root.iterdir()) == []


# --------------------------------------------------------------------------- #
# #40: the default scope needs a git repository, and --global does not
# --------------------------------------------------------------------------- #


def test_inside_a_git_repository_no_flag_lands_in_the_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """`project.target` puts a `.git` above `root`: the ordinary case."""
    # given
    project.catalog_of(tmp_path, monkeypatch, "alpha")
    root = project.target(tmp_path, monkeypatch)

    code, _ = project.run(
        capsys, "install", "--skill", "alpha", "--runtime", "claude-code", "--yes"
    )

    assert code == 0
    assert (root / project.CLAUDE / "alpha" / "SKILL.md").is_file()


def test_outside_a_git_repository_no_scope_exits_two_and_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """Axiom 2 — the git is the manifest — only holds where there is git."""
    # given
    project.catalog_of(tmp_path, monkeypatch, "alpha")
    bare = tmp_path / "no-repo-here"
    bare.mkdir()
    monkeypatch.chdir(bare)
    monkeypatch.setenv("HOME", str(tmp_path / "unused-home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "unused-home"))
    monkeypatch.setattr(cli, "_out", project.pinned(tty=False))

    code, output = project.run(capsys, "install", "--skill", "alpha", "--runtime", "claude-code")

    assert code == 2
    assert "--global" in project.joined(output)
    assert list(bare.iterdir()) == []


def test_outside_a_git_repository_a_graft_exits_two_as_well(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The check is about the scope, not about the class — asserted, not assumed (#81).

    The graft class gained a machine destination, and the reflex reading of that
    is *"then it no longer needs a repository"*. It does: `--global` is what
    names the machine, and a line without it is still a project-scope line, whose
    root is a repository that is not there. Exit **2** and not 3 — nothing is
    wrong with what was asked, only with where it was asked from.
    """
    # given
    project.catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": MCP_URL})
    bare = tmp_path / "no-repo-here"
    bare.mkdir()
    monkeypatch.chdir(bare)
    monkeypatch.setenv("HOME", str(tmp_path / "unused-home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "unused-home"))
    monkeypatch.setattr(cli, "_out", project.pinned(tty=False))

    code, output = project.run(capsys, "install", "--mcp", "cloudflare", "--runtime", "claude-code")

    assert code == 2
    assert "--global" in project.joined(output)
    assert list(bare.iterdir()) == []
    assert not (tmp_path / "unused-home").exists()


def test_global_needs_no_git_repository_at_all(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """`--global` names the machine, which settles the question the git check asks."""
    # given
    project.catalog_of(tmp_path, monkeypatch, "alpha")
    home = tmp_path / "home"
    home.mkdir()
    bare = tmp_path / "no-repo-here"
    bare.mkdir()
    monkeypatch.chdir(bare)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setattr(cli, "_out", project.pinned(tty=False))

    code, _ = project.run(
        capsys, "install", "--skill", "alpha", "--runtime", "claude-code", "--global", "--yes"
    )

    assert code == 0
    assert (home / project.CLAUDE / "alpha" / "SKILL.md").is_file()


# --------------------------------------------------------------------------- #
# #41: install pelado (no artifact selector) opens the wizard in a terminal
# --------------------------------------------------------------------------- #


def _stub_wizard(filled: Request, root: Path) -> Wizard:
    """A `run_wizard` replacement that fills the gaps and touches nothing else.

    It `replace`s rather than returning `filled` whole, and that mirrors the
    contract instead of merely satisfying it: `--dry-run`, `--force` and `--yes`
    are not wizard steps, so they arrive inside the request the wizard is handed
    and leave inside the request it answers.

    Named and explicitly typed rather than a lambda closing over `filled` and
    `root`: `pytest.MonkeyPatch.setattr`'s string-keyed overload types `value`
    as `object`, so an unannotated lambda parameter stays `Unknown` under
    `pyright --strict` with nothing to infer it from.
    """

    def wizard(
        asked: Request,
        _catalog: Catalog | None,
        _environment: Environment,
        _cwd: Path,
        _scoped: tuple[Scope, Path] | None,
        *,
        console: Console,  # noqa: ARG001 — the seam takes it; this stub narrates nothing
    ) -> tuple[Request, Path]:
        return (
            replace(
                asked,
                ai_frameworks=filled.ai_frameworks,
                bundles=filled.bundles,
                skills=filled.skills,
                mcps=filled.mcps,
                runtimes=filled.runtimes,
                scope=filled.scope,
            ),
            root,
        )

    return wizard


def _wizard_steps(
    monkeypatch: pytest.MonkeyPatch,
    *,
    scope: Scope = Scope.PROJECT,
    runtimes: tuple[str, ...] = ("claude-code",),
) -> list[str]:
    """Stub the four seams of the wizard and record, in order, which ones opened.

    The seams and not `run_wizard`: what this ticket decides is *which steps a
    line opens*, and a stub of the whole wizard cannot see that.
    """
    opened: list[str] = []

    def ask_artifacts(
        _catalog: Catalog,
    ) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
        opened.append("artifacts")
        return ((), (), ("alpha",), ())

    def ask_scope(
        cwd: Path, environment: Environment, _console: Console, *, sourced: bool = False
    ) -> tuple[Scope, Path]:
        del sourced
        opened.append("scope")
        return scope, (cwd if scope is Scope.PROJECT else environment.home)

    def ask_runtimes(_scope: Scope, _root: Path, _environment: Environment) -> tuple[str, ...]:
        opened.append("runtimes")
        return runtimes

    def ask_mcp_runtimes(_scope: Scope, _root: Path, _environment: Environment) -> tuple[str, ...]:
        opened.append("mcp_runtimes")
        return runtimes

    monkeypatch.setattr(wizard, "ask_artifacts", ask_artifacts)
    monkeypatch.setattr(wizard, "ask_scope", ask_scope)
    monkeypatch.setattr(wizard, "ask_runtimes", ask_runtimes)
    monkeypatch.setattr(wizard, "ask_mcp_runtimes", ask_mcp_runtimes)
    return opened


def _never_called(*_args: object, **_kwargs: object) -> object:
    message = "the wizard must not run here"
    raise AssertionError(message)


def test_a_bare_install_in_a_terminal_calls_the_wizard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """`install` pelado com TTY abre o wizard: the wizard's `Request` drives the same flow."""
    # given
    project.catalog_of(tmp_path, monkeypatch, "alpha")
    root = project.target(tmp_path, monkeypatch)
    project.terminal(monkeypatch)
    request = Request(skills=("alpha",), runtimes=("claude-code",), scope=Scope.PROJECT)
    monkeypatch.setattr(cli, "run_wizard", _stub_wizard(request, root))

    code, _ = project.run(capsys, "install", "--yes")

    assert code == 0
    assert (root / project.CLAUDE / "alpha" / "SKILL.md").is_file()


def test_a_bare_install_without_a_terminal_never_touches_the_wizard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """Without a TTY the bare invocation still reaches `NothingSelectedError` — exit 2, no hang."""
    # given
    project.catalog_of(tmp_path, monkeypatch, "alpha")
    project.target(tmp_path, monkeypatch)  # tty=False by default
    monkeypatch.setattr(cli, "run_wizard", _never_called)

    code, output = project.run(capsys, "install")

    assert code == 2
    assert "nothing to install" in project.joined(output)


def test_flags_given_in_a_terminal_do_not_open_the_wizard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """A selector on the line is not a bare invocation, even from a terminal."""
    # given
    project.catalog_of(tmp_path, monkeypatch, "alpha")
    root = project.target(tmp_path, monkeypatch)
    project.terminal(monkeypatch)
    monkeypatch.setattr(cli, "run_wizard", _never_called)

    code, _ = project.run(
        capsys, "install", "--skill", "alpha", "--runtime", "claude-code", "--yes"
    )

    assert code == 0
    assert (root / project.CLAUDE / "alpha" / "SKILL.md").is_file()


def test_the_wizard_being_abandoned_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """Backing out of the wizard is the same shape as declining the confirmation."""

    def abandoned(
        _asked: Request,
        _catalog: Catalog | None,
        _environment: Environment,
        _cwd: Path,
        _scoped: tuple[Scope, Path] | None,
        *,
        console: Console,  # noqa: ARG001 — the seam takes it; backing out narrates nothing
    ) -> None:
        return None

    # given
    project.catalog_of(tmp_path, monkeypatch, "alpha")
    root = project.target(tmp_path, monkeypatch)
    project.terminal(monkeypatch)
    monkeypatch.setattr(cli, "run_wizard", abandoned)

    code, output = project.run(capsys, "install")

    assert code == 1
    assert "nothing was written" in project.joined(output)
    assert list(root.iterdir()) == []


def test_the_wizard_request_still_takes_its_mode_flags_from_the_command_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """`--dry-run`, `--force` and `--yes` are not wizard steps — they pass through unchanged."""
    # given
    project.catalog_of(tmp_path, monkeypatch, "alpha")
    root = project.target(tmp_path, monkeypatch)
    project.terminal(monkeypatch)
    request = Request(skills=("alpha",), runtimes=("claude-code",), scope=Scope.PROJECT)
    monkeypatch.setattr(cli, "run_wizard", _stub_wizard(request, root))

    code, output = project.run(capsys, "install", "--dry-run")

    assert code == 0
    assert "dry run" in project.joined(output)
    assert list(root.iterdir()) == []


# --------------------------------------------------------------------------- #
# #57: the trigger is the gap, and the wizard opens only what the flags left open
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("argv", "opened"),
    [
        pytest.param(("install",), ["artifacts", "scope", "runtimes"], id="bare"),
        pytest.param(
            ("install", "--skill", "alpha"), ["scope", "runtimes"], id="no runtime on the line"
        ),
        pytest.param(
            ("install", "--runtime", "claude-code"), ["artifacts"], id="no selection on the line"
        ),
        pytest.param(
            ("install", "--skill", "alpha", "--runtime", "claude-code"), [], id="complete"
        ),
    ],
)
def test_the_wizard_opens_exactly_the_steps_the_line_did_not_fix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: CaptureFixture,
    argv: tuple[str, ...],
    opened: list[str],
) -> None:
    """The trigger stops being *"nothing was selected"* and becomes *"this cannot be planned"*.

    Giving `--runtime` takes the scope question with it: the list `--runtime`
    accepts is a function of the scope (ADR 0009), so the scope step exists to
    scope the runtime step. The wizard is one gesture, not a question per absent
    flag.

    Whichever steps opened, the disk shows `.claude/skills/` and nothing beside
    it — the wizard has no lock to add on this path, and ADR 0011's lock is of
    the screen anyway.
    """
    # given
    project.catalog_of(tmp_path, monkeypatch, "alpha")
    root = project.target(tmp_path, monkeypatch)
    project.terminal(monkeypatch)
    steps = _wizard_steps(monkeypatch)

    code, _ = project.run(capsys, *argv, "--yes")

    assert code == 0
    assert steps == opened
    assert (root / project.CLAUDE / "alpha" / "SKILL.md").is_file()
    assert [child.name for child in root.iterdir()] == [".claude"]


def test_global_on_the_line_answers_the_scope_step_and_the_wizard_asks_the_rest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """A boolean flag that *is* there is a decision; only its absence is *"did not say"*."""
    # given
    project.catalog_of(tmp_path, monkeypatch, "alpha")
    project.target(tmp_path, monkeypatch)
    project.terminal(monkeypatch)
    steps = _wizard_steps(monkeypatch)

    code, _ = project.run(capsys, "install", "--global", "--yes")

    assert code == 0
    assert steps == ["artifacts", "runtimes"]
    assert (tmp_path / project.CLAUDE / "alpha" / "SKILL.md").is_file()


@pytest.mark.parametrize(
    "selector",
    [
        pytest.param(("--skill", "alpha"), id="--skill"),
        pytest.param(("--ai-framework", "fw"), id="--ai-framework"),
        pytest.param(("--bundle", "bun"), id="--bundle"),
    ],
)
def test_a_partial_line_without_a_terminal_still_exits_two_with_the_message_of_today(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: CaptureFixture,
    selector: tuple[str, str],
) -> None:
    """No terminal, no wizard — and the refusal is word for word the one that was there.

    The whole sentence and not a fragment of it: what the ticket promised is
    that widening the wizard's trigger changes nothing off a terminal, and a
    substring would still pass if the message had been rewritten around it.
    """
    # given
    project.catalog_of(
        tmp_path, monkeypatch, "alpha", frameworks={"fw": ["fa"]}, bundles={"bun": ["alpha"]}
    )
    root = project.target(tmp_path, monkeypatch)  # tty=False by default
    monkeypatch.setattr(cli, "run_wizard", _never_called)

    code, output = project.run(capsys, "install", *selector)

    assert code == 2
    assert "no --runtime, and there is no default destination to fall back on" in project.joined(
        output
    )
    assert list(root.iterdir()) == []


def test_yes_in_a_terminal_suppresses_the_confirmation_and_no_wizard_step(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """`--yes` skips the confirmation and nothing else — #8, unchanged by the wider trigger."""
    # given
    asked: list[str] = []
    project.catalog_of(tmp_path, monkeypatch, "alpha")
    project.target(tmp_path, monkeypatch)
    project.terminal(monkeypatch)
    steps = _wizard_steps(monkeypatch)
    monkeypatch.setattr(cli, "_confirmed", lambda: bool(asked.append("asked")))

    code, _ = project.run(capsys, "install", "--skill", "alpha", "--yes")

    assert code == 0
    assert steps == ["scope", "runtimes"]
    assert asked == []


def test_the_line_the_list_prints_installs_when_it_is_pasted_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The journey the ticket closes, taken end to end and in one process.

    The line is not typed here: it is read back off the screen `list` drew, so
    the two halves cannot drift apart. Its first word being `overpower` is the
    assertion that the line is bare — a `$` in front would land there instead.

    The catalog is read off a pipe and the line is pasted into a terminal, which
    is both the honest gesture and the one that keeps the parsing simple: under
    a pipe there is no ANSI to strip out of the row before splitting it.
    """
    # given
    project.catalog_of(tmp_path, monkeypatch, "alpha")
    root = project.target(tmp_path, monkeypatch)  # tty=False: the catalog goes through a pipe

    listed_code, listed = project.run(capsys, "list")
    line = next(row for row in _rows(listed) if row.startswith("overpower install"))
    project.terminal(monkeypatch)
    steps = _wizard_steps(monkeypatch)
    code, output = project.run(capsys, *shlex.split(line)[1:], "--yes")

    assert listed_code == 0
    assert line == "overpower install --skill alpha"
    assert shlex.split(line)[0] == "overpower"
    assert code == 0
    assert steps == ["scope", "runtimes"]
    assert "summary" in project.joined(output)
    assert (root / project.CLAUDE / "alpha" / "SKILL.md").is_file()


def test_the_mcp_line_the_list_prints_installs_when_it_is_pasted_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """#97's own version of the journey above: `--mcp` with no `--runtime` reaches a screen.

    Before #97 this exact line opened the skills runtime step, which offered
    nothing this class could use — the command `list --mcp` prints did not
    work pasted back. It opens the graft class's own step now.
    """
    # given
    project.catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": MCP_URL})
    root = project.target(tmp_path, monkeypatch)  # tty=False: the catalog goes through a pipe

    listed_code, listed = project.run(capsys, "list", "--mcp", "cloudflare")
    line = next(row for row in _rows(listed) if row.startswith("overpower install"))
    project.terminal(monkeypatch)
    steps = _wizard_steps(monkeypatch)
    code, output = project.run(capsys, *shlex.split(line)[1:], "--yes")

    assert listed_code == 0
    assert line == "overpower install --mcp cloudflare"
    assert code == 0
    assert steps == ["scope", "mcp_runtimes"]
    assert "summary" in project.joined(output)
    assert (root / ".mcp.json").is_file()


def _rows(output: str) -> list[str]:
    """The screen as rows, with the frame off and every run of spaces collapsed."""
    return [" ".join(line.strip().strip("│").split()) for line in output.splitlines()]


def test_a_flag_line_that_names_one_runtime_writes_only_that_runtime_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """ADR 0011: the lock is of the screen and never of the plan.

    A lock that were a planning rule would make this line write two trees, and
    the flag would stop saying what it does — which is what the command line
    being the manifest (#8) rests on.
    """
    # given
    project.catalog_of(tmp_path, monkeypatch, "alpha")
    root = project.target(tmp_path, monkeypatch)

    code, _ = project.run(capsys, "install", "--skill", "alpha", "--runtime", "claude-code")

    assert code == 0
    assert (root / project.CLAUDE / "alpha" / "SKILL.md").is_file()
    assert [child.name for child in root.iterdir()] == [".claude"]


# --------------------------------------------------------------------------- #
# #42: --from, the remote search root, and the exit codes it answers with
# --------------------------------------------------------------------------- #

REMOTE = "https://github.com/owner/repo"
"""Any GitHub URL, without registration. Nothing here reaches it: the obtainer
is the one double the doctrine's table sanctions on this path."""


def _exploding(*_: object, **__: object) -> object:
    """A catalog read that must never happen: `--from` is exclusive."""
    message = "the embedded catalog was read while `--from` was given"
    raise OverpowerError(message)


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(("install", "--runtime", "claude-code"), id="install"),
        pytest.param(("list",), id="list"),
    ],
)
def test_from_with_an_ai_framework_exits_two_before_obtaining_anything(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: CaptureFixture,
    command: tuple[str, ...],
) -> None:
    """The one unit `--from` cannot name, on both verbs, and before any obtention.

    A framework is a folder of the wheel: there is nothing remote for the flag
    to reach, so the refusal is a statement about the *model* and not a queue
    position. Both obtainers explode, which is what makes *"before anything is
    fetched"* an assertion rather than a comment.
    """
    # given
    project.target(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    monkeypatch.setattr(remote, "fetch_with_git", git_remote.refusing("obtention was attempted"))
    monkeypatch.setattr(remote, "fetch_tarball", git_remote.refusing("obtention was attempted"))

    verb, *rest = command
    code, output = project.run(
        capsys, verb, "--from", REMOTE, "--ai-framework", "matt-pocock", *rest
    )

    assert code == 2
    assert "--ai-framework" in project.joined(output)
    assert "does not exist" in project.joined(output)


def test_from_with_nothing_to_look_for_exits_two_before_obtaining_anything(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """A search root and nothing to search for costs a repository download otherwise."""
    # given
    project.target(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    monkeypatch.setattr(remote, "fetch_with_git", git_remote.refusing("obtention was attempted"))
    monkeypatch.setattr(remote, "fetch_tarball", git_remote.refusing("obtention was attempted"))

    code, _ = project.run(capsys, "install", "--from", REMOTE, "--runtime", "claude-code")

    assert code == 2


@pytest.mark.parametrize(
    "url",
    [
        pytest.param(REMOTE, id="repository root"),
        pytest.param(f"{REMOTE}/tree/main/skills", id="a subfolder"),
        pytest.param(f"{REMOTE}/tree/main/skills/alpha", id="the artifact's own folder"),
    ],
)
def test_the_three_depths_of_url_install_the_same_skill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture, url: str
) -> None:
    """And the embedded catalog is never read: with `--from`, only the remote is consulted."""
    # given
    root = project.target(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    monkeypatch.setattr(
        remote, "fetch_with_git", git_remote.planting(git_remote.skill_files("alpha", "beta"))
    )

    code, _ = project.run(
        capsys, "install", "--from", url, "--skill", "alpha", "--runtime", "claude-code", "--yes"
    )

    assert code == 0
    assert (root / project.CLAUDE / "alpha" / "SKILL.md").is_file()
    assert not (root / project.CLAUDE / "beta").exists()


@pytest.mark.parametrize(
    "url",
    [
        pytest.param(REMOTE, id="repository root"),
        pytest.param(f"{REMOTE}/tree/main/.overpower", id="a subfolder"),
        pytest.param(f"{REMOTE}/tree/main/.overpower/mcp", id="the recipe's own folder"),
    ],
)
def test_the_three_depths_of_url_install_the_same_mcp_recipe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture, url: str
) -> None:
    """`--mcp` joined `--skill` under `--from` in #83: the embedded catalog stays shut."""
    # given
    root = project.target(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    monkeypatch.setattr(
        remote, "fetch_with_git", git_remote.planting(git_remote.mcp_recipe_files("cloudflare"))
    )

    code, _ = project.run(
        capsys, "install", "--from", url, "--mcp", "cloudflare", "--runtime", "claude-code", "--yes"
    )

    assert code == 0
    assert (root / ".mcp.json").is_file()


def test_an_mcp_recipe_that_is_not_found_remotely_exits_three_and_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """Same axis as the skill search: obtained, searched, and the answer is no."""
    # given
    root = project.target(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    monkeypatch.setattr(
        remote, "fetch_with_git", git_remote.planting(git_remote.mcp_recipe_files("cloudflare"))
    )

    code, output = project.run(
        capsys, "install", "--from", REMOTE, "--mcp", "vercel", "--runtime", "claude-code", "--yes"
    )

    assert code == 3
    assert "vercel" in project.joined(output)
    assert list(root.iterdir()) == []


def test_a_search_that_finds_nothing_does_not_fall_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """#25 measured this as a live bug: the fallback ran for *"the skill is not
    there"*, re-fetched the whole repository and returned the same answer.

    Obtention failure -> fallback, then exit 1 if it also fails.
    Obtained, searched, not found -> exit 3, and the fallback is never called.
    """
    # given
    asked: list[object] = []
    root = project.target(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    monkeypatch.setattr(
        remote, "fetch_with_git", git_remote.planting(git_remote.skill_files("alpha"))
    )

    def fallback(*args: object, **_kwargs: object) -> object:
        return asked.append(args)

    monkeypatch.setattr(remote, "fetch_tarball", fallback)

    code, output = project.run(
        capsys, "install", "--from", REMOTE, "--skill", "beta", "--runtime", "claude-code", "--yes"
    )

    assert code == 3
    assert asked == []
    assert "beta" in project.joined(output)
    assert list(root.iterdir()) == []


def test_an_obtention_that_fails_on_both_paths_exits_one_carrying_the_transport_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """Exit 1 is *could not run*, and the message is the transport's, because it
    is the one that names the problem."""
    # given
    root = project.target(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    monkeypatch.setattr(
        remote, "fetch_with_git", git_remote.refusing("fatal: couldn't find remote ref nope")
    )
    monkeypatch.setattr(remote, "fetch_tarball", git_remote.refusing("HTTP Error 404: Not Found"))

    code, output = project.run(
        capsys, "install", "--from", REMOTE, "--skill", "alpha", "--runtime", "claude-code", "--yes"
    )

    assert code == 1
    assert "couldn't find remote ref nope" in project.joined(output)
    assert list(root.iterdir()) == []


def test_a_dry_run_resolves_the_remote_and_still_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """A dry run that does not fetch is a report about another installation."""
    # given
    obtained: list[object] = []
    root = project.target(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    planted = git_remote.planting(git_remote.skill_files("alpha"))

    def fetch(url: str, ref: str, into: Path) -> Path:
        obtained.append(url)
        return planted(url, ref, into)

    monkeypatch.setattr(remote, "fetch_with_git", fetch)

    code, output = project.run(
        capsys,
        "install",
        "--from",
        REMOTE,
        "--skill",
        "alpha",
        "--runtime",
        "claude-code",
        "--dry-run",
    )

    assert code == 0
    assert obtained
    assert "alpha" in project.joined(output)
    assert list(root.iterdir()) == []


def test_a_complete_from_line_in_a_terminal_installs_without_a_wizard_step(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """Not because it is `--from`, but because the line names both halves of a plan.

    That distinction is what #57 changed: the exclusion used to be of the whole
    wizard, and is now of the **artifacts step** alone — the only step that
    consults a catalog, and therefore the only one *"only the remote is
    consulted"* has anything to say about.
    """
    # given
    root = project.target(tmp_path, monkeypatch)
    project.terminal(monkeypatch)
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    monkeypatch.setattr(cli, "run_wizard", _never_called)
    monkeypatch.setattr(
        remote, "fetch_with_git", git_remote.planting(git_remote.skill_files("alpha"))
    )

    code, _ = project.run(
        capsys, "install", "--from", REMOTE, "--skill", "alpha", "--runtime", "claude-code", "--yes"
    )

    assert code == 0
    assert (root / project.CLAUDE / "alpha" / "SKILL.md").is_file()


def test_a_from_line_missing_the_runtime_opens_scope_and_runtimes_and_never_the_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """Neither of those two steps touches a catalog, so neither can consult the wrong one.

    The artifacts step is kept out by construction rather than by a condition:
    a `--from` line has to name `--skill` before anything is fetched, so the
    selection is never empty and the step it would open never opens.
    `cli.load_catalog` exploding is what proves the embedded catalog stayed shut.
    """
    # given
    root = project.target(tmp_path, monkeypatch)
    project.terminal(monkeypatch)
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    monkeypatch.setattr(
        remote, "fetch_with_git", git_remote.planting(git_remote.skill_files("alpha"))
    )
    steps = _wizard_steps(monkeypatch)

    code, _ = project.run(capsys, "install", "--from", REMOTE, "--skill", "alpha", "--yes")

    assert code == 0
    assert steps == ["scope", "runtimes"]
    assert (root / project.CLAUDE / "alpha" / "SKILL.md").is_file()


def test_a_bare_from_line_in_a_terminal_opens_the_wizard_on_the_showcase(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """#135: the same wizard, with the remote catalog in place of the embedded one.

    Nobody learns a second flow because of provenance. What proves the catalog
    that reached the artifacts step is the remote one is that the choice offered
    is `alpha` — a name the embedded catalog does not have — while
    `cli.load_catalog` exploding proves the embedded one stayed shut.
    """
    # given
    offered: list[str] = []

    def ask_artifacts(
        catalog: Catalog,
    ) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
        offered.extend(artifact.name for artifact in catalog.pool)
        return ((), (), ("alpha",), ())

    root = project.target(tmp_path, monkeypatch)
    project.terminal(monkeypatch)
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    monkeypatch.setattr(wizard, "ask_artifacts", ask_artifacts)
    monkeypatch.setattr(
        remote, "fetch_with_git", git_remote.planting(git_remote.skill_files("alpha", "beta"))
    )

    code, _ = project.run(capsys, "install", "--from", REMOTE, "--runtime", "claude-code", "--yes")

    assert code == 0
    assert offered == ["alpha", "beta"]
    assert (root / project.CLAUDE / "alpha" / "SKILL.md").is_file()
    assert not (root / project.CLAUDE / "beta").exists()


def test_the_artifacts_step_offers_the_bundles_the_repository_declares(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """#137: the composition takes its place in the step, beside the skills and the recipes.

    The point of the assertion is *what the step was handed*, not what was
    picked: a bundle that reaches the showcase and not the wizard would be
    listable and unchoosable, which is the half-state a person cannot act on.
    """
    # given
    offered: list[tuple[str, str]] = []

    def ask_artifacts(
        catalog: Catalog,
    ) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
        offered.extend(("bundle", bundle.name) for bundle in catalog.bundles)
        offered.extend(("skill", artifact.name) for artifact in catalog.pool)
        offered.extend(("mcp", recipe.name) for recipe in catalog.mcps)
        return ((), ("api-python",), (), ())

    root = project.target(tmp_path, monkeypatch)
    project.terminal(monkeypatch)
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    monkeypatch.setattr(wizard, "ask_artifacts", ask_artifacts)
    planted = {
        **git_remote.offering("alpha", "beta", bundles={"api-python": ["alpha"]}),
        **git_remote.mcp_recipe_files("cloudflare"),
    }
    monkeypatch.setattr(remote, "fetch_with_git", git_remote.planting(planted))

    code, _ = project.run(capsys, "install", "--from", REMOTE, "--runtime", "claude-code", "--yes")

    assert code == 0
    assert offered == [
        ("bundle", "api-python"),
        ("skill", "alpha"),
        ("skill", "beta"),
        ("mcp", "cloudflare"),
    ]
    # And the bundle picked in the step installs out of that very tree, rather
    # than being a row the wizard could offer and the writer could not honour.
    assert (root / project.CLAUDE / "alpha" / "SKILL.md").is_file()
    assert not (root / project.CLAUDE / "beta").exists()


def test_a_bare_from_line_obtains_the_repository_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The showcase the wizard read is the catalog the writer copies from.

    Obtaining a second time to install what the first obtention showed would be
    two repositories on one line: the tree the wizard described could move
    between the two calls, and the scratch of the first is gone by the second.
    """
    # given
    obtained: list[str] = []
    planted = git_remote.planting(git_remote.skill_files("alpha"))

    def fetch(url: str, ref: str, into: Path) -> Path:
        obtained.append(url)
        return planted(url, ref, into)

    root = project.target(tmp_path, monkeypatch)
    project.terminal(monkeypatch)
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    _ = _wizard_steps(monkeypatch)
    monkeypatch.setattr(remote, "fetch_with_git", fetch)

    code, _ = project.run(capsys, "install", "--from", REMOTE, "--yes")

    assert code == 0
    assert len(obtained) == 1
    assert (root / project.CLAUDE / "alpha" / "SKILL.md").is_file()


def test_a_bare_from_line_off_a_pipe_is_still_refused_before_obtaining_anything(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """Without a terminal there is no wizard, so there is still nothing to look for.

    The showcase is a step of the wizard, and a line that cannot open one has
    the shape it always had — a search root and no unit — so the refusal keeps
    its old *order* too: no repository is downloaded to reach it.
    """
    # given
    project.target(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    monkeypatch.setattr(cli, "run_wizard", _never_called)
    monkeypatch.setattr(remote, "fetch_with_git", git_remote.refusing("obtention was attempted"))
    monkeypatch.setattr(remote, "fetch_tarball", git_remote.refusing("obtention was attempted"))

    code, output = project.run(capsys, "install", "--from", REMOTE, "--runtime", "claude-code")

    assert code == 2
    assert "--skill" in project.joined(output)


def test_a_bare_from_line_pointed_at_a_repository_that_offers_nothing_exits_three(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """And no step is asked: the problem is the URL, not any answer the user could give."""
    # given
    project.target(tmp_path, monkeypatch)
    project.terminal(monkeypatch)
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    monkeypatch.setattr(wizard, "ask_artifacts", _never_called)
    monkeypatch.setattr(
        remote, "fetch_with_git", git_remote.planting({"README.md": "# nothing here\n"})
    )

    code, output = project.run(capsys, "install", "--from", REMOTE, "--runtime", "claude-code")

    assert code == 3
    assert "skills" in project.joined(output)


def test_a_repository_equipped_with_the_overpower_installs_its_own_skill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The false ambiguity #135 fixes, asserted end to end.

    A repository that installed its own skill carries it at `skills/alpha` and
    at `.claude/skills/alpha`. Before the deny-list that pair refused the line
    outright — and the refusal named an ambiguity that was never there.
    """
    # given
    root = project.target(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    planted = {
        **git_remote.skill_files("alpha"),
        **git_remote.installed_skill_files("alpha"),
    }
    monkeypatch.setattr(remote, "fetch_with_git", git_remote.planting(planted))

    code, _ = project.run(
        capsys, "install", "--from", REMOTE, "--skill", "alpha", "--runtime", "claude-code", "--yes"
    )

    assert code == 0
    assert (root / project.CLAUDE / "alpha" / "SKILL.md").is_file()


def test_the_showcase_install_is_identical_dry_real_and_on_disk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The three-way identity, on the one path that never had it.

    Three sets, and each compared against each: the destinations `--dry-run`
    names, the destinations the real run names, and what a walk of the target
    finds afterwards — plus the two exit codes agreeing and the dry run leaving
    the target untouched. That is what makes `--dry-run` an audit of *this*
    installation rather than a report about another one, and a showcase install
    is where the two runs could most easily diverge: the catalog itself is
    obtained, not read off the wheel.

    **The two granularities are both asserted, and they are not the same claim.**
    The screens speak in *landings* — a destination directory, with the artifact
    named on its own row — so the three-way equality is at that granularity. The
    disk is then read at the leaf, against a literal, because the equality alone
    would hold just as well if `beta` had landed where `alpha` was announced.
    """

    def picked(
        _catalog: Catalog,
    ) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
        return ((), (), ("alpha",), ())

    def project_scope(
        cwd: Path, _environment: Environment, _console: Console, *, sourced: bool = False
    ) -> tuple[Scope, Path]:
        del sourced
        return Scope.PROJECT, cwd

    def fixed_runtimes(_scope: Scope, _root: Path, _environment: Environment) -> tuple[str, ...]:
        return ("claude-code",)

    # given
    root = project.target(tmp_path, monkeypatch)
    project.terminal(monkeypatch)
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    monkeypatch.setattr(wizard, "ask_artifacts", picked)
    monkeypatch.setattr(wizard, "ask_scope", project_scope)
    monkeypatch.setattr(wizard, "ask_runtimes", fixed_runtimes)
    monkeypatch.setattr(
        remote, "fetch_with_git", git_remote.planting(git_remote.skill_files("alpha"))
    )

    dry_code, dry_out = project.run(capsys, "install", "--from", REMOTE, "--dry-run")
    assert list(root.iterdir()) == []
    real_code, real_out = project.run(capsys, "install", "--from", REMOTE, "--yes")

    landed = {found.parent.relative_to(root).as_posix() for found in root.rglob("SKILL.md")}
    # The parent, because that is the granularity the two screens speak in: a
    # landing is a destination directory, and the artifact is named on its own row.
    walked = {PurePosixPath(folder).parent.as_posix() for folder in landed}
    dry_paths = _destinations(dry_out)
    real_paths = _destinations(real_out)
    assert (dry_code, real_code) == (0, 0)
    assert dry_paths == real_paths == walked == {project.CLAUDE}
    # The leaf, against a literal: the equality above would hold just as well if
    # `beta` had landed where `alpha` was announced, and nothing else names it.
    assert landed == {f"{project.CLAUDE}/alpha"}
    assert "alpha" in project.joined(dry_out)
    # And what a dry run promised is all that is there — no file it never named.
    assert {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()} == {
        f"{project.CLAUDE}/alpha/SKILL.md"
    }


def _destinations(output: str) -> set[str]:
    """Every `.claude/skills/<name>` a plan or a closing screen printed, as posix paths.

    Read word by word rather than row by row: a plan row carries a glyph before
    the path and a closing row may carry more than one path, and neither of
    those is what the identity is about.
    """
    return {
        word.rstrip("/")
        for row in _rows(output)
        for word in row.split()
        if word.startswith(project.CLAUDE)
    }


def test_a_url_that_is_not_a_github_repository_exits_two_before_obtaining_anything(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    # given
    project.target(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    monkeypatch.setattr(remote, "fetch_with_git", git_remote.refusing("obtention was attempted"))
    monkeypatch.setattr(remote, "fetch_tarball", git_remote.refusing("obtention was attempted"))

    code, output = project.run(
        capsys,
        "install",
        "--from",
        "https://gitlab.com/owner/repo",
        "--skill",
        "alpha",
        "--runtime",
        "claude-code",
    )

    assert code == 2
    assert "gitlab.com" in project.joined(output)


def test_list_mcp_from_shows_the_recipe_and_writes_nothing(
    monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The other AC of #83: `list --mcp <slug> --from <url>` needs no target at all."""
    # given
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    monkeypatch.setattr(
        remote, "fetch_with_git", git_remote.planting(git_remote.mcp_recipe_files("cloudflare"))
    )

    code, output = output_of(capsys, ["list", "--mcp", "cloudflare", "--from", REMOTE])

    assert code == 0
    assert "cloudflare" in output
    assert "claude-code" in project.joined(output)


def test_the_line_a_federated_recipe_prints_carries_the_origin_it_came_from(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The invariant `test_the_mcp_line_the_list_prints_installs_when_it_is_pasted_back` fixes,
    on the one path that never had it.

    A federated recipe is **not in the catalog** — that is what `--from` is for —
    so `overpower install --mcp acme` pasted back exits 2 naming the four slugs
    that are. The line the screen prints is a promise that typing it does what
    the screen just described, and it is the same promise whether the recipe was
    obtained or embedded.

    Asserted here as *the line carries the origin*, and by the sibling below as
    *the embedded line still does not*, because the failure mode of the fix is
    printing `--from` for every recipe on the catalog screen.
    """
    # given
    _ = project.target(tmp_path, monkeypatch)  # tty=False: the screen goes through a pipe
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    monkeypatch.setattr(
        remote, "fetch_with_git", git_remote.planting(git_remote.mcp_recipe_files("cloudflare"))
    )

    code, output = project.run(capsys, "list", "--mcp", "cloudflare", "--from", REMOTE)

    line = next(row for row in _rows(output) if row.startswith("overpower install"))
    assert code == 0
    assert line == f"overpower install --mcp cloudflare --from {REMOTE}"


def test_the_embedded_recipe_prints_no_origin_it_did_not_come_from(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The other half: a recipe read off the catalog has no origin to name.

    `--from` on that line would be a flag the reader has to delete, pointing at
    a repository the recipe never came from.
    """
    # given
    project.catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": MCP_URL})
    _ = project.target(tmp_path, monkeypatch)

    code, output = project.run(capsys, "list", "--mcp", "cloudflare")

    line = next(row for row in _rows(output) if row.startswith("overpower install"))
    assert code == 0
    assert line == "overpower install --mcp cloudflare"


def test_list_from_with_no_selector_prints_the_showcase(
    monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """#135: the question before the name — *what does this repository offer?*

    Both classes in one command, because a repository offers both and reading
    two commands to find that out is the reader's problem, not the product's.
    """
    # given
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    planted = {
        **git_remote.skill_files("alpha"),
        **git_remote.mcp_recipe_files("cloudflare"),
    }
    monkeypatch.setattr(remote, "fetch_with_git", git_remote.planting(planted))

    code, output = output_of(capsys, ["list", "--from", REMOTE])

    joined = project.joined(output)
    assert code == 0
    assert "alpha" in joined
    assert "The alpha skill." in joined
    assert "cloudflare" in joined


def test_the_showcase_omits_the_one_unit_a_repository_cannot_offer(
    monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """No AI Framework block, ever, and no empty block of anything else.

    The embedded screen keeps all four — an empty bundle list is a real shape of
    *this* catalog. Off the wheel a heading over nothing would be the screen
    inventing a category, so the empty ones are dropped; the framework heading is
    the one that cannot appear at all, because a framework is a folder of the
    wheel and nothing remote can hold one.
    """
    # given
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    monkeypatch.setattr(
        remote, "fetch_with_git", git_remote.planting(git_remote.skill_files("alpha"))
    )

    code, output = output_of(capsys, ["list", "--from", REMOTE])

    joined = project.joined(output)
    assert code == 0
    assert "AI Frameworks" not in joined
    assert "Bundles" not in joined
    assert "MCP servers" not in joined
    assert "Pool skills" in joined


# --------------------------------------------------------------------------- #
# #137: the bundle that crosses `--from`
# --------------------------------------------------------------------------- #


def test_install_bundle_from_installs_what_the_bundle_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """A whole context of work equipped in one command, and the embedded catalog stays shut."""
    # given
    root = project.target(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    planted = git_remote.offering(
        "alpha", "beta", "gamma", bundles={"api-python": ["alpha", "beta"]}
    )
    monkeypatch.setattr(remote, "fetch_with_git", git_remote.planting(planted))

    code, _ = project.run(
        capsys,
        *("install", "--from", REMOTE, "--bundle", "api-python"),
        *("--runtime", "claude-code", "--yes"),
    )

    assert code == 0
    assert (root / project.CLAUDE / "alpha" / "SKILL.md").is_file()
    assert (root / project.CLAUDE / "beta" / "SKILL.md").is_file()
    assert not (root / project.CLAUDE / "gamma").exists()


@pytest.mark.parametrize(
    "url",
    [
        pytest.param(REMOTE, id="repository root"),
        pytest.param(f"{REMOTE}/tree/main/skills", id="a subfolder"),
        pytest.param(f"{REMOTE}/tree/main/.overpower", id="the manifest's own folder"),
    ],
)
def test_the_three_depths_of_url_install_the_same_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture, url: str
) -> None:
    """The manifest is read from the root, so the URL's subfolder does not interfere."""
    # given
    root = project.target(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    planted = git_remote.offering("alpha", "beta", bundles={"api-python": ["alpha"]})
    monkeypatch.setattr(remote, "fetch_with_git", git_remote.planting(planted))

    code, _ = project.run(
        capsys,
        *("install", "--from", url, "--bundle", "api-python"),
        *("--runtime", "claude-code", "--yes"),
    )

    assert code == 0
    assert (root / project.CLAUDE / "alpha" / "SKILL.md").is_file()
    assert not (root / project.CLAUDE / "beta").exists()


def test_a_bundle_that_is_not_declared_remotely_exits_three_and_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """Obtained, read, and the answer is no: the manifest is a stranger's file."""
    # given
    root = project.target(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    planted = git_remote.offering("alpha", bundles={"api-python": ["alpha"]})
    monkeypatch.setattr(remote, "fetch_with_git", git_remote.planting(planted))

    code, output = project.run(
        capsys,
        *("install", "--from", REMOTE, "--bundle", "web-node"),
        *("--runtime", "claude-code", "--yes"),
    )

    assert code == 3
    assert "web-node" in project.joined(output)
    assert list(root.iterdir()) == []


def test_a_bundle_item_the_repository_does_not_offer_exits_three_naming_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The one AC that decides who the reader complains to: the item travels in the message."""
    # given
    root = project.target(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    planted = git_remote.offering("alpha", bundles={"api-python": ["alpha", "ghost"]})
    monkeypatch.setattr(remote, "fetch_with_git", git_remote.planting(planted))

    code, output = project.run(
        capsys,
        *("install", "--from", REMOTE, "--bundle", "api-python"),
        *("--runtime", "claude-code", "--yes"),
    )

    assert code == 3
    assert "ghost" in project.joined(output)
    assert list(root.iterdir()) == []


def test_a_bundle_item_never_reaches_the_embedded_catalog(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """`--from` is exclusive, and `items` is not the hole in it.

    The embedded catalog really does have a skill by that name — the fixture
    builds one — and the line still exits 3. A resolution that fell through to
    the wheel would install content the pointed repository never carried, under
    a manifest that never named it.
    """
    # given
    project.catalog_of(tmp_path, monkeypatch, "embedded-only")
    root = project.target(tmp_path, monkeypatch)
    planted = git_remote.offering("alpha", bundles={"api-python": ["alpha", "embedded-only"]})
    monkeypatch.setattr(remote, "fetch_with_git", git_remote.planting(planted))

    code, output = project.run(
        capsys,
        *("install", "--from", REMOTE, "--bundle", "api-python"),
        *("--runtime", "claude-code", "--yes"),
    )

    assert code == 3
    assert "embedded-only" in project.joined(output)
    assert list(root.iterdir()) == []


def test_a_bundle_and_a_skill_on_one_from_line_both_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The two selectors are independent under `--from` the way they are off the wheel.

    Worth asserting because they do not read the tree the same way: the bundle
    resolves against the **enumerated** skills, anchored at the repository, while
    `--skill` reaches from the search root at any depth. A line naming both runs
    the two rules over one obtained tree, and nothing about the units changes.
    """
    # given
    root = project.target(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    planted = git_remote.offering(
        "alpha", "beta", "gamma", bundles={"api-python": ["alpha", "beta"]}
    )
    monkeypatch.setattr(remote, "fetch_with_git", git_remote.planting(planted))

    code, _ = project.run(
        capsys,
        *("install", "--from", REMOTE, "--bundle", "api-python", "--skill", "gamma"),
        *("--runtime", "claude-code", "--yes"),
    )

    assert code == 0
    assert {found.parent.name for found in root.rglob("SKILL.md")} == {"alpha", "beta", "gamma"}


def test_list_bundle_from_shows_what_the_bundle_names_and_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """Deciding with the content in view, and the *before* is half the claim.

    The target is built and walked afterwards rather than left out, because
    *"mostra o que ele nomeia, sem instalar"* is two assertions and a screen that
    was right would hide a write that should not have happened.
    """
    # given
    root = project.target(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    planted = git_remote.offering(
        "alpha", "beta", "gamma", bundles={"api-python": ["alpha", "beta"]}
    )
    monkeypatch.setattr(remote, "fetch_with_git", git_remote.planting(planted))

    code, output = project.run(capsys, "list", "--bundle", "api-python", "--from", REMOTE)

    joined = project.joined(output)
    assert code == 0
    assert "The api-python bundle." in joined
    assert "alpha" in joined
    assert "beta" in joined
    assert "gamma" not in joined
    assert list(root.iterdir()) == []


def test_the_showcase_lists_the_bundles_the_repository_declares(
    monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The bundle takes its place beside the skills and the recipes, with no selector."""
    # given
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    planted = {
        **git_remote.offering("alpha", bundles={"api-python": ["alpha"]}),
        **git_remote.mcp_recipe_files("cloudflare"),
    }
    monkeypatch.setattr(remote, "fetch_with_git", git_remote.planting(planted))

    code, output = output_of(capsys, ["list", "--from", REMOTE])

    joined = project.joined(output)
    assert code == 0
    assert "Bundles" in joined
    assert "The api-python bundle." in joined
    assert "Pool skills" in joined
    assert "MCP servers" in joined


def test_a_repository_with_no_manifest_omits_the_section_and_stays_installable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The manifest is optional, and adopting it is the author's move to make."""
    # given
    root = project.target(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    monkeypatch.setattr(
        remote, "fetch_with_git", git_remote.planting(git_remote.skill_files("alpha"))
    )

    listed, output = project.run(capsys, "list", "--from", REMOTE)
    installed, _ = project.run(
        capsys,
        *("install", "--from", REMOTE, "--skill", "alpha"),
        *("--runtime", "claude-code", "--yes"),
    )

    joined = project.joined(output)
    assert (listed, installed) == (0, 0)
    assert "Bundles" not in joined
    assert "alpha" in joined
    assert (root / project.CLAUDE / "alpha" / "SKILL.md").is_file()


def test_the_line_a_federated_bundle_prints_carries_the_origin_it_came_from(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The same promise the federated recipe already keeps: the line works pasted back.

    A federated bundle is **not in the catalog**, so `overpower install --bundle
    api-python` without the origin exits 2 naming the bundles that are.
    """
    # given
    _ = project.target(tmp_path, monkeypatch)  # tty=False: the screen goes through a pipe
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    planted = git_remote.offering("alpha", bundles={"api-python": ["alpha"]})
    monkeypatch.setattr(remote, "fetch_with_git", git_remote.planting(planted))

    code, output = project.run(capsys, "list", "--bundle", "api-python", "--from", REMOTE)

    line = next(row for row in _rows(output) if row.startswith("overpower install"))
    assert code == 0
    assert line == f"overpower install --bundle api-python --from {REMOTE}"


def test_a_malformed_federated_manifest_names_the_field_and_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """Recused naming the field, exactly the way the embedded written file is."""
    # given
    root = project.target(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    planted = {
        **git_remote.skill_files("alpha"),
        ".overpower/catalog.yaml": "bundles:\n  api-python:\n    items: [alpha]\n",
    }
    monkeypatch.setattr(remote, "fetch_with_git", git_remote.planting(planted))

    code, output = project.run(
        capsys,
        *("install", "--from", REMOTE, "--bundle", "api-python"),
        *("--runtime", "claude-code", "--yes"),
    )

    assert code == 1
    assert "bundles.api-python.description" in project.joined(output)
    assert list(root.iterdir()) == []


def test_the_showcase_lines_carry_the_origin_they_came_from(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The same promise `test_the_line_a_federated_recipe_prints_carries_the_origin_it_came_from`
    fixed for one recipe, now for every row of the showcase.

    A skill read through `--from` is **not in the catalog**, so
    `overpower install --skill alpha` pasted back exits 2 naming the skills that
    are. The line a screen prints is a promise that typing it does what the
    screen just described.
    """
    # given
    _ = project.target(tmp_path, monkeypatch)  # tty=False: the screen goes through a pipe
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    monkeypatch.setattr(
        remote, "fetch_with_git", git_remote.planting(git_remote.skill_files("alpha"))
    )

    code, output = project.run(capsys, "list", "--from", REMOTE)

    line = next(row for row in _rows(output) if row.startswith("overpower install"))
    assert code == 0
    assert line == f"overpower install --skill alpha --from {REMOTE}"


def test_list_from_a_repository_that_offers_nothing_exits_three(
    monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """Obtained, walked, and the answer is no — the defect is the URL's, not the line's."""
    # given
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    monkeypatch.setattr(
        remote, "fetch_with_git", git_remote.planting({"README.md": "# nothing here\n"})
    )

    code, output = output_of(capsys, ["list", "--from", REMOTE])

    assert code == 3
    assert "skills" in project.joined(output)


def test_list_skill_from_shows_the_skill_whole(
    monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The selector `list --from` was missing: read it before installing it."""
    # given
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    monkeypatch.setattr(
        remote, "fetch_with_git", git_remote.planting(git_remote.skill_files("alpha", "beta"))
    )

    code, output = output_of(capsys, ["list", "--skill", "alpha", "--from", REMOTE])

    joined = project.joined(output)
    assert code == 0
    assert "alpha" in joined
    assert "beta" not in joined


# The `list` half of this refusal — and its *before any obtention* rider — is
# asserted by `test_from_with_an_ai_framework_exits_two_before_obtaining_anything`,
# which parametrises over both verbs. It moved there when #137 took `--bundle`
# off the refused list and left the two commands refusing exactly one unit each:
# two tests over a one-element list, one per verb, was the same claim written
# twice.


@pytest.mark.parametrize(
    "depth",
    [
        pytest.param("", id="repository root"),
        pytest.param("/tree/main/skills", id="a subfolder"),
        pytest.param("/tree/main/skills/alpha", id="the artifact's own folder"),
    ],
)
def test_the_showcase_a_url_prints_does_not_depend_on_its_depth(
    monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture, depth: str
) -> None:
    """Asserted through `main(argv)` and stdout, which is where the promise is made.

    `tests/test_remote.py` already holds this against `catalog_from`; the same
    claim at the command line is a different one, because it is the command line
    that decides whether a bare `--from` even reaches the showcase.
    """
    # given
    monkeypatch.setattr(cli, "load_catalog", _exploding)
    monkeypatch.setattr(
        remote, "fetch_with_git", git_remote.planting(git_remote.skill_files("alpha", "beta"))
    )

    code, output = output_of(capsys, ["list", "--from", f"{REMOTE}{depth}"])

    joined = project.joined(output)
    assert code == 0
    assert "alpha" in joined
    assert "beta" in joined
