"""`Request` → `Plan`: the one place a destination is decided.

The order is always the same — `Request`, then `Plan`, then the write — and the
writer consumes **the plan and nothing beyond it**. That is a design rule before
it is a testing one: a writer that recomputed a path could diverge from the
screen *by construction*, and no test written afterwards would close that.

**`Request`** is what was asked for: the artifacts by type, the scope, the
runtimes and the mode flags. v0.1.0's first selector is `--skill`, so `skills` is
the one artifact tuple here; `--ai-framework` and `--bundle` join it as sibling
tuples (https://github.com/panlabs-tech/overpower/issues/39) and the wizard
produces **the same type** from keystrokes
(https://github.com/panlabs-tech/overpower/issues/41), so the selection logic is
tested over values and never over keys.

**`Plan`** is an *ordered* sequence of writes. Each write carries origin,
destination and mode. It is what the plan screen renders, what `--dry-run`
prints and what the writer executes — one object, three readers, so they cannot
disagree.

**The destination is a datum with two forms**, and that is the graft lock the
v0.1.0 has to honour without implementing it (`domain.md`, "Reservado para
depois da v0.1.0"): a copy lands in a **folder**, a graft lands in a **file plus
a key inside it**, and one artifact may cost **more than one write**, the second
possibly outside the repository. Modelling a destination as a folder path is the
regression that turns v0.2 into a rewrite of the flow instead of the sum of one
operation. v0.1.0 implements one operation; `overpower.writing` is where the
other one says it does not exist yet.

**Destination is a function of (type, runtime, scope)** — rule 8, ADR 0006 — so
it is a table in code and never a catalog field. The (runtime, scope) half of
that function is `overpower.runtimes`; this module is the (type) half and the
composition.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, assert_never

from overpower.errors import BadInvocationError
from overpower.runtimes import Scope, resolve_project_dir, runtimes_in

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence
    from pathlib import Path

    from overpower.discovery import Artifact, ArtifactType, Catalog
    from overpower.runtimes import Runtime


class WriteMode(StrEnum):
    """How a write lands.

    The three are the ladder decided in
    https://github.com/panlabs-tech/overpower/issues/9. **Project scope uses
    `COPY` and only `COPY`**: under `core.symlinks=false` — which git
    auto-detects and records into the clone, so the default on Windows — a link
    becomes a text file, `git status` stays *clean*, and the equipment is broken
    for whoever cloned. `LINK` and `JUNCTION` are the rungs the global scope
    climbs (https://github.com/panlabs-tech/overpower/issues/40); they are
    declared here because the plan is the vocabulary the screen and the writer
    share, and a mode the plan cannot spell is a mode the screen cannot show.
    """

    COPY = "copy"
    LINK = "link"
    JUNCTION = "junction"


@dataclass(frozen=True)
class DirectoryTree:
    """A folder that receives a source tree whole — the copy class.

    Collision is of *path*: in `git status` it shows up as a new file.
    """

    path: Path


@dataclass(frozen=True)
class DocumentKey:
    """A key inside a document the user also edits — the graft class.

    Collision is of *key*: in `git diff` it shows up as a change to a file that
    is theirs. Nothing in v0.1.0 constructs one — there is no MCP server and no
    hook in the catalog — and the form exists anyway, because the flow must not
    assume *"one artifact, one write, all of it inside the target"*.
    """

    path: Path
    key: str


Destination = DirectoryTree | DocumentKey
"""Where a write lands: a folder, or a document and a key inside it."""


@dataclass(frozen=True)
class Write:
    """One landing: where it comes from, where it goes, and how it gets there."""

    source: Path
    destination: Destination
    mode: WriteMode
    files: int
    """How many files this write puts on disk. The screen adds them up."""


@dataclass(frozen=True)
class Landing:
    """One place the plan writes into, and every runtime that reads it.

    The plan names **the path and who consumes it**, never just the name of a
    runtime (ADR 0008): selecting Cursor writes `.agents/skills/`, which Codex,
    Copilot, VS Code and 16 others also read, so announcing *"Cursor"* would
    promise one target and deliver twenty.
    """

    place: Path
    """What the screen names: a folder for the copy class, the document for a graft."""

    readers: tuple[str, ...]
    writes: tuple[Write, ...]

    @property
    def files(self) -> int:
        """How many files land here."""
        return sum(write.files for write in self.writes)

    @property
    def folder(self) -> bool:
        """Whether `place` is a folder, which is what earns a trailing separator."""
        return all(isinstance(write.destination, DirectoryTree) for write in self.writes)


@dataclass(frozen=True)
class Selection:
    """One thing the user asked for, and everywhere it lands."""

    name: str
    artifacts: tuple[ArtifactType, ...]
    """One entry per artifact this selection brings, so the screen can count and name them."""

    landings: tuple[Landing, ...]


@dataclass(frozen=True)
class Plan:
    """The ordered sequence of writes a request costs, and the only input the writer has."""

    root: Path
    """What the destinations hang off, and what the screen shows them relative to."""

    selections: tuple[Selection, ...]

    @property
    def writes(self) -> tuple[Write, ...]:
        """Every write, in the order the writer performs them.

        Selection order is the order the names were typed; landing order is the
        order of the runtime table. Both are deterministic, which is what lets
        the failure report say *"wrote 14 of 22, stopped here"* and mean
        something.
        """
        return tuple(
            write
            for selection in self.selections
            for landing in selection.landings
            for write in landing.writes
        )


@dataclass(frozen=True)
class Request:
    """What was asked for, as values — never as keystrokes.

    Produced two ways, and it is the same type both times: from the flags, and
    from the wizard. That is what keeps the selection logic testable over values
    (`docs/agents/testing.md`, §7).
    """

    skills: tuple[str, ...] = ()
    runtimes: tuple[str, ...] = ()
    scope: Scope = Scope.PROJECT
    dry_run: bool = False
    yes: bool = False


class UnknownRuntimeError(BadInvocationError):
    """A `--runtime` value outside the closed set.

    The message carries the whole set, and the length of it is the point: the
    table is closed, there is no `--dir` hatch in v0.1.0 and nothing else in the
    product lists the runtimes, so an error that only said *"unknown"* would
    leave the caller with nowhere to look.
    """

    def __init__(self, key: str, scope: Scope, known: Iterable[str]) -> None:
        """Name the value that missed, the scope it missed in, and the whole set."""
        self.key = key
        self.scope = scope
        listed = ", ".join(sorted(known))
        super().__init__(f"unknown runtime `{key}` in {scope} scope; the set is: {listed}")


class NoRuntimeSelectedError(BadInvocationError):
    """No `--runtime`, and nothing to ask.

    There is no default, and the absence is the decision: guessing a destination
    is the class of error this product exists not to commit. Upstream installs
    into all 76 when nothing is detected, and that only survives *because* it
    skips silently — under unconditional writing it would create 55 directories
    in the repository (ADR 0008).
    """

    def __init__(self) -> None:
        """Say what is missing and that there is no default to fall back on."""
        super().__init__("no --runtime, and there is no default destination to fall back on")


class NothingSelectedError(BadInvocationError):
    """Nothing was asked for.

    The command line is the manifest, so an empty one is a typo and not a
    request — answering it with an empty plan and exit 0 would be the *"success
    with the wrong content"* class this product exists to avoid. In a terminal
    the bare `install` is the wizard instead
    (https://github.com/panlabs-tech/overpower/issues/41), which is a branch
    this error gets replaced by rather than a case it competes with.
    """

    def __init__(self) -> None:
        """Say that nothing was named, and what naming something looks like."""
        super().__init__("nothing to install: name at least one --skill")


class UnknownSkillError(BadInvocationError):
    """A `--skill` name the catalog does not have."""

    def __init__(self, name: str, known: Iterable[str]) -> None:
        """Name the miss and the pool, which is small enough to print whole."""
        self.name = name
        listed = ", ".join(sorted(known)) or "empty"
        super().__init__(f"unknown skill `{name}`; the pool is: {listed}")


class UnsupportedScopeError(BadInvocationError):
    """A scope this version cannot plan for.

    The global scope lands by a different shape — one canonical copy and links
    to the rest — and planning it as copy-everywhere would answer the wrong
    question quietly. It arrives in
    https://github.com/panlabs-tech/overpower/issues/40.
    """

    def __init__(self, scope: Scope) -> None:
        """Name the scope, so the refusal is not mistaken for a missing flag."""
        self.scope = scope
        super().__init__(f"the {scope} scope is not planned by this version")


def plan_for(request: Request, catalog: Catalog, root: Path) -> Plan:
    """The ordered writes `request` costs against `catalog`, landing under `root`.

    *What* before *where*, so a line missing both selectors is answered about
    the one the reader typed first.
    """
    artifacts = _selected_skills(request.skills, catalog)
    landings = _landings(_selected_runtimes(request.runtimes, request.scope), request.scope, root)
    return Plan(
        root=root,
        selections=tuple(_selection(artifact, landings) for artifact in artifacts),
    )


def _selection(artifact: Artifact, places: Mapping[Path, tuple[str, ...]]) -> Selection:
    """One artifact, landing in every selected place, as a real copy in each."""
    return Selection(
        name=artifact.name,
        artifacts=(artifact.type,),
        landings=tuple(
            Landing(
                place=place,
                readers=readers,
                writes=(
                    Write(
                        source=artifact.path,
                        destination=DirectoryTree(place / artifact.name),
                        mode=WriteMode.COPY,
                        files=artifact.files,
                    ),
                ),
            )
            for place, readers in places.items()
        ),
    )


def _selected_runtimes(keys: Sequence[str], scope: Scope) -> tuple[Runtime, ...]:
    """The runtimes named, validated against the set the scope allows.

    One implementation of that set — `runtimes_in` — so the validator and the
    screen cannot disagree, which is the failure ADR 0009 closes one layer
    earlier.
    """
    if not keys:
        raise NoRuntimeSelectedError
    allowed = {runtime.key: runtime for runtime in runtimes_in(scope)}
    chosen: dict[str, Runtime] = {}
    for key in keys:
        runtime = allowed.get(key)
        if runtime is None:
            raise UnknownRuntimeError(key, scope, allowed)
        chosen[key] = runtime
    # Back into table order: the order the plan lists places in is the order the
    # writer performs them, and the table is the only order both ends share.
    return tuple(runtime for runtime in runtimes_in(scope) if runtime.key in chosen)


def _selected_skills(names: Sequence[str], catalog: Catalog) -> tuple[Artifact, ...]:
    """The pool artifacts named, deduplicated, in the order they were typed.

    The command is the contract (rule 7): `--skill wayfinder` writes `wayfinder`
    and nothing else, even when its text tells the agent to invoke four others.
    Nothing is declared, validated, warned about or dragged along.
    """
    if not names:
        raise NothingSelectedError
    pool = {artifact.name: artifact for artifact in catalog.pool}
    chosen: dict[str, Artifact] = {}
    for name in names:
        artifact = pool.get(name)
        if artifact is None:
            raise UnknownSkillError(name, pool)
        chosen[name] = artifact
    return tuple(chosen.values())


def _landings(
    runtimes: Sequence[Runtime], scope: Scope, root: Path
) -> Mapping[Path, tuple[str, ...]]:
    """Each distinct place the selected runtimes read, mapped to all of its readers.

    Two runtimes collapse into one place far more often than not — 19 of the 76
    rows read `.agents/skills` — and collapsing them is what makes the plan
    honest about what a selection costs.

    Insertion order is the order of the runtime table, and that is what the plan
    inherits: it is the only order the screen and the writer both share.
    """
    grouped: dict[Path, list[str]] = {}
    for runtime in runtimes:
        grouped.setdefault(_place_of(runtime, scope, root), []).append(runtime.key)
    return {place: tuple(readers) for place, readers in grouped.items()}


def _place_of(runtime: Runtime, scope: Scope, root: Path) -> Path:
    """Where `runtime` reads skills, in `scope`."""
    match scope:
        case Scope.PROJECT:
            return resolve_project_dir(runtime, root)
        case Scope.GLOBAL:
            raise UnsupportedScopeError(scope)
        case _ as unreachable:
            assert_never(unreachable)
