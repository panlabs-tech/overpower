"""`Request` → `Plan`: the one place a destination is decided.

The order is always the same — `Request`, then `Plan`, then the write — and the
writer consumes **the plan and nothing beyond it**. That is a design rule before
it is a testing one: a writer that recomputed a path could diverge from the
screen *by construction*, and no test written afterwards would close that.

**`Request`** is what was asked for: the artifacts by type, the scope, the
runtimes and the mode flags. `skills`, `ai_frameworks` and `bundles` are sibling
tuples — the three units are chosen independently — and the wizard produces
**the same type** from keystrokes
(https://github.com/panlabs-tech/overpower/issues/41), so the selection logic is
tested over values and never over keys.

**A line may mix all three**, and the plan they produce has a fixed, documented
order — framework, then bundle, then individual artifact
(https://github.com/panlabs-tech/overpower/issues/39). That is also the order a
collided destination resolves in: an intra-command collision is not *detected* —
`install --ai-framework matt-pocock --skill <x>` may write the same destination
twice, once from each selector — but the order means the individual artifact,
the most specific unit, is always the last write and therefore the content that
survives. Testability is why the order is fixed rather than left to the parser:
*"overwrites somehow"* has no assertion, and *"the individual artifact's content
is what's on disk"* does.

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

import sys
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from overpower.errors import BadInvocationError, RefusedError
from overpower.runtimes import RUNTIMES_BY_KEY, Scope, places_of, runtimes_in

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence
    from pathlib import Path

    from overpower.discovery import Artifact, Bundle, Catalog, Framework
    from overpower.runtimes import Environment, Runtime


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

    @property
    def mode(self) -> WriteMode:
        """The mode every write of this landing shares.

        Uniform by construction: mode is decided per *landing* — canonical or
        rung of the ladder (https://github.com/panlabs-tech/overpower/issues/40)
        — never per artifact, so every write inside one landing carries the same
        one.
        """
        return self.writes[0].mode


@dataclass(frozen=True)
class Selection:
    """One thing the user asked for, and everywhere it lands."""

    name: str
    artifacts: tuple[Artifact, ...]
    """One entry per artifact this selection brings, so the screen can count and name them.

    The artifacts themselves and not just their types, because the plan **names**
    them (#58): it is the last gate before the write, and a gate that could only
    count would ask someone to accept a set they cannot see. The type travels
    inside each one, so the head line still says *"25 skills"* from the same
    datum the stacked list below it is drawn from — one source, and therefore no
    way for the count and the list to disagree.
    """

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

    `ai_frameworks`, `bundles` and `skills` are independent, and a line may name
    any combination of the three (https://github.com/panlabs-tech/overpower/issues/39).
    """

    ai_frameworks: tuple[str, ...] = ()
    bundles: tuple[str, ...] = ()
    skills: tuple[str, ...] = ()
    runtimes: tuple[str, ...] = ()
    scope: Scope = Scope.PROJECT
    force: bool = False
    dry_run: bool = False
    yes: bool = False


class UnknownRuntimeError(BadInvocationError):
    """A `--runtime` value outside the closed table — not a typo of scope.

    The message carries the whole table, and the length of it is the point: the
    table is closed, there is no `--dir` hatch in v0.1.0 and nothing else in the
    product lists the runtimes, so an error that only said *"unknown"* would
    leave the caller with nowhere to look. A value that *is* in the table but has
    no destination in the requested scope is a different defect —
    `RuntimeUnavailableInScopeError`, ADR 0009 — because the text typed matches
    something real; what is missing is not on this line.
    """

    def __init__(self, key: str, known: Iterable[str]) -> None:
        """Name the value that missed and the whole table."""
        self.key = key
        listed = ", ".join(sorted(known))
        super().__init__(f"unknown runtime `{key}`; the table is: {listed}")


class RuntimeUnavailableInScopeError(RefusedError):
    """A `--runtime` value the table has, with no destination in this scope.

    ADR 0009: `eve` and `promptscript` declare no global destination, so the set
    `--runtime` accepts is a function of scope — 76 in project, 74 in global —
    and asking for one of the missing two in global scope is a **valid**
    invocation with a **negative** answer. The value exists, the flag exists,
    nothing about the line is malformed; what does not exist is the
    *destination*, and destination is a fact of the table, not of the command
    line. That is the axis against `UnknownRuntimeError`: this one names a real
    row, wrong scope.
    """

    def __init__(self, key: str, scope: Scope) -> None:
        """Name the runtime, the scope that refused it, and the fix."""
        self.key = key
        self.scope = scope
        super().__init__(
            f"`{key}` has no destination in {scope} scope; "
            "install in the repository instead of the machine"
        )


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
    """Nothing was asked for, on any of the three independent selectors.

    The command line is the manifest, so an empty one is a typo and not a
    request — answering it with an empty plan and exit 0 would be the *"success
    with the wrong content"* class this product exists to avoid. In a terminal
    the bare `install` is the wizard instead
    (https://github.com/panlabs-tech/overpower/issues/41), which is a branch
    this error gets replaced by rather than a case it competes with.
    """

    def __init__(self) -> None:
        """Say that nothing was named, and what naming something looks like."""
        super().__init__(
            "nothing to install: name at least one --skill, --ai-framework or --bundle"
        )


class UnknownSkillError(BadInvocationError):
    """A `--skill` name the catalog does not have."""

    def __init__(self, name: str, known: Iterable[str]) -> None:
        """Name the miss and the pool, which is small enough to print whole."""
        self.name = name
        listed = ", ".join(sorted(known)) or "empty"
        super().__init__(f"unknown skill `{name}`; the pool is: {listed}")


class DestinationExistsError(RefusedError):
    """A global destination that already occupies the path, and no one to ask.

    The `--force` trigger has exactly one condition: global scope, and the path
    already there — https://github.com/panlabs-tech/overpower/issues/40. Project
    scope has no such refusal (`overpower.writing` writes unconditionally, and
    `git status` is the safety net); global scope has no git to reveal or undo an
    overwrite, so an existing path is refused instead of clobbered — detectable
    in advance, the same reasoning ADR 0009 already used for the
    runtime-without-destination case. A real terminal turns the refusal into a
    question instead (`overpower.cli._confirmed_overwrite`,
    https://github.com/panlabs-tech/overpower/issues/69); this is what fires
    when there is no terminal to ask, or `--yes`/`--dry-run` already declined
    that kind of interaction.
    """

    def __init__(self, paths: Sequence[Path]) -> None:
        """Name every colliding path and the flag that lifts the refusal."""
        self.paths = tuple(paths)
        listed = ", ".join(str(path) for path in self.paths)
        super().__init__(f"already exists, use --force to overwrite: {listed}")


def plan_for(request: Request, catalog: Catalog, root: Path, environment: Environment) -> Plan:
    """The ordered writes `request` costs against `catalog`, landing under `root`.

    *What* before *where*, so a line missing both selectors is answered about
    the one the reader typed first.

    Selections are built framework, then bundle, then individual artifact — the
    fixed collision order (module docstring, https://github.com/panlabs-tech/overpower/issues/39)
    — and that order is what the writer executes, since `Plan.writes` flattens
    `selections` in place.

    `environment` only feeds global-scope resolution (`overpower.runtimes`) —
    it is unused and still required in project scope, because a function whose
    shape changes with its own input is a harder one to call correctly.
    """
    if not (request.ai_frameworks or request.bundles or request.skills):
        raise NothingSelectedError
    frameworks = _selected_frameworks(request.ai_frameworks, catalog)
    bundles = _selected_bundles(request.bundles, catalog)
    skills = _selected_skills(request.skills, catalog)
    runtimes = _selected_runtimes(request.runtimes, request.scope)
    landings = places_of(runtimes, request.scope, root, environment)
    return Plan(
        root=root,
        selections=(
            *(_framework_selection(framework, landings, request.scope) for framework in frameworks),
            *(_bundle_selection(bundle, landings, request.scope) for bundle in bundles),
            *(_skill_selection(artifact, landings, request.scope) for artifact in skills),
        ),
    )


def existing_destinations(plan: Plan, request: Request) -> tuple[Path, ...]:
    """Global-scope write destinations already on disk, sorted — a fact, not a verdict.

    Detectable before the first byte — `Path.exists()`, never a write. Global
    scope only, and always empty when `--force` was given: project scope has no
    such question (`overpower.writing` writes unconditionally, by design), and
    `--force` already means "I know, overwrite it" before a caller has anything
    to decide. What used to be decided here — refuse outright — is now the
    caller's call (`overpower.cli._perform`): whether there is a terminal to
    turn this into a question, or `DestinationExistsError` is still the answer,
    https://github.com/panlabs-tech/overpower/issues/69.
    """
    if request.scope is not Scope.GLOBAL or request.force:
        return ()
    return tuple(
        sorted({write.destination.path for write in plan.writes if write.destination.path.exists()})
    )


def _framework_selection(
    framework: Framework, places: Mapping[Path, tuple[str, ...]], scope: Scope
) -> Selection:
    """The whole framework — rule 1 — every artifact it carries, in every selected place."""
    return _grouped_selection(framework.name, framework.artifacts, places, scope)


def _bundle_selection(
    bundle: Bundle, places: Mapping[Path, tuple[str, ...]], scope: Scope
) -> Selection:
    """Exactly what the bundle's manifest names (ADR 0002), in every selected place."""
    return _grouped_selection(bundle.name, bundle.artifacts, places, scope)


def _skill_selection(
    artifact: Artifact, places: Mapping[Path, tuple[str, ...]], scope: Scope
) -> Selection:
    """One pool artifact, landing in every selected place."""
    return _grouped_selection(artifact.name, (artifact,), places, scope)


def _grouped_selection(
    name: str, artifacts: Sequence[Artifact], places: Mapping[Path, tuple[str, ...]], scope: Scope
) -> Selection:
    """One thing that was asked for, every artifact it carries, everywhere it lands.

    The shape serves a pool skill (one artifact), a bundle (the artifacts its
    manifest names) and a framework (every artifact it carries) alike: the unit
    differs, the landing arithmetic does not.

    In project scope every landing is a real copy — #9 removed the canonical
    there. In global scope the **first place in table order** is the canonical
    — a real copy — and every subsequent place is a link pointing at it: the
    escada https://github.com/panlabs-tech/overpower/issues/40 climbs, because
    `~/` has no git to deduplicate and duplicating bytes there is a real cost.

    `places` is never empty here: `plan_for` already refused an empty runtime
    selection (`NoRuntimeSelectedError`) before a `Selection` is ever built, so
    indexing the first entry for the canonical needs no guard.
    """
    ordered = tuple(places.items())
    canonical = ordered[0][0]
    return Selection(
        name=name,
        artifacts=tuple(artifacts),
        landings=tuple(
            Landing(
                place=place,
                readers=readers,
                writes=tuple(
                    _write_for(
                        artifact, place, canonical, scope=scope, canonical_landing=index == 0
                    )
                    for artifact in artifacts
                ),
            )
            for index, (place, readers) in enumerate(ordered)
        ),
    )


def _write_for(
    artifact: Artifact, place: Path, canonical: Path, *, scope: Scope, canonical_landing: bool
) -> Write:
    """One artifact's write into `place` — a real copy, or a rung of the ladder.

    The canonical landing (project scope, always; global scope, the first place
    in table order) copies from the catalog. Every other global landing links to
    the canonical's *destination* — not the catalog source — because that is
    the one thing on disk a link can actually point at.
    """
    destination = DirectoryTree(place / artifact.name)
    if scope is Scope.PROJECT or canonical_landing:
        return Write(
            source=artifact.path, destination=destination, mode=WriteMode.COPY, files=artifact.files
        )
    mode = WriteMode.JUNCTION if sys.platform == "win32" else WriteMode.LINK
    return Write(
        source=canonical / artifact.name, destination=destination, mode=mode, files=artifact.files
    )


def _selected_runtimes(keys: Sequence[str], scope: Scope) -> tuple[Runtime, ...]:
    """The runtimes named, validated against the closed table and against the scope.

    Two different misses, two different codes. A key outside the 76-member
    table is a typo — exit 2, `UnknownRuntimeError`. A key the table has, with
    no destination in `scope`, is `runtimes_in(scope)` saying no — exit 3,
    `RuntimeUnavailableInScopeError`, ADR 0009. One implementation of the scoped
    set, `runtimes_in`, so the validator and the screen cannot disagree.
    """
    if not keys:
        raise NoRuntimeSelectedError
    allowed = {runtime.key: runtime for runtime in runtimes_in(scope)}
    chosen: dict[str, Runtime] = {}
    for key in keys:
        if key not in RUNTIMES_BY_KEY:
            raise UnknownRuntimeError(key, RUNTIMES_BY_KEY)
        runtime = allowed.get(key)
        if runtime is None:
            raise RuntimeUnavailableInScopeError(key, scope)
        chosen[key] = runtime
    # Back into table order: the order the plan lists places in is the order the
    # writer performs them, and the table is the only order both ends share.
    return tuple(runtime for runtime in runtimes_in(scope) if runtime.key in chosen)


def _selected_skills(names: Sequence[str], catalog: Catalog) -> tuple[Artifact, ...]:
    """The pool artifacts named, deduplicated, in the order they were typed.

    The command is the contract (rule 7): `--skill wayfinder` writes `wayfinder`
    and nothing else, even when its text tells the agent to invoke four others.
    Nothing is declared, validated, warned about or dragged along. A framework's
    inner artifact is not in this pool (rule 1: no partial framework install), so
    naming one here is the same miss as naming any other unknown skill.
    """
    pool = {artifact.name: artifact for artifact in catalog.pool}
    chosen: dict[str, Artifact] = {}
    for name in names:
        artifact = pool.get(name)
        if artifact is None:
            raise UnknownSkillError(name, pool)
        chosen[name] = artifact
    return tuple(chosen.values())


def _selected_frameworks(names: Sequence[str], catalog: Catalog) -> tuple[Framework, ...]:
    """The AI Frameworks named, deduplicated, in the order they were typed.

    Lookup goes through `Catalog.framework`, the same closed-list error `list`
    already answers with — one place names what the catalog does not have.
    """
    chosen: dict[str, Framework] = {}
    for name in names:
        chosen[name] = catalog.framework(name)
    return tuple(chosen.values())


def _selected_bundles(names: Sequence[str], catalog: Catalog) -> tuple[Bundle, ...]:
    """The bundles named, deduplicated, in the order they were typed."""
    chosen: dict[str, Bundle] = {}
    for name in names:
        chosen[name] = catalog.bundle(name)
    return tuple(chosen.values())
