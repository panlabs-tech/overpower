"""A real content tree, a real target and the CLI between them.

Machinery with no subject of its own, and it belongs here for the reason the
ruler draws the line at: **`support/` talks to real infrastructure**, which is
exactly what building a content tree on disk and pointing the product at it is.
There is no filesystem double anywhere below the CLI (ADR 0010).

`content_root` and `catalog_file` are redirected, and that is not a double
either: they are aimed at a **real tree built in `tmp_path`**. Two properties
need it — the shipped catalog carries a single pool skill while the criteria ask
for two names on one line, and the internal-link property needs a source tree
that *contains* a link. The tree the product walks is real either way; only its
address moves.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from rich.console import Console

from overpower import cli
from overpower.screens import THEME

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    import pytest

CLAUDE = ".claude/skills"
"""Where Claude Code reads skills in a repository — measured, not transcribed."""

AGENTS = ".agents/skills"
"""The path Cursor reads, shared with 18 other rows of the table."""

PATH = re.compile(r"(?:[\w.@+-]+/)+")
"""Every `/`-terminated path token on a screen.

The plan screen is the only screen that prints paths, and it prints them
relative to the target with a trailing separator — so this finds the announced
set and nothing else. A runtime key carries no separator.
"""


def catalog_of(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *names: str, extra: Sequence[str] = ()
) -> Path:
    """Build a real content tree of `names`, aim the product at it, answer its root.

    Each skill gets the `SKILL.md` whose frontmatter discovery reads, plus
    whatever `extra` names — which is how a skill is given more than one file
    when the test is about what survives a second install.
    """
    content = tmp_path / "packaged" / "content"
    for name in names:
        skill = content / "pool" / "skills" / name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: The {name} skill.\n---\n\n# {name}\n",
            encoding="utf-8",
        )
        for relative in extra:
            path = skill / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"{name}: {relative}\n", encoding="utf-8")

    written = tmp_path / "packaged" / "catalog.toml"
    written.write_text("", encoding="utf-8")
    monkeypatch.setattr(cli, "content_root", lambda: content)
    monkeypatch.setattr(cli, "catalog_file", lambda: written)
    return content


def source(content: Path, name: str) -> Path:
    """The directory a pool skill occupies inside the content tree."""
    return content / "pool" / "skills" / name


def target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str = "project") -> Path:
    """An empty directory, made the working directory, the home and a pipe."""
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(root)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    # Rich reads `COLUMNS` off the environment mapping it captured at
    # construction, so this pins the width of the error panel, which is the one
    # screen that does not go through the console pinned below.
    monkeypatch.setenv("COLUMNS", "100")
    monkeypatch.setattr(cli, "_out", pinned(tty=False))
    return root


def pinned(*, tty: bool) -> Console:
    """The product's stdout console with the `isatty()` answer pinned.

    Not a convenience. Measured in #12 and recorded in `test_cli.py`: rich and
    typer read `FORCE_COLOR`, `PY_COLORS` and `GITHUB_ACTIONS` and force a
    terminal when any of them is set, and both this machine and the CI runner
    set one. An in-process test that left it alone would assert the developer's
    environment instead of the product — and it would put the ASCII banner,
    which is made of `/` and `_`, into the very output the path assertions read.
    The other half of the gate, a real pipe on a real child, lives in
    `test_cli.py`.
    """
    return Console(theme=THEME, width=100, force_terminal=tty, highlight=False)


def terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    """Move the product into a terminal, which is where the confirmation lives."""
    monkeypatch.setattr(cli, "_out", pinned(tty=True))


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str]:
    """The command, in process, with its two streams joined the way a user reads them."""
    code = cli.main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out + captured.err


def joined(output: str) -> str:
    """The output with its frame and its re-wrapping undone.

    A message is allowed to wrap; the assertion is about what it says, and that
    is only visible after joining the lines back up.
    """
    lines = [line.strip().strip("│").strip() for line in output.splitlines()]
    return " ".join(" ".join(line.split()) for line in lines if line)


def paths_in(output: str) -> set[str]:
    """Every path the screen announced."""
    return {match.group(0) for match in PATH.finditer(output)}


def files_under(root: Path) -> set[str]:
    """Every file below `root`, relative and separator-normalised. A plain walk."""
    return {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}


def landings_of(files: set[str], announced: set[str]) -> set[str]:
    """Each walked file mapped to the announced path it landed under, or to itself.

    This is what makes the disk half of the identity a **walk** rather than a
    lookup. Nothing here knows what was asked for: a file that landed under no
    announced path maps to *itself* and therefore cannot disappear into the
    comparison, and an announced path that received nothing is simply absent
    from the result. Comparing this against the announced set closes both
    directions of the measured `npx skills` defect at once — a path announced
    and never written, and a path written and never announced.
    """
    return {next((named for named in announced if path.startswith(named)), path) for path in files}
