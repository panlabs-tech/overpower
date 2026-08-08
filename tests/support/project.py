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
from overpower.inspection import GIT_CONFIG_GLOBAL
from overpower.runtimes import RUNTIMES, EnvironmentAnchor
from overpower.screens import THEME

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
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

ANCHORS = (
    GIT_CONFIG_GLOBAL,
    *sorted(
        {
            runtime.global_dir.anchor.variable
            for runtime in RUNTIMES
            if runtime.global_dir is not None
            and isinstance(runtime.global_dir.anchor, EnvironmentAnchor)
        }
    ),
)
"""Every variable that can move a path the product reads, out of the sandbox.

Scrubbed alongside `HOME`, and for the same reason: a developer with
`CLAUDE_CONFIG_DIR` exported would send a global install *out* of the sandbox,
and a test that asserted against `tmp_path` would fail on their machine and
nowhere else. `doctor` makes it sharper — it walks **every** global destination
of the table, so an unscrubbed anchor is the suite reading the developer's own
equipment — and `GIT_CONFIG_GLOBAL` joins them because `overpower.inspection`
honours it when it looks for `core.symlinks`.

**Derived from the table, never listed by hand.** The runtime table grows and
never shrinks, so a hand-written list would go quietly stale on the next
transcription and restore exactly the leak this exists to close.
"""


def catalog_of(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *names: str,
    extra: Sequence[str] = (),
    frameworks: Mapping[str, Sequence[str]] | None = None,
    bundles: Mapping[str, Sequence[str]] | None = None,
) -> Path:
    """Build a real content tree of `names`, aim the product at it, answer its root.

    Each pool skill gets the `SKILL.md` whose frontmatter discovery reads, plus
    whatever `extra` names — which is how a skill is given more than one file
    when the test is about what survives a second install.

    `frameworks` maps a framework name to the skill names inside it, each built
    the same way as a pool skill and written into the catalog with a description
    (#39: a framework needs one, discovery reads it and not a tree). `bundles`
    maps a bundle name to the pool skill names its manifest points at. Both are
    optional and additive, so a call that only names pool skills is unaffected.
    """
    content = tmp_path / "packaged" / "content"
    for name in names:
        _skill(content / "pool" / "skills" / name, name, extra)
    for framework, artifacts in (frameworks or {}).items():
        for artifact_name in artifacts:
            _skill(content / "frameworks" / framework / "skills" / artifact_name, artifact_name, ())

    written = tmp_path / "packaged" / "catalog.toml"
    written.write_text(_written(frameworks or {}, bundles or {}), encoding="utf-8")
    monkeypatch.setattr(cli, "content_root", lambda: content)
    monkeypatch.setattr(cli, "catalog_file", lambda: written)
    return content


def _skill(skill: Path, name: str, extra: Sequence[str]) -> None:
    """One skill directory, with the `SKILL.md` frontmatter discovery reads."""
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: The {name} skill.\n---\n\n# {name}\n", encoding="utf-8"
    )
    for relative in extra:
        path = skill / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{name}: {relative}\n", encoding="utf-8")


def _written(frameworks: Mapping[str, Sequence[str]], bundles: Mapping[str, Sequence[str]]) -> str:
    """The written catalog: one description per framework, one manifest per bundle."""
    bundle_tables = (
        f'[bundles.{name}]\ndescription = "The {name} bundle."\nitems = {list(items)!r}\n'
        for name, items in bundles.items()
    )
    framework_tables = (
        f'[frameworks.{name}]\ndescription = "The {name} framework."\n' for name in frameworks
    )
    return "\n".join((*bundle_tables, *framework_tables))


def source(content: Path, name: str) -> Path:
    """The directory a pool skill occupies inside the content tree."""
    return content / "pool" / "skills" / name


def target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str = "project") -> Path:
    """An empty directory, made the working directory, the home and a pipe.

    `tmp_path` itself carries a `.git` marker, and `root` is a subdirectory of
    it — a repository with the command run from inside it, the ordinary case
    (https://github.com/panlabs-tech/overpower/issues/40). The marker sits
    *above* `root`, never inside it, so every existing `root.iterdir()`
    assertion keeps seeing exactly what `install` wrote and nothing else. A
    test of the *outside-a-repository* refusal builds its own bare directory
    instead of calling this.
    """
    (tmp_path / ".git").mkdir(exist_ok=True)
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(root)
    _sandboxed(monkeypatch, tmp_path)
    monkeypatch.setattr(cli, "_out", pinned(tty=False))
    return root


def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """A repository and a home that are **different directories**, and the CLI in it.

    `target` puts the two on top of each other — the `.git` marker sits on
    `tmp_path`, which is also `HOME` — and for `install` that costs nothing,
    because one command writes in one scope. `doctor` reads **both scopes in one
    output**, so a home that is also the repository would make every project
    place and its global twin the same directory on disk: the counts double and
    a divergence between them can never exist. Pulling them apart is what makes
    the two halves of the screen separately assertable.

    Answers `(repository, home)`, with the working directory inside the
    repository — the ordinary case, and the one where `install` and `doctor`
    disagree about the root on purpose: `install` writes where you stand,
    `doctor` reads the repository, so that running it from a subdirectory cannot
    answer *"nothing installed"* about a repository that is fully equipped.
    """
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    root = tmp_path / "repo"
    root.mkdir(parents=True, exist_ok=True)
    (root / ".git").mkdir(exist_ok=True)
    monkeypatch.chdir(root)
    _sandboxed(monkeypatch, home)
    monkeypatch.setattr(cli, "_out", pinned(tty=False))
    return root, home


def _sandboxed(monkeypatch: pytest.MonkeyPatch, home: Path) -> None:
    """Point every machine variable the product can read at the sandbox."""
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    for anchor in ANCHORS:
        monkeypatch.delenv(anchor, raising=False)
    # Rich reads `COLUMNS` off the environment mapping it captured at
    # construction, so this pins the width of the error panel, which is the one
    # screen that does not go through the console pinned in `pinned`.
    monkeypatch.setenv("COLUMNS", "100")


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
    """Every file below `root`, relative and separator-normalised.

    `Path.walk(follow_symlinks=True)`, not `rglob` — a global-scope landing may
    be a symlink, and the whole point of the central identity
    (https://github.com/panlabs-tech/overpower/issues/40) is that content
    reachable *through* one still counts. `rglob`'s own `recurse_symlinks` is
    3.13+ only; `Path.walk` carries the same option since 3.12, which is the
    floor here. A junction needs no opt-in: it is not a symlink
    (`os.path.islink()` is `False` for one), so the walk always descends into
    it regardless of `follow_symlinks`.
    """
    return {
        (base / name).relative_to(root).as_posix()
        for base, _dirs, names in root.walk(follow_symlinks=True)
        for name in names
    }


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
