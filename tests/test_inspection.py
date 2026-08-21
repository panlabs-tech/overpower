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
from typing import TYPE_CHECKING

from overpower import remote
from overpower.writing import points_elsewhere
from tests.support.git_remote import build, git, instead_of_github
from tests.support.project import (
    AGENTS,
    CLAUDE,
    SLOT_VARIABLE,
    SLOTTED,
    catalog_of,
    custom_recipe,
    joined,
    run,
    workspace,
)

if TYPE_CHECKING:
    import subprocess
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
    blob = must(git("hash-object", "-w", "--stdin", cwd=source, stdin=target))
    entry = f"120000,{blob.stdout.strip()},{at}"
    must(git("update-index", "--add", "--cacheinfo", entry, cwd=source))


def equipped_source(tmp_path: Path) -> Path:
    """A repository carrying a link inside an equipped skill, committed as mode `120000`."""
    source = tmp_path / "source"
    source.mkdir()
    must(git("init", "-b", "main", cwd=source))
    skill = source / CLAUDE / "alpha"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: alpha\n---\n", encoding="utf-8", newline="\n")
    must(git("add", "-A", cwd=source))
    commit_a_symlink(source, f"{CLAUDE}/alpha/{LINKED}", "SKILL.md")
    must(git("commit", "-m", "equipped", cwd=source))
    return source


def cloned_with_links_off(tmp_path: Path, source: Path, *, config: Path | None = None) -> Path:
    """Clone `source` the way a machine without working links does.

    Two spellings of the same broken checkout, and `config` chooses between
    them. Without it, `core.symlinks=false` is passed to the clone and git
    records it in the **new repository** — the auto-detection the ticket names.
    With it, the value lives in the user's own config file, and the clone is
    stripped of anything it recorded about links so that file is the **only**
    source left.

    Stripping is what makes the second case the same case on the nine cells, and
    it cost a red Windows build to learn: git *also* probes the filesystem at
    clone time, so where links do not work it writes `symlinks = false` into the
    clone whatever the user's config says. Asserting that git had written
    nothing was asserting the platform. Unsetting afterwards heals nothing — the
    working tree is already on disk, text file and all — it only removes the
    second source of the answer.
    """
    clone = tmp_path / "clone"
    detected = () if config is not None else ("-c", "core.symlinks=false")
    environment = {} if config is None else {"GIT_CONFIG_GLOBAL": str(config)}
    must(git("clone", *detected, str(source), str(clone), cwd=tmp_path, env=environment))
    if config is not None:
        # exit 5 is `--unset` on a key that was not there, which is a fine outcome.
        git("config", "--unset", "core.symlinks", cwd=clone, env=environment)
    return clone


def machine_config_disabling_links(home: Path) -> Path:
    """`~/.gitconfig` with links turned off — the common Windows workaround."""
    config = home / ".gitconfig"
    config.write_text("[core]\n\tsymlinks = false\n", encoding="utf-8", newline="\n")
    return config


def dirty(repository: Path, config: Path | None = None) -> str:
    """What `git status` has to say. Empty is the whole premise of the finding.

    `config` has to be the same one the developer has, and finding that out cost
    a red test: with links *enabled*, `git status` reports the text file as a
    typechange (`T`) against the recorded mode `120000` and the premise
    evaporates. It is only clean for the person whose configuration turned links
    off — which is precisely the person the finding is for, and precisely why
    the git lies to them and to nobody else.
    """
    environment = {} if config is None else {"GIT_CONFIG_GLOBAL": str(config)}
    return must(git("status", "--porcelain", cwd=repository, env=environment)).stdout.strip()


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
    clone = cloned_with_links_off(tmp_path, equipped_source(tmp_path))
    monkeypatch.chdir(clone)

    code, output = run(capsys, "doctor")

    said = joined(output)
    assert dirty(clone) == ""
    assert not (clone / CLAUDE / "alpha" / LINKED).is_symlink()
    assert code == 3
    assert "link became a text file" in said
    assert LINKED in said


def test_links_turned_off_by_the_machine_and_not_by_the_clone_are_found_too(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The value can live in either file, and a reader of one of them misses the other.

    Measured on POSIX, where links do work: `core.symlinks=false` set only in
    the user's own config produces the **identical** broken checkout and the
    identical clean status, and git records nothing about links in the clone. So
    the fixture leaves that file as the only source — the clone is stripped of
    anything it recorded — and what is asserted is that the product still finds
    it. Reading only the repository's config would answer *"links are fine"*.
    """
    # given
    _, home = workspace(tmp_path, monkeypatch)
    config = machine_config_disabling_links(home)
    clone = cloned_with_links_off(tmp_path, equipped_source(tmp_path), config=config)
    monkeypatch.chdir(clone)

    code, output = run(capsys, "doctor")

    assert "symlinks" not in (clone / ".git" / "config").read_text(encoding="utf-8")
    assert dirty(clone, config) == ""
    assert code == 3
    assert "link became a text file" in joined(output)


def test_a_repository_that_re_enables_links_overrides_the_machine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """Git's own precedence: the repository's config is read last and therefore wins.

    Absent has to be distinguishable from present-and-true, or a clone that
    turns links back on could not undo a machine that turned them off — and the
    checkout it produces is not broken at all.
    """
    # given
    _, home = workspace(tmp_path, monkeypatch)
    config = machine_config_disabling_links(home)
    clone = cloned_with_links_off(tmp_path, equipped_source(tmp_path), config=config)
    must(git("config", "core.symlinks", "true", cwd=clone))
    monkeypatch.chdir(clone)

    code, output = run(capsys, "doctor")

    assert code == 0
    assert "link became a text file" not in joined(output)


def test_the_finding_survives_a_git_worktree_where_the_config_is_elsewhere(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """Measured: a linked worktree's gitdir carries `commondir` and **no config**.

    A reader that stopped at the `gitdir:` pointer would look for a file that
    does not exist and answer *"links are fine"* in every worktree — which is
    the layout `docs/agents/workflow.md` mandates for every branch of this
    repository, so the blind spot would be the one its own developers live in.
    """
    # given
    workspace(tmp_path, monkeypatch)
    clone = cloned_with_links_off(tmp_path, equipped_source(tmp_path))
    linked = tmp_path / "linked-worktree"
    must(git("worktree", "add", str(linked), "-b", "probe", cwd=clone))
    assert (linked / ".git").is_file()
    monkeypatch.chdir(linked)

    code, output = run(capsys, "doctor")

    assert code == 3
    assert "link became a text file" in joined(output)


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
    # The fixture is asserted before it is broken: the ladder degrades to a real
    # copy where a link cannot be created, and `SKILL.md` being there is equally
    # true of that path — `rmtree` would then leave a healthy copy and the test
    # would fail on the product instead of on its own premise.
    assert points_elsewhere(home / CURSOR / "alpha")
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


def test_a_graft_counts_as_an_artifact_and_its_document_as_the_place(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """A repository whose only installation is a graft used to read *"0 artifacts"*.

    Under a block headed *"what is installed"*, and with the server sitting in
    `.mcp.json` two lines below. The count was fed from `_landed_in` alone,
    which walks skill trees, so the graft class never reached it.

    Counting it is the consistent answer rather than the generous one: neither
    class carries provenance. `_landed_in` counts every tree sitting in a
    runtime path — including one a user made by hand — so a `doctor` that
    declined to count a server it could not prove it wrote would be applying to
    the graft class a rule the copy class never had.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": MCP_URL})
    root, _ = workspace(tmp_path, monkeypatch)
    run(capsys, "install", "--mcp", "cloudflare", "--runtime", "claude-code")
    approve(root, "cloudflare")

    code, output = run(capsys, "doctor")

    assert code == 0
    assert "1 artifact · 1 place" in joined(output)


def test_a_copy_and_a_graft_are_summed_into_one_pair_of_numbers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """One line of counting over two landing classes, which is what the block promises.

    The classes are counted apart and added, never merged into one set: a skill
    and a server may share a name — the pool namespaces by type — and a union
    over `(scope, name)` would silently answer one where the disk holds two.
    """
    # given
    catalog_of(tmp_path, monkeypatch, "alpha", mcps={"cloudflare": MCP_URL})
    root, _ = workspace(tmp_path, monkeypatch)
    run(capsys, "install", "--skill", "alpha", "--runtime", "claude-code", "--yes")
    run(capsys, "install", "--mcp", "cloudflare", "--runtime", "claude-code")
    approve(root, "cloudflare")

    code, output = run(capsys, "doctor")

    assert code == 0
    assert "2 artifacts · 2 places" in joined(output)


# --------------------------------------------------------------------------- #
# MCP grafts: unapproved, a vanished clone, an unset slot, an orphan clone
# --------------------------------------------------------------------------- #

MCP_URL = "https://mcp.cloudflare.com/mcp"

SOURCED = """\
description: "A server with code of its own."
transport: "stdio"

source:
  url: "https://github.com/example/homegrown-mcp"

server:
  command: "uv"
  args:
    - "run"
    - "--project"
    - "{source}"
    - "server.py"
"""


def approve(root: Path, *names: str) -> None:
    """Write the registry Claude Code writes once a human passes the trust dialog.

    The graft is born switched off (ADR 0014), so a test that wants to assert
    anything *else* about a written server has to get the pending-approval
    finding out of the way first — otherwise every one of them reads exit 3 and
    says nothing about what it was written to check.
    """
    settings = root / ".claude" / "settings.local.json"
    settings.parent.mkdir(parents=True, exist_ok=True)
    enabled = ", ".join(f'"{name}"' for name in names)
    settings.write_text(
        f'{{"hasTrustDialogAccepted": true, "enabledMcpjsonServers": [{enabled}]}}\n',
        encoding="utf-8",
    )


def test_a_written_mcp_server_claude_code_has_not_approved_exits_three(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """ADR 0014's own case, read back: the file is there and nobody approved it.

    The install-time warning fires once, at exit 0, and is gone the moment the
    process exits — `doctor` is what still knows the fact a session later.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": MCP_URL})
    root, _ = workspace(tmp_path, monkeypatch)
    run(capsys, "install", "--mcp", "cloudflare", "--runtime", "claude-code")
    assert (root / ".mcp.json").is_file()

    code, output = run(capsys, "doctor")

    said = joined(output)
    assert code == 3
    assert "pending approval" in said
    assert ".mcp.json" in said
    assert "cloudflare" in said


def test_an_mcp_server_claude_code_has_approved_is_healthy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The registry Claude Code itself writes once a human passes the trust dialog."""
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": MCP_URL})
    root, _ = workspace(tmp_path, monkeypatch)
    run(capsys, "install", "--mcp", "cloudflare", "--runtime", "claude-code")
    settings = root / ".claude" / "settings.local.json"
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(
        '{"hasTrustDialogAccepted": true, "enabledMcpjsonServers": ["cloudflare"]}\n',
        encoding="utf-8",
    )

    code, output = run(capsys, "doctor")

    assert code == 0
    assert "pending approval" not in joined(output)


def test_a_config_pointing_at_a_missing_clone_exits_three(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """#84 clones to the machine; when the clone is gone, the config still names it."""
    # given
    catalog_of(tmp_path, monkeypatch)
    custom_recipe(tmp_path, "homegrown", SOURCED)
    _, home = workspace(tmp_path, monkeypatch)
    local = build(tmp_path / "origin", {"server.py": "print('hi')\n"})
    monkeypatch.setattr(remote, "fetch_with_git", instead_of_github(local))
    run(capsys, "install", "--mcp", "homegrown", "--runtime", "claude-code", "--global")
    destination = home / ".overpower" / "mcp" / "homegrown"
    assert destination.is_dir()
    shutil.rmtree(destination)

    code, output = run(capsys, "doctor")

    said = joined(output)
    assert code == 3
    assert "homegrown" in said
    assert ".claude.json" in said


def test_a_slot_not_set_in_this_environment_is_a_notice_not_a_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """The variable has to exist when the runtime starts, not when `doctor` runs.

    Global scope, so the approval check ADR 0014 gates in project scope stays
    out of this test's way — `born_pending` is false for `("claude-code",
    Scope.GLOBAL)`, and this is a test of the slot check alone.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"panel": SLOTTED})
    workspace(tmp_path, monkeypatch)
    monkeypatch.delenv(SLOT_VARIABLE, raising=False)
    run(capsys, "install", "--mcp", "panel", "--runtime", "claude-code", "--global")

    code, output = run(capsys, "doctor")

    said = joined(output)
    assert code == 0
    assert SLOT_VARIABLE in said
    assert "not set" in said


def test_a_clone_directory_no_config_references_is_named_and_not_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture
) -> None:
    """`doctor` never deletes: an orphan clone is named, and left exactly where it was."""
    # given
    _, home = workspace(tmp_path, monkeypatch)
    orphan = home / ".overpower" / "mcp" / "leftover"
    orphan.mkdir(parents=True)
    (orphan / "server.py").write_text("print('hi')\n", encoding="utf-8")

    code, output = run(capsys, "doctor")

    said = joined(output)
    assert code == 0
    assert "leftover" in said
    assert (orphan / "server.py").is_file()
