"""The write boundary: what the plan promised is what the disk carries.

Mirror of `src/overpower/writing.py` **and of `src/overpower/grafting.py`**, the
way `test_catalog.py` mirrors two modules: they answer one question between them
— *what ends up on disk* — and ADR 0016 puts the assertion that catches the
graft's measured trap here rather than over the function, because the trap is
exit 0 with a byte-identical file and only the **content of the file** shows it.

The subject is the boundary rather than the function: every case here goes
through the CLI, with `tmp_path` as the working directory and as `HOME`, because
that is the one seam the doctrine allows — and because a writer asserted
directly could not show the *screen* half of the identity, which is half of the
defect it exists to catch.

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
    BEARER,
    CLAUDE,
    OTHER_SLOTTED,
    SLOT_VARIABLE,
    SLOTTED,
    STDIO,
    at_home,
    catalog_of,
    document_keys,
    files_under,
    joined,
    keys_in,
    landings_of,
    parsed,
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


def test_a_document_key_asked_for_by_copy_is_refused_by_name(tmp_path: Path) -> None:
    """Both operations exist now, so what has no branch is a **pair** that does not go together.

    A graft is a key written by `WriteMode.GRAFT` out of a rendered fragment;
    asking for a document key by copy, from a source path, is a plan nobody
    builds — and the dispatch says so instead of answering with a copy, which
    would be the silent wrong answer this product exists to avoid.
    """
    # given
    grafted = Artifact(
        type=ArtifactType.SKILL,
        name="probe",
        path=tmp_path / "source",
        description="A copy asked to land inside a document.",
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
# the graft: a key inside a document that is the user's
# --------------------------------------------------------------------------- #

CLOUDFLARE = "https://mcp.cloudflare.com/mcp"
"""The URL the recipe carries, so a test can assert what reached the file."""

MCP_JSON = ".mcp.json"
"""Where Claude Code reads MCP servers in a repository — measured, not transcribed."""

VSCODE_JSON = ".vscode/mcp.json"
"""Where VS Code reads MCP servers in a repository — measured, not transcribed."""

VSCODE = ("--runtime", "vscode")
"""The selector under test, spelled once: the second target the product renders.

Up here with `MCP_JSON` and not down in its own section, because the two
documents differ by something this section needs: `.vscode/mcp.json` tolerates a
comment and `.mcp.json` does not, so the tests about what the insertion does
*around* a comment can only be written against this one.
"""

OCCUPIED = """\
{
  "$schema": "https://example.com/mcp.schema.json",
  "mcpServers": {
    "antigo": {
      "command": "node",
      "args": ["server.js"]
    }
  }
}
"""
"""A document with everything the graft has to leave alone.

A root key no tool of ours knows, and a server of the user's whose `args` are on
one line — which is exactly what `json.dumps` reflows, measured, in the
friendliest case there is.

**Strict JSON, and it carried a comment until it could not.** This seed is fed
to `.mcp.json` and to Devin's document, and both of those are parsed by their
runtime with a strict reader: a comment here is a file Claude Code does not
read, so a graft preserving one was preserving a document that was already
dead. The comment moved to `.vscode/mcp.json`, where it is legal and idiomatic
and where the same insertion mechanics are proven against it.
"""


def lost_lines(before: str, after: str) -> list[str]:
    """Lines of `before` that `after` does not carry, ignoring one added comma.

    This is *"the rest of the document arrives byte for byte"*, written as
    something a machine can check. The comma is the one exception the format
    imposes and not a licence: inserting a pair after the last one means the line
    that used to end the object now ends with `,`, and there is no JSON in which
    it does not.
    """
    kept = set(after.splitlines())
    return [line for line in before.splitlines() if line not in kept and f"{line}," not in kept]


def occupied(root: Path, text: str = OCCUPIED) -> Path:
    """A `.mcp.json` already on disk, written byte for byte as given."""
    path = root / MCP_JSON
    path.write_text(text, encoding="utf-8", newline="")
    return path


@pytest.mark.parametrize(
    "kind",
    [
        pytest.param(CLOUDFLARE, id="no-slot"),
        pytest.param(SLOTTED, id="env-slot-and-a-literal"),
        pytest.param(BEARER, id="bearer-slot"),
    ],
)
def test_the_plan_the_screen_and_the_document_name_the_same_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], kind: str
) -> None:
    """The three-way identity, with the half a graft needs.

    A graft creates no path, so the copy class's `walk(disk)` has nothing to
    compare: what it creates is a **key**. So the assertion keeps its shape and
    changes its subject — every key the plan named is in the document afterwards,
    and no key it did not name appeared. The second half is the one that catches
    the measured trap of the insertion library, which returns exit 0 with a
    byte-identical file and the graft gone.

    Slots do not change the shape of it and that is the claim being made: what
    they add lives *inside* the server's value, so a fragment with a secret in it
    still names exactly one key — and the run still exits 0 with the variable
    unset (https://github.com/panlabs-tech/overpower/issues/78).
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": kind})
    dry_root = target(tmp_path, monkeypatch, "dry")
    real_root = target(tmp_path, monkeypatch, "real")
    dry_document = occupied(dry_root)
    real_document = occupied(real_root)
    before = document_keys(real_document)
    selectors = ("install", "--mcp", "cloudflare", "--runtime", "claude-code")

    monkeypatch.chdir(dry_root)
    dry_code, dry_out = run(capsys, *selectors, "--dry-run")
    monkeypatch.chdir(real_root)
    real_code, real_out = run(capsys, *selectors)

    named = keys_in(real_out)
    after = document_keys(real_document)
    assert keys_in(dry_out) == named
    assert named <= after
    assert after - before <= named
    assert dry_document.read_text(encoding="utf-8") == OCCUPIED
    assert files_under(dry_root) == {MCP_JSON}
    assert dry_code == real_code == 0


def test_the_rest_of_the_document_arrives_byte_for_byte(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """ADR 0016, and it is the reason a dependency was bought.

    *"In a repository the git is the manifest"* only holds if `git diff` answers
    exactly what the tool wrote. Measured, `json.dumps` in the friendliest case
    there is — strict JSON, no comments, the same indent — already reflows a
    server nobody touched, and this document **is** that friendliest case: the
    same promise over a comment is proven where a comment may legally sit, in
    `test_a_comment_in_the_vscode_document_survives_both_grafts`.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": CLOUDFLARE})
    root = target(tmp_path, monkeypatch)
    document = occupied(root)

    code, _ = run(capsys, "install", "--mcp", "cloudflare", "--runtime", "claude-code")

    assert code == 0
    after = document.read_text(encoding="utf-8")
    assert lost_lines(OCCUPIED, after) == []
    assert '      "args": ["server.js"]' in after
    assert '  "$schema": "https://example.com/mcp.schema.json",' in after
    assert CLOUDFLARE in after


def test_a_server_of_the_same_name_is_overwritten_without_asking(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """ADR 0013: key collision resolves the way path collision does — unconditionally.

    `--force` is not consulted and is not passed here: it governs an existing
    destination of the **copy** class in global scope, and a second regime of
    collision would make the user need to know an artifact's class to predict
    what the command does.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": CLOUDFLARE})
    root = target(tmp_path, monkeypatch)
    document = occupied(
        root,
        '{\n  "mcpServers": {\n    "cloudflare": {\n      "type": "sse",\n'
        '      "url": "https://stale.example.com/sse"\n    },\n'
        '    "antigo": { "command": "node" }\n  }\n}\n',
    )

    code, _ = run(capsys, "install", "--mcp", "cloudflare", "--runtime", "claude-code")

    assert code == 0
    after = document.read_text(encoding="utf-8")
    assert "stale.example.com" not in after
    assert CLOUDFLARE in after
    assert '    "antigo": { "command": "node" }' in after


def test_grafting_the_same_server_twice_writes_again_and_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The write is unconditional, and running twice asks nothing.

    The second run is also the interesting one for the format: it grafts over a
    key the first run wrote, so the document has to come out the same rather than
    accumulating a second copy of the server.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": CLOUDFLARE})
    root = target(tmp_path, monkeypatch)
    selectors = ("install", "--mcp", "cloudflare", "--runtime", "claude-code")
    first, _ = run(capsys, *selectors)
    once = (root / MCP_JSON).read_text(encoding="utf-8")

    second, _ = run(capsys, *selectors)

    assert first == second == 0
    assert (root / MCP_JSON).read_text(encoding="utf-8") == once


def test_a_comment_at_the_end_of_the_object_is_not_swallowed_by_the_comma(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The hazard the insertion is *shaped* around, and it destroys a line if missed.

    Appending a pair means the previous one gains a comma. If that comma landed
    after the whitespace the object already carried, it would be written **onto
    the comment line** — `// a note,` — and the comment would swallow it: valid
    JSON5, one server short, exit 0. So the whitespace is moved onto the new
    entry instead of rebuilt, and the comma goes in front of it.

    Against `.vscode/mcp.json`, because that is the only document where the
    hazard can arise: a comment is idiomatic there and refused in `.mcp.json`,
    whose reader parses strict JSON.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": CLOUDFLARE})
    root = target(tmp_path, monkeypatch)
    document = root / VSCODE_JSON
    document.parent.mkdir(parents=True)
    text = (
        '{\n  "servers": {\n    "antigo": { "command": "node" }\n'
        "    // a note the user left at the end\n  }\n}\n"
    )
    document.write_text(text, encoding="utf-8", newline="")

    code, output = run(capsys, "install", "--mcp", "cloudflare", *VSCODE)

    assert code == 0
    after = document.read_text(encoding="utf-8")
    assert "    // a note the user left at the end\n" in after
    assert keys_in(output) <= document_keys(document)
    assert lost_lines(text, after) == []


@pytest.mark.parametrize("newline", [pytest.param("\n", id="lf"), pytest.param("\r\n", id="crlf")])
def test_a_comment_at_the_end_of_a_line_stays_on_the_entry_it_annotates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    newline: str,
) -> None:
    """The other place a comment can sit, and the one where moving it is wrong.

    The test above puts the note on a **line of its own**, where it annotates the
    object rather than any one entry — so carrying it down onto the new last pair
    keeps it saying what it said. On the **same line** as an entry it annotates
    that entry, and moving it re-anchors the sentence onto a server the user
    never wrote:

        "antigo": {"command": "node"} // meu comentario sobre o antigo

    becomes `"antigo"`, then the grafted server, then the comment — which now
    reads as being about the graft. Story 14 asks for *"the rest of the document
    byte for byte"* and ADR 0016 for a diff that shows only what was written;
    `lost_lines` is that promise as something a machine checks, and it answered
    with this line.

    The comma hazard the sibling exists for is unchanged, and it is what fixes
    where the comma may go: **before** the comment and never after it, because
    `} // note,` puts the comma inside the comment and drops it.

    That is also why `lost_lines` still names this one line. Its allowance is a
    comma **at the end**, which is where the format puts one when nothing
    follows the value; here something does, so the same single forced comma
    lands mid-line. The line is byte-identical either side of it, and the exact
    assertion below is what says so — the helper is right about every other
    line, and narrow about this one.

    Both line endings, because a break is one thing and `\\r\\n` is two
    characters: a split between them would strand the carriage return on the
    line above, which is a byte moved by the one function whose whole purpose is
    to move none.

    Against `.vscode/mcp.json` for the same reason its sibling is: a comment is
    legal there and refused in a document whose reader parses strict JSON.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": CLOUDFLARE})
    root = target(tmp_path, monkeypatch)
    note = "// meu comentario sobre o antigo"
    annotated = f'    "antigo": {{ "command": "node" }} {note}'
    text = f'{{{newline}  "servers": {{{newline}{annotated}{newline}  }}{newline}}}{newline}'
    document = root / VSCODE_JSON
    document.parent.mkdir(parents=True)
    document.write_text(text, encoding="utf-8", newline="")

    code, output = run(capsys, "install", "--mcp", "cloudflare", *VSCODE)

    assert code == 0
    after = document.read_text(encoding="utf-8")
    raw = document.read_bytes()
    assert f'    "antigo": {{ "command": "node" }}, {note}{newline}'.encode() in raw
    # Every break is the one the document arrived with, and no other: strip the
    # document's own ending and no line ending may be left standing.
    assert raw.replace(newline.encode(), b"") == raw.replace(newline.encode(), b"").replace(
        b"\n", b""
    )
    assert lost_lines(text, after) == [annotated]
    assert keys_in(output) <= document_keys(document)


@pytest.mark.skipif(sys.platform == "win32", reason="a mode of 0 is not how Windows refuses")
def test_a_document_that_cannot_be_read_is_named_and_not_blamed_on_the_product(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The third state of the user's file, and the only one that accused the product.

    The same document, in the same command, already has two modelled answers:
    **malformed** is a named refusal, and **not writable** is a named failure
    naming where it stopped. **Not readable** fell past both into the handler
    for an unexpected exception — so the product printed a traceback and said
    *"This is a bug in the overpower, not in what you typed"* over a permission
    somebody else set.

    The exit code was never the defect and does not move: a file that cannot be
    read is *could not run*, the stop is before the first byte, and nothing is
    lost. What moves is the sentence, because the flag that prints it exists to
    say whose fault it is, and it was answering wrong.

    `chmod 000` is the cheapest way to reach the state; a config written by root
    in a container, a mounted volume and a corporate ACL reach the same one.
    Presumes an ordinary user, which every cell of the matrix is.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": CLOUDFLARE})
    root = target(tmp_path, monkeypatch)
    document = occupied(root)
    document.chmod(0o000)

    code, output = run(capsys, "install", "--mcp", "cloudflare", "--runtime", "claude-code")

    document.chmod(0o600)
    joined = " ".join(" ".join(line.split()) for line in output.splitlines())
    assert code == 1
    assert "bug in the overpower" not in joined
    assert MCP_JSON in joined


def test_a_stdio_server_lands_with_its_array_inline_and_its_table_expanded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The formatting rule, asserted where ADR 0016 says it has to be: on the file.

    **Objects expand and arrays stay inline** — one rule per shape, and the
    reason to check it here rather than over the renderer is that the whitespace
    does not exist until the model is dumped. `args` is the field the measured
    `json.dumps` diff reflowed, so it is also the one worth reading back.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"coolify": STDIO})
    root = target(tmp_path, monkeypatch)

    code, _ = run(capsys, "install", "--mcp", "coolify", "--runtime", "claude-code")

    assert code == 0
    assert (root / MCP_JSON).read_text(encoding="utf-8") == (
        "{\n"
        '  "mcpServers": {\n'
        '    "coolify": {\n'
        '      "type": "stdio",\n'
        '      "command": "uvx",\n'
        '      "args": ["coolify-server", "--repository", "."],\n'
        '      "env": {\n'
        '        "PANEL_URL": "https://panel.example.com"\n'
        "      }\n"
        "    }\n"
        "  }\n"
        "}\n"
    )


def test_a_slot_lands_as_a_reference_and_a_literal_lands_as_itself(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The distinction, asserted where it matters: on the file that gets committed.

    The variable is **set in the process** on purpose. That is the case in which
    a product that resolved slots would write the secret into a versioned file
    and exit 0 — which is what two configurations of this organisation did by
    hand, and both of them stayed out of git, where nobody reviewed them.

    The address of the panel is written, because it is not a secret and the
    server needs it to know where to talk.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"coolify": SLOTTED})
    root = target(tmp_path, monkeypatch)
    monkeypatch.setenv(SLOT_VARIABLE, "SUPER-SECRET-42")

    code, _ = run(capsys, "install", "--mcp", "coolify", "--runtime", "claude-code")

    assert code == 0
    after = (root / MCP_JSON).read_text(encoding="utf-8")
    assert "SUPER-SECRET-42" not in after
    assert f'"{SLOT_VARIABLE}": "${{{SLOT_VARIABLE}}}"' in after
    assert '"PANEL_URL": "https://panel.example.com"' in after
    assert ":-" not in after


def test_a_bearer_slot_lands_as_the_header_the_recipe_never_spelled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The role is in the recipe and the scheme is in the file, which is the whole trick."""
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"github": BEARER})
    root = target(tmp_path, monkeypatch)

    code, _ = run(capsys, "install", "--mcp", "github", "--runtime", "claude-code")

    assert code == 0
    assert (root / MCP_JSON).read_text(encoding="utf-8") == (
        "{\n"
        '  "mcpServers": {\n'
        '    "github": {\n'
        '      "type": "http",\n'
        '      "url": "https://mcp.example.com/mcp",\n'
        '      "headers": {\n'
        f'        "Authorization": "Bearer ${{{SLOT_VARIABLE}}}"\n'
        "      }\n"
        "    }\n"
        "  }\n"
        "}\n"
    )


def test_two_servers_on_one_line_both_reach_the_same_document(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The second graft reads what the first one wrote, rather than the file it found.

    Two writes, one document, and they are performed in plan order — so a writer
    that had kept the original text in hand would land the second server over
    the first and report two writes for one key.
    """
    # given
    catalog_of(
        tmp_path,
        monkeypatch,
        mcps={"cloudflare": CLOUDFLARE, "hostinger-vps": "https://mcp.hostinger.com/mcp"},
    )
    root = target(tmp_path, monkeypatch)

    code, output = run(
        capsys, "install", "--mcp", "cloudflare,hostinger-vps", "--runtime", "claude-code"
    )

    assert code == 0
    assert document_keys(root / MCP_JSON) == keys_in(output)
    assert {"mcpServers.cloudflare", "mcpServers.hostinger-vps"} <= keys_in(output)


def test_the_document_is_created_when_the_repository_has_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Creating a file is not repairing one, and it is the ordinary first install."""
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": CLOUDFLARE})
    root = target(tmp_path, monkeypatch)

    code, output = run(capsys, "install", "--mcp", "cloudflare", "--runtime", "claude-code")

    assert code == 0
    assert files_under(root) == {MCP_JSON}
    assert document_keys(root / MCP_JSON) == keys_in(output)


# --------------------------------------------------------------------------- #
# the VS Code document: two keys of one file, and the prompt behind the secret
# --------------------------------------------------------------------------- #


def test_a_vscode_install_writes_the_server_and_the_prompt_into_one_document(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The whole point of the target, on disk: a reference, and the vault behind it.

    Measured (`docs/research/mcp-config-formats.md`, trap 10): `password: true`
    is what encrypts the typed value under a key in the OS keychain. Without it
    the same value goes to `state.vscdb` in plain text, and the reference alone
    would point at a prompt that does not exist.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"panel": SLOTTED})
    root = target(tmp_path, monkeypatch)

    code, _ = run(capsys, "install", "--mcp", "panel", *VSCODE)

    assert code == 0
    assert files_under(root) == {VSCODE_JSON}
    document = parsed(root / VSCODE_JSON)
    assert document["servers"] == {
        "panel": {
            "type": "stdio",
            "command": "uvx",
            "args": ["panel-server", "--repository", "."],
            "env": {
                "PANEL_URL": "https://panel.example.com",
                SLOT_VARIABLE: "${input:panel-token}",
            },
        }
    }
    assert document["inputs"] == [
        {
            "type": "promptString",
            "id": "panel-token",
            "description": SLOT_VARIABLE,
            "password": True,
        }
    ]


def test_the_vscode_document_never_carries_the_spelling_that_fails_in_silence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`${env:VAR}` is the one grafia this target must never receive.

    Measured: VS Code resolves it against the environment of its own process and
    an absent variable becomes the **empty string**, with no error and no prompt.
    The file parses, the install is green, and the server comes up
    unauthenticated. Asserted over the bytes of the file rather than over the
    renderer, because it is the file that the editor reads.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"panel": SLOTTED, "github": BEARER})
    root = target(tmp_path, monkeypatch)

    code, _ = run(capsys, "install", "--mcp", "panel,github", *VSCODE)

    assert code == 0
    written = (root / VSCODE_JSON).read_text(encoding="utf-8")
    assert "${env:" not in written
    assert f"${{{SLOT_VARIABLE}}}" not in written
    assert "${input:panel-token}" in written


def test_the_plan_the_screen_and_the_document_name_both_keys_of_the_vscode_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The three-way identity, over the target whose recipe is **two** keys.

    Same assertion as the Claude twin and a bigger claim: one recipe writes
    `servers.panel` and `inputs`, both are named on the screen, and no third key
    appears in the document. It is what proves the second graft is planned rather
    than smuggled in by the writer.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"panel": SLOTTED})
    dry_root = target(tmp_path, monkeypatch, "dry")
    real_root = target(tmp_path, monkeypatch, "real")
    selectors = ("install", "--mcp", "panel", *VSCODE)

    monkeypatch.chdir(dry_root)
    dry_code, dry_out = run(capsys, *selectors, "--dry-run")
    monkeypatch.chdir(real_root)
    real_code, real_out = run(capsys, *selectors)

    named = keys_in(real_out)
    assert keys_in(dry_out) == named
    assert {"servers.panel", "inputs"} <= named
    assert document_keys(real_root / VSCODE_JSON) == named
    assert files_under(dry_root) == set()
    assert dry_code == real_code == 0


def test_a_recipe_with_no_slot_writes_no_prompt_list_at_all(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """An empty `inputs[]` is a key the reader has to interpret, for nothing.

    Cloudflare authorises in the browser. The second graft does not exist rather
    than existing empty, and the screen says one key because one key landed.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": CLOUDFLARE})
    root = target(tmp_path, monkeypatch)

    code, output = run(capsys, "install", "--mcp", "cloudflare", *VSCODE)

    assert code == 0
    assert "inputs" not in parsed(root / VSCODE_JSON)
    assert document_keys(root / VSCODE_JSON) == keys_in(output)


def test_a_second_server_is_added_to_the_prompts_already_there(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Appending, never rewriting — and the reason is measured, not tidiness.

    VS Code trusts this file by `TrustedOnNonce` over the hash of the launch, so
    a graft that rebuilt `inputs[]` would make the user re-approve **every**
    server, **every** time. The prompt the first install put there has to still
    be the same bytes after the second one.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"panel": SLOTTED, "other": OTHER_SLOTTED})
    root = target(tmp_path, monkeypatch)
    first, _ = run(capsys, "install", "--mcp", "panel", *VSCODE)
    after_one = (root / VSCODE_JSON).read_text(encoding="utf-8")

    second, _ = run(capsys, "install", "--mcp", "other", *VSCODE)

    assert first == second == 0
    after_two = (root / VSCODE_JSON).read_text(encoding="utf-8")
    assert lost_lines(after_one, after_two) == []
    prompts = cast("list[dict[str, object]]", parsed(root / VSCODE_JSON)["inputs"])
    assert [entry["id"] for entry in prompts] == ["panel-token", "other-token"]


def test_the_same_secret_asked_for_twice_is_one_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Two recipes, one variable, **one** entry — the identity is the id and not the row.

    Both fixtures name `PANEL_TOKEN`, so they derive the same id. Asking the
    person for the same secret twice is the failure this deduplication exists to
    prevent, and a list has no key to make it impossible by construction.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"panel": SLOTTED, "github": BEARER})
    root = target(tmp_path, monkeypatch)

    code, _ = run(capsys, "install", "--mcp", "panel,github", *VSCODE)

    assert code == 0
    prompts = cast("list[dict[str, object]]", parsed(root / VSCODE_JSON)["inputs"])
    assert [entry["id"] for entry in prompts] == ["panel-token"]


def test_installing_the_same_server_twice_leaves_the_vscode_file_identical(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Idempotent over **both** keys, and the list is the half that could drift.

    A table cannot grow a duplicate — the second write lands on the same key. A
    list can, and a `.append` that never looked would grow it every run.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"panel": SLOTTED})
    root = target(tmp_path, monkeypatch)
    selectors = ("install", "--mcp", "panel", *VSCODE)
    first, _ = run(capsys, *selectors)
    once = (root / VSCODE_JSON).read_text(encoding="utf-8")

    second, _ = run(capsys, *selectors)

    assert first == second == 0
    assert (root / VSCODE_JSON).read_text(encoding="utf-8") == once


def test_a_comment_in_the_vscode_document_survives_both_grafts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """JSONC is the file's real type, and the standard library cannot read it.

    This is why the tolerant reader was a requirement rather than a convenience:
    `.vscode/mcp.json` is documented as accepting comments, so a user's file
    routinely has one — and here two grafts pass over the same document, so the
    comment has to survive being appended after twice.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"panel": SLOTTED})
    root = target(tmp_path, monkeypatch)
    document = root / VSCODE_JSON
    document.parent.mkdir(parents=True)
    text = (
        "{\n  // the servers I set up by hand, and nobody asked the overpower to touch them\n"
        '  "servers": {\n    "antigo": { "type": "stdio", "command": "node" }\n  }\n}\n'
    )
    document.write_text(text, encoding="utf-8", newline="")

    code, _ = run(capsys, "install", "--mcp", "panel", *VSCODE)

    assert code == 0
    after = document.read_text(encoding="utf-8")
    assert lost_lines(text, after) == []
    assert "// the servers I set up by hand" in after
    assert "antigo" in parsed(document)["servers"]  # pyright: ignore[reportOperatorIssue]


def test_a_trailing_comma_keeps_the_entry_it_terminates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """JSONC admits a trailing comma, and this file is where they are idiomatic.

    Appending after one is where the comma can be stranded: the whitespace
    before the closing brace hangs off the **comma** and not off the last value,
    so moving it the way the no-comma path does leaves a `,` alone on a line of
    its own. Valid JSONC, and a diff line nobody wrote — which is the whole thing
    ADR 0016 buys a dependency to avoid.

    Asserted on the bytes, in both shapes the document has: the object under
    `servers` and the list under `inputs`.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"panel": SLOTTED})
    root = target(tmp_path, monkeypatch)
    document = root / VSCODE_JSON
    document.parent.mkdir(parents=True)
    text = (
        '{\n  "servers": {\n    "antigo": { "type": "stdio", "command": "node" },\n  },\n'
        '  "inputs": [\n    { "type": "promptString", "id": "outro" },\n  ],\n}\n'
    )
    document.write_text(text, encoding="utf-8", newline="")

    code, _ = run(capsys, "install", "--mcp", "panel", *VSCODE)

    assert code == 0
    after = document.read_text(encoding="utf-8")
    assert lost_lines(text, after) == []
    assert "\n  ,\n" not in after
    assert "\n,\n" not in after
    assert "    },\n  },\n" in after
    assert "    },\n  ],\n" in after


def test_a_prompt_written_with_the_other_quote_is_the_same_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The lookup that decides append-against-replace has to see the key that is there.

    A false miss costs a **duplicate**, not a retry: the entry is appended beside
    the one it should have replaced, and the person is asked for the same secret
    twice. The tolerant parser accepts both quote styles, so a document written
    by hand with single quotes is a document that already has the key — and the
    same holds for the root key itself, which would otherwise gain a second
    `inputs`.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"panel": SLOTTED})
    root = target(tmp_path, monkeypatch)
    document = root / VSCODE_JSON
    document.parent.mkdir(parents=True)
    document.write_text(
        "{\n  'inputs': [\n    { 'type': 'promptString', 'id': 'panel-token' }\n  ]\n}\n",
        encoding="utf-8",
        newline="",
    )

    code, _ = run(capsys, "install", "--mcp", "panel", *VSCODE)

    assert code == 0
    after = document.read_text(encoding="utf-8")
    assert after.count("promptString") == 1
    assert after.count("inputs") == 1


def test_a_prompt_list_that_is_not_a_list_is_refused_before_the_first_byte(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`inputs` holding an object parses, and has nowhere to receive a prompt.

    The twin of the `mcpServers`-is-a-string case, on the second root key: the
    refusal is exit 3 and it lands before the first byte, so the dry run and the
    real run answer the same thing and the server is not written half-way.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"panel": SLOTTED})
    root = target(tmp_path, monkeypatch)
    document = root / VSCODE_JSON
    document.parent.mkdir(parents=True)
    text = '{\n  "inputs": { "not": "a list" }\n}\n'
    document.write_text(text, encoding="utf-8", newline="")

    code, output = run(capsys, "install", "--mcp", "panel", *VSCODE)

    assert code == 3
    assert "is not ours to repair" in joined(output)
    assert document.read_text(encoding="utf-8") == text


@pytest.mark.parametrize(
    ("text", "kept"),
    [
        pytest.param(
            '{\n\t"mcpServers": {\n\t\t"antigo": {\n\t\t\t"command": "node"\n\t\t}\n\t}\n}\n',
            '\t\t"cloudflare": {',
            id="tabs",
        ),
        pytest.param(
            '{\n    "mcpServers": {\n        "antigo": {\n            "command": "node"\n'
            "        }\n    }\n}\n",
            '        "cloudflare": {',
            id="four-spaces",
        ),
    ],
)
def test_the_document_keeps_the_indentation_it_already_had(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    text: str,
    kept: str,
) -> None:
    """The indent of a new entry is read off the entry already there, never invented."""
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": CLOUDFLARE})
    root = target(tmp_path, monkeypatch)
    document = occupied(root, text)

    code, _ = run(capsys, "install", "--mcp", "cloudflare", "--runtime", "claude-code")

    assert code == 0
    after = document.read_text(encoding="utf-8")
    assert kept in after
    assert lost_lines(text, after) == []


def test_a_document_written_with_crlf_keeps_every_one_of_them(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The trap is the default of `read_text`, not the platform.

    Universal newlines translate `\\r\\n` to `\\n` on the way in, so a document
    written back would arrive with **every** line ending changed — the largest
    possible non-additive diff, produced by the one function whose whole purpose
    is not to produce one. It runs on the nine cells because the file is written
    with explicit bytes on all of them.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": CLOUDFLARE})
    root = target(tmp_path, monkeypatch)
    document = occupied(root, OCCUPIED.replace("\n", "\r\n"))

    code, _ = run(capsys, "install", "--mcp", "cloudflare", "--runtime", "claude-code")

    assert code == 0
    raw = document.read_bytes()
    assert b"\r\n" in raw
    assert raw.replace(b"\r\n", b"") == raw.replace(b"\r\n", b"").replace(b"\n", b"")


BROKEN = [
    pytest.param('{"mcpServers": {,,}}\n', id="not-json"),
    pytest.param('["mcpServers"]\n', id="not-an-object"),
    pytest.param('{"mcpServers": "not a table"}\n', id="root-key-not-an-object"),
    pytest.param(
        '{"mcpServers": {"antigo": {"command": "node"}},\n'
        ' "mcpServers": {"outro": {"command": "node"}}}\n',
        id="duplicate-root-key",
    ),
    pytest.param(
        '{"mcpServers": {"cloudflare": {"command": "A"},\n'
        '                "cloudflare": {"command": "B"}}}\n',
        id="duplicate-server-name",
    ),
    pytest.param(
        '{"mcpServers": {"antigo": {"command": "node"}}, "mcpServers": "not a table"}\n',
        id="shadowed-root-key-not-an-object",
    ),
    pytest.param('{"mcpServers": {"antigo": {"command": "node"},},}\n', id="trailing-comma"),
    pytest.param(
        '{\n  // mine, and the reader of this file cannot parse it\n  "mcpServers": {}\n}\n',
        id="comment",
    ),
]
"""The shapes of *already broken*, and the ones that hide are the whole point.

The first two fail at the parser. The third parses perfectly and still has
nowhere to put a server — so a check that stopped at the top level would answer
that it is fine, which is exactly what it did until it was measured.

The last three carry one key twice, which the RFC calls valid and leaves
*unpredictable*. Measured, `JSON.parse` and `json.loads` both resolve it by the
**last** occurrence while the graft lands on the **first**: the write is real,
the exit is 0, and the runtime goes on reading the old value. The sixth is the
third one wearing a disguise — alone it is refused with 3, and hidden behind a
duplicated root it was accepted with 0, which made the duplicate an evasion of
a check that already existed.

The last two are broken only **here**. Every shape is fed to `.mcp.json`, which
its readers parse as strict JSON, and a trailing comma or a comment stops them
dead — the same two bytes are idiomatic in `.vscode/mcp.json` and stay accepted
there. This list is a list of documents that are already broken *for the
runtime that reads them*, which is why the file it is fed to is part of it.
"""


@pytest.mark.parametrize("broken", BROKEN)
def test_a_configuration_file_that_is_already_broken_is_refused_and_not_repaired(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], broken: str
) -> None:
    """Repairing means editing, on our own initiative, a file that is not ours.

    Exit **3** — the invocation was well formed, the product ran, and the answer
    is no — and the file is left exactly as it was found. It is also what the
    official CLIs do, measured: `claude mcp add` and `codex mcp add` both refuse.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": CLOUDFLARE})
    root = target(tmp_path, monkeypatch)
    document = occupied(root, broken)

    code, output = run(capsys, "install", "--mcp", "cloudflare", "--runtime", "claude-code")

    assert code == 3
    assert document.read_text(encoding="utf-8") == broken
    assert MCP_JSON in joined(output)


@pytest.mark.parametrize("broken", BROKEN)
def test_a_broken_file_is_refused_by_the_dry_run_with_the_same_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], broken: str
) -> None:
    """#8, still: a report that answered 0 where the real run answers 3 is a report
    about a different installation, and useless as a CI gate.

    Parametrised over **every** shape of broken, and that is what this case
    bought: measured, checking only the top level let `{"mcpServers": "not a
    table"}` through the dry run at 0 while the real run refused it with 3 — one
    shape of broken passing, the other two hiding it.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": CLOUDFLARE})
    root = target(tmp_path, monkeypatch)
    occupied(root, broken)
    selectors = ("install", "--mcp", "cloudflare", "--runtime", "claude-code")

    dry_code, _ = run(capsys, *selectors, "--dry-run")
    real_code, _ = run(capsys, *selectors)

    assert dry_code == real_code == 3


@pytest.mark.parametrize("broken", BROKEN)
def test_a_broken_file_is_refused_before_the_copies_of_the_same_line_land(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], broken: str
) -> None:
    """*"Recusado antes do primeiro byte"* is about the **line**, not about the graft.

    A refusal that lived in the writer would let the skills of
    `--skill alpha --mcp cloudflare` land first and report 3 afterwards, which is
    half an installation announced as a refusal.
    """
    # given
    catalog_of(tmp_path, monkeypatch, "alpha", mcps={"cloudflare": CLOUDFLARE})
    root = target(tmp_path, monkeypatch)
    document = occupied(root, broken)

    code, _ = run(
        capsys,
        *("install", "--skill", "alpha", "--mcp", "cloudflare"),
        *("--runtime", "claude-code"),
    )

    assert code == 3
    assert not (root / CLAUDE).exists()
    assert document.read_text(encoding="utf-8") == broken


def test_a_duplicate_the_graft_never_looks_up_is_not_ours_to_refuse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The refusal is narrow by construction, and this is the edge that says so.

    What makes a duplicate refusable is not that it is a duplicate — it is that
    the graft *reads that key* to decide where to land, so an ambiguous answer
    sends the write somewhere the runtime does not look. `$schema` is a key the
    graft never asks about, so it stays the user's business, exactly like every
    other thing in a file that is not ours to repair.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": CLOUDFLARE})
    root = target(tmp_path, monkeypatch)
    text = (
        '{\n  "$schema": "https://example.com/a.json",\n'
        '  "$schema": "https://example.com/b.json",\n'
        '  "mcpServers": {\n    "antigo": {"command": "node"}\n  }\n}\n'
    )
    document = occupied(root, text)

    code, _ = run(capsys, "install", "--mcp", "cloudflare", "--runtime", "claude-code")

    assert code == 0
    assert "cloudflare" in parsed(document)["mcpServers"]  # pyright: ignore[reportOperatorIssue]


def test_two_prompts_carrying_one_id_are_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The list has a lookup of its own, and it shadows the way the object does.

    `inputs` is matched by a field and never by position — that is what makes
    the same secret asked for twice one prompt. Two entries carrying one id
    leave that lookup answering the first while VS Code reads whichever it
    reads, which is the ambiguity of a duplicated key one level down.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"panel": SLOTTED})
    root = target(tmp_path, monkeypatch)
    document = root / VSCODE_JSON
    document.parent.mkdir(parents=True)
    text = (
        '{\n  "servers": {},\n  "inputs": [\n'
        '    { "type": "promptString", "id": "panel-token", "description": "mine" },\n'
        '    { "type": "promptString", "id": "panel-token", "description": "also mine" }\n'
        "  ]\n}\n"
    )
    document.write_text(text, encoding="utf-8", newline="")

    code, output = run(capsys, "install", "--mcp", "panel", *VSCODE)

    assert code == 3
    assert document.read_text(encoding="utf-8") == text
    assert "mcp.json" in joined(output)


# --------------------------------------------------------------------------- #
# #80: the second target, and the writer that does not know there are two
# --------------------------------------------------------------------------- #

DEVIN_JSON = ".devin/mcp_config.json"
"""Where Devin reads MCP servers in a repository — vendor documentation, not measured.

The binary was absent from the machine this row was written on, so the grade of
evidence is the one the research already counts among its weaknesses — Cursor's
grade *there*, which has no row here — and not the one `.mcp.json` carries
(`docs/research/mcp-config-formats.md` § Adendo 2026-08-13).
"""


def test_the_second_target_lands_in_its_own_document_under_a_directory_it_creates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The first row whose document is not at the root, so the parent has to be made.

    `.mcp.json` sits at the top of the repository and every graft written until
    now landed in a directory that already existed. This one does not, and a
    writer that only ever opened a file would fail on the ordinary first install.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": CLOUDFLARE})
    root = target(tmp_path, monkeypatch)

    code, output = run(capsys, "install", "--mcp", "cloudflare", "--runtime", "devin")

    assert code == 0
    assert files_under(root) == {DEVIN_JSON}
    assert document_keys(root / DEVIN_JSON) == keys_in(output)


def test_the_second_target_refuses_a_document_its_reader_could_not_parse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Devin enters the table strict, and this is where that decision is written down.

    Measured in https://github.com/panlabs-tech/overpower/issues/87: a malformed
    `.devin/mcp_config.json` answers *"No MCP servers configured"* at exit 0 —
    the graft disappears with no error at all, which is the worst class the spec
    names. The row's grade of evidence is vendor documentation and not a
    measurement, so the column is set on the **asymmetry** and not on certainty:
    strict and wrong costs a refusal that names its own fix, tolerant and wrong
    costs a server that silently is not there.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": CLOUDFLARE})
    root = target(tmp_path, monkeypatch)
    document = root / DEVIN_JSON
    document.parent.mkdir(parents=True)
    text = '{"mcpServers": {"antigo": {"command": "node"},},}\n'
    document.write_text(text, encoding="utf-8", newline="")

    code, output = run(capsys, "install", "--mcp", "cloudflare", "--runtime", "devin")

    assert code == 3
    assert document.read_text(encoding="utf-8") == text
    assert "mcp_config.json" in joined(output)


def test_the_two_targets_write_two_documents_that_disagree_on_everything_but_the_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """One line, two runtimes, and the dialects part company inside the same root key.

    This is the assertion that could not exist while the table had one row: the
    recipe is the same object, the key it occupies is the same string, and what
    lands under it differs by the discriminator **and** by the spelling of the
    secret. A renderer that had leaked one dialect into the other would still
    produce two files, both green, and only this comparison would say so.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"github": BEARER})
    root = target(tmp_path, monkeypatch)

    code, _ = run(capsys, "install", "--mcp", "github", "--runtime", "claude-code,devin")

    assert code == 0
    assert (root / DEVIN_JSON).read_text(encoding="utf-8") == (
        "{\n"
        '  "mcpServers": {\n'
        '    "github": {\n'
        '      "transport": "http",\n'
        '      "url": "https://mcp.example.com/mcp",\n'
        '      "headers": {\n'
        f'        "Authorization": "Bearer ${{env:{SLOT_VARIABLE}}}"\n'
        "      }\n"
        "    }\n"
        "  }\n"
        "}\n"
    )
    claude = (root / MCP_JSON).read_text(encoding="utf-8")
    assert '"type": "http"' in claude
    assert f'"Bearer ${{{SLOT_VARIABLE}}}"' in claude
    assert "${env:" not in claude


def test_the_second_target_infers_stdio_from_the_command_and_is_written_that_way(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """No discriminator on stdio, because the vendor documents none — asserted on the file.

    The formatting rule is the same one ADR 0016 buys everywhere: objects expand,
    arrays stay inline. What is specific here is the field that is *absent*, and
    absence is only checkable against the bytes.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"coolify": STDIO})
    root = target(tmp_path, monkeypatch)

    code, _ = run(capsys, "install", "--mcp", "coolify", "--runtime", "devin")

    assert code == 0
    assert (root / DEVIN_JSON).read_text(encoding="utf-8") == (
        "{\n"
        '  "mcpServers": {\n'
        '    "coolify": {\n'
        '      "command": "uvx",\n'
        '      "args": ["coolify-server", "--repository", "."],\n'
        '      "env": {\n'
        '        "PANEL_URL": "https://panel.example.com"\n'
        "      }\n"
        "    }\n"
        "  }\n"
        "}\n"
    )


def test_a_slot_reaches_the_second_target_as_its_own_spelling_and_never_as_the_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The variable is set in the process on purpose: that is when a resolver leaks.

    `${env:VAR}` here and `${VAR}` next door, out of one recipe that carries
    neither — rule 4, on the two files that get committed.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"coolify": SLOTTED})
    root = target(tmp_path, monkeypatch)
    monkeypatch.setenv(SLOT_VARIABLE, "SUPER-SECRET-42")

    code, _ = run(capsys, "install", "--mcp", "coolify", "--runtime", "devin")

    assert code == 0
    after = (root / DEVIN_JSON).read_text(encoding="utf-8")
    assert "SUPER-SECRET-42" not in after
    assert f'"{SLOT_VARIABLE}": "${{env:{SLOT_VARIABLE}}}"' in after
    assert '"PANEL_URL": "https://panel.example.com"' in after
    assert ":-" not in after


@pytest.mark.parametrize(
    "kind",
    [
        pytest.param(CLOUDFLARE, id="no-slot"),
        pytest.param(SLOTTED, id="env-slot-and-a-literal"),
        pytest.param(BEARER, id="bearer-slot"),
    ],
)
def test_the_plan_the_screen_and_the_second_document_name_the_same_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], kind: str
) -> None:
    """The three-way identity, on the row that was not there when it was written.

    Same shape and the same three recipes as the first target's, because the
    identity is a property of the **plan**, not of a dialect: a second spelling
    that had leaked into the announced key would show up here and nowhere else.

    What is repeated rather than parametrised *with* the first target is the
    target itself, and the reason is on the last assertion: this document arrives
    with its own parent directory, so `files_under(dry_root)` being empty is the
    half that says the audit did not create the directory on its way to
    announcing the key.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": kind})
    dry_root = target(tmp_path, monkeypatch, "dry")
    real_root = target(tmp_path, monkeypatch, "real")
    selectors = ("install", "--mcp", "cloudflare", "--runtime", "devin")

    monkeypatch.chdir(dry_root)
    dry_code, dry_out = run(capsys, *selectors, "--dry-run")
    monkeypatch.chdir(real_root)
    real_code, real_out = run(capsys, *selectors)

    named = keys_in(real_out)
    assert keys_in(dry_out) == named
    assert named == document_keys(real_root / DEVIN_JSON)
    assert files_under(dry_root) == set()
    assert dry_code == real_code == 0


def test_the_second_target_leaves_the_rest_of_its_document_byte_for_byte(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """ADR 0016 is a property of the writer, and the writer never learned there are two.

    The document is the user's in both targets, so the additive diff has to hold
    in the one that arrived second — with the same comment the standard library
    cannot parse and the same server of theirs that `json.dumps` would reflow.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": CLOUDFLARE})
    root = target(tmp_path, monkeypatch)
    document = root / DEVIN_JSON
    document.parent.mkdir(parents=True)
    document.write_text(OCCUPIED, encoding="utf-8", newline="")

    code, output = run(capsys, "install", "--mcp", "cloudflare", "--runtime", "devin")

    assert code == 0
    after = document.read_text(encoding="utf-8")
    assert lost_lines(OCCUPIED, after) == []
    assert keys_in(output) <= document_keys(document)


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

    at_home(monkeypatch, dry_home)
    dry_code, dry_out = run(capsys, *selectors, "--dry-run")

    at_home(monkeypatch, real_home)
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


def test_the_three_way_identity_of_a_graft_holds_in_machine_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """#81: the identity is a property of the product, not of the project scope.

    All three targets on one line, because machine scope is where they stop
    sharing a directory: `~/.claude.json` sits at the top of the home and the
    other two sit under a per-system profile, so this is also the case where an
    announced key and a written key could most easily drift apart.

    The disk half is a **walk of the home**, not a lookup of three known files —
    which is what makes *"a key written and never announced"* detectable, in the
    one scope where a stray write lands somewhere nobody would think to look.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": "https://mcp.example.com/mcp"})
    monkeypatch.setattr(cli, "_out", pinned(tty=False))
    dry_home = tmp_path / "dry"
    real_home = tmp_path / "real"
    dry_home.mkdir()
    real_home.mkdir()
    selectors = (
        *("install", "--mcp", "cloudflare"),
        *("--runtime", "claude-code,vscode,devin", "--global"),
    )

    at_home(monkeypatch, dry_home)
    dry_code, dry_out = run(capsys, *selectors, "--dry-run")
    at_home(monkeypatch, real_home)
    real_code, real_out = run(capsys, *selectors)

    named = keys_in(real_out)
    written = [path for path in real_home.rglob("*") if path.is_file()]
    assert keys_in(dry_out) == named
    assert len(written) == 3
    assert {key for path in written for key in document_keys(path)} == named
    assert files_under(dry_home) == set()
    assert dry_code == real_code == 0


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
