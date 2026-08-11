"""The write boundary: what the plan promised is what the disk carries.

Mirror of `src/overpower/writing.py`, and the subject is the boundary rather
than the function — every case here goes through the CLI, with `tmp_path` as the
working directory and as `HOME`, because that is the one seam the doctrine
allows and because a writer asserted directly could not show the *screen* half
of the identity, which is half of the defect it exists to catch.

The central assertion lives here for the same reason: it says the writer put on
disk exactly what the plan announced, and nothing else.

    paths(stdout of --dry-run) == paths(stdout of the real run) == walk of the disk

with two riders — the dry run leaves nothing behind, and the two exit codes
coincide. It runs on the nine cells because it is the property most likely to
break by platform: the path separator (the table keeps `/` and the disk does
not), a filesystem that does not distinguish case, and the measured case of
`WindowsPath("/home/dev").is_absolute()` being `False`.

The three mandatory traps are behaviour of a real filesystem, and a double that
did not implement symlink and junction for real would go green exactly where the
product breaks (ADR 0010).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest

from overpower import cli, remote, writing
from overpower.discovery import Artifact, ArtifactType
from overpower.planning import DocumentKey, Landing, Plan, Selection, Write, WriteMode
from overpower.writing import UnsupportedWriteError, execute, points_elsewhere
from tests.support import git_remote
from tests.support.project import (
    AGENTS,
    CLAUDE,
    catalog_of,
    files_under,
    joined,
    landings_of,
    paths_in,
    pinned,
    run,
    source,
    target,
)

if TYPE_CHECKING:
    from collections.abc import Callable


# --------------------------------------------------------------------------- #
# the central assertion
# --------------------------------------------------------------------------- #


def test_the_plan_the_screen_and_the_disk_name_the_same_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """One assertion, and it proves the three measured lies of `npx skills` at once.

    The disk side is a **walk**: `landings_of` maps every file it finds back to
    the path the screen announced, and a file under no announced path maps to
    itself. So a directory the plan never named breaks the equality, and so does
    a path announced and never written.
    """
    # given
    catalog_of(tmp_path, monkeypatch, "alpha", "beta")
    dry_root = target(tmp_path, monkeypatch, "dry")
    real_root = target(tmp_path, monkeypatch, "real")
    selectors = ("install", "--skill", "alpha,beta", "--runtime", "claude-code", "--runtime")

    monkeypatch.chdir(dry_root)
    dry_code, dry_out = run(capsys, *selectors, "cursor", "--dry-run")
    monkeypatch.chdir(real_root)
    real_code, real_out = run(capsys, *selectors, "cursor")

    announced = paths_in(real_out)
    assert paths_in(dry_out) == announced
    assert landings_of(files_under(real_root), announced) == announced
    assert list(dry_root.iterdir()) == []
    assert dry_code == real_code == 0


def test_the_three_way_identity_holds_with_all_three_selectors_mixed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """#39: framework, bundle and skill on one line do not break the identity.

    Three distinct names — one per selector, none shared with a bundle — so this
    proves the identity and not the fixed collision order, which has its own
    test right below.
    """
    # given
    catalog_of(
        tmp_path,
        monkeypatch,
        "alpha",
        "beta",
        frameworks={"matt-pocock": ("gamma",)},
        bundles={"api-python": ("beta",)},
    )
    dry_root = target(tmp_path, monkeypatch, "dry")
    real_root = target(tmp_path, monkeypatch, "real")
    selectors = (
        "install",
        "--ai-framework",
        "matt-pocock",
        "--bundle",
        "api-python",
        "--skill",
        "alpha",
        "--runtime",
        "claude-code",
    )

    monkeypatch.chdir(dry_root)
    dry_code, dry_out = run(capsys, *selectors, "--dry-run")
    monkeypatch.chdir(real_root)
    real_code, real_out = run(capsys, *selectors)

    announced = paths_in(real_out)
    assert paths_in(dry_out) == announced
    assert landings_of(files_under(real_root), announced) == announced
    assert list(dry_root.iterdir()) == []
    assert dry_code == real_code == 0


def test_the_identity_holds_for_a_skill_that_came_from_a_remote(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """#42: `--from` moves where the source comes from, and nothing about the identity.

    Worth its own case because it is the first source that lives **outside the
    package** — a scratch directory that exists only for the length of the
    command — and because a dry run that resolved the remote differently from the
    real run would be a report about a different installation. The embedded
    catalog is made to explode, so this also proves the write path never reaches
    for it.
    """

    # given
    def unread(*_: object, **__: object) -> object:
        message = "the embedded catalog was read while `--from` was given"
        raise AssertionError(message)

    dry_root = target(tmp_path, monkeypatch, "dry")
    real_root = target(tmp_path, monkeypatch, "real")
    monkeypatch.setattr(cli, "load_catalog", unread)
    local = git_remote.build(tmp_path / "origin", git_remote.skill_files("alpha", "beta"))
    monkeypatch.setattr(remote, "fetch_with_git", git_remote.instead_of_github(local))
    selectors = (
        "install",
        "--from",
        f"https://github.com/owner/repo/tree/{local.branch}",
        "--skill",
        "alpha,beta",
        "--runtime",
        "claude-code",
        "--runtime",
        "cursor",
    )

    monkeypatch.chdir(dry_root)
    dry_code, dry_out = run(capsys, *selectors, "--dry-run")
    monkeypatch.chdir(real_root)
    real_code, real_out = run(capsys, *selectors)

    announced = paths_in(real_out)
    assert paths_in(dry_out) == announced
    assert landings_of(files_under(real_root), announced) == announced
    assert list(dry_root.iterdir()) == []
    assert dry_code == real_code == 0


def test_a_collided_destination_ends_with_the_individual_artifacts_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """#39: the order is framework -> bundle -> individual artifact, the last write standing.

    Detecting the intra-command collision is not the point — this asserts *which*
    content survives it, which is the only assertion a fixed order buys.
    """
    # given
    content = catalog_of(tmp_path, monkeypatch, "shared", frameworks={"matt-pocock": ("shared",)})
    (source(content, "shared") / "SKILL.md").write_text(
        "---\nname: shared\ndescription: The pool version.\n---\n\npool\n", encoding="utf-8"
    )
    (content / "frameworks" / "matt-pocock" / "skills" / "shared" / "SKILL.md").write_text(
        "---\nname: shared\ndescription: The framework version.\n---\n\nframework\n",
        encoding="utf-8",
    )
    root = target(tmp_path, monkeypatch)

    code, _ = run(
        capsys,
        "install",
        "--ai-framework",
        "matt-pocock",
        "--skill",
        "shared",
        "--runtime",
        "claude-code",
        "--yes",
    )

    assert code == 0
    landed = (root / CLAUDE / "shared" / "SKILL.md").read_text(encoding="utf-8")
    assert "pool" in landed
    assert "framework" not in landed


def test_the_selected_artifacts_land_in_every_selected_path_as_a_real_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Copy, everywhere, never a link: under `core.symlinks=false` a link is a text file."""
    # given
    content = catalog_of(tmp_path, monkeypatch, "alpha", "beta", extra=("references/one.md",))
    root = target(tmp_path, monkeypatch)

    code, _ = run(
        capsys, "install", "--skill", "alpha,beta", "--runtime", "claude-code,cursor", "--yes"
    )

    assert code == 0
    for landing in (CLAUDE, AGENTS):
        assert {entry.name for entry in (root / landing).iterdir()} == {"alpha", "beta"}
        for name in ("alpha", "beta"):
            landed = root / landing / name
            assert not landed.is_symlink()
            assert files_under(landed) == files_under(source(content, name))


# --------------------------------------------------------------------------- #
# the three mandatory traps
# --------------------------------------------------------------------------- #


def test_removing_a_symlinked_destination_does_not_write_through_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """#9: `rmtree(ignore_errors=True)` over a symlink removes nothing, silently.

    The `copytree` that follows then writes *through* the link and corrupts
    whatever it pointed at.
    """
    # given
    catalog_of(tmp_path, monkeypatch, "alpha")
    root = target(tmp_path, monkeypatch)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "precious.md").write_text("do not touch\n", encoding="utf-8")
    destination = root / CLAUDE / "alpha"
    destination.parent.mkdir(parents=True)
    destination.symlink_to(elsewhere, target_is_directory=True)

    code, _ = run(capsys, "install", "--skill", "alpha", "--runtime", "claude-code", "--yes")

    assert code == 0
    assert files_under(elsewhere) == {"precious.md"}
    assert not destination.is_symlink()
    assert (destination / "SKILL.md").is_file()


@pytest.mark.skipif(sys.platform != "win32", reason="a junction only exists on Windows")
def test_removing_a_junction_uses_the_predicate_that_recognises_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """#19: `os.path.islink()` is `False` for a junction and `rmtree` refuses it anyway.

    The idiomatic `if islink: unlink else: rmtree` therefore breaks exactly on
    Windows. Keyed on `sys.platform`, never on an environment variable: a
    variable can be forgotten in the workflow and the job goes green skipping
    everything.
    """
    import _winapi  # noqa: PLC0415 — a Windows-only import inside a Windows-only test

    # given
    catalog_of(tmp_path, monkeypatch, "alpha")
    root = target(tmp_path, monkeypatch)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "precious.md").write_text("do not touch\n", encoding="utf-8")
    destination = root / CLAUDE / "alpha"
    destination.parent.mkdir(parents=True)
    # `_winapi` is private and Windows-only — the API #19 settled on — and the
    # `static` job runs on ubuntu, where its stub carries no such attribute. The
    # cast is what the suppression costs, and it also records the measured
    # signature: the API accepts `str` only, and a `Path` raises `TypeError`.
    create_junction = cast(
        "Callable[[str, str], None]",
        _winapi.CreateJunction,  # pyright: ignore[reportAttributeAccessIssue,reportUnknownMemberType]
    )
    create_junction(str(elsewhere), str(destination))

    code, _ = run(capsys, "install", "--skill", "alpha", "--runtime", "claude-code", "--yes")

    assert code == 0
    assert files_under(elsewhere) == {"precious.md"}
    assert (destination / "SKILL.md").is_file()


def test_installing_over_a_previous_version_leaves_no_stale_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """#9: `dirs_exist_ok=True` overlays without syncing, so yesterday's file survives.

    It is this case that binds the write semantics to the three-way identity: if
    the disk has to equal the plan, the destination has to end up **equal** to
    the source, not overlaid on it.
    """
    # given
    content = catalog_of(tmp_path, monkeypatch, "alpha")
    root = target(tmp_path, monkeypatch)
    run(capsys, "install", "--skill", "alpha", "--runtime", "claude-code", "--yes")
    stale = root / CLAUDE / "alpha" / "references" / "gone.md"
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_text("yesterday\n", encoding="utf-8")

    code, _ = run(capsys, "install", "--skill", "alpha", "--runtime", "claude-code", "--yes")

    assert code == 0
    assert not stale.exists()
    assert files_under(root / CLAUDE / "alpha") == files_under(source(content, "alpha"))


def test_an_internal_link_of_the_skill_arrives_as_a_link(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Without `symlinks=True` a link inside the source lands as a second copy."""
    # given
    content = catalog_of(tmp_path, monkeypatch, "alpha")
    (source(content, "alpha") / "alias.md").symlink_to("SKILL.md")
    root = target(tmp_path, monkeypatch)

    code, _ = run(capsys, "install", "--skill", "alpha", "--runtime", "claude-code", "--yes")

    assert code == 0
    assert (root / CLAUDE / "alpha" / "alias.md").is_symlink()


# --------------------------------------------------------------------------- #
# write semantics
# --------------------------------------------------------------------------- #


def test_running_the_same_command_twice_writes_again_and_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The write is unconditional: no byte comparison, no backup, no question."""
    # given
    catalog_of(tmp_path, monkeypatch, "alpha")
    root = target(tmp_path, monkeypatch)
    first, _ = run(capsys, "install", "--skill", "alpha", "--runtime", "claude-code")

    second, _ = run(capsys, "install", "--skill", "alpha", "--runtime", "claude-code")

    assert first == second == 0
    assert (root / CLAUDE / "alpha" / "SKILL.md").is_file()


def test_a_failure_in_the_middle_leaves_what_it_wrote_and_says_where_it_stopped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """No rollback: half an installation is a diagnosis, and the message is the report.

    `.agents` is a *file* here, so the second landing cannot be created. The
    first one already happened, and it stays.
    """
    # given
    catalog_of(tmp_path, monkeypatch, "alpha")
    root = target(tmp_path, monkeypatch)
    (root / ".agents").write_text("not a directory\n", encoding="utf-8")

    code, output = run(
        capsys, "install", "--skill", "alpha", "--runtime", "claude-code,cursor", "--yes"
    )

    assert code == 1
    assert "wrote 1 of 2" in joined(output)
    assert (root / CLAUDE / "alpha" / "SKILL.md").is_file()


def test_a_destination_that_is_a_document_key_is_refused_by_name(tmp_path: Path) -> None:
    """The graft class exists in the model and has no operation yet.

    Modelling a destination as a folder path is the regression that turns v0.2
    into a rewrite of the flow instead of the sum of one operation, so the shape
    is here and the missing half says so out loud. Built by hand because nothing
    in the v0.1.0 catalog can produce one — there is no MCP server and no hook.
    """
    # given
    grafted = Artifact(
        type=ArtifactType.SKILL,
        name="probe",
        path=tmp_path / "source",
        description="The graft that has no operation yet.",
        files=1,
        size=1,
    )
    write = Write(
        source=tmp_path / "source",
        destination=DocumentKey(path=tmp_path / ".mcp.json", key="probe"),
        mode=WriteMode.COPY,
        files=1,
    )
    plan = Plan(
        root=tmp_path,
        selections=(
            Selection(
                name="probe",
                artifacts=(grafted,),
                landings=(
                    Landing(
                        place=tmp_path / ".mcp.json", readers=("claude-code",), writes=(write,)
                    ),
                ),
            ),
        ),
    )

    with pytest.raises(UnsupportedWriteError):
        execute(plan)


# --------------------------------------------------------------------------- #
# #40: global scope climbs the canonical + link ladder
# --------------------------------------------------------------------------- #


def test_the_global_ladder_lands_a_canonical_copy_and_a_link_pointing_at_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`claude-code` precedes `cursor` in table order: it is the real copy.

    `points_elsewhere` — the same predicate the removal trap uses — is what
    makes the second half of this assertion true on every platform: a symlink
    on POSIX, a junction on Windows, never `is_symlink()` alone.
    """
    # given
    catalog_of(tmp_path, monkeypatch, "alpha")
    target(tmp_path, monkeypatch)

    code, _ = run(
        capsys,
        "install",
        "--skill",
        "alpha",
        "--runtime",
        "claude-code,cursor",
        "--global",
        "--yes",
    )

    assert code == 0
    canonical = tmp_path / CLAUDE / "alpha"
    linked = tmp_path / ".cursor" / "skills" / "alpha"
    assert canonical.is_dir()
    assert not points_elsewhere(canonical)
    assert (canonical / "SKILL.md").is_file()
    assert points_elsewhere(linked)
    assert (linked / "SKILL.md").is_file()
    if sys.platform != "win32":
        # relative, so the link survives $HOME moving and the machine cloning
        # — a junction's target is always absolute (#19), so this half of the
        # property is POSIX only.
        assert not linked.readlink().is_absolute()


def test_force_detaches_an_existing_link_before_writing_the_new_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """#9's removal trap, exercised on the write this issue adds: link, not tree.

    `rmtree(ignore_errors=True)` over a symlink removes nothing and the
    `copytree` that follows would write *through* it — here the reinstall has
    to detach the old link first, or the second run corrupts the canonical it
    points at.
    """
    # given
    catalog_of(tmp_path, monkeypatch, "alpha")
    target(tmp_path, monkeypatch)
    selectors = ("install", "--skill", "alpha", "--runtime", "claude-code,cursor", "--global")
    run(capsys, *selectors, "--yes")
    linked = tmp_path / ".cursor" / "skills" / "alpha"
    assert points_elsewhere(linked)

    code, _ = run(capsys, *selectors, "--force", "--yes")

    assert code == 0
    canonical = tmp_path / CLAUDE / "alpha"
    assert canonical.is_dir()
    assert not points_elsewhere(canonical)
    assert points_elsewhere(linked)
    assert (linked / "SKILL.md").is_file()


def test_the_three_way_identity_holds_in_global_scope_including_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """#40: the plan now carries mode, and what the screen calls link has to be link on disk."""
    # given
    catalog_of(tmp_path, monkeypatch, "alpha", "beta")
    monkeypatch.setattr(cli, "_out", pinned(tty=False))
    dry_home = tmp_path / "dry"
    real_home = tmp_path / "real"
    dry_home.mkdir()
    real_home.mkdir()
    selectors = ("install", "--skill", "alpha,beta", "--runtime", "claude-code,cursor", "--global")

    monkeypatch.setenv("HOME", str(dry_home))
    monkeypatch.setenv("USERPROFILE", str(dry_home))
    dry_code, dry_out = run(capsys, *selectors, "--dry-run")

    monkeypatch.setenv("HOME", str(real_home))
    monkeypatch.setenv("USERPROFILE", str(real_home))
    real_code, real_out = run(capsys, *selectors, "--yes")

    announced = paths_in(real_out)
    assert paths_in(dry_out) == announced
    assert landings_of(files_under(real_home), announced) == announced
    assert list(dry_home.iterdir()) == []
    assert dry_code == real_code == 0

    # what the screen calls the non-canonical rung is what lands on disk:
    # a link on POSIX, a junction on Windows — never a real copy either way.
    rung = "junction" if sys.platform == "win32" else "link"
    assert rung in joined(dry_out)
    assert rung in joined(real_out)
    for name in ("alpha", "beta"):
        canonical = real_home / CLAUDE / name
        linked = real_home / ".cursor" / "skills" / name
        assert canonical.is_dir()
        assert not points_elsewhere(canonical)
        assert points_elsewhere(linked)
        assert (linked / "SKILL.md").is_file()


@pytest.mark.skipif(
    sys.platform == "win32", reason="the link rung is POSIX only; Windows takes the junction rung"
)
def test_a_symlink_that_cannot_be_created_degrades_to_a_copy_with_a_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Not reproducible on demand — FAT32, a network share, PyPy without parity.

    ADR 0010 rules out a fabricated filesystem; this is not one. A single call
    is stubbed at the exact seam `_land_link` isolates it behind, and everything
    downstream — the resulting copy, the report, the warning — is real.
    """
    # given
    catalog_of(tmp_path, monkeypatch, "alpha")
    target(tmp_path, monkeypatch)

    def refuse(self: Path, link_target: str, *, target_is_directory: bool = False) -> None:
        del self, link_target, target_is_directory
        message = "symlinks not supported on this filesystem"
        raise OSError(message)

    monkeypatch.setattr(Path, "symlink_to", refuse)

    code, output = run(
        capsys,
        "install",
        "--skill",
        "alpha",
        "--runtime",
        "claude-code,cursor",
        "--global",
        "--yes",
    )

    assert code == 0
    assert "degraded to copy" in joined(output)
    landed = tmp_path / ".cursor" / "skills" / "alpha"
    assert not landed.is_symlink()
    assert landed.is_dir()
    assert (landed / "SKILL.md").is_file()


@pytest.mark.skipif(sys.platform != "win32", reason="the junction rung is Windows only")
def test_a_junction_that_cannot_be_created_degrades_to_a_copy_with_a_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The Windows twin of the POSIX symlink-fallback test above, same seam, same reasoning."""
    # given
    catalog_of(tmp_path, monkeypatch, "alpha")
    target(tmp_path, monkeypatch)

    def refuse(source: Path, destination: Path) -> None:
        del source, destination
        message = "junction creation blocked"
        raise OSError(message)

    monkeypatch.setattr(writing, "_create_junction", refuse)

    code, output = run(
        capsys,
        "install",
        "--skill",
        "alpha",
        "--runtime",
        "claude-code,cursor",
        "--global",
        "--yes",
    )

    assert code == 0
    assert "degraded to copy" in joined(output)
    landed = tmp_path / ".cursor" / "skills" / "alpha"
    assert not points_elsewhere(landed)
    assert landed.is_dir()
    assert (landed / "SKILL.md").is_file()


@pytest.mark.skipif(sys.platform != "win32", reason="a junction only exists on Windows")
def test_the_global_ladder_lands_a_junction_on_windows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # given
    catalog_of(tmp_path, monkeypatch, "alpha")
    target(tmp_path, monkeypatch)

    code, _ = run(
        capsys,
        "install",
        "--skill",
        "alpha",
        "--runtime",
        "claude-code,cursor",
        "--global",
        "--yes",
    )

    assert code == 0
    canonical = tmp_path / CLAUDE / "alpha"
    linked = tmp_path / ".cursor" / "skills" / "alpha"
    assert canonical.is_dir()
    assert not canonical.is_symlink()
    assert linked.is_junction()
    assert (linked / "SKILL.md").is_file()


@pytest.mark.skipif(sys.platform != "win32", reason="a junction only exists on Windows")
def test_junction_creation_refuses_a_source_that_is_not_a_directory(tmp_path: Path) -> None:
    """#19: `_winapi.CreateJunction` validates existence, not type, and creates garbage."""
    from overpower.writing import (  # noqa: PLC0415 — direct unit test of the guard
        _create_junction,  # pyright: ignore[reportPrivateUsage]
    )

    source_file = tmp_path / "not-a-directory"
    source_file.write_text("x", encoding="utf-8")
    destination = tmp_path / "junction"

    with pytest.raises(NotADirectoryError):
        _create_junction(source_file, destination)

    assert not destination.exists()
