"""What a request costs: the plan that comes out, and every line that is refused.

Mirror of `src/overpower/planning.py`. The refusals go through the CLI, because
what they promise is an **exit code** and that is only observable there; the
shape of the plan is asserted over values, the way the runtime table already is,
because the plan is the vocabulary the screen and the writer share and its
*shape* is what the graft lock is about.

Nothing here reaches the disk except to build a real content tree for the
product to walk — the writing side is next door, in `test_writing.py`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from overpower.discovery import load_catalog
from overpower.planning import DirectoryTree, Request, WriteMode, plan_for
from overpower.runtimes import Scope
from tests.support.project import CLAUDE, catalog_of, joined, run, target

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_the_copy_class_lands_in_a_folder_and_the_planner_says_which(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The implemented half of the two-form destination, straight from the planner.

    The other half — a destination that is a document and a key — is refused by
    name in `test_writing.py`, which is where the operation would live.
    """
    # given
    content = catalog_of(tmp_path, monkeypatch, "alpha")
    root = target(tmp_path, monkeypatch)
    catalog = load_catalog(content, tmp_path / "packaged" / "catalog.toml")

    plan = plan_for(
        Request(skills=("alpha",), runtimes=("claude-code",), scope=Scope.PROJECT), catalog, root
    )

    assert [write.destination for write in plan.writes] == [
        DirectoryTree(path=root / CLAUDE / "alpha")
    ]
    assert [write.mode for write in plan.writes] == [WriteMode.COPY]


def test_comma_and_repetition_both_accumulate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """What `ruff --select E,F,W` and `gh pr create --reviewer a,b --reviewer c` taught."""
    # given
    catalog_of(tmp_path, monkeypatch, "alpha", "beta", "gamma")
    root = target(tmp_path, monkeypatch)

    code, _ = run(
        capsys,
        *("install", "--skill", "alpha", "--skill", "beta,gamma"),
        *("--runtime", "claude-code", "--yes"),
    )

    assert code == 0
    assert {entry.name for entry in (root / CLAUDE).iterdir()} == {"alpha", "beta", "gamma"}


def test_a_runtime_with_no_directory_in_the_target_is_created_and_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A named runtime is an equipped runtime — the silent skip is not inherited.

    Upstream returns `success: true, skipped: true` for a non-universal runtime
    whose root directory does not exist, and writes nothing (ADR 0008).
    """
    # given
    catalog_of(tmp_path, monkeypatch, "alpha")
    root = target(tmp_path, monkeypatch)
    assert not (root / ".devin").exists()

    code, _ = run(capsys, "install", "--skill", "alpha", "--runtime", "devin", "--yes")

    assert code == 0
    assert (root / ".devin" / "skills" / "alpha" / "SKILL.md").is_file()


def test_a_missing_runtime_without_a_terminal_exits_two(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Guessing a destination is the class of error this product exists not to commit."""
    # given
    catalog_of(tmp_path, monkeypatch, "alpha")
    root = target(tmp_path, monkeypatch)

    code, _ = run(capsys, "install", "--skill", "alpha")

    assert code == 2
    assert list(root.iterdir()) == []


def test_a_runtime_outside_the_table_exits_two_naming_the_closed_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The table is closed, and there is no `--dir` hatch in v0.1.0."""
    # given
    catalog_of(tmp_path, monkeypatch, "alpha")
    target(tmp_path, monkeypatch)

    code, output = run(capsys, "install", "--skill", "alpha", "--runtime", "cursr")

    assert code == 2
    assert "cursr" in joined(output)
    assert "claude-code" in joined(output)


def test_a_skill_outside_the_catalog_exits_two(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # given
    catalog_of(tmp_path, monkeypatch, "alpha")
    target(tmp_path, monkeypatch)

    code, output = run(capsys, "install", "--skill", "alfa", "--runtime", "claude-code")

    assert code == 2
    assert "alfa" in joined(output)


def test_naming_nothing_exits_two_instead_of_writing_nothing_and_saying_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """An empty manifest is a typo, and an empty plan at exit 0 is the lie to avoid."""
    # given
    catalog_of(tmp_path, monkeypatch, "alpha")
    root = target(tmp_path, monkeypatch)

    code, _ = run(capsys, "install", "--runtime", "claude-code")

    assert code == 2
    assert list(root.iterdir()) == []
