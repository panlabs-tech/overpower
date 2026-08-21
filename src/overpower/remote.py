"""`--from <url>`: any GitHub repository as a search root, obtained two ways.

The vendored copy ages by construction — measured, the upstream moved a version
in two days — so `--from` points at **any GitHub repository, with no
registration**. It is exclusive: with it, only the remote is consulted, which is
what extinguishes the question of precedence between embedded and remote before
anyone has to answer it. It holds for **three of the four units** — `--skill`,
`--mcp` (https://github.com/ThiagoPanini/overpower/issues/83) and `--bundle`
(https://github.com/ThiagoPanini/overpower/issues/137) — and the one left out is
left out **by decision rather than by adjournment**: an AI Framework is a folder
of this wheel, so there is nothing in a third-party repository for the flag to
name. The reason that once excluded bundle alongside it — *"they only exist in a
repository that already knows the overpower"* — stopped holding the moment a
federated recipe shipped, since a repository that writes `.overpower.yaml` knows
the overpower by construction.

**The URL is a search root, not an address.** The repository root, a subfolder
and the artifact's own folder give the *same* result, and the deepest one only
buys a shorter walk. `tree/<ref>/<path>` pins a branch, a tag **or a SHA** with
no field of our own — reproducibility for free.

**Two questions, and the URL means something different to each**
(https://github.com/ThiagoPanini/overpower/issues/135). Named a unit, the URL is
that search root and the walk is free-depth: *reach*. Named none, the question is
the one before the name — *what does this repository offer?* — and the answer is
**anchored** at `skills/` and `.overpower.yaml` as direct children of the
repository, with the URL's subpath ignored entirely. An offer is a property of
the repository, so the root URL and a subfolder's have to answer the same.

**A runtime destination is not an offer.** A repository already equipped with the
overpower carries its skill twice — at `skills/<name>/` and at the runtime's own
`<project_dir>/<name>/` — and the second is where an install put it. Each half
answers that in the way its own rule allows: the showcase by the **anchor**,
which leaves the copy outside the walk with no predicate needed, and the reach by
a **tie-break** — a copy never wins against an offer, and never hides what would
otherwise be the only answer. That unmakes an ambiguity the reach used to refuse
falsely, and costs nothing where the copy is all there is.

**A skill is found by its own `SKILL.md`; a recipe and a bundle are read out of
the one file the repository declares itself in, `.overpower.yaml` at its root**
(`docs/agents/domain.md` § Vocabulário). Only the skill walks, because only a
skill *has* a tree to be found in. The declaration does not walk at all: it is
read at the repository root or it is somebody else's, which is the anchor
`FEDERATED_FILE` carries the reasoning for. One file, one format, one reader —
the very reader the wheel's own `catalog.yaml` goes through (ADR 0021, which
replaced the two addresses and the two formats of ADR 0020).

**The recipe stopped reaching, and that is the visible change of ADR 0021.**
`--mcp <slug> --from <url>` used to walk for `.overpower/mcp/<slug>.toml` at any
depth; now the slug is a key of the declaration, and a declaration is anchored.
A repository still carrying the old layout and no `.overpower.yaml` is refused
naming the file to write (`LegacyRecipeLayoutError`), never read half-way.

**Obtention has two paths and one search** (ADR 0007,
https://github.com/ThiagoPanini/overpower/issues/25):

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

from overpower.discovery import SKILL_FILE, ArtifactType, Bundle, Catalog, artifact_at
from overpower.errors import BadInvocationError, OverpowerError, RefusedError
from overpower.recipes import MCP_KEY
from overpower.runtimes import RUNTIMES
from overpower.written import ItemNamespace, WrittenCatalog, read_written_catalog

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable, Mapping, Sequence

    from overpower.discovery import Artifact
    from overpower.recipes import Recipe
    from overpower.written import WrittenBundleItem

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

FEDERATED_FILE = ".overpower.yaml"
"""The one file a repository writes about everything it offers, at its root.

Bundles under `bundles:` and recipes under `mcp:`, read by the very reader the
wheel's own `catalog.yaml` goes through — one file, one format, one reader
(ADR 0021). It replaced two addresses in two formats, and the publisher is who
paid for those: the first real repository to federate carried three files, two
formats and one namespace, with **zero lines of the product** teaching either
address.

Anchored rather than reached, and the anchor is not a shortcut. A declaration
answers *what does this repository offer?* — the same question the showcase
answers about `skills/`, and a property of the repository the URL names. A
vendored dependency carrying its own `.overpower.yaml` speaks for its own
repository, so a reach that found one would let the URL's subpath change what
this repository is said to offer (ADR 0019). It is also why `--mcp` stopped
walking: the recipe became part of the declaration, so it is anchored with it."""

_LEGACY_MCP_DIR = (".overpower", "mcp")
"""Where a recipe lived before ADR 0021, and refusing is all this is still for.

Nothing is ever read from here. A repository laid out the old way and carrying
no `.overpower.yaml` is refused naming the file to write instead, because the
alternative is the silent half — a showcase that lists the skills, omits the
servers and exits 0, leaving the author believing they federate something the
product never saw. Checked at the repository root only, like the declaration it
stands in for: a vendored dependency's leftovers are not this repository's."""

OFFER_DIR = "skills"
"""The one folder a repository's **offer** lives in, as a direct child of its root.

The anchor of the showcase, and the one place the two searches part company.
The *reach* — `--skill <name>` — walks the search root at any depth, because
the caller already knows the name and the URL is theirs to narrow. The
*showcase* answers a question nobody has narrowed, so it cannot walk a whole
third-party repository and call whatever carries a `SKILL.md` an offer: a
vendored dependency's skills are not what that repository offers.

The anchor was chosen against measurement and the price is declared: **2 of the
75 `SKILL.md` measured fall outside it**, and stay installable by name. The
sentence is *"`list` shows the showcase; `--skill` reaches what you can name"*.

`commands/` and `agents/` are not enumerated — 0 of the 75 live in them — and
admitting them later is additive."""

_RUNTIME_DESTINATIONS: frozenset[tuple[str, ...]] = frozenset(
    tuple(runtime.project_dir.relative.split("/"))
    for runtime in RUNTIMES
    if runtime.project_dir is not None and runtime.project_dir.relative != OFFER_DIR
)
"""Every place inside a repository an install writes skills to, as path segments.

Derived from the table rather than listed, so a runtime added to `RUNTIMES`
arrives here without a second edit — a hand-kept copy of a 100-row table is a
copy that goes stale silently.

**`openclaw`'s row is excluded, and that exclusion is the rule and not an
exception.** Its `project_dir` is `skills` — the offer anchor itself — so a
deny-list that kept it would deny every offer in the product. Where a
destination and the anchor are the same path, the anchor wins: a repository's
own `skills/` is what it offers, whoever else also reads it.

Global destinations are absent for a different reason: they hang off the home
directory, and what `--from` walks is a repository."""


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


class NothingOfferedError(RefusedError):
    """The repository has no `skills/` and no `.overpower.yaml` to show.

    Exit **3**, on the same axis every other refusal on this path sits: the URL
    parsed, the repository was obtained, the walk ran, and the answer is no. The
    defect named is the **URL's**, which is the whole point of refusing here
    rather than opening a wizard on an empty catalog — that would put the
    question *"what should this install bring?"* to someone whose only honest
    answer is *"nothing, and not because of anything I typed"*.
    """

    def __init__(self, source: Source) -> None:
        """Name the repository, and both things that would have made it an offer."""
        self.source = source
        super().__init__(
            f"{source.shown} offers nothing to install: "
            f"no `{OFFER_DIR}/` and no `{FEDERATED_FILE}` at its root"
        )


class LegacyRecipeLayoutError(RefusedError):
    """Recipes at the address the format left behind, and no `.overpower.yaml` beside them.

    Exit **3**, and it names the fix the way every exit 3 of this product does:
    which files were found, that the format is gone, and the one file to write in
    their place. The alternative is the silent half — list the skills, omit the
    servers, exit 0 — which describes the repository as offering less than its
    author declared, with no line anywhere to point at.

    There is no compatibility window, and the reason is measured rather than
    taken on principle: on the day of ADR 0021 the whole installed base was
    **two untracked files** in a repository that did not yet have a commit, and a
    window would have cost two readers for one schema for as long as it lasted.
    """

    def __init__(self, source: Source, found: Sequence[Path], tree: Path) -> None:
        """Name the files that were found, and the one file to write instead."""
        self.source = source
        self.found = tuple(found)
        listed = ", ".join(path.relative_to(tree).as_posix() for path in self.found)
        super().__init__(
            f"{source.shown} declares its MCP servers at {listed}, which this version no "
            f"longer reads: a recipe is an entry of the `{MCP_KEY}:` key of "
            f"`{FEDERATED_FILE}`, at the repository root. Write that file instead"
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
    """No entry of that name under the `mcp:` key of the repository's declaration.

    Exit **3**, the same axis as `RemoteSkillNotFoundError`: the file is a
    stranger's and it is optional, so a name that is not in it — or a repository
    that declares none at all — is the product having looked and the answer being
    no, never the exit **2** a closed list answers a typo with.

    **It has no ambiguous twin, and that is what anchoring bought.** While a
    recipe was reached by walking, two copies of `.overpower/mcp/<slug>.toml`
    under one root were a real outcome and had to be refused by name. A key
    appears once in a mapping, so the question stopped existing (ADR 0021).
    """

    def __init__(self, name: str, source: Source) -> None:
        """Name what was looked for and where, in the terms of the URL."""
        self.name = name
        self.source = source
        super().__init__(f"no recipe named `{name}` in {source.shown}")


class RemoteBundleNotFoundError(RefusedError):
    """No entry of that name in the repository's `.overpower.yaml`.

    Exit **3**, on the axis its two siblings above sit on: the manifest is a
    file someone else owns and it is optional, so a name that is not in it — or
    a repository that declares none at all — is the product having looked and
    the answer being no, never the exit **2** a closed list answers a typo with.
    """

    def __init__(self, name: str, source: Source) -> None:
        """Name what was looked for and where, in the terms of the URL."""
        self.name = name
        self.source = source
        super().__init__(f"no bundle named `{name}` in {source.shown}")


class UnknownRemoteBundleItemError(RefusedError):
    """A bundle naming something the repository does not offer.

    Exit **3** and not the exit **1** the embedded twin answers with
    (`discovery.UnknownBundleItemError`), and the axis is *whose defect it is*
    (ADR 0009). Off the wheel a bundle naming an absent artifact is **our**
    tree contradicting **our** manifest — code 1, a defect the product points
    at itself. Here both files belong to a stranger, the line that was typed is
    well-formed, and the reader can do nothing but report it upstream — so the
    item travels in the message, which is what makes reporting it one paste.
    """

    def __init__(self, bundle: str, item: str, source: Source, among: str) -> None:
        """Name all four: the manifest, the name it points at, the repository, and what missed."""
        self.bundle = bundle
        self.item = item
        self.source = source
        super().__init__(
            f"the bundle `{bundle}` of {source.shown} names `{item}`, "
            f"which is not among the {among}"
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
    url: str, skills: Sequence[str] = (), mcps: Sequence[str] = (), bundles: Sequence[str] = ()
) -> Generator[Catalog]:
    """The remote `skills`, `mcps` and `bundles`, as a catalog, for the life of the block.

    A `Catalog` and not a new type, so everything downstream — planning, the
    screen, the writer — stays exactly as it is: `--from` changes *where the
    catalog comes from* and nothing else about what happens to it. It carries no
    framework, which is the same statement the invocation guard makes on the
    command line, said again in the data: an AI Framework is a folder of the
    overpower's own wheel and there is nothing remote for it to name.

    **Naming nothing is a question, not an empty selection.** With no selector
    at all, this answers *"what does this repository offer?"* — the showcase —
    instead of building a catalog of nothing. The three units read the tree by
    two different rules and it is worth saying which is which:

    | | walks from | matches |
    | --- | --- | --- |
    | reach, `--skill` | the **search root**, so the URL narrows it | any depth |
    | `--mcp`/`--bundle` | the **repository**, so the URL narrows nothing | the declaration |
    | showcase, no selector | the **repository**, so the URL narrows nothing | the anchors |

    The showcase ignoring the subpath is not an oversight of the search-root
    doctrine but its complement: an offer is a property of the repository, so
    pasting the root URL and pasting a subfolder's have to answer the same. A
    bundle and a recipe sit on that side of the table rather than with the one
    remaining selector because both are *declared* rather than found — there is
    one declaration per repository, and it is at the root or it is somebody
    else's (ADR 0021). Only a skill is still reached, because only a skill has a
    tree of its own to be reached in.

    The scratch is removed in the `finally`, so it goes whether the search
    answered, refused or the caller declined the confirmation inside the block.
    """
    source = parse(url)
    scratch = Path(tempfile.mkdtemp(prefix=SCRATCH_PREFIX))
    try:
        tree = obtain(source, scratch)
        if not skills and not mcps and not bundles:
            yield _offered_by(tree, source)
            return
        # Resolved **only** where it is read, and that is not a micro-optimisation.
        # `search_root` refuses a subpath the repository does not have, and a line
        # whose selectors are all anchored must never meet that refusal: the
        # declaration is read at the repository, so the URL's subpath narrows
        # nothing for it — and a rule that narrows nothing cannot be allowed to
        # fail anything either. The `tree` fallback is never read: without
        # `--skill`, the comprehension below is empty.
        root = search_root(tree, source) if skills else tree
        # Read **once**, and only when something anchored was asked for. Once,
        # because the file is one file and validating it per name would let the
        # same document be admitted and refused in one invocation; only when
        # asked, because a line whose sole selector is `--skill` never opens the
        # declaration at all — a skill is found by walking, so a repository whose
        # declaration is missing, malformed or laid out the old way still
        # answers `--skill <name>`.
        declared = _declared_by(tree, source) if mcps or bundles else _NOTHING_DECLARED
        yield Catalog(
            frameworks=(),
            pool=tuple(_skill_called(name, root, tree, source) for name in dict.fromkeys(skills)),
            bundles=_bundles_called(dict.fromkeys(bundles), declared, tree, source),
            mcps=tuple(_mcp_called(name, declared, source) for name in dict.fromkeys(mcps)),
        )
    finally:
        discard(scratch)


def _offered_by(tree: Path, source: Source) -> Catalog:
    """The showcase: what `skills/` holds and what `.overpower.yaml` declares.

    Both halves anchored at `tree` — the repository — and not at the search root,
    which is what makes the URL's subpath irrelevant here.

    An empty result is refused rather than returned. A `Catalog` with nothing in
    it renders as a screen with no rows and opens a wizard with no choices, and
    both of those describe the invocation as the problem when the problem is the
    URL (`NothingOfferedError`). The bundles are not part of that test and could
    not be: a bundle carries no content of its own, so a repository whose only
    file is a declaration of bundles offers nothing to install and its own
    `items` are the first thing that would refuse.
    """
    offers = _skills_offered(tree)
    declared = _declared_by(tree, source)
    catalog = Catalog(
        frameworks=(),
        pool=offers,
        bundles=_bundles_of(declared, offers, source),
        mcps=declared.mcps,
    )
    if not catalog.pool and not catalog.mcps:
        raise NothingOfferedError(source)
    return catalog


_NOTHING_DECLARED = WrittenCatalog(bundles=(), frameworks={}, mcps=())
"""What a repository with no `.overpower.yaml` declares, which is a real answer.

The file is **optional**, and a repository that has not written one is not
defective: it keeps its skills listed and installable, and only what the file
would have declared is absent. The author adopts when they want to.
"""


def _declared_by(tree: Path, source: Source) -> WrittenCatalog:
    """Everything `<tree>/.overpower.yaml` declares, through *the* reader.

    The one place a federated declaration is read, which is what makes the
    anchor a fact rather than a convention repeated in three functions: bundles,
    recipes and the showcase all arrive here, and none of them sees a path.

    Read through `read_written_catalog` — the reader the wheel's own written file
    goes through — so a declaration that reaches the screen is one the product
    would have written itself, and a malformed one is refused naming the same
    field on both sides. There is no second validator anywhere in the product.
    """
    manifest = tree / FEDERATED_FILE
    if manifest.is_file():
        return read_written_catalog(manifest)
    _refuse_the_old_layout(tree, source)
    return _NOTHING_DECLARED


def _refuse_the_old_layout(tree: Path, source: Source) -> None:
    """Exit 3 when the recipes are at the address the format left behind.

    Checked only where the declaration would have been — the repository root —
    so a vendored dependency's leftovers refuse nothing. Absence of the old
    layout is the ordinary case and answers nothing at all.
    """
    legacy = tree.joinpath(*_LEGACY_MCP_DIR)
    if not legacy.is_dir():
        return
    found = sorted(path for path in legacy.glob("*.toml") if path.is_file())
    if found:
        raise LegacyRecipeLayoutError(source, found, tree)


def _bundles_of(
    declared: WrittenCatalog, offers: Sequence[Artifact], source: Source
) -> tuple[Bundle, ...]:
    """Every bundle the repository declares, resolved over the skills it offers.

    `items` resolve against `offers` — the **enumerated** skills of this
    repository — and against nothing else. Not the embedded catalog, because
    `--from` is exclusive; not a third repository, because `items` would then be
    a carrier of an address and ADR 0006 forbids one by name; and not a
    free-depth walk either, because a vendored dependency's skill is reachable
    by `--skill <name>` without being part of what this repository composes.

    **The loop below is `discovery.load_catalog`'s, on purpose and declared.** The
    two assemble a `Bundle` the same way, and the temptation is to share one
    helper — which would have to take the resolver *and* its error as parameters,
    since both differ and both differ for reasons that are the point: what a name
    resolves against (the walked pool there, the anchored offer here) and what a
    miss costs (exit 1 there, exit 3 here, ADR 0009). A helper parameterised on
    everything that differs is longer than the two loops it replaces and hides
    the one line worth reading. What must not diverge is the *reader*, and that
    one really is shared — `_declared_by` is the only door.
    """
    by_skill = {artifact.name: artifact for artifact in offers}
    by_mcp = {recipe.name: recipe for recipe in declared.mcps}
    return tuple(
        Bundle(
            name=written.name,
            description=written.description,
            artifacts=tuple(
                _offered_item(written.name, item, by_skill, by_mcp, source)
                for item in written.items
            ),
        )
        for written in declared.bundles
    )


def _bundles_called(
    names: Iterable[str], declared: WrittenCatalog, tree: Path, source: Source
) -> tuple[Bundle, ...]:
    """The bundles named, in the order they were typed, out of the one declaration.

    The whole declaration is read and resolved even when one name was asked for,
    and that is the embedded behaviour rather than a shortcut: `load_catalog`
    resolves every bundle it finds, so a declaration with a broken entry is a
    broken declaration on both sides. Resolving lazily here would make the
    federated path forgive what the wheel refuses, which is the divergence this
    ticket exists to prevent.
    """
    offered = {
        bundle.name: bundle for bundle in _bundles_of(declared, _skills_offered(tree), source)
    }
    chosen: list[Bundle] = []
    for name in names:
        if name not in offered:
            raise RemoteBundleNotFoundError(name, source)
        chosen.append(offered[name])
    return tuple(chosen)


def _offered_item(
    bundle: str,
    item: WrittenBundleItem,
    offers: Mapping[str, Artifact],
    mcps: Mapping[str, Recipe],
    source: Source,
) -> Artifact | Recipe:
    """The offered skill or declared recipe a bundle points at, in its own namespace (ADR 0022)."""
    if item.namespace is ItemNamespace.MCP:
        recipe = mcps.get(item.name)
        if recipe is None:
            raise UnknownRemoteBundleItemError(
                bundle, item.name, source, "mcp servers that repository declares"
            )
        return recipe
    artifact = offers.get(item.name)
    if artifact is None:
        raise UnknownRemoteBundleItemError(
            bundle, item.name, source, "skills that repository offers"
        )
    return artifact


def _skills_offered(tree: Path) -> tuple[Artifact, ...]:
    """Every skill folder under `<tree>/skills/`, at any depth below it.

    `skills/` has to be a direct child of the repository root; below it the
    depth is free, so `skills/<category>/<name>/` is offered exactly the way
    `skills/<name>/` is — categories are how a large repository files its own
    offer, and refusing to see them would make the anchor a rule about
    two levels rather than about one.

    **No deny-list runs here, and the anchor is why** (ADR 0019). Measured, the
    anchor beats `rglob` plus a deny-list on this half — 73 of 73 against 74 with
    a false positive — and no runtime writes skills to a path under `skills/`, so
    an installed copy is outside the walk before any predicate could see it. The
    deny-list belongs to the reach, where the anchor has nothing to say.

    Described through `artifact_at`, the same function the embedded walk uses,
    which is what makes the two paths describe an artifact identically.
    """
    offers = tree / OFFER_DIR
    if not offers.is_dir():
        return ()
    found = {
        match.parent
        for match in offers.rglob(SKILL_FILE)
        # `match.parent != offers` because a `SKILL.md` lying loose in `skills/`
        # names no folder of its own, and rule 8 (ADR 0006) has nothing to read
        # a name off there.
        if match.is_file() and match.parent != offers
    }
    return tuple(artifact_at(folder, ArtifactType.SKILL) for folder in sorted(found))


def _is_a_runtime_destination(folder: Path, tree: Path) -> bool:
    """Whether `folder` is a skill an install wrote, rather than one the repository offers.

    An install writes a project-scope skill at exactly
    `<repository>/<project_dir>/<name>/`, so the test is an **exact** path from
    the repository root and not a suffix or a substring of one: `skills/` is a
    destination for `openclaw` and the offer anchor for everyone, and only the
    distance from the root tells `skills/alpha` apart from `.claude/skills/alpha`.

    The measured defect this answers: a repository equipped with the overpower
    carries its own skill twice, and before this the reach refused it as
    ambiguous — a refusal that was **false**, since there is one skill there and
    the second path is where an install put it.
    """
    return folder.parent.relative_to(tree).parts in _RUNTIME_DESTINATIONS


def _offers_among(matches: Iterable[Path], tree: Path) -> list[Path]:
    """`matches` with installed copies dropped — unless dropping them leaves nothing.

    **A tie-break, not a filter**, and the difference is the whole correctness of
    it. What the deny-list exists to stop is a copy *competing* with the offer it
    was copied from; what it must never do is answer *not found* about the only
    thing there. Both cases fall out of one rule:

    | under the root | filtered | answered |
    | --- | --- | --- |
    | `skills/alpha` + `.claude/skills/alpha` | `skills/alpha` | one, no ambiguity |
    | `.claude/skills/alpha` alone | *empty* | the copy, because it is all there is |
    | `skills/alpha` + `vendor/skills/alpha` | both | still ambiguous, as before |

    The second row is the one a filter gets wrong, and it is not a corner: a URL
    pointed at `.claude` names that copy on purpose, and two destinations in the
    table — `agent/skills` (`eve`) and `data/skills` (`astrbot`) — are ordinary
    folder names a repository could be genuinely offering out of. Neither cost
    was measured in ADR 0019, which weighed the deny-list on the enumeration
    only; the tie-break is what makes the reach's half cost nothing at all.
    """
    found = sorted(matches)
    offers = [match for match in found if not _is_a_runtime_destination(match, tree)]
    return offers or found


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


def _skill_called(name: str, root: Path, tree: Path, source: Source) -> Artifact:
    """The one skill folder called `name` under `root`, described by its own `SKILL.md`.

    The folder name is the artifact's name, exactly as it is for the embedded
    tree (rule 8, ADR 0006) — and the description comes out of `SKILL.md` through
    the same function the embedded walk uses, which is what makes the two paths
    describe an artifact identically.

    `root` is where the walk starts and `tree` is the repository the deny-list is
    measured from, and they differ exactly when the URL named a subpath. Both are
    needed: the walk is the caller's to narrow, while whether a hit is an
    installed copy is a fact about its distance from the repository root.
    """
    matches = _offers_among(
        {
            found.parent
            for found in root.rglob(SKILL_FILE)
            if found.is_file() and found.parent.name == name
        },
        tree,
    )
    if not matches:
        raise RemoteSkillNotFoundError(name, source)
    if len(matches) > 1:
        raise AmbiguousRemoteSkillError(
            name, source, [match.relative_to(root) for match in matches]
        )
    return artifact_at(matches[0], ArtifactType.SKILL)


def _mcp_called(name: str, declared: WrittenCatalog, source: Source) -> Recipe:
    """The recipe named `name` under the `mcp:` key of the repository's declaration.

    `declared` and not a search root: a declaration is anchored, so `--mcp` reads
    the same entry whether the URL named the repository or a folder inside it
    (ADR 0021). The subpath keeps narrowing `--skill`, which is the one selector
    that still walks.

    What arrives already went through `_declared_by`, so the recipe passed the
    same contract the embedded catalog's did — a recipe that gets past this
    function is a recipe that renders, whether it came from the wheel or from
    someone else's repository.
    """
    for recipe in declared.mcps:
        if recipe.name == name:
            return recipe
    raise RemoteRecipeNotFoundError(name, source)
