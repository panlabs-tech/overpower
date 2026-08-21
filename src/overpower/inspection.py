"""What is on the disk of the target, and what is wrong with it — the `doctor`.

Sibling of `overpower.discovery` with the roots swapped. Discovery walks the
**catalog** tree and answers what *may* be installed; this module walks the
**runtime paths** of the repository and of the machine and answers what *is*,
and whether it still works.

`doctor` answers two questions in one output — *how is the terminal*, and *how is
what was installed* — and the second half is why it exists at all: six named
holes that nothing else in the product closes.

**`core.symlinks=false` breaking links.** The exact point where axiom 2 does not
answer on its own. Measured: git **auto-detects** the capability and writes it
into the clone — the default on Windows — a committed link checks out as an
ordinary text file carrying its own target, and **`git status` stays clean**. The
git lies, and the `doctor` is what contradicts it. So the check is two conditions
and not one: the clone's own config says links are off, *and* a file inside
installed equipment reads as a link that became text. Either alone is a guess.

**A link that does not resolve.** Global scope climbs the canonical + link ladder
(https://github.com/ThiagoPanini/overpower/issues/40), and a link whose target
went away is invisible equipment: the directory listing shows the name, and
nothing is there.

**Two copies of one artifact that disagree.** Project scope lands a **real copy**
in every selected path (https://github.com/ThiagoPanini/overpower/issues/9), and
that decision accepted losing the single point of truth **naming the `doctor` as
its mitigation**. This check is the payment of that debt.

**A server Claude Code has not approved.** ADR 0014 decided the overpower writes
an MCP server and never turns it on, and made the install-time warning about it a
requirement. `doctor` is the same fact asked again after the session that wrote
it is gone: it reads the registry Claude Code itself writes to
`.claude/settings.local.json` once a human passes the trust dialog, and answers
**exit 3** where the write-time warning could only answer exit 0.

**The runner a `source:` recipe needs, gone from this machine.** ADR 0023:
nothing is cloned any more, so the one precondition an installed server has
left to lose is its own launcher — `uvx` or `npx`, still on `PATH`. Read back
off the rendered command exactly the way the approval check reads the
registry: `doctor` has no `Plan` and opens no catalog, so it recognises the
shape its own renderer produces — a runner as `command`, a `git+` address
among the `args` — rather than asking a recipe it cannot see. Offline, on
purpose: ADR 0023 measured the alternative and refused it — verifying the
`ref` still resolves would turn an offline command into a network client to
catch what the runner itself already reports, loud, on its first real run.

One neighbour of that same graft axis is **informative, and never fails the
gate**: a slot the recipe reads out of the process environment that this one
does not carry. Read back off the document exactly as the approval check is —
`doctor` has no `Plan` to ask — and exit **0** for the reason
`overpower.cli._warn_about_unset_slots` already is: the file is correct, and
what is missing is the user's to fix on their own clock. It travels on
`Diagnosis.notices` and never on `.findings`.

**There is no manifest to read.** Axiom 2 forbids state in the target, so the
question *"where could equipment be"* has exactly one answer: the closed runtime
table, whole, in both scopes. That is also why `doctor` takes no `--global` — the
ticket asks for one output, and a flag that switched between the halves would
make it two.

Two consequences of that are **accepted costs and not oversights**, and they are
written here so nobody has to re-derive them:

- **anything sitting in a runtime path is equipment.** Not every project path in
  the table is dotted — `skills`, `data/skills` and `agent/skills` are real rows
  — so a repository whose *own* layout occupies one gets its directories read as
  landed writes, and two same-named directories in two runtime paths are
  reported as divergent. That reading is correct on the table's own terms: a
  runtime really does read there. Narrowing it would mean guessing which
  directories the overpower wrote, and `overpower.writing` refuses a provenance
  heuristic for the same reason in the other direction;
- **`doctor` reads the repository where `install` writes the working directory.**
  Deliberate, and the axis is what each one does: `install` equips the place you
  are standing in, while a diagnosis run from `packages/api` that answered
  *"nothing installed"* about a fully equipped repository would be the silent
  false negative this command exists to prevent. `git status` reports the whole
  repository from anywhere for the same reason.

**The answer is about writes, not about artifacts.** Every record here carries a
`Destination` — the same two-form datum a `Plan` spells, folder or document plus
a key — and an artifact maps to a *tuple* of places rather than to one. That is
the graft lock of `domain.md`: an artifact may cost more than one write, and the
second may land outside the repository. v0.1.0 produces only the folder form; a
shape that assumed *"one artifact, one write, all of it inside the target"* is
what would turn v0.2 into a rewrite instead of a sum.

Nothing here decides an exit code. `Diagnosis.healthy` is the fact; **3** when it
is false is `overpower.cli`, where every other code of the table also lives.
"""

from __future__ import annotations

import hashlib
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, assert_never, cast

from json5 import loads as _loads

from overpower.planning import DirectoryTree, DocumentKey
from overpower.rendering import expands_from_environment
from overpower.runtimes import (
    Dialect,
    Scope,
    mcp_places_of,
    mcp_runtimes_in,
    places_of,
    runtimes_in,
)
from overpower.writing import points_elsewhere

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Mapping

    from overpower.planning import Destination
    from overpower.runtimes import Environment, McpPlace

GIT_DIR = ".git"
"""What `overpower.scope` walked up to find, and what carries the config below."""

GIT_CONFIG = "config"

GIT_DIR_POINTER = "gitdir:"
"""How a worktree and a submodule spell `.git` as a file instead of a directory."""

GIT_COMMON_DIR = "commondir"
"""How a **linked worktree** says where the shared configuration actually lives.

Measured: `git worktree add` writes a `.git` *file* pointing at
`<main>/.git/worktrees/<name>`, and that directory carries `HEAD`, `index`,
`refs` and `commondir` — and **no `config` at all**. A reader that stopped at
the pointer would look for a file that does not exist and answer *"links are
fine"* in every worktree, which is the layout this repository's own workflow
mandates for every branch.
"""

MACHINE_CONFIG = ".gitconfig"
"""`~/.gitconfig`, which git reads last of the two user-level files and so wins."""

XDG_CONFIG = "XDG_CONFIG_HOME"
"""Anchor of `<xdg>/git/config`, the other user-level file, read *before* `~/.gitconfig`."""

GIT_CONFIG_GLOBAL = "GIT_CONFIG_GLOBAL"
"""Git's own override of both user-level files. Honoured so a hermetic caller stays hermetic."""

LINK_TARGET_LIMIT = 255
"""Longest text a file may carry and still be read as a link that became one.

A link target is a path, and a path component is bounded far below this on every
filesystem the matrix runs on. The bound is here to keep the check off the body
of a real document: a `SKILL.md` is never a single unterminated line of 255
characters that also happens to name one of its own siblings.
"""

_FALSE = frozenset({"false", "no", "off", "0"})
"""How git spells false. Anything else — including a bare key — is true."""


@dataclass(frozen=True)
class Terminal:
    """The four facts that answer *"my screen came out strange"* with no round trip.

    Values, not readings: the CLI owns the console and the environment, and hands
    both over already resolved, so the screen and the tests see the same datum.
    """

    tty: bool
    colour: str
    width: int
    no_color: str | None
    """The raw `NO_COLOR` value, `None` when unset — the variable is *presence*
    based, so an empty string is a different answer from absent and both are
    shown as they are rather than folded into a boolean."""


@dataclass(frozen=True)
class Landed:
    """One write found on disk: what it is called, where it is, and what it holds.

    `destination` and not a path, because that is the datum a `Plan` writes and
    the one the graft class already occupies. `fingerprint` is `None` when the
    content could not be read at all — a link that resolves nowhere is the case
    that produces it — which is what keeps a dangling link out of the divergence
    comparison it would otherwise poison.
    """

    name: str
    scope: Scope
    destination: Destination
    fingerprint: str | None


@dataclass(frozen=True)
class Grafted:
    """One MCP server read back off a document: what it is called, and where it sits.

    The graft-class twin of `Landed`, and it carries no fingerprint on purpose.
    A copy can be compared against the catalog tree it came from; a graft is a
    **rendering** of a recipe into the dialect of one runtime, so the bytes on
    disk are not the bytes of anything this product stores — the four checks
    below ask their questions of the config itself instead.
    """

    name: str
    scope: Scope
    destination: DocumentKey


@dataclass(frozen=True)
class DanglingLink:
    """A landed write that points at something that is not there."""

    destination: Destination
    points_at: str | None


@dataclass(frozen=True)
class LinkTurnedText:
    """A file inside landed equipment that is a link's target, spelled as content.

    `destination` is the write it was found inside, `inside` is the file itself:
    the finding is about the write, and the path is what makes it fixable.
    """

    destination: Destination
    inside: Path
    points_at: str


@dataclass(frozen=True)
class Divergence:
    """Copies of one artifact, in one scope, whose content does not agree."""

    name: str
    scope: Scope
    destinations: tuple[Destination, ...]


@dataclass(frozen=True)
class PendingApproval:
    """A server written into a graft Claude Code gates, that it has not approved."""

    destination: DocumentKey
    name: str


@dataclass(frozen=True)
class MissingRunner:
    """A graft rendered from a `source:` recipe whose runner is no longer on `PATH`."""

    destination: DocumentKey
    name: str
    runner: str


Finding = DanglingLink | LinkTurnedText | Divergence | PendingApproval | MissingRunner
"""Everything the `doctor` can say is wrong. Empty means exit 0."""


@dataclass(frozen=True)
class UnsetSlot:
    """A slot a graft reads out of the environment, that this environment lacks."""

    destination: DocumentKey
    name: str
    variable: str


Notice = UnsetSlot
"""Everything the `doctor` can say without failing the gate over it. Never emptied
into `.findings` — see the module docstring for why the two are kept apart."""


@dataclass(frozen=True)
class Diagnosis:
    """One output, two questions: the terminal, and the integrity of what landed."""

    terminal: Terminal
    root: Path | None
    """The repository the project half was read from, `None` outside one.

    Outside a repository the `doctor` still answers — it reports the terminal and
    the machine. Refusing to diagnose because there is no git would be refusing
    exactly where a diagnosis is cheapest to want.
    """

    home: Path
    landed: tuple[Landed, ...]
    grafted: tuple[Grafted, ...]
    """The graft class of the same question `landed` answers for the copy class.

    Two fields and not one list of a union type, because the two are found by
    different walks over different roots — a tree in a runtime path against a
    key inside a document a user also edits — and the checks below take one or
    the other, never both.
    """

    findings: tuple[Finding, ...]
    notices: tuple[Notice, ...]
    """What is worth saying and never worth exit 3 over. See the module docstring."""

    @property
    def healthy(self) -> bool:
        """Whether the run found nothing. This is what the exit code follows."""
        return not self.findings

    @property
    def artifacts(self) -> int:
        """How many distinct artifacts are installed, counted once per scope.

        Distinct from `self.places` on purpose: one artifact in four runtime
        paths is **one** artifact and **four** places, and the screen says both.

        **Both landing classes count**, because neither carries provenance and
        the copy class never pretended to: `_landed_in` counts every tree
        sitting in a runtime path, including one a user made by hand. Leaving
        grafts out made a repository whose only installation is an MCP server
        read `0 artifacts · 0 places` under a block headed *"what is
        installed"* — the audit of the graft spec named that number and could
        not point at a story that asked for it either way.

        The two classes are counted apart and **added**, never merged into one
        set: the pool namespaces by type, so a skill and a server may share a
        name, and a union over `(scope, name)` would answer one where the disk
        holds two.
        """
        copies = {(item.scope, item.name) for item in self.landed}
        grafts = {(item.scope, item.name) for item in self.grafted}
        return len(copies) + len(grafts)

    @property
    def places(self) -> int:
        """How many writes are on disk — a tree in a runtime path, or a key in a document.

        The second number of the count line. It is a property rather than
        `len(self.landed)` at the call site for the reason the docstring above
        gives: once the graft class counts, *place* is a sum over two fields and
        a screen reaching for one of them would print half of it.
        """
        return len(self.landed) + len(self.grafted)


def diagnose(terminal: Terminal, root: Path | None, environment: Environment) -> Diagnosis:
    """Read both scopes and answer what is there and what is wrong with it.

    Project first, then global, because that is the order of the two roots a
    reader thinks in — and inside each, the order of the runtime table, so the
    output of two runs against an unchanged disk is byte-identical.
    """
    landed = (
        *(() if root is None else _landed_in(Scope.PROJECT, root, environment)),
        # `environment.home` is passed as the root and never read: a global path
        # hangs off an anchor of the table, which `Environment` resolves. The
        # parameter stays required because a function whose shape changes with
        # its own input is a harder one to call correctly.
        *_landed_in(Scope.GLOBAL, environment.home, environment),
    )
    places = _mcp_documents(root, environment)
    grafted = tuple(
        Grafted(name=name, scope=scope, destination=_document_key(place, name))
        for scope, place, name, _ in _servers_of(places)
    )
    findings: tuple[Finding, ...] = (
        *_dangling(landed),
        *(() if root is None else _links_turned_text(root, landed, environment)),
        *_divergences(landed),
        *(() if root is None else _pending_approvals(places, root)),
        *_missing_runners(places, environment),
    )
    notices: tuple[Notice, ...] = (*_unset_slots(places, environment),)
    return Diagnosis(
        terminal=terminal,
        root=root,
        home=environment.home,
        landed=landed,
        grafted=grafted,
        findings=findings,
        notices=notices,
    )


def _landed_in(scope: Scope, root: Path, environment: Environment) -> tuple[Landed, ...]:
    """Every write sitting in a runtime path of `scope`, in table order."""
    return tuple(
        Landed(
            name=entry.name,
            scope=scope,
            destination=DirectoryTree(entry),
            fingerprint=_fingerprint(entry),
        )
        for place in places_of(runtimes_in(scope), scope, root, environment)
        for entry in _entries(place)
    )


def _entries(place: Path) -> list[Path]:
    """What sits directly under a runtime path — including what does not resolve.

    `is_dir()` alone would miss the finding this whole module owes the global
    ladder: it follows the link, so a link whose target went away answers
    `False` and the invisible equipment stays invisible. `points_elsewhere` is
    the same predicate the removal trap uses, and it is never re-implemented.

    A loose *file* is not a write, which is the blind spot `overpower.discovery`
    closes on the other tree, for the same reason.
    """
    if not place.is_dir():
        return []
    try:
        children = sorted(place.iterdir(), key=lambda child: child.name)
    except OSError:  # pragma: no cover — a directory that lists nowhere on the matrix
        return []
    return [child for child in children if child.is_dir() or points_elsewhere(child)]


def _fingerprint(place: Path) -> str | None:
    """A digest of everything under `place`: relative names and bytes, in order.

    Names are folded in alongside the bytes, so a file *renamed* between two
    copies diverges even when the bytes of the tree are the same set. `None`
    means the content could not be read, which is the honest answer for a link
    that resolves nowhere — and the one thing the divergence check has to be
    able to tell apart from *"read it, and it differs"*.
    """
    if not place.is_dir():
        return None
    digest = hashlib.sha256()
    try:
        for file in _files_under(place):
            digest.update(file.relative_to(place).as_posix().encode("utf-8"))
            digest.update(b"\x00")
            digest.update(file.read_bytes())
            digest.update(b"\x00")
    except OSError:  # pragma: no cover — a file that vanishes mid-walk
        return None
    return digest.hexdigest()


def _files_under(place: Path) -> list[Path]:
    """Every file below `place`, in one order, on the nine cells.

    Sorted because `rglob` answers in the filesystem's order, and both callers
    need one of ours: a digest folds the order into its own value, and a finding
    that changed position between two runs would read as a different finding.
    """
    return sorted(path for path in place.rglob("*") if path.is_file())


def _dangling(landed: Iterable[Landed]) -> Iterator[DanglingLink]:
    """Every landed write that points elsewhere and whose elsewhere is not there."""
    for item in landed:
        path = item.destination.path
        if points_elsewhere(path) and not path.exists():
            yield DanglingLink(destination=item.destination, points_at=_target_of(path))


def _target_of(path: Path) -> str | None:
    """Where a link points, as text, or `None` when the link cannot be read.

    `readlink` answers for a junction too, so the message names a target on
    Windows as well — and when it does not, the finding is still the finding:
    the path is what the reader needs, the target is what saves them a command.
    """
    try:
        return path.readlink().as_posix()
    except OSError:  # pragma: no cover — a link that unlinks between two calls
        return None


def _links_turned_text(
    root: Path, landed: Iterable[Landed], environment: Environment
) -> Iterator[LinkTurnedText]:
    """Files that are a link's target spelled as content, where links are turned off.

    Gated on the git configuration, and the gate is what makes the check precise
    instead of a guess: with links enabled, a one-line file naming a sibling is a
    one-line file naming a sibling. With `core.symlinks=false` in force, it is
    the measured failure — and `git status` will not say so.
    """
    if not _symlinks_disabled(root, environment):
        return
    for item in landed:
        if item.scope is not Scope.PROJECT:
            continue
        for inside, target in _texts_that_read_as_links(item.destination.path):
            yield LinkTurnedText(destination=item.destination, inside=inside, points_at=target)


def _texts_that_read_as_links(place: Path) -> Iterator[tuple[Path, str]]:
    """Every file under `place` whose whole content names an existing sibling."""
    if not place.is_dir():
        return
    for file in _files_under(place):
        target = _link_target_text(file)
        if target is not None:
            yield file, target


def _link_target_text(file: Path) -> str | None:
    """The link target this file carries as its whole content, or `None`.

    Four conditions, and the last one is what carries the precision. Measured
    against a real clone: git writes the target with **no trailing newline**, so
    a single unterminated line is the shape — and requiring that the target
    **resolve against the file's own directory** is what separates it from every
    ordinary short file, which names nothing that exists next to it.
    """
    try:
        size = file.stat().st_size
        if not 0 < size <= LINK_TARGET_LIMIT:
            return None
        text = file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    if text != text.strip() or any(char in text for char in "\n\r\x00"):
        return None
    if not (file.parent / text).exists():
        return None
    return text


def _symlinks_disabled(root: Path, environment: Environment) -> bool:
    """Whether `core.symlinks` is off for this checkout — read, never asked of git.

    Plain file reads and not `git config --get`, for the reason axiom 1 draws the
    transport-versus-installer line at: a question asked of a third-party binary
    is a dependency on it being installed, and the answer is one line of an INI
    file.

    **Two files, in git's own precedence order**, because the value can live in
    either and a reader of one of them misses the other. Git auto-detects the
    capability and writes it into the clone, which is the mechanism the ticket
    names — but measured on a machine where links *do* work, a
    `core.symlinks=false` set in the user's own config produces the **identical**
    broken checkout and the identical clean `git status`, with git recording
    nothing about links in the new repository. A reader that looked only at the
    clone would answer *"links are fine"* to a checkout that is not.

    The system file (`/etc/gitconfig`) is deliberately not read: it is
    administrator territory, the two files above are the two that were measured,
    and a third read would be a guess dressed as thoroughness.
    """
    disabled = False
    for config in _git_configs(root, environment):
        declared = _declared_symlinks(config)
        if declared is not None:
            disabled = declared
    return disabled


def _git_configs(root: Path, environment: Environment) -> Iterator[Path]:
    """The config files that govern `root`, **lowest precedence first**.

    The order is git's: the user-level files, then the repository's own, so a
    clone that re-enables links overrides a machine that turned them off.
    """
    yield from _machine_configs(environment)
    repository = _repository_config(root)
    if repository is not None:
        yield repository


def _machine_configs(environment: Environment) -> Iterator[Path]:
    """`$GIT_CONFIG_GLOBAL`, or the two user-level files git reads in its own order.

    `GIT_CONFIG_GLOBAL` replaces both when set, which is exactly what git does
    with it — and honouring it is what lets a caller that wants to be hermetic
    (this suite) actually be hermetic instead of reading whoever ran it.
    """
    override = environment.variables.get(GIT_CONFIG_GLOBAL)
    if override:
        yield Path(override)
        return
    xdg = environment.variables.get(XDG_CONFIG)
    base = Path(xdg) if xdg and Path(xdg).is_absolute() else environment.home / ".config"
    # `<xdg>/git/config` first and `~/.gitconfig` second, because that is the
    # order git reads them in and therefore which of the two wins.
    yield base / "git" / GIT_CONFIG
    yield environment.home / MACHINE_CONFIG


def _repository_config(root: Path) -> Path | None:
    """The config of the repository at `root`, through both indirections git uses.

    `.git` is a directory in an ordinary clone and a **file** in a worktree or a
    submodule — the same two shapes `overpower.scope` accepts when it decides
    whether there is a repository at all. The two files do not point at the same
    kind of place: a submodule's gitdir carries its own `config`, while a linked
    worktree's carries `commondir` and no config, and following that is what
    keeps the finding alive in the layout this repository develops in.
    """
    git = root / GIT_DIR
    directory = git if git.is_dir() else _pointed_at(root, git)
    if directory is None:
        return None
    return _shared_git_dir(directory) / GIT_CONFIG


def _pointed_at(root: Path, git: Path) -> Path | None:
    """The directory a `.git` *file* names, or `None` when it is not one."""
    if not git.is_file():
        return None
    try:
        pointer = git.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):  # pragma: no cover — a `.git` file that does not read
        return None
    if not pointer.startswith(GIT_DIR_POINTER):
        return None
    named = Path(pointer[len(GIT_DIR_POINTER) :].strip())
    return named if named.is_absolute() else root / named


def _shared_git_dir(directory: Path) -> Path:
    """`commondir` followed when there is one — a linked worktree — else itself."""
    common = directory / GIT_COMMON_DIR
    try:
        named = Path(common.read_text(encoding="utf-8").strip()) if common.is_file() else None
    except (OSError, UnicodeDecodeError):  # pragma: no cover — a `commondir` that does not read
        return directory
    if named is None:
        return directory
    return named if named.is_absolute() else directory / named


def _declared_symlinks(config: Path) -> bool | None:
    """Whether `config` turns `core.symlinks` off, on, or does not mention it.

    Three answers and not two: *absent* has to be told from *present and true*,
    or a repository that re-enables links could not override a machine that
    turned them off.
    """
    try:
        text = config.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    return _core_symlinks_false(text)


def _core_symlinks_false(text: str) -> bool | None:
    """`core.symlinks` out of a git config, hand-parsed, last occurrence winning.

    Hand-parsed for the reason `overpower.discovery` hand-parses one frontmatter
    key: `configparser` is not a git-config parser — a bare key with no `=` is
    valid here and a parse error there — and pulling one key out of one section
    does not justify getting the difference wrong.
    """
    section = ""
    disabled: bool | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("["):
            section = _section_of(line)
            continue
        key, separator, value = line.partition("=")
        if section == "core" and separator and key.strip().lower() == "symlinks":
            disabled = _declared_false(value)
    return disabled


def _section_of(line: str) -> str:
    """`[core]` and `[remote "origin"]` both answer their first word, lowercased."""
    head, _, _ = line[1:].partition("]")
    words = head.split()
    return words[0].strip('"').lower() if words else ""


def _declared_false(value: str) -> bool:
    """Whether a git config value spells false, comments and quotes taken off."""
    for comment in ("#", ";"):
        value = value.split(comment, maxsplit=1)[0]
    return value.strip().strip('"').lower() in _FALSE


def _divergences(landed: Iterable[Landed]) -> Iterator[Divergence]:
    """Artifacts whose copies inside one scope do not agree.

    Grouped **per scope**, never across: a repository and a machine hold
    independent installs, and calling those two divergent would be noise on
    every machine where one is older than the other. Inside one scope they are
    copies of one write that was announced once, and disagreeing is the defect.
    """
    grouped: dict[tuple[Scope, str], list[Landed]] = {}
    for item in landed:
        grouped.setdefault((item.scope, item.name), []).append(item)
    for (scope, name), copies in grouped.items():
        readable = [copy for copy in copies if copy.fingerprint is not None]
        if len({copy.fingerprint for copy in readable}) > 1:
            yield Divergence(
                name=name, scope=scope, destinations=tuple(copy.destination for copy in readable)
            )


# --------------------------------------------------------------------------- #
# the graft class: MCP servers, read back off the document — no `Plan` here
# --------------------------------------------------------------------------- #


def _mcp_documents(
    root: Path | None, environment: Environment
) -> tuple[tuple[Scope, McpPlace], ...]:
    """Every place an MCP graft can be, in both scopes — candidates, not writes.

    Unlike `_landed_in`, every row of `mcp_runtimes_in` is walked whether or not
    anything landed there: the checks below need the whole closed table to tell
    *"never installed"* apart from *"installed, and now broken"*, and only a
    document actually on disk answers either question — `_parsed_servers` is
    where that filter happens.
    """
    project = (
        ()
        if root is None
        else (
            (Scope.PROJECT, place)
            for place in mcp_places_of(
                mcp_runtimes_in(Scope.PROJECT), Scope.PROJECT, root, environment
            )
        )
    )
    global_ = (
        (Scope.GLOBAL, place)
        for place in mcp_places_of(
            mcp_runtimes_in(Scope.GLOBAL), Scope.GLOBAL, environment.home, environment
        )
    )
    return (*project, *global_)


def _parsed_object(path: Path) -> dict[str, object] | None:
    """`path` as a JSON object, tolerantly — or `None` when it is not there or not one.

    The same loader `overpower.grafting` and the test doctrine already read a
    graft document with, for the reason `tests/support/project.parsed` gives:
    `.mcp.json` is strict JSON and `.vscode/mcp.json` is JSONC, and a reader
    built for only one of them fails on whichever it was not built for.
    """
    if not path.is_file():
        return None
    try:
        parsed = cast("object", _loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    return cast("dict[str, object]", parsed) if isinstance(parsed, dict) else None


def _parsed_servers(place: McpPlace) -> Mapping[str, object] | None:
    """The server table `place` holds on disk, or `None` when there is none to read.

    `None` covers three cases none of the four checks below tell apart: the
    document was never written, it no longer parses, or its root key is not an
    object. Every one means *nothing here to check against* — a document that
    is broken is `overpower.grafting`'s refusal to raise, not this module's to
    invent a second time.
    """
    document = _parsed_object(place.path)
    if document is None:
        return None
    servers = document.get(place.document.root_key)
    return cast("dict[str, object]", servers) if isinstance(servers, dict) else None


def _strings_in(value: object) -> Iterator[str]:
    """Every string leaf under `value`, depth-first — where a rendered path can hide.

    A server's config is not flat: the clone this product renders sits inside
    `args`, and the slot it renders sits inside `env` or `headers` — a check
    that only read top-level values would miss both.
    """
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in cast("list[object]", value):
            yield from _strings_in(item)
    elif isinstance(value, dict):
        for item in cast("dict[str, object]", value).values():
            yield from _strings_in(item)


def _servers_of(
    places: Iterable[tuple[Scope, McpPlace]],
) -> Iterator[tuple[Scope, McpPlace, str, object]]:
    """Every server the four checks below can each ask their own question about.

    The one walk all of them share: a place with nothing to read contributes
    nothing, and every other place hands over each of its servers by name and
    config. Pulled out once so a fourth check does not have to write the walk a
    fourth time.
    """
    for scope, place in places:
        servers = _parsed_servers(place)
        if servers is None:
            continue
        for name, config in servers.items():
            yield scope, place, name, config


def _document_key(place: McpPlace, name: str) -> DocumentKey:
    """Where one server's graft sits: the document, and the key inside it."""
    return DocumentKey(place.path, f"{place.document.root_key}.{name}")


_APPROVAL_FILES = ("settings.local.json", "settings.json")
"""Both files `docs/research/mcp-config-formats.md` measured, in no precedence
between them — either one naming a server is enough to call it approved."""


def _approved_servers(root: Path) -> tuple[set[str], bool]:
    """Every server name Claude Code approved for `root`, and whether it approved all of them.

    Read from `.claude/settings.local.json` and `.claude/settings.json`, and
    **only** where `hasTrustDialogAccepted` is true in that same file — measured,
    the two keys that grant approval do nothing until a human has passed the
    trust dialog once, so a file that carries the keys and not the flag has
    approved nothing yet (`docs/adr/0014-o-enxerto-nasce-desligado-e-o-produto-diz-isso.md`).

    **The third file the research names is deliberately not read here.** Claude
    Code's *user*-level settings carry the same two keys and approve **without**
    the trust-dialog gate — ADR 0014 measured exactly that, which is why it
    refused to ever *write* there (one file approving every project blind is a
    supply-chain hole). Reading it back would not reopen that hole, but the
    research this module answers to has no measured **path** for that file, only
    the fact that it exists — and this codebase's own bar is a primary source,
    read directly, never a path guessed from memory. A server actually approved
    that way still reads as pending here; closing that gap is a re-measurement,
    not a rewrite of this function.
    """
    named: set[str] = set()
    approve_all = False
    for filename in _APPROVAL_FILES:
        settings = _parsed_object(root / ".claude" / filename)
        if settings is None or not settings.get("hasTrustDialogAccepted"):
            continue
        if settings.get("enableAllProjectMcpServers"):
            approve_all = True
        enabled = settings.get("enabledMcpjsonServers")
        if isinstance(enabled, list):
            named |= {name for name in cast("list[object]", enabled) if isinstance(name, str)}
    return named, approve_all


def _pending_approvals(
    places: Iterable[tuple[Scope, McpPlace]], root: Path
) -> Iterator[PendingApproval]:
    """Every server a graft Claude Code gates was handed, that it has not approved.

    ADR 0014 made the write-time warning a requirement; this is the same fact,
    read back after the session that wrote it is gone — the one case
    `overpower.planning.pending_activation` cannot answer here, because there is
    no `Plan` for `doctor` to ask, only the document and the registry Claude
    Code itself writes.
    """
    approved, approve_all = _approved_servers(root)
    for scope, place, name, _config in _servers_of(places):
        if scope is not Scope.PROJECT or not place.document.born_pending:
            continue
        if approve_all or name in approved:
            continue
        yield PendingApproval(destination=_document_key(place, name), name=name)


_RUNNERS = frozenset({"uvx", "npx"})
"""The same closed set `overpower.recipes.Runner` names, read back rather than
imported: this module asks *"is the command a graft rendered still on PATH"*,
never *"what does the schema declare"*, and a recipe-schema import into a
module that opens no catalog is a coupling this doctrine has already refused
once (`_CLONE_DIR`'s three-copy precedent, before ADR 0023 removed it)."""


def _sourced(config: object) -> bool:
    """Whether `config` is the shape `overpower.recipes` derives for a `source:` recipe.

    Matched by the render itself and not by a catalog lookup — `doctor` has
    none — so the signal is `command` naming a runner **and** an argument
    starting with `git+`, exactly what `_sourced_command` writes and nothing a
    hand-declared `command: "uvx"` recipe (a published package, not a source)
    ever carries alongside it.
    """
    if not isinstance(config, dict):
        return False
    args = cast("dict[str, object]", config).get("args")
    return isinstance(args, list) and any(
        isinstance(item, str) and item.startswith("git+") for item in cast("list[object]", args)
    )


def _missing_runners(
    places: Iterable[tuple[Scope, McpPlace]], environment: Environment
) -> Iterator[MissingRunner]:
    """Every graft whose `source:` runner is no longer on `PATH` — offline, always.

    The re-run of the one precondition ADR 0023 leaves an installed server to
    lose: no clone to go missing any more, only its own launcher.
    """
    for _scope, place, name, config in _servers_of(places):
        if not _sourced(config):
            continue
        command = cast("dict[str, object]", config).get("command")
        if not isinstance(command, str) or command not in _RUNNERS:
            continue
        if shutil.which(command, path=environment.variables.get("PATH")) is None:
            yield MissingRunner(destination=_document_key(place, name), name=name, runner=command)


_CLAUDE_REFERENCE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
"""`${VAR}` — `overpower.rendering._claude_reference`'s own spelling, read back."""

_DEVIN_REFERENCE = re.compile(r"\$\{env:([A-Za-z_][A-Za-z0-9_]*)\}")
"""`${env:VAR}` — `overpower.rendering._devin_reference`'s own spelling, read back."""


def _slot_pattern(dialect: Dialect) -> re.Pattern[str] | None:
    """How `dialect` spells a reference read out of the environment, or `None`.

    Gated on `expands_from_environment` and then matched on the closed set for
    the reason every other one in this product is: a new dialect must land as a
    hole the type checker names, not silently skip this check the way a mapping
    with no entry for it would.
    """
    if not expands_from_environment(dialect):
        return None
    match dialect:
        case Dialect.CLAUDE:
            return _CLAUDE_REFERENCE
        case Dialect.DEVIN:
            return _DEVIN_REFERENCE
        case Dialect.VSCODE:  # pragma: no cover — expands_from_environment already excludes it
            return None
        case _ as unreachable:
            assert_never(unreachable)


def _unset_slots(
    places: Iterable[tuple[Scope, McpPlace]], environment: Environment
) -> Iterator[UnsetSlot]:
    """Every slot a graft reads from the environment that this environment does not carry.

    Mirrors `overpower.planning.unset_slots`, off the document instead of off a
    `Plan` — `doctor` has none. Exit 0 for the same reason the install-time
    warning is: the file is correct either way, and the variable has to exist
    when the runtime starts, not when `doctor` runs.
    """
    for _scope, place, name, config in _servers_of(places):
        pattern = _slot_pattern(place.document.dialect)
        if pattern is None:
            continue
        variables = {
            match.group(1) for text in _strings_in(config) for match in pattern.finditer(text)
        }
        for variable in sorted(variables):
            if variable not in environment.variables:
                yield UnsetSlot(
                    destination=_document_key(place, name), name=name, variable=variable
                )
