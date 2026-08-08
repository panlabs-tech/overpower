"""What is on the disk of the target, and what is wrong with it — the `doctor`.

Sibling of `overpower.discovery` with the roots swapped. Discovery walks the
**catalog** tree and answers what *may* be installed; this module walks the
**runtime paths** of the repository and of the machine and answers what *is*,
and whether it still works.

`doctor` answers two questions in one output — *how is the terminal*, and *how is
what was installed* — and the second half is why it exists at all: three named
holes that nothing else in the product closes.

**`core.symlinks=false` breaking links.** The exact point where axiom 2 does not
answer on its own. Measured: git **auto-detects** the capability and writes it
into the clone — the default on Windows — a committed link checks out as an
ordinary text file carrying its own target, and **`git status` stays clean**. The
git lies, and the `doctor` is what contradicts it. So the check is two conditions
and not one: the clone's own config says links are off, *and* a file inside
installed equipment reads as a link that became text. Either alone is a guess.

**A link that does not resolve.** Global scope climbs the canonical + link ladder
(https://github.com/panlabs-tech/overpower/issues/40), and a link whose target
went away is invisible equipment: the directory listing shows the name, and
nothing is there.

**Two copies of one artifact that disagree.** Project scope lands a **real copy**
in every selected path (https://github.com/panlabs-tech/overpower/issues/9), and
that decision accepted losing the single point of truth **naming the `doctor` as
its mitigation**. This check is the payment of that debt.

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
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from overpower.planning import DirectoryTree
from overpower.runtimes import Scope, places_of, runtimes_in
from overpower.writing import points_elsewhere

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from overpower.planning import Destination
    from overpower.runtimes import Environment

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


Finding = DanglingLink | LinkTurnedText | Divergence
"""Everything the `doctor` can say is wrong. Empty means exit 0."""


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
    findings: tuple[Finding, ...]

    @property
    def healthy(self) -> bool:
        """Whether the run found nothing. This is what the exit code follows."""
        return not self.findings

    @property
    def artifacts(self) -> int:
        """How many distinct artifacts are installed, counted once per scope.

        Distinct from `len(self.landed)` on purpose: one artifact in four runtime
        paths is **one** artifact and **four** places, and the screen says both.
        """
        return len({(item.scope, item.name) for item in self.landed})


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
    findings: tuple[Finding, ...] = (
        *_dangling(landed),
        *(() if root is None else _links_turned_text(root, landed, environment)),
        *_divergences(landed),
    )
    return Diagnosis(
        terminal=terminal,
        root=root,
        home=environment.home,
        landed=landed,
        findings=findings,
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
