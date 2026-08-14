"""`--from`: the URL, the two obtention paths, and the search that never re-fetches.

The doctrine cuts this path in one place and one only — **the subprocess runs;
the network does not** (`docs/agents/testing.md`, §3). Everything below honours
that cut:

| layer | double |
| --- | --- |
| deciding to fall back | **stub** of the obtainer, returning the outcome |
| the primary `git` | **none** — a real subprocess against a local remote |
| the fallback's unpacking | **none** — real `tarfile` over a real `.tar.gz` |
| the fallback's HTTP | **stub** of `urlopen` (200, 404, timeout) |
| the `SKILL.md` search | **none** — a real walk over `tmp_path` |
| GitHub | **none, and outside the gate** |
"""

from __future__ import annotations

import email.message
import io
import os
import subprocess
import sys
import tarfile
import urllib.error
from typing import TYPE_CHECKING

import pytest

from overpower import remote
from overpower.errors import BadInvocationError, OverpowerError, RefusedError
from tests.support import git_remote
from tests.support.gates import needs_network

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from pathlib import Path

ROOT_URL = "https://github.com/owner/repo"
_TARBALL = "https://codeload.github.com/owner/repo/tar.gz/HEAD"
_NO_HEADERS = email.message.Message()
"""What `HTTPError` wants in the `hdrs` position: an `email.message.Message`."""


def _tarball(tmp_path: Path, files: Mapping[str, str], *, top: str = "repo-main") -> bytes:
    """A real `.tar.gz` of the shape codeload serves: one top directory, then the tree."""
    staged = tmp_path / "staged" / top
    for relative, content in files.items():
        destination = staged / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8", newline="\n")

    archive_path = tmp_path / "payload.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(staged, arcname=top)
    return archive_path.read_bytes()


def _planting(monkeypatch: pytest.MonkeyPatch, files: Mapping[str, str]) -> None:
    """Aim the primary obtainer at a tree that is simply already there."""
    monkeypatch.setattr(remote, "fetch_with_git", git_remote.planting(files))


def _serving(payload: bytes) -> Callable[..., io.BytesIO]:
    """A stub of `urlopen` answering 200 with `payload`."""

    def opener(*_args: object, **_kwargs: object) -> io.BytesIO:
        return io.BytesIO(payload)

    return opener


def _refusing(failure: Exception) -> Callable[..., io.BytesIO]:
    """A stub of `urlopen` that fails the way the network fails."""

    def opener(*_args: object, **_kwargs: object) -> io.BytesIO:
        raise failure

    return opener


# --------------------------------------------------------------------------- #
# the URL is a search root, not an address
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("url", "ref", "subpath"),
    [
        pytest.param(ROOT_URL, "HEAD", "", id="repository root"),
        pytest.param(f"{ROOT_URL}/", "HEAD", "", id="trailing slash"),
        pytest.param(f"{ROOT_URL}.git", "HEAD", "", id="dot-git"),
        pytest.param("github.com/owner/repo", "HEAD", "", id="no scheme"),
        pytest.param(f"{ROOT_URL}/tree/main", "main", "", id="branch, no path"),
        pytest.param(f"{ROOT_URL}/tree/main/skills", "main", "skills", id="a subfolder"),
        pytest.param(
            f"{ROOT_URL}/tree/v1.0.0/skills/alpha", "v1.0.0", "skills/alpha", id="a tag, deeper"
        ),
        pytest.param(
            f"{ROOT_URL}/blob/9f8e7d6/skills/alpha/SKILL.md",
            "9f8e7d6",
            "skills/alpha/SKILL.md",
            id="a sha, at the file",
        ),
    ],
)
def test_a_github_url_parses_into_owner_repository_ref_and_search_root(
    url: str, ref: str, subpath: str
) -> None:
    """`tree/<ref>/<path>` pins branch, tag or SHA with no field of our own."""
    source = remote.parse(url)

    assert (source.owner, source.repo) == ("owner", "repo")
    assert source.ref == ref
    assert source.subpath == subpath


def test_the_remote_and_the_tarball_are_rebuilt_from_the_parts() -> None:
    """Rebuilt, never echoed: whatever userinfo a pasted URL carried is dropped.

    Credential is *nothing on either side* — the primary uses what `git` already
    has, the fallback is always anonymous — so a token pasted into the URL has to
    stop here rather than travel into a subprocess.
    """
    source = remote.parse("https://ghp_secret@github.com/owner/repo/tree/main/skills")

    assert source.remote_url == "https://github.com/owner/repo.git"
    assert source.tarball_url == "https://codeload.github.com/owner/repo/tar.gz/main"


@pytest.mark.parametrize(
    "url",
    [
        pytest.param("https://gitlab.com/owner/repo", id="another forge"),
        pytest.param("https://github.com/owner", id="no repository"),
        pytest.param("https://github.com/owner/repo/pull/42", id="not a tree url"),
        pytest.param("https://github.com/owner/repo/tree/main/../../etc", id="climbing out"),
    ],
)
def test_a_url_that_is_not_a_github_repository_exits_two(url: str) -> None:
    """The defect is in what was typed, so it is `2` and not `1`."""
    with pytest.raises(BadInvocationError):
        remote.parse(url)


# --------------------------------------------------------------------------- #
# the primary: a real subprocess against a real local remote
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "kind",
    [
        pytest.param("branch", id="branch"),
        pytest.param("tag", id="tag"),
        pytest.param("sha", id="full sha"),
    ],
)
def test_branch_tag_and_a_full_sha_all_reach_the_same_tree(tmp_path: Path, kind: str) -> None:
    """The discriminator that made `init`+`fetch` beat `clone --branch`, which fails on a SHA."""
    # given
    local = git_remote.build(tmp_path / "origin", git_remote.skill_files("alpha"), tag="v1.0.0")
    ref = {"branch": local.branch, "tag": local.tag or "", "sha": local.head}[kind]

    tree = remote.fetch_with_git(local.url, ref, tmp_path / "scratch")

    assert (tree / "skills" / "alpha" / "SKILL.md").is_file()
    assert not (tree / ".git").exists()


def test_a_ref_that_does_not_exist_is_an_obtention_failure_naming_it(tmp_path: Path) -> None:
    """`couldn't find remote ref` comes out identical here and against GitHub."""
    # given
    local = git_remote.build(tmp_path / "origin", git_remote.skill_files("alpha"))

    with pytest.raises(remote.ObtentionError) as failure:
        remote.fetch_with_git(local.url, "nope", tmp_path / "scratch")

    assert "couldn't find remote ref" in str(failure.value)


def test_a_remote_that_does_not_exist_is_an_obtention_failure(tmp_path: Path) -> None:
    with pytest.raises(remote.ObtentionError):
        remote.fetch_with_git(str(tmp_path / "nothing-here"), "main", tmp_path / "scratch")


def test_the_git_subprocess_runs_under_the_c_locale(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The three obtention failures all exit 128 and only the stderr tells them apart.

    Git's strings are translatable — 20 `git.mo` catalogues on the host that
    measured it — so the guard is what keeps the classification from depending on
    the developer's locale.

    The expected environment is **written out here** rather than read back off
    the module: comparing the product against its own constant would assert
    nothing. What it says is the whole policy — the parent's environment is
    inherited, because *"the primary uses what `git` already has"* is the
    credential surface, and exactly two keys are overridden. The mechanism of the
    primary stays undoubled next door, against a real local remote; a spy is the
    only instrument that can see what a subprocess was handed.
    """
    # given
    seen: list[object] = []
    monkeypatch.setenv("OVERPOWER_INHERITED_PROBE", "carried through")

    def spy(*_args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        seen.append(kwargs.get("env"))
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", spy)

    remote.fetch_with_git("https://github.com/owner/repo.git", "main", tmp_path / "scratch")

    expected = {**os.environ, "LC_ALL": "C", "GIT_TERMINAL_PROMPT": "0"}
    assert expected["OVERPOWER_INHERITED_PROBE"] == "carried through"
    assert seen == [expected] * len(seen)
    assert len(seen) == 4


# --------------------------------------------------------------------------- #
# the fallback: real tarfile, stubbed HTTP
# --------------------------------------------------------------------------- #


def test_the_fallback_unpacks_a_real_tarball_into_the_search_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The top directory codeload wraps the tree in is unwrapped here, not searched through."""
    # given
    payload = _tarball(tmp_path, git_remote.skill_files("alpha"))
    monkeypatch.setattr(remote, "urlopen", _serving(payload))

    tree = remote.fetch_tarball(remote.parse(ROOT_URL).tarball_url, tmp_path / "scratch")

    assert (tree / "skills" / "alpha" / "SKILL.md").is_file()


@pytest.mark.parametrize(
    "failure",
    [
        pytest.param(
            urllib.error.HTTPError(_TARBALL, 404, "Not Found", _NO_HEADERS, None),
            id="404",
        ),
        pytest.param(urllib.error.URLError(TimeoutError("timed out")), id="timeout"),
    ],
)
def test_a_fallback_that_cannot_reach_codeload_is_an_obtention_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: Exception
) -> None:
    """Anonymous means the 404 is bare in all three cases — it is not classified, only reported."""
    monkeypatch.setattr(remote, "urlopen", _refusing(failure))

    with pytest.raises(remote.ObtentionError):
        remote.fetch_tarball(remote.parse(ROOT_URL).tarball_url, tmp_path / "scratch")


def test_a_payload_that_is_not_an_archive_is_an_obtention_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A corporate proxy answering 200 with an HTML login page is the measured shape of this."""
    monkeypatch.setattr(remote, "urlopen", _serving(b"<html>sign in</html>"))

    with pytest.raises(remote.ObtentionError):
        remote.fetch_tarball(remote.parse(ROOT_URL).tarball_url, tmp_path / "scratch")


# --------------------------------------------------------------------------- #
# which path runs, and what happens when neither does
# --------------------------------------------------------------------------- #


def test_a_failed_primary_falls_back_to_the_anonymous_tarball(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No third-party binary is a requirement — axiom 1, as amended by ADR 0007."""
    # given
    monkeypatch.setattr(remote, "fetch_with_git", git_remote.refusing("git: not found"))
    payload = _tarball(tmp_path, git_remote.skill_files("alpha"))
    monkeypatch.setattr(remote, "urlopen", _serving(payload))

    tree = remote.obtain(remote.parse(ROOT_URL), tmp_path / "scratch")

    assert (tree / "skills" / "alpha" / "SKILL.md").is_file()


def test_a_primary_that_fails_outside_its_own_error_still_falls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """*"Obtention failure"* is a class, not one exception: a scratch that cannot
    be created is exactly as failed as a ref that does not exist.

    Left uncaught it would reach the CLI's last resort and render as *"this is a
    bug in the overpower"* — a diagnosis that is both wrong and unactionable —
    with the fallback that could have recovered it never even tried.
    """

    # given
    def broken(*_args: object, **_kwargs: object) -> Path:
        message = "No space left on device"
        raise OSError(message)

    monkeypatch.setattr(remote, "fetch_with_git", broken)
    payload = _tarball(tmp_path, git_remote.skill_files("alpha"))
    monkeypatch.setattr(remote, "urlopen", _serving(payload))

    tree = remote.obtain(remote.parse(ROOT_URL), tmp_path / "scratch")

    assert (tree / "skills" / "alpha" / "SKILL.md").is_file()


def test_a_git_directory_that_will_not_go_does_not_discard_an_obtained_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Shedding `.git` is hygiene, and hygiene must not throw away a checkout.

    Failing here would send an already-delivered tree into a fallback that
    re-downloads the whole repository to return the identical answer — the exact
    defect #25 measured, arriving through a different door.
    """
    # given
    local = git_remote.build(tmp_path / "origin", git_remote.skill_files("alpha"))

    def immovable(path: Path) -> None:
        if path.name == ".git":
            message = "Device or resource busy"
            raise OSError(message)
        remote.discard(path)

    monkeypatch.setattr(remote, "discard", immovable)

    tree = remote.fetch_with_git(local.url, local.branch, tmp_path / "scratch")

    assert (tree / "skills" / "alpha" / "SKILL.md").is_file()


def test_when_both_paths_fail_the_transport_error_is_the_one_passed_through(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`git` names the problem; the anonymous tarball answers a bare 404 to all three.

    Propagating the last exception would show the user the worse of the two.
    """
    # given
    monkeypatch.setattr(
        remote, "fetch_with_git", git_remote.refusing("fatal: couldn't find remote ref nope")
    )
    monkeypatch.setattr(
        remote, "urlopen", _refusing(urllib.error.URLError(TimeoutError("timed out")))
    )

    with pytest.raises(remote.ObtentionError) as failure:
        remote.obtain(remote.parse(ROOT_URL), tmp_path / "scratch")

    assert "couldn't find remote ref nope" in str(failure.value)


# --------------------------------------------------------------------------- #
# the search, and the scratch
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "depth",
    [
        pytest.param("", id="repository root"),
        pytest.param("/skills", id="a subfolder"),
        pytest.param("/skills/alpha", id="the artifact's own folder"),
    ],
)
def test_the_three_depths_of_url_find_the_same_skill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, depth: str
) -> None:
    """The URL is a search root, not an address: deeper only buys a shorter walk.

    Against a **real local remote**, through the real `git` subprocess — the
    doubles table leaves the primary undoubled, and only the one argument that
    cannot be a local path, the URL, is replaced.
    """
    # given
    local = git_remote.build(tmp_path / "origin", git_remote.skill_files("alpha", "beta"))
    monkeypatch.setattr(remote, "fetch_with_git", git_remote.instead_of_github(local))

    with remote.catalog_from(f"{ROOT_URL}/tree/{local.branch}{depth}", ["alpha"]) as catalog:
        assert [artifact.name for artifact in catalog.pool] == ["alpha"]
        assert catalog.pool[0].description == "The alpha skill."


def test_a_skill_that_is_not_under_the_root_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """Obtained, searched, and the answer is no — the defect is not in the line."""
    _planting(monkeypatch, git_remote.skill_files("alpha"))

    with pytest.raises(RefusedError), remote.catalog_from(ROOT_URL, ["beta"]):
        pass  # unreachable: the search raises before the block is entered


def test_two_skills_with_the_same_name_under_one_root_are_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Measured at zero in `mattpocock/skills`, and still answered rather than guessed."""
    # given
    planted = {
        **git_remote.skill_files("alpha"),
        **git_remote.skill_files("alpha", under="vendor/skills"),
    }
    _planting(monkeypatch, planted)

    with pytest.raises(RefusedError), remote.catalog_from(ROOT_URL, ["alpha"]):
        pass  # unreachable: the search raises before the block is entered


def test_a_subpath_the_repository_does_not_have_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Still exit 3: a second obtention would return the identical answer."""
    _planting(monkeypatch, git_remote.skill_files("alpha"))

    with pytest.raises(RefusedError), remote.catalog_from(f"{ROOT_URL}/tree/HEAD/nope", ["alpha"]):
        pass  # unreachable: the descent raises before the block is entered


def test_the_scratch_is_removed_even_when_the_search_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No cache, and no leftovers: remote content is fresh by decision (rule 5)."""
    # given
    scratches: list[Path] = []

    def planting(url: str, ref: str, into: Path) -> Path:
        scratches.append(into.parent)
        return git_remote.planting(git_remote.skill_files("alpha"))(url, ref, into)

    monkeypatch.setattr(remote, "fetch_with_git", planting)

    with pytest.raises(RefusedError), remote.catalog_from(ROOT_URL, ["beta"]):
        pass  # unreachable: the search raises before the block is entered

    assert scratches
    assert not any(scratch.exists() for scratch in scratches)


def test_the_scratch_is_removed_after_a_successful_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # given
    scratches: list[Path] = []

    def planting(url: str, ref: str, into: Path) -> Path:
        scratches.append(into.parent)
        return git_remote.planting(git_remote.skill_files("alpha"))(url, ref, into)

    monkeypatch.setattr(remote, "fetch_with_git", planting)

    with remote.catalog_from(ROOT_URL, ["alpha"]) as catalog:
        assert catalog.pool[0].path.is_dir()

    assert scratches
    assert not any(scratch.exists() for scratch in scratches)


def test_a_scratch_carrying_a_real_git_directory_is_still_removed(tmp_path: Path) -> None:
    """Git writes its objects read-only, and on Windows that is what defeats `rmtree`."""
    # given
    local = git_remote.build(tmp_path / "origin", git_remote.skill_files("alpha"))
    scratch = tmp_path / "scratch"
    git_remote.git("clone", local.url, str(scratch), cwd=tmp_path)

    remote.discard(scratch)

    assert not scratch.exists()


@pytest.mark.skipif(sys.platform == "win32", reason="a mode of 0 is not how Windows refuses")
def test_a_directory_that_refuses_to_be_walked_is_still_removed(tmp_path: Path) -> None:
    """The other half of the retry: on POSIX what refuses is a *directory*.

    Setting `S_IWRITE` absolutely would strip read and execute and leave the walk
    exactly as stuck as it was. Presumes an ordinary user, which every cell of
    the matrix is — root would not be refused in the first place.
    """
    # given
    scratch = tmp_path / "scratch"
    locked = scratch / "locked"
    locked.mkdir(parents=True)
    (locked / "inside.txt").write_text("content", encoding="utf-8")
    locked.chmod(0o000)

    remote.discard(scratch)

    assert not scratch.exists()


def test_a_remote_search_describes_a_skill_the_way_the_embedded_walk_does(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both paths read the artifact's own `SKILL.md`, which is why they agree."""
    _planting(monkeypatch, git_remote.skill_files("alpha"))

    with remote.catalog_from(ROOT_URL, ["alpha"]) as catalog:
        artifact = catalog.pool[0]

    assert artifact.description == "The alpha skill."
    assert artifact.files == 1
    assert artifact.size > 0


@pytest.mark.parametrize(
    "depth",
    [
        pytest.param("", id="repository root"),
        pytest.param("/.overpower", id="a subfolder"),
        pytest.param("/.overpower/mcp", id="the recipe's own folder"),
    ],
)
def test_the_three_depths_of_url_find_the_same_mcp_recipe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, depth: str
) -> None:
    """Same rule as the skill search (#83): the URL is a search root, not an address."""
    # given
    local = git_remote.build(tmp_path / "origin", git_remote.mcp_recipe_files("alpha", "beta"))
    monkeypatch.setattr(remote, "fetch_with_git", git_remote.instead_of_github(local))

    with remote.catalog_from(f"{ROOT_URL}/tree/{local.branch}{depth}", mcps=["alpha"]) as catalog:
        assert [recipe.name for recipe in catalog.mcps] == ["alpha"]
        assert catalog.mcps[0].description == "The alpha MCP server."


def test_an_mcp_recipe_that_is_not_under_the_root_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Obtained, searched, and the answer is no — the defect is not in the line."""
    _planting(monkeypatch, git_remote.mcp_recipe_files("alpha"))

    with pytest.raises(RefusedError), remote.catalog_from(ROOT_URL, mcps=["beta"]):
        pass  # unreachable: the search raises before the block is entered


def test_two_mcp_recipes_with_the_same_name_under_one_root_are_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same reasoning as the skill collision: picking one would be the defect."""
    # given
    planted = {
        **git_remote.mcp_recipe_files("alpha"),
        **git_remote.mcp_recipe_files("alpha", under="vendor/.overpower/mcp"),
    }
    _planting(monkeypatch, planted)

    with pytest.raises(RefusedError), remote.catalog_from(ROOT_URL, mcps=["alpha"]):
        pass  # unreachable: the search raises before the block is entered


def test_a_remote_search_reads_an_mcp_recipe_the_way_the_embedded_walk_does(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both paths go through `read_recipe`, which is why they agree on the shape."""
    _planting(monkeypatch, git_remote.mcp_recipe_files("alpha"))

    with remote.catalog_from(ROOT_URL, mcps=["alpha"]) as catalog:
        recipe = catalog.mcps[0]

    assert recipe.description == "The alpha MCP server."
    assert recipe.transport is recipe.transport.STDIO


def test_an_obtention_failure_is_not_a_refusal() -> None:
    """The `except` order of the CLI is the axis: 1 is ours, 3 is the answer being no."""
    assert issubclass(remote.ObtentionError, OverpowerError)
    assert not issubclass(remote.ObtentionError, RefusedError)
    assert not issubclass(remote.ObtentionError, BadInvocationError)


# --------------------------------------------------------------------------- #
# the real GitHub: an act of curation, in no CI job
# --------------------------------------------------------------------------- #


@pytest.mark.network
@needs_network
def test_a_pasted_github_url_serves_a_skill_from_the_real_github() -> None:
    """The end-to-end proof, run by hand next to refreshing the vendored content.

        OVERPOWER_NETWORK_TESTS=1 uv run pytest -m network

    A gate blocks what this repository controls; what depends on a third party is
    an act of curation. With the variable set the skip can no longer be
    satisfied, so this turning red is what a rename or a loss looks like.
    """
    with remote.catalog_from("https://github.com/mattpocock/skills", ["wayfinder"]) as catalog:
        assert catalog.pool[0].name == "wayfinder"
        assert catalog.pool[0].description
        assert catalog.pool[0].files > 0


@pytest.mark.network
@needs_network
def test_the_real_codeload_serves_the_tarball_the_fallback_asks_for(tmp_path: Path) -> None:
    """The fallback's own end-to-end proof, and it needs its own: the test above
    exercises the primary and would stay green with codeload's URL shape wrong.

    What it pins is the shape rather than the content — the direct `tar.gz/<ref>`
    address answering without a redirect, and the single top directory the
    unwrapping steps past.
    """
    source = remote.parse("https://github.com/mattpocock/skills")

    tree = remote.fetch_tarball(source.tarball_url, tmp_path / "scratch")

    assert sorted(found.parent.name for found in tree.rglob("SKILL.md"))
    assert (tree / "skills").is_dir()
