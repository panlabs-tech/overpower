"""The `doctor`: the terminal, the integrity of what landed, and the exit code.

Mirror of `src/overpower/inspection.py`, and every case goes through the CLI —
the one seam the doctrine allows — with a real repository and a real home built
in `tmp_path`. There is no filesystem double (ADR 0010), which matters more here
than anywhere else in the suite: two of the three checks are *about* filesystem
objects a double would have to fake, a link that resolves nowhere and a link that
a clone turned into text.

The equipment under inspection is written by `install` and not by hand, so a
change to where the product writes cannot leave these tests asserting a layout
nothing produces any more.

**The `core.symlinks=false` case runs real `git`**, and the reason is that the
premise *is* the finding: `git status` staying clean over a broken link is what
makes the `doctor` necessary, and only git can witness that. The link is put into
the source repository through `hash-object` plus `update-index --cacheinfo
120000`, never through `Path.symlink_to` — that is the real scenario (a
repository equipped on one machine, cloned on another), and it is also the only
spelling that behaves identically on the nine cells, since whether a locally
created link is *recorded* as one depends on the platform and on privilege.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING

from tests.support.git_remote import git
from tests.support.project import AGENTS, CLAUDE, catalog_of, joined, run, workspace

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

    CaptureFixture = pytest.CaptureFixture[str]

CURSOR = ".cursor/skills"
"""Where `cursor` reads skills on the machine.

Its own directory, unlike in a project — which is what makes a global install of
`claude-code,cursor` a canonical copy plus a link, and therefore the one shape
that can dangle.
"""

LINKED = "alias.md"
"""The name of the link inside the equipped skill, in the fixture and the finding."""


def must(result: subprocess.CompletedProcess[str]) -> subprocess.CompletedProcess[str]:
    """Fail where the fixture is built, not where the product is asserted."""
    assert result.returncode == 0, result.stderr
    return result


def commit_a_symlink(source: Path, at: str, target: str) -> None:
    """Record `at` as a symlink pointing at `target`, through git's own plumbing.

    `Path.symlink_to` is deliberately not used. Whether git *records* a locally
    created link as mode `120000` depends on the platform and on whether the
    machine grants the privilege at all, so building the index entry directly is
    what makes the same commit exist on the nine cells — and it is the honest
    scenario too, since the repository carrying the link was equipped elsewhere.
    """
    blob = subprocess.run(
        # `git` by name and without a shell, the same call shape and the same
        # exemption `tests/support/git_remote.py` states once for the helper:
        # resolving an absolute path would pin the suite to the machine that
        # wrote it, and the product's own argv looks exactly like this.
        ["git", "hash-object", "-w", "--stdin"],  # noqa: S607
        cwd=source,
        input=target.encode("utf-8"),
        capture_output=True,
        check=True,
    )
    entry = f"120000,{blob.stdout.decode().strip()},{at}"
    must(git("update-index", "--add", "--cacheinfo", entry, cwd=source))


def equipped_clone(tmp_path: Path) -> Path:
    """A repository carrying a link inside a skill, cloned with links turned off.

    The clone is what a Windows machine gets by default: git auto-detects the
    capability and writes `core.symlinks=false` into the new repository, and the
    committed link materialises as an ordinary file carrying its own target.
    """
    source = tmp_path / "source"
    source.mkdir()
    must(git("init", "-b", "main", cwd=source))
    skill = source / CLAUDE / "alpha"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: alpha\n---\n", encoding="utf-8", newline="\n")
    must(git("add", "-A", cwd=source))
    commit_a_symlink(source, f"{CLAUDE}/alpha/{LINKED}", "SKILL.md")
    must(git("commit", "-m", "equipped", cwd=source))

    clone = tmp_path / "clone"
    must(git("clone", "-c", "core.symlinks=false", str(source), str(clone), cwd=tmp_path))
    return clone


def dirty(repository: Path) -> str:
    """What `git status` has to say. Empty is the whole premise of the finding."""
    return must(git("status", "--porcelain", cwd=repository)).stdout.strip()


# --------------------------------------------------------------------------- #
# the terminal half
# --------------------------------------------------------------------------- #


def test_the_doctor_reports_tty_colour_width_and_no_color_in_one_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The four facts that answer *"my screen came out strange"* with no round trip."""
    # given
    workspace(tmp_path, monkeypatch)
    monkeypatch.setenv("NO_COLOR", "1")

    code, output = run(capsys, "doctor")

    said = joined(output)
    assert code == 0
    assert "tty no" in said
    assert "colour" in said
    assert "width 100 columns" in said
    assert "NO_COLOR 1" in said


def test_an_unset_no_color_is_reported_as_unset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """`NO_COLOR` is presence-based, so absent and empty are different answers."""
    # given
    workspace(tmp_path, monkeypatch)
    monkeypatch.delenv("NO_COLOR", raising=False)

    code, output = run(capsys, "doctor")

    assert code == 0
    assert "NO_COLOR unset" in joined(output)


# --------------------------------------------------------------------------- #
# the exit code
# --------------------------------------------------------------------------- #


def test_a_healthy_target_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """Installed, intact, agreeing: nothing to say and nothing to fail a gate on."""
    # given
    catalog_of(tmp_path, monkeypatch, "alpha")
    workspace(tmp_path, monkeypatch)
    run(capsys, "install", "--skill", "alpha", "--runtime", "claude-code,cursor", "--yes")

    code, output = run(capsys, "doctor")

    assert code == 0
    assert "no findings" in joined(output)


def test_nothing_installed_anywhere_is_healthy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """An empty target is not a defect: `doctor` counts zero and exits 0."""
    # given
    workspace(tmp_path, monkeypatch)

    code, output = run(capsys, "doctor")

    assert code == 0
    assert "0 artifacts · 0 places" in joined(output)


def test_outside_a_repository_the_doctor_still_answers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """`install` refuses without git and `doctor` does not, and the axis is what each does.

    Refusing to diagnose because there is no repository would refuse exactly
    where a diagnosis is cheapest to want: the machine half is still there, and
    the terminal half never needed git at all.
    """
    # given
    catalog_of(tmp_path, monkeypatch, "alpha")
    _, home = workspace(tmp_path, monkeypatch)
    run(capsys, "install", "--skill", "alpha", "--runtime", "claude-code", "--global", "--yes")
    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.chdir(outside)

    code, output = run(capsys, "doctor")

    assert code == 0
    assert "1 artifact · 1 place" in joined(output)
    assert (home / CLAUDE / "alpha" / "SKILL.md").is_file()


# --------------------------------------------------------------------------- #
# `core.symlinks=false`, where the git lies and `git status` stays clean
# --------------------------------------------------------------------------- #


def test_a_link_that_became_a_text_file_is_found_with_a_clean_git_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The exact point where axiom 2 does not answer on its own.

    Reproduced here end to end: git auto-detects the capability and records it
    into the clone, a committed link checks out as a text file carrying its own
    target, and **`git status` reports nothing**. The clean status is asserted
    alongside the finding, because it is the premise the finding exists for —
    without it the `doctor` would be duplicating a question git already answers.
    """
    # given
    workspace(tmp_path, monkeypatch)
    clone = equipped_clone(tmp_path)
    monkeypatch.chdir(clone)

    code, output = run(capsys, "doctor")

    said = joined(output)
    assert dirty(clone) == ""
    assert not (clone / CLAUDE / "alpha" / LINKED).is_symlink()
    assert code == 3
    assert "link became a text file" in said
    assert LINKED in said


def test_the_same_text_file_is_not_a_finding_where_links_are_enabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The gate is what makes the check precise instead of a guess.

    With links working, a one-line file naming a sibling is a one-line file
    naming a sibling. Only a clone that recorded `core.symlinks=false` turns the
    same bytes into the measured failure, so the config is half the finding.
    """
    # given
    catalog_of(tmp_path, monkeypatch, "alpha")
    root, _ = workspace(tmp_path, monkeypatch)
    run(capsys, "install", "--skill", "alpha", "--runtime", "claude-code", "--yes")
    (root / CLAUDE / "alpha" / LINKED).write_text("SKILL.md", encoding="utf-8", newline="\n")

    code, output = run(capsys, "doctor")

    assert code == 0
    assert "link became a text file" not in joined(output)


# --------------------------------------------------------------------------- #
# a link that resolves nowhere
# --------------------------------------------------------------------------- #


def test_a_link_in_global_scope_that_does_not_resolve_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """A dangling link is invisible equipment: the name is listed and nothing is there.

    The link is the product's own — the rung the global ladder climbs — and what
    breaks it is the canonical going away, which is exactly how it happens: a
    `~/.claude/skills` cleared out by hand leaves every other runtime pointing at
    a hole, with no error anywhere and nothing on the machine to audit it.
    """
    # given
    catalog_of(tmp_path, monkeypatch, "alpha")
    _, home = workspace(tmp_path, monkeypatch)
    run(
        capsys,
        "install",
        "--skill",
        "alpha",
        "--runtime",
        "claude-code,cursor",
        "--global",
        "--yes",
    )
    assert (home / CURSOR / "alpha" / "SKILL.md").is_file()
    shutil.rmtree(home / CLAUDE / "alpha")

    code, output = run(capsys, "doctor")

    said = joined(output)
    assert code == 3
    assert "dangling link" in said
    assert "~/.cursor/skills/alpha/" in said


# --------------------------------------------------------------------------- #
# copies of one artifact that disagree
# --------------------------------------------------------------------------- #


def test_two_copies_of_one_artifact_that_differ_are_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The payment of the debt #9 took on: copying gave up the single point of truth.

    The decision to copy rather than link in a project accepted that cost and
    named the `doctor` as its mitigation. Without this line #9 keeps the
    expensive half of its decision and loses the half that compensates for it.
    """
    # given
    catalog_of(tmp_path, monkeypatch, "alpha")
    root, _ = workspace(tmp_path, monkeypatch)
    run(capsys, "install", "--skill", "alpha", "--runtime", "claude-code,cursor", "--yes")
    (root / AGENTS / "alpha" / "SKILL.md").write_text("edited by hand\n", encoding="utf-8")

    code, output = run(capsys, "doctor")

    said = joined(output)
    assert code == 3
    assert "copies of `alpha` differ" in said
    assert f"{CLAUDE}/alpha/" in said
    assert f"{AGENTS}/alpha/" in said


def test_copies_that_agree_are_not_reported_as_divergent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """Two real copies of one install agree, and agreeing is not a finding."""
    # given
    catalog_of(tmp_path, monkeypatch, "alpha", extra=("references/one.md",))
    workspace(tmp_path, monkeypatch)
    run(capsys, "install", "--skill", "alpha", "--runtime", "claude-code,cursor", "--yes")

    code, output = run(capsys, "doctor")

    assert code == 0
    assert "differ" not in joined(output)


def test_a_file_only_one_copy_carries_is_a_divergence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The digest folds names in alongside bytes, so a file only one copy has counts."""
    # given
    catalog_of(tmp_path, monkeypatch, "alpha")
    root, _ = workspace(tmp_path, monkeypatch)
    run(capsys, "install", "--skill", "alpha", "--runtime", "claude-code,cursor", "--yes")
    (root / AGENTS / "alpha" / "leftover.md").write_text("yesterday\n", encoding="utf-8")

    code, output = run(capsys, "doctor")

    assert code == 3
    assert "copies of `alpha` differ" in joined(output)


def test_the_repository_and_the_machine_are_not_compared_against_each_other(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """Two scopes hold independent installs, and calling those divergent is noise.

    A machine equipped in March and a repository equipped in August are both
    correct; the finding is about copies of **one** write, which is a fact inside
    one scope.
    """
    # given
    content = catalog_of(tmp_path, monkeypatch, "alpha")
    root, home = workspace(tmp_path, monkeypatch)
    run(capsys, "install", "--skill", "alpha", "--runtime", "claude-code", "--global", "--yes")
    (content / "pool" / "skills" / "alpha" / "SKILL.md").write_text(
        "---\nname: alpha\ndescription: A newer alpha.\n---\n", encoding="utf-8"
    )
    run(capsys, "install", "--skill", "alpha", "--runtime", "claude-code", "--yes")
    machine = (home / CLAUDE / "alpha" / "SKILL.md").read_text(encoding="utf-8")
    repository = (root / CLAUDE / "alpha" / "SKILL.md").read_text(encoding="utf-8")

    code, output = run(capsys, "doctor")

    assert machine != repository
    assert code == 0
    assert "differ" not in joined(output)


# --------------------------------------------------------------------------- #
# the answer is about writes, never about one write per artifact
# --------------------------------------------------------------------------- #


def test_one_artifact_in_two_runtime_paths_counts_as_one_artifact_and_two_places(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The graft lock, asserted on the only shape v0.1.0 can produce.

    A report that assumed *"one artifact, one write, all of it inside the
    target"* would count two artifacts here, and v0.2 — where one artifact costs
    a second write, possibly outside the repository — would be a rewrite of the
    answer instead of a sum.
    """
    # given
    catalog_of(tmp_path, monkeypatch, "alpha")
    workspace(tmp_path, monkeypatch)
    run(capsys, "install", "--skill", "alpha", "--runtime", "claude-code,cursor", "--yes")

    code, output = run(capsys, "doctor")

    assert code == 0
    assert "1 artifact · 2 places" in joined(output)


def test_both_scopes_are_read_in_one_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """One output over two roots, which is why `doctor` has no `--global`.

    The count is what proves it: the repository alone would answer one, and the
    machine alone would answer one.
    """
    # given
    catalog_of(tmp_path, monkeypatch, "alpha", "beta")
    workspace(tmp_path, monkeypatch)
    run(capsys, "install", "--skill", "alpha", "--runtime", "claude-code", "--yes")
    run(capsys, "install", "--skill", "beta", "--runtime", "claude-code", "--global", "--yes")

    code, output = run(capsys, "doctor")

    assert code == 0
    assert "2 artifacts · 2 places" in joined(output)
