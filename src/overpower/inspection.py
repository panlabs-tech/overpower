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
        *_landed_in(Scope.GLOBAL, environment.home, environment),
    )
    findings: tuple[Finding, ...] = (
        *_dangling(landed),
        *(() if root is None else _links_turned_text(root, landed)),
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
        for file in sorted(path for path in place.rglob("*") if path.is_file()):
            digest.update(file.relative_to(place).as_posix().encode("utf-8"))
            digest.update(b"\x00")
            digest.update(file.read_bytes())
            digest.update(b"\x00")
    except OSError:  # pragma: no cover — a file that vanishes mid-walk
        return None
    return digest.hexdigest()


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


def _links_turned_text(root: Path, landed: Iterable[Landed]) -> Iterator[LinkTurnedText]:
    """Files that are a link's target spelled as content, in a clone with links off.

    Gated on the clone's own config, and the gate is what makes the check precise
    instead of a guess: with links enabled, a one-line file naming a sibling is a
    one-line file naming a sibling. With `core.symlinks=false` recorded in the
    clone, it is the measured failure — and `git status` will not say so.
    """
    if not _symlinks_disabled(root):
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
    for file in sorted(path for path in place.rglob("*") if path.is_file()):
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


def _symlinks_disabled(root: Path) -> bool:
    """Whether this clone records `core.symlinks=false` — read, never asked of git.

    A plain file read and not `git config --get`, for the reason axiom 1 draws
    the transport-versus-installer line at: a question asked of a third-party
    binary is a dependency on it being installed, and the answer is one line of
    an INI file.

    The **repository's own** config, and only it: git auto-detects the capability
    at clone time and writes it there, which is the mechanism the finding is
    about. A value inherited from the user's global config would say something
    about the machine and nothing about this checkout.
    """
    config = _git_config(root)
    if config is None:
        return False
    try:
        text = config.read_text(encoding="utf-8", errors="replace")
    except OSError:  # pragma: no cover — a `.git` that lists but does not read
        return False
    return _core_symlinks_false(text)


def _git_config(root: Path) -> Path | None:
    """The config file of the repository at `root`, following a `gitdir:` pointer.

    `.git` is a directory in an ordinary clone and a **file** in a worktree or a
    submodule — the same two shapes `overpower.scope` already accepts when it
    decides whether there is a repository at all.
    """
    git = root / GIT_DIR
    if git.is_dir():
        return git / GIT_CONFIG
    if not git.is_file():
        return None
    try:
        pointer = git.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):  # pragma: no cover — a `.git` file that does not read
        return None
    if not pointer.startswith(GIT_DIR_POINTER):
        return None
    named = Path(pointer[len(GIT_DIR_POINTER) :].strip())
    return (named if named.is_absolute() else root / named) / GIT_CONFIG


def _core_symlinks_false(text: str) -> bool:
    """`core.symlinks` out of a git config, hand-parsed, last occurrence winning.

    Hand-parsed for the reason `overpower.discovery` hand-parses one frontmatter
    key: `configparser` is not a git-config parser — a bare key with no `=` is
    valid here and a parse error there — and pulling one key out of one section
    does not justify getting the difference wrong.
    """
    section = ""
    disabled = False
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
