"""`--from <url>`: any GitHub repository as a search root, obtained two ways.

The vendored copy ages by construction — measured, the upstream moved a version
in two days — so `--from` points at **any GitHub repository, with no
registration**. It is exclusive: with it, only the remote is consulted, which is
what extinguishes the question of precedence between embedded and remote before
anyone has to answer it. And it holds **for `--skill` and `--mcp` only** in
v0.1.0: those two are the units that exist outside a repository that already
knows the overpower, while a bundle and an AI Framework only exist in one
(https://github.com/panlabs-tech/overpower/issues/83).

**The URL is a search root, not an address.** The repository root, a subfolder
and the artifact's own folder give the *same* result, and the deepest one only
buys a shorter walk. `tree/<ref>/<path>` pins a branch, a tag **or a SHA** with
no field of our own — reproducibility for free.

**A skill is found by its own `SKILL.md`; a recipe, by the fixed convention
path `.overpower/mcp/<slug>.toml`** (`docs/agents/domain.md` § Vocabulário) —
the one half of that convention the MCP spec's tracer bullet fixed without
deciding the other, which is what a bundle or an AI Framework in a home-made
repository still waits on (#26). Both searches obey the same root rule; only
what they match at the bottom of the walk differs.

**Obtention has two paths and one search** (ADR 0007,
https://github.com/panlabs-tech/overpower/issues/25):

- **primary** — `init` + `remote add` + `fetch --depth 1 origin <ref>` +
  `checkout FETCH_HEAD`, a full checkout, then a walk for `SKILL.md`.
  `clone --branch` lost by measurement rather than by taste: it **fails on a
  SHA**, which would break the pinning `tree/<ref>/<path>` promises. One code
  path serves branch, tag and SHA;
- **fallback** — the anonymous `codeload` tarball, which answers **200 with zero
  redirect** for all three kinds of ref, against an API path that reaches the
  same bytes through a 302 and costs **one more host** on the allow-list. Pure
  Python: **no third-party binary is a requirement** (axiom 1, as amended). `git`
  enters as **transport, never as installer**.

**The fallback fires on a failure to obtain, and never on "I did not find it"** —
measured as a live bug in #25, where it ran for *"the skill is not there"* and
returned an identical answer **after re-fetching the whole repository**. The
ruler:

- **exit 1** — could not obtain the search root. The transport's own error is
  passed through, because it is the one that names the problem: a ref that does
  not exist, a repository that does not exist, a credential that is missing;
- **exit 3** — obtained, searched, and the answer is no. **The fallback does not
  run**, because a second obtention would return the identical answer.

**`LC_ALL=C` is mandatory** on the subprocess: the three obtention failures all
exit `128` and **only the stderr tells them apart** — and git's strings are
translatable.

**Credential: none on either side.** The primary uses whatever `git` already
has; the fallback is always anonymous. The accepted consequence: a private
repository the local `git` cannot reach is not recoverable.

**Scratch in a temporary directory, removed in the `finally`, no cache.** Remote
content is fresh by decision (rule 5 of the model), and the only thing a cache
would buy is time — the axis the dev declared does not weigh. **Zero new
dependencies**: `urllib`, `tarfile`, `shutil` and `tempfile` are the standard
library.
"""

from __future__ import annotations

import io
import os
import shutil
import stat
import subprocess
import tarfile
import tempfile
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlsplit
from urllib.request import urlopen

from overpower.discovery import SKILL_FILE, ArtifactType, Catalog, artifact_at
from overpower.errors import BadInvocationError, OverpowerError, RefusedError
from overpower.recipes import RECIPE_SUFFIX, read_recipe
from overpower.runtimes import Scope

if TYPE_CHECKING:
    from collections.abc import Generator, Mapping, Sequence

    from overpower.discovery import Artifact
    from overpower.recipes import Recipe

_GIT = "git"
"""Invoked by name and without a shell. Resolving an absolute path would pin the
product to the machine that built it, which is what `S603`/`S607` are waived for."""

HOSTS = frozenset({"github.com", "www.github.com"})
"""The source is GitHub, and only GitHub — other forges left the scope in #25."""

CODELOAD = "https://codeload.github.com"
"""Where the anonymous tarball lives, direct: 200 with zero redirect on all three
kinds of ref, against a 302 and one extra allow-list host through the API."""

DEFAULT_REF = "HEAD"
"""What a URL with no `tree/<ref>` means, and it is a ref both paths accept."""

TREE_SEGMENTS = frozenset({"tree", "blob"})
"""What GitHub puts between the repository and the path. `blob` is accepted for
the same reason the URL is a search root: the address of a `SKILL.md` and the
address of the folder holding it are the same question."""

TIMEOUT = 30.0
"""Seconds the anonymous fetch waits. The primary carries none on purpose: a
wrong number there would kill a legitimately slow clone of a large repository."""

SCRATCH_PREFIX = "overpower-"
"""`tempfile` honours `TMPDIR`; the prefix is what makes a leaked directory
identifiable as ours."""

_PRIMARY_DIR = "git"
_FALLBACK_DIR = "tarball"
"""Each path unpacks into its own subdirectory of the scratch, so a primary that
failed halfway cannot leave debris inside the tree the fallback then lands."""

_FEDERATED_MCP_DIR = (".overpower", "mcp")
"""The fixed two segments a recipe's parent directory must end in.

A recipe has no folder of its own the way a skill does — one flat directory
holds every `<slug>.toml` — so the search matches a **fixed path suffix**
instead of a free-form folder name. Checked as the last two `.parts` of the
match's parent rather than as a prefix of `root`, which is what makes the same
check pass at any of the three depths: the suffix is there whether `root` is
the repository, `.overpower`, or `.overpower/mcp` itself."""


class BadRemoteUrlError(BadInvocationError):
    """A `--from` value that is not a GitHub repository URL.

    Exit **2**: the defect is in what was typed, and no obtention is attempted —
    a malformed line must not cost a network round trip.
    """

    def __init__(self, url: str, because: str) -> None:
        """Name the URL that was given and the rule it missed."""
        self.url = url
        super().__init__(f"`--from {url}` is not a GitHub repository URL: {because}")


class ObtentionError(OverpowerError):
    """The search root could not be obtained — the named half of exit **1**.

    Both paths raise it, and `obtain` re-raises the **primary's** message with
    the fallback's as a note. That order is measured: `git` names the problem
    (`could not read Username`, `couldn't find remote ref …`) while the anonymous
    tarball answers a bare `404` to all three cases, so propagating the last
    exception would show the user the worse of the two.
    """


class MissingSubpathError(RefusedError):
    """The URL names a folder the repository does not have at that ref.

    Exit **3**, not 1, and the discriminator is the one #25 measured: obtaining
    the repository a second time returns the identical answer, so this is *"ran,
    and the answer is no"* rather than *"could not run"*. It is named apart from
    the skill not being found because the defect is in a different half of the
    URL, and naming the actual defect is the whole thesis of the error model.
    """

    def __init__(self, source: Source) -> None:
        """Name the path and the ref it was looked for at."""
        self.source = source
        super().__init__(
            f"`{source.subpath}` is not in {source.owner}/{source.repo} at `{source.ref}`"
        )


class RemoteSkillNotFoundError(RefusedError):
    """No `SKILL.md` under the search root sits in a folder of that name.

    Exit **3**, and deliberately not the exit **2** the embedded catalog answers
    with. There the list is closed, so a name outside it is a typo; here the
    search space is a whole repository someone else owns, so the product ran,
    looked, and the answer is no.
    """

    def __init__(self, name: str, source: Source) -> None:
        """Name what was looked for and where, in the terms of the URL."""
        self.name = name
        self.source = source
        super().__init__(f"no skill named `{name}` under {source.shown}")


class AmbiguousRemoteSkillError(RefusedError):
    """More than one folder of that name carries a `SKILL.md` under the root.

    Measured at **zero** among the 35 `SKILL.md` of `mattpocock/skills`, and
    answered anyway: picking one would be the class of defect this product exists
    not to commit. The fix is in the caller's hands — a deeper URL is a narrower
    search root — so every candidate travels in the message.
    """

    def __init__(self, name: str, source: Source, found: Sequence[Path]) -> None:
        """Name every candidate, relative to the search root, so a deeper URL is one edit."""
        self.name = name
        self.source = source
        self.found = tuple(found)
        listed = ", ".join(path.as_posix() for path in self.found)
        super().__init__(
            f"`{name}` is ambiguous under {source.shown}: {listed}. "
            "Point --from at one of them instead"
        )


class RemoteRecipeNotFoundError(RefusedError):
    """No `.overpower/mcp/<slug>.toml` under the search root names this recipe.

    Exit **3**, the same axis as `RemoteSkillNotFoundError`: the search space is
    a whole repository someone else owns, so the product ran, looked, and the
    answer is no — not the exit **2** the embedded catalog's closed list answers
    a typo with.
    """

    def __init__(self, name: str, source: Source) -> None:
        """Name what was looked for and where, in the terms of the URL."""
        self.name = name
        self.source = source
        super().__init__(f"no recipe named `{name}` under {source.shown}")


class AmbiguousRemoteRecipeError(RefusedError):
    """More than one `.overpower/mcp/{name}.toml` sits under the search root.

    Same reasoning as `AmbiguousRemoteSkillError`: picking one would be the
    class of defect this product exists not to commit, so every candidate
    travels in the message and the fix stays in the caller's hands.
    """

    def __init__(self, name: str, source: Source, found: Sequence[Path]) -> None:
        """Name every candidate, relative to the search root, so a deeper URL is one edit."""
        self.name = name
        self.source = source
        self.found = tuple(found)
        listed = ", ".join(path.as_posix() for path in self.found)
        super().__init__(
            f"`{name}` is ambiguous under {source.shown}: {listed}. "
            "Point --from at one of them instead"
        )


@dataclass(frozen=True)
class Source:
    """A GitHub URL, taken apart into the four things obtention and search need.

    The two URLs it answers are **rebuilt from the parts**, never echoed: a
    token pasted into the address stops here rather than travelling into a
    subprocess or onto the wire, which is what *"no credential on either side"*
    means in code.
    """

    owner: str
    repo: str
    ref: str
    subpath: str
    """Repository-relative, `/`-separated, possibly empty — the search root."""

    @property
    def remote_url(self) -> str:
        """What `git remote add origin` receives."""
        return f"https://github.com/{self.owner}/{self.repo}.git"

    @property
    def tarball_url(self) -> str:
        """What the anonymous fallback asks `codeload` for."""
        return f"{CODELOAD}/{self.owner}/{self.repo}/tar.gz/{self.ref}"

    @property
    def shown(self) -> str:
        """How a message names the search root back to whoever typed it."""
        below = f"/{self.subpath}" if self.subpath else ""
        return f"{self.owner}/{self.repo}@{self.ref}{below}"


def parse(url: str) -> Source:
    """A GitHub URL as the parts obtention needs, or the error naming what missed.

    The scheme is optional because a URL copied out of a browser bar sometimes
    arrives without one, and demanding it would be a refusal with no subject.
    """
    text = url.strip()
    if "://" not in text:
        text = f"https://{text}"
    split = urlsplit(text)
    if split.hostname not in HOSTS:
        raise BadRemoteUrlError(url, "the source of `--from` is github.com, and only github.com")

    segments = [segment for segment in split.path.split("/") if segment]
    if len(segments) < 2:  # noqa: PLR2004 — owner and repository, the two a URL must carry
        raise BadRemoteUrlError(url, "a repository URL names an owner and a repository")

    owner, repo, *below = segments
    ref, subpath = _ref_and_subpath(url, below)
    return Source(owner=owner, repo=repo.removesuffix(".git"), ref=ref, subpath=subpath)


def _ref_and_subpath(url: str, below: Sequence[str]) -> tuple[str, str]:
    """`tree/<ref>/<path>` taken apart, or `HEAD` and the whole repository.

    **The known limit, declared rather than papered over**: a branch whose name
    contains a `/` is indistinguishable from a ref plus a path without asking the
    server which refs exist, and asking costs a round trip on every invocation.
    The first segment is the ref; a `tree/release/1.0/skills` URL therefore reads
    `release` plus `1.0/skills`, and the fix in the user's hands is a deeper URL
    or a SHA.
    """
    if not below:
        return DEFAULT_REF, ""
    kind, *rest = below
    if kind not in TREE_SEGMENTS or not rest:
        raise BadRemoteUrlError(url, "below the repository a GitHub URL reads `tree/<ref>/<path>`")
    ref, *parts = rest
    if any(part in {".", ".."} for part in parts):
        raise BadRemoteUrlError(url, "a `.` or `..` segment is not part of a GitHub URL")
    return ref, "/".join(parts)


@contextmanager
def catalog_from(
    url: str, skills: Sequence[str] = (), mcps: Sequence[str] = ()
) -> Generator[Catalog]:
    """The remote `skills` and `mcps`, as a catalog, for the life of the block.

    A `Catalog` and not a new type, so everything downstream — planning, the
    screen, the writer — stays exactly as it is: `--from` changes *where the
    catalog comes from* and nothing else about what happens to it. It carries no
    framework and no bundle, which is the same statement the invocation guard
    makes on the command line, said again in the data.

    The scratch is removed in the `finally`, so it goes whether the search
    answered, refused or the caller declined the confirmation inside the block.
    """
    source = parse(url)
    scratch = Path(tempfile.mkdtemp(prefix=SCRATCH_PREFIX))
    try:
        root = search_root(obtain(source, scratch), source)
        yield Catalog(
            frameworks=(),
            pool=tuple(_skill_called(name, root, source) for name in dict.fromkeys(skills)),
            bundles=(),
            mcps=tuple(_mcp_called(name, root, source) for name in dict.fromkeys(mcps)),
        )
    finally:
        discard(scratch)


@contextmanager
def sources_for(
    catalog: Catalog, names: Sequence[str], scope: Scope
) -> Generator[Mapping[str, Path]]:
    """The clone each `[source]`-bearing recipe among `names` brings, keyed by its name.

    Obtained here and not inside `overpower.planning.plan_for`, for the same reason
    `catalog_from` obtains its catalog outside it: planning stays a value-in,
    value-out function, and a plan that fetched for itself could not be built
    from a scratch tree that survives past the call that built it — the writer
    needs that tree still on disk at `execute()` time.

    **Nothing is obtained outside `Scope.GLOBAL`.** `overpower.planning` refuses
    a `[source]` recipe in any other scope before the plan names a single write
    (ADR 0015) — the answer is already known from `scope` alone, with no catalog
    lookup needed to reach it, so obtaining first would cost a real `git fetch`
    for a line already certain to be refused.

    In `Scope.GLOBAL`, every named recipe with `[source]` is obtained
    **unconditionally**, dry run or not — the same promise `overpower.cli._perform`'s
    docstring makes for `--from`: a `--dry-run` that skipped this would report on
    a clone different from the one the real run brings. What dry run skips is the
    second half — landing the clone at its destination — which is
    `overpower.writing`'s, run only when `execute()` is.

    The scratch is removed in the `finally`, so it goes whether the plan built
    on top of it was written, printed as a dry run, or never reached at all.
    """
    scratch = Path(tempfile.mkdtemp(prefix=SCRATCH_PREFIX))
    try:
        trees: dict[str, Path] = {}
        if scope is Scope.GLOBAL:
            for name in dict.fromkeys(names):
                recipe = catalog.mcp(name)
                if recipe.source is None:
                    continue
                found = parse(recipe.source)
                trees[name] = search_root(obtain(found, scratch / name), found)
        yield trees
    finally:
        discard(scratch)


def obtain(source: Source, scratch: Path) -> Path:
    """The repository tree on disk: the transport first, the anonymous tarball after.

    The two are tried in this order and no other. The primary reuses the
    credential surface `git` already has — helper, SSH key, the editor's
    `GIT_ASKPASS` — and the fallback exists so that no third-party binary is a
    *requirement*, which is the obligation the amendment to axiom 1 added.
    """
    try:
        return fetch_with_git(source.remote_url, source.ref, scratch / _PRIMARY_DIR)
    except (ObtentionError, OSError) as transport:
        try:
            return fetch_tarball(source.tarball_url, scratch / _FALLBACK_DIR)
        except (ObtentionError, OSError) as anonymous:
            message = f"{transport} (the anonymous fallback did not recover it either: {anonymous})"
            raise ObtentionError(message) from transport


def fetch_with_git(remote_url: str, ref: str, into: Path) -> Path:
    """`init` + `remote add` + `fetch --depth 1` + `checkout FETCH_HEAD`, then no `.git`.

    One code path for a branch, a tag and a full SHA — which is precisely what
    `clone --branch` cannot do.

    **The honest limit**, and it is the server's rather than ours: fetching an
    arbitrary SHA depends on the remote allowing it (`uploadpack.allowAnySHA1InWant`).
    That GitHub does was measured in #25.
    """
    into.mkdir(parents=True, exist_ok=True)
    _git("init", "-q", cwd=into)
    _git("remote", "add", "origin", remote_url, cwd=into)
    _git("fetch", "--depth", "1", "origin", ref, cwd=into)
    _git("checkout", "-q", "FETCH_HEAD", cwd=into)
    _shed_repository_metadata(into)
    return into


def _shed_repository_metadata(tree: Path) -> None:
    """Take `.git` out of the obtained tree — and never fail the obtention over it.

    The removal is hygiene, not obtention: by the time it runs the checkout has
    already delivered, and a tree in hand must not be thrown away — least of all
    into a fallback that would download the whole repository again to return the
    identical answer, which is the exact defect #25 measured. If it survives, the
    only cost is a longer walk, because `.git` holds packed objects and refs and
    no `SKILL.md`, and the scratch it sits in is removed either way.
    """
    with suppress(OSError):
        discard(tree / ".git")


def fetch_tarball(tarball_url: str, into: Path) -> Path:
    """The anonymous `codeload` tarball, unpacked, unwrapped, and nothing else.

    `filter="data"` is not decoration: the archive comes from a repository the
    overpower does not own, and the data filter is what refuses an absolute path
    or a `..` that would land bytes outside the scratch.
    """
    into.mkdir(parents=True, exist_ok=True)
    payload = _downloaded(tarball_url)
    try:
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
            archive.extractall(into, filter="data")
    except (tarfile.TarError, OSError, ValueError) as broken:
        message = f"the tarball at {tarball_url} did not unpack: {broken}"
        raise ObtentionError(message) from broken
    return _unwrapped(into)


def _git_environment() -> dict[str, str]:
    """The environment every `git` subprocess receives, and why it is not `os.environ`.

    Inherited rather than replaced, because *"the primary uses what `git` already
    has"* is the whole credential policy — a scrubbed environment would drop the
    credential helper, `GIT_ASKPASS`, `HOME` and any proxy the corporate machine
    needs. Two keys are overridden:

    - `LC_ALL=C`, because the three obtention failures are told apart by their
      stderr and git's strings are translatable;
    - `GIT_TERMINAL_PROMPT=0`, because a `git` that stops to ask for a username
      would **hang the command in a terminal** instead of failing — and a
      primary that never returns is a fallback that never fires. It also keeps
      the promise that this product asks for no credential of its own.
    """
    return {**os.environ, "LC_ALL": "C", "GIT_TERMINAL_PROMPT": "0"}


def discard(path: Path) -> None:
    """Remove a tree, including one `git` wrote, and never mind if it is already gone.

    Git writes its objects read-only. On POSIX that is usually harmless — the
    *directory* is what governs an unlink — but on Windows `unlink` refuses a
    read-only file outright, which turns an ordinary `rmtree` of a scratch
    checkout into a `PermissionError`. So a refusal widens the owner's rights
    over the whole tree and tries once more, which is what makes the promise
    *"the scratch is removed even on failure"* true on all nine cells.

    A second pass rather than `onexc`, and the reason is mechanical: the callback
    receives the function that failed, and on POSIX `shutil.rmtree` uses the
    file-descriptor walk, where that function is `os.open` with a `dir_fd` — not
    something a retry can call with a path. Widening first and removing after
    needs no assumption about which implementation is running.
    """
    if not path.exists():
        return
    try:
        shutil.rmtree(path)
    except OSError:
        _grant_owner_full_rights(path)
        shutil.rmtree(path)


def _grant_owner_full_rights(root: Path) -> None:
    """Make every entry below `root` removable by the user about to remove it.

    **Symlinks are skipped, and that is the point of the guard**: `chmod` follows
    them, and a checkout of somebody else's repository may carry a link pointing
    anywhere on the machine. Widening rights on a tree that is one call from
    deletion costs nothing; widening them on whatever a link happens to name is a
    different act entirely.
    """
    _widen(root)
    # Top-down, and each name is widened *before* the walk descends into it —
    # which is the documented order, and the only one that reaches inside a
    # directory that currently refuses to be listed at all.
    for base, directories, files in root.walk():
        for name in (*directories, *files):
            _widen(base / name)


def _widen(entry: Path) -> None:
    """Add the owner's rights to whatever `entry` already has, or leave it alone."""
    if entry.is_symlink():
        return
    with suppress(OSError):
        entry.chmod(entry.stat().st_mode | stat.S_IRWXU)


def _git(*args: str, cwd: Path) -> None:
    """One `git` invocation, with its stderr becoming the obtention failure.

    A `git` that is not on the machine at all raises `OSError` here rather than a
    non-zero return code, and it is the same class of outcome: the transport did
    not deliver, so the fallback is what answers next.
    """
    try:
        finished = subprocess.run(  # noqa: S603 — fixed argv, no shell; see _GIT above
            [_GIT, *args],
            cwd=cwd,
            env=_git_environment(),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as unavailable:
        message = f"`git {args[0]}` could not be run: {unavailable}"
        raise ObtentionError(message) from unavailable
    if finished.returncode != 0:
        message = f"`git {args[0]}` failed: {_said(finished)}"
        raise ObtentionError(message)


def _said(finished: subprocess.CompletedProcess[str]) -> str:
    """What the subprocess said, passed through as it said it."""
    return (
        finished.stderr.strip()
        or finished.stdout.strip()
        or f"exit {finished.returncode}, and it said nothing"
    )


def _downloaded(url: str) -> bytes:
    """The bytes at `url`, anonymously, or the obtention failure that says why.

    `HTTPError`, `URLError` and a timeout are all `OSError`, and all three are
    the same outcome here: the anonymous path answers a bare `404` to a missing
    repository, a missing ref and a private repository alike, so there is nothing
    to classify — only something to report.
    """
    try:
        with urlopen(url, timeout=TIMEOUT) as response:  # noqa: S310 — the URL is rebuilt, https, ours
            return bytes(response.read())
    except OSError as failure:
        message = f"the anonymous tarball at {url} did not arrive: {failure}"
        raise ObtentionError(message) from failure


def _unwrapped(into: Path) -> Path:
    """Past the single top directory `codeload` wraps the tree in.

    Falling back to `into` itself when the shape is anything else keeps the walk
    correct rather than guessing: an extra level costs a longer search and never
    a wrong answer.
    """
    children = [child for child in into.iterdir() if child.is_dir()]
    return children[0] if len(children) == 1 else into


def search_root(tree: Path, source: Source) -> Path:
    """Where the walk starts: the tree, or the folder the URL pointed inside it.

    A URL that names a *file* — the `blob` address of a `SKILL.md` — searches
    from the folder holding it, because the URL is a search root and those two
    addresses are the same question.
    """
    if not source.subpath:
        return tree
    root = tree.joinpath(*source.subpath.split("/"))
    if root.is_dir():
        return root
    if root.is_file():
        return root.parent
    raise MissingSubpathError(source)


def _skill_called(name: str, root: Path, source: Source) -> Artifact:
    """The one skill folder called `name` under `root`, described by its own `SKILL.md`.

    The folder name is the artifact's name, exactly as it is for the embedded
    tree (rule 8, ADR 0006) — and the description comes out of `SKILL.md` through
    the same function the embedded walk uses, which is what makes the two paths
    describe an artifact identically.
    """
    matches = sorted(
        {
            found.parent
            for found in root.rglob(SKILL_FILE)
            if found.is_file() and found.parent.name == name
        }
    )
    if not matches:
        raise RemoteSkillNotFoundError(name, source)
    if len(matches) > 1:
        raise AmbiguousRemoteSkillError(
            name, source, [match.relative_to(root) for match in matches]
        )
    return artifact_at(matches[0], ArtifactType.SKILL)


def _mcp_called(name: str, root: Path, source: Source) -> Recipe:
    """The one recipe named `name` under `.overpower/mcp/` somewhere below `root`.

    Read through `read_recipe` — the same reader the embedded catalog uses — so
    a recipe that gets past this function is a recipe that renders, whether it
    came from `catalog/mcps/` or from someone else's repository.
    """
    matches = sorted(
        {
            found
            for found in root.rglob(f"{name}{RECIPE_SUFFIX}")
            if found.is_file() and found.parent.parts[-2:] == _FEDERATED_MCP_DIR
        }
    )
    if not matches:
        raise RemoteRecipeNotFoundError(name, source)
    if len(matches) > 1:
        raise AmbiguousRemoteRecipeError(
            name, source, [match.relative_to(root) for match in matches]
        )
    return read_recipe(matches[0])
