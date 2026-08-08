"""Mirror of `src/overpower/scope.py`."""

from __future__ import annotations

from typing import TYPE_CHECKING

from overpower.scope import git_root

if TYPE_CHECKING:
    from pathlib import Path


def test_a_directory_carrying_a_git_folder_is_its_own_root(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()

    assert git_root(tmp_path) == tmp_path


def test_a_subdirectory_of_a_repository_finds_the_root_above_it(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    nested = tmp_path / "src" / "overpower"
    nested.mkdir(parents=True)

    assert git_root(nested) == tmp_path


def test_a_git_file_counts_too(tmp_path: Path) -> None:
    """A worktree or a submodule carries a `.git` *file* — `gitdir: ...` — not a directory."""
    (tmp_path / ".git").write_text("gitdir: ../elsewhere\n", encoding="utf-8")

    assert git_root(tmp_path) == tmp_path


def test_outside_any_repository_is_none(tmp_path: Path) -> None:
    assert git_root(tmp_path) is None
