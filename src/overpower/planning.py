"""`Request` → `Plan`: the one place a destination is decided.

The order is always the same — `Request`, then `Plan`, then the write — and the
writer consumes **the plan and nothing beyond it**. That is a design rule before
it is a testing one: a writer that recomputed a path could diverge from the
screen *by construction*, and no test written afterwards would close that.

**`Request`** is what was asked for: the artifacts by type, the scope, the
runtimes and the mode flags. `skills`, `ai_frameworks` and `bundles` are sibling
tuples — the three units are chosen independently — and the wizard produces
**the same type** from keystrokes
(https://github.com/ThiagoPanini/overpower/issues/41), so the selection logic is
tested over values and never over keys.

**A line may mix all three**, and the plan they produce has a fixed, documented
order — framework, then bundle, then individual artifact
(https://github.com/ThiagoPanini/overpower/issues/39). That is also the order a
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

import shutil
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, assert_never, cast

from overpower.discovery import Artifact
from overpower.errors import BadInvocationError, RefusedError
from overpower.grafting import UnreadableDocumentError, read_document, refuse_if_broken
from overpower.jsonio import loads_json
from overpower.recipes import Check, Precondition, Recipe
from overpower.rendering import (
    Fragment,
    Inputs,
    expands_from_environment,
    render,
    slot_value,
)
from overpower.runtimes import (
    RUNTIMES_BY_KEY,
    Scope,
    known_runtimes,
    mcp_document_of,
    mcp_places_of,
    mcp_runtimes_in,
    places_of,
    runtimes_in,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping, Sequence

    from overpower.discovery import Bundle, Catalog, Framework
    from overpower.rendering import Graft
    from overpower.runtimes import Environment, McpDocument, McpPlace, Runtime


class WriteMode(StrEnum):
    """How a write lands.

    The three are the ladder decided in
    https://github.com/ThiagoPanini/overpower/issues/9. **Project scope uses
    `COPY` and only `COPY`**: under `core.symlinks=false` — which git
    auto-detects and records into the clone, so the default on Windows — a link
    becomes a text file, `git status` stays *clean*, and the equipment is broken
    for whoever cloned. `LINK` and `JUNCTION` are the rungs the global scope
    climbs (https://github.com/ThiagoPanini/overpower/issues/40); they are
    declared here because the plan is the vocabulary the screen and the writer
    share, and a mode the plan cannot spell is a mode the screen cannot show.
    """

    COPY = "copy"
    LINK = "link"
    JUNCTION = "junction"
    GRAFT = "graft"
    """A key written **inside a document the user also edits**.

    The second operation of the model, and the one `domain.md` reserved the
    shape for: a copy collides by *path* and shows up in `git status` as a new
    file, a graft collides by *key* and shows up in `git diff` as a change to a
    file that is theirs. It is a mode and not a second writer because the write
    boundary stays single — `overpower.writing` gains a branch, not a sibling.
    """

    CLONE = "clone"
    """The code a `source:` recipe brings, landed exactly like `COPY`.

    Its own member and not a plain `COPY`, because the two disagree on the one
    axis `existing_destinations` asks about: a global copy that already exists
    is refused without `--force` (issue #40), and a clone is re-cloned
    unconditionally, by decision (ADR 0015) — reinstalling must not leave last
    week's checkout on disk under this week's name. `overpower.writing` lands
    the two identically; only the refusal tells them apart.
    """


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
    is theirs. `key` is the **whole path** to it — `mcpServers.cloudflare` —
    because that is what the plan prints, and with unconditional overwriting
    (ADR 0013) that line is the only chance the reader has to notice the key
    about to be replaced is one of theirs.
    """

    path: Path
    key: str


Destination = DirectoryTree | DocumentKey
"""Where a write lands: a folder, or a document and a key inside it."""


@dataclass(frozen=True)
class Write:
    """One landing: where it comes from, where it goes, and how it gets there."""

    source: Path | Graft
    """A directory to copy, **or the rendered graft to splice in**.

    A graft has no source path — nothing on disk is being moved — so the origin
    of a write became one of two things when the second operation arrived. The
    alternative was for the writer to re-render the recipe, and *"the writer
    consumes the plan and nothing beyond it"* is precisely what makes the plan
    and the disk unable to disagree.
    """

    destination: Destination
    mode: WriteMode
    files: int
    """How many files this write puts on disk, as far as its own landing can tell.

    One for the first graft into a document: the document is a file, and writing
    a key into it writes that file. **Zero for a second graft into the same
    one** — a VS Code slot lands the server and its prompt as two keys, and the
    report at the end counts what landed on disk, where one file did. What the
    *plan* counts for a graft is keys and not files, which is why the two halves
    of one recipe still show as two rows on the screen.

    **The final count is not a sum of this field**, and cannot be: a landing is
    built per selection, so three servers asked for in one line are three
    landings each answering `1` for the same `.vscode/mcp.json`. Only
    `overpower.writing` sees the whole plan, and it is where the same document
    reached twice stops counting twice.
    """


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
        """Whether `place` is a folder, which is what earns a trailing separator.

        Uniform by construction, the way `mode` is: the form of a destination
        follows from the **place**, and a place is either a directory runtimes
        read or a document they parse — never both. `all` rather than the first
        write because that is the claim, and a landing that ever mixed the two
        would answer *document* here and be read as one.
        """
        return all(isinstance(write.destination, DirectoryTree) for write in self.writes)

    @property
    def keys(self) -> tuple[str, ...]:
        """The document keys this landing writes, empty for the copy class.

        What a graft costs is counted in keys and never in paths: it creates no
        path, so the screen and the identity assertion both read this instead.
        """
        return tuple(
            write.destination.key
            for write in self.writes
            if isinstance(write.destination, DocumentKey)
        )

    @property
    def mode(self) -> WriteMode:
        """The mode every write of this landing shares.

        Uniform by construction: mode is decided per *landing* — canonical or
        rung of the ladder (https://github.com/ThiagoPanini/overpower/issues/40)
        — never per artifact, so every write inside one landing carries the same
        one.
        """
        return self.writes[0].mode


type Carried = Artifact | Recipe
"""What a selection brings: a directory to copy, or a server to declare.

A union rather than one widened type, and for the same reason `Destination` is
one: an `Artifact` is a directory with a weight, a `Recipe` is a declaration
with none, and a value that had to spell both would lie about half of its fields
on every instance.
"""


@dataclass(frozen=True)
class Selection:
    """One thing the user asked for, and everywhere it lands."""

    name: str
    artifacts: tuple[Carried, ...]
    """One entry per artifact this selection brings, so the screen can count and name them.

    The artifacts themselves and not just their types, because the plan **names**
    them (#58): it is the last gate before the write, and a gate that could only
    count would ask someone to accept a set they cannot see. The type travels
    inside each one, so the head line still says *"25 skills"* from the same
    datum the stacked list below it is drawn from — one source, and therefore no
    way for the count and the list to disagree.
    """

    landings: tuple[Landing, ...]


class MissingClass(StrEnum):
    """Which of the two tables a `SkippedClass` runtime has no row on."""

    MCP = "MCP"
    SKILLS = "skills"


@dataclass(frozen=True)
class SkippedClass:
    """One runtime a mixed line carried both classes for, that had a row on only one.

    Not a refusal: `_selected_runtimes` already turns away a runtime with a
    row on **neither** table before `plan_for` gets this far (ADR 0009). The
    runtime named here received the class it does have a row for; `missing`
    is the other one.
    """

    runtime: str
    missing: MissingClass


@dataclass(frozen=True)
class Plan:
    """The ordered sequence of writes a request costs, and the only input the writer has."""

    root: Path
    """What the destinations hang off, and what the screen shows them relative to."""

    selections: tuple[Selection, ...]

    skipped: tuple[SkippedClass, ...] = ()
    """Every runtime a mixed line carried both classes for, that received only one.

    Issue #100: narrows `plan_for`'s refusal from the whole line to the
    runtime with a row on neither table, so the runtime that has one still
    needs a way to say so on screen instead of going silent about the class it
    did not receive.
    """

    @property
    def landings(self) -> tuple[Landing, ...]:
        """Every landing, in the order the writer reaches them.

        The sibling of `writes` and the reason it is not derived from it: a
        landing is a **place**, and how many writes fall in one differs by class
        — a copy landing carries one per artifact, a graft landing one per key.
        The writer needs the boundary to count what the report promises, and
        flattening first is exactly what loses it.
        """
        return tuple(landing for selection in self.selections for landing in selection.landings)

    @property
    def writes(self) -> tuple[Write, ...]:
        """Every write, in the order the writer performs them.

        Selection order is the order the names were typed; landing order is the
        order of the runtime table. Both are deterministic, which is what lets
        the failure report say *"wrote 14 of 22, stopped here"* and mean
        something.
        """
        return tuple(write for landing in self.landings for write in landing.writes)


@dataclass(frozen=True)
class Request:
    """What was asked for, as values — never as keystrokes.

    Produced two ways, and it is the same type both times: from the flags, and
    from the wizard. That is what keeps the selection logic testable over values
    (`docs/agents/testing.md`, §7).

    `ai_frameworks`, `bundles` and `skills` are independent, and a line may name
    any combination of the three (https://github.com/ThiagoPanini/overpower/issues/39).
    """

    ai_frameworks: tuple[str, ...] = ()
    bundles: tuple[str, ...] = ()
    skills: tuple[str, ...] = ()
    mcps: tuple[str, ...] = ()
    """The MCP servers named, a fourth independent selector.

    A line may mix it with the other three — the line is the manifest, and the
    manifest cannot be two lines — so it accumulates the same way they do and is
    refused the same way when nothing at all was named.
    """

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
    `--runtime` accepts is a function of scope — the union of `runtimes_in(scope)`
    and `mcp_runtimes_in(scope)` — and asking for one of the missing two in global
    scope is a **valid** invocation with a **negative** answer. The value exists,
    the flag exists, nothing about the line is malformed; what does not exist is
    the *destination*, and destination is a fact of the table, not of the command
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


class SourceRequiresMachineScopeError(RefusedError):
    """A recipe with `source:` asked for in a scope that cannot receive its clone.

    ADR 0015, in the shape ADR 0009 already gave the model: there, the set of
    **runtimes** `--runtime` accepts is a function of scope; here the same move
    happens on the other axis — **the set of scopes a recipe can land in is a
    function of the recipe**, and project is not in it for one that clones. The
    reason is textually the one the curation criterion already refused a third
    party for: the rendered command carries the absolute path of the clone,
    which is a fact of whoever's machine installed it, and a manifest committed
    to the repository must not carry that.

    Fired before the plan names a single write — the same "refuse before the
    first byte" reasoning `_refuse_a_runtime_with_no_document` already applies,
    now against `request.scope` instead of a runtime table.
    """

    def __init__(self, recipe: str) -> None:
        """Name the recipe and the fix: the one scope that can receive its clone."""
        self.recipe = recipe
        super().__init__(
            f"`{recipe}`: brings its own source code, which lands on this machine "
            "and not in the repository; install with --global instead"
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
    (https://github.com/ThiagoPanini/overpower/issues/41), which is a branch
    this error gets replaced by rather than a case it competes with.
    """

    def __init__(self) -> None:
        """Say that nothing was named, and what naming something looks like."""
        super().__init__(
            "nothing to install: name at least one --skill, --ai-framework, --bundle or --mcp"
        )


class UnknownSkillError(BadInvocationError):
    """A `--skill` name the catalog does not have."""

    def __init__(self, name: str, known: Iterable[str]) -> None:
        """Name the miss and the pool, which is small enough to print whole."""
        self.name = name
        listed = ", ".join(sorted(known)) or "empty"
        super().__init__(f"unknown skill `{name}`; the pool is: {listed}")


class NoMcpDocumentError(RefusedError):
    """A selected runtime has nowhere to receive an MCP server in this scope.

    ADR 0009's reading, applied to the second axis: destination is a function of
    (type, runtime, scope), the function is **partial**, and where it is not
    defined the pair does not exist. Asking for one is a valid invocation with a
    negative answer — exit 3.

    Fires only on a line that carries **no** copy class: `--mcp b --runtime
    cursor` alone has nothing else for `cursor` to receive, so the whole line
    is refused. A line that mixes `--skill` in has a second table to check —
    `plan_for` asks `_skipped_classes_of` instead, and a `cursor` with a
    skills row there receives it and is merely *named* in a `SkippedClass`,
    not refused (issue #100). There is no third case where `cursor` has a row
    on **neither** table: `_selected_runtimes` already refused it before
    `plan_for` got this far — a key that reaches here survived ADR 0009's
    scope-reachability filter, which is exactly "a row on at least one of the
    two," so a mixed line never needs a refusal this function doesn't already
    have upstream.

    There is no canonical MCP format to fall back on — measured, the same server
    has three root keys and three file names across three targets, and the MCP
    spec documents the absence itself — so a runtime with no row is a runtime
    nobody has rendered for, not a runtime whose path we merely have not typed.
    """

    def __init__(self, key: str, scope: Scope) -> None:
        """Name the runtime, the scope, and every runtime that *can* take one."""
        self.key = key
        self.scope = scope
        listed = ", ".join(mcp_runtimes_in(scope)) or "none of them"
        super().__init__(
            f"`{key}` has no MCP document in {scope} scope; "
            f"the runtimes that take one there are: {listed}"
        )


class NoSkillsDestinationError(RefusedError):
    """A selected runtime is a graft target and reads no skills anywhere.

    The mirror of `NoMcpDocumentError` on the other axis, and it exists because
    the two tables stopped being nested: `vscode` reads `.vscode/mcp.json` and
    has **no row in the skills transcription** — upstream declares none, and the
    transcription is a transcription. So `--runtime vscode --mcp x` is an install
    and `--runtime vscode --skill y` is a valid line with a negative answer.

    Exit **3** and not 2, for the reason ADR 0009 gives: the value is a real
    target, the flag is real, nothing about the line is malformed. What does not
    exist is the destination for *that class*.

    Scope is not in the message because it is not in the fact: this runtime has
    no skills destination in a repository and none on the machine either, so
    naming a scope would suggest the other one works.

    **It says *destination* and never *"reads no skills"*, which would be false.**
    Measured, VS Code does read `.agents/skills` — it just reads the one 19 other
    rows write, and it has no row of its own to name. So what the refusal means
    is *"there is nowhere for `--runtime vscode` to put a skill"*, and the fix it
    names is the true one: name a runtime that writes the folder this one reads.

    Fires only on a line that carries **no** graft class: `--skill y --runtime
    vscode` alone has nothing else for `vscode` to receive. A line that mixes
    `--mcp` in checks the other table too, and a `vscode` with a document
    there receives it and is merely *named* in a `SkippedClass`, not refused
    (issue #100) — the twin refusal `NoMcpDocumentError`'s docstring
    considers, "a row on neither table," never actually reaches a mixed
    line: `_selected_runtimes` already turned it away.
    """

    def __init__(self, key: str) -> None:
        """Name the runtime, why it has nowhere to put a skill, and the two ways out."""
        self.key = key
        super().__init__(
            f"`{key}` takes MCP servers and has no skills destination of its own; "
            "name a runtime that writes the folder it reads, or drop the skills from the line"
        )


class DestinationExistsError(RefusedError):
    """A global destination that already occupies the path, and no one to ask.

    The `--force` trigger has exactly one condition: global scope, and the path
    already there — https://github.com/ThiagoPanini/overpower/issues/40. Project
    scope has no such refusal (`overpower.writing` writes unconditionally, and
    `git status` is the safety net); global scope has no git to reveal or undo an
    overwrite, so an existing path is refused instead of clobbered — detectable
    in advance, the same reasoning ADR 0009 already used for the
    runtime-without-destination case. A real terminal turns the refusal into a
    question instead (`overpower.cli._confirmed_overwrite`,
    https://github.com/ThiagoPanini/overpower/issues/69); this is what fires
    when there is no terminal to ask, or `--yes`/`--dry-run` already declined
    that kind of interaction.
    """

    def __init__(self, paths: Sequence[Path]) -> None:
        """Name every colliding path and the flag that lifts the refusal."""
        self.paths = tuple(paths)
        listed = ", ".join(str(path) for path in self.paths)
        super().__init__(f"already exists, use --force to overwrite: {listed}")


def plan_for(  # noqa: PLR0913, PLR0917 — the four a plan needs, plus the two a caller obtained
    request: Request,
    catalog: Catalog,
    root: Path,
    environment: Environment,
    sources: Mapping[str, Path] = MappingProxyType({}),
    secrets: Mapping[str, str] = MappingProxyType({}),
) -> Plan:
    """The ordered writes `request` costs against `catalog`, landing under `root`.

    *What* before *where*, so a line missing both selectors is answered about
    the one the reader typed first.

    Selections are built framework, then bundle, then individual artifact — the
    fixed collision order (module docstring, https://github.com/ThiagoPanini/overpower/issues/39)
    — and that order is what the writer executes, since `Plan.writes` flattens
    `selections` in place.

    `environment` only feeds global-scope resolution (`overpower.runtimes`) —
    it is unused and still required in project scope, because a function whose
    shape changes with its own input is a harder one to call correctly.

    `sources` is the clone each selected `source:` recipe already brought, keyed
    by recipe name (`overpower.remote.sources_for`) — obtained outside this
    function and handed in, the same reason `catalog` itself is: a planner that
    fetched for itself could not be built from a value that survives past the
    call that built it, and the writer needs the clone still on disk at
    `execute()` time. Empty by default, and every recipe with no `source:` never
    looks itself up in it.

    `secrets` is the slot values a person answered for, and **it is dropped
    outside the machine scope right here** (ADR 0024,
    https://github.com/ThiagoPanini/overpower/issues/167). The gate is in this
    function rather than at the prompt because this is where a destination is
    decided, and *"a project document goes to the git"* is a fact about the
    destination: a caller that gathered a value and then asked for a project plan
    gets references back, with no second place to have got it right. Which
    *dialects* may take a value is the renderer's half of the same rule, and it
    stays there for the same reason.
    """
    if not (request.ai_frameworks or request.bundles or request.skills or request.mcps):
        raise NothingSelectedError
    frameworks = _selected_frameworks(request.ai_frameworks, catalog)
    bundles = _selected_bundles(request.bundles, catalog)
    skills = _selected_skills(request.skills, catalog)
    mcps = _selected_mcps(request.mcps, catalog)
    bundled_artifacts = tuple(
        item for bundle in bundles for item in bundle.artifacts if isinstance(item, Artifact)
    )
    bundled_recipes = tuple(
        item for bundle in bundles for item in bundle.artifacts if isinstance(item, Recipe)
    )
    _refuse_a_sourced_recipe_outside_machine_scope((*mcps, *bundled_recipes), request.scope)
    runtimes = _selected_runtimes(request.runtimes, request.scope)
    # Before the first `Selection` is built, so a refusal costs no screen and no
    # byte. Fired only for the classes the line actually carries: a line
    # carrying one class alone still refuses the whole line for a runtime with
    # no row on it — there is nothing else here for that runtime to receive.
    #
    # A line carrying both never needs that refusal a third time: every key in
    # `runtimes` already survived `_selected_runtimes`'s scope-reachability
    # filter, ADR 0009 — "a row in the union of the two tables, for this
    # scope" — which is exactly "a row on at least one of the classes a mixed
    # line could carry." So a runtime with no row on the table this branch
    # would otherwise check is only ever missing the *other* one, never both
    # — issue #100 asks only that the gap be named (`SkippedClass`) instead of
    # refusing the runtime for a class it was always going to receive.
    carries_mcp = bool(mcps) or bool(bundled_recipes)
    carries_skills = bool(frameworks or bundled_artifacts or skills)
    skipped: tuple[SkippedClass, ...] = ()
    if carries_mcp and carries_skills:
        skipped = _skipped_classes_of(runtimes, request.scope)
    elif carries_mcp:
        _refuse_a_runtime_with_no_document(runtimes, request.scope)
    elif carries_skills:
        _refuse_a_runtime_with_no_skills(runtimes)
    landings = places_of(_that_take_skills(runtimes), request.scope, root, environment)
    documents = mcp_places_of(runtimes, request.scope, root, environment)
    # A runtime `_skipped_classes_of` counted as missing one table can still be
    # the only runtime the line named — the whole selected set then has no
    # landing at all for the other class, even though no single runtime was
    # refused for it. `landings`/`documents` empty means nothing to receive
    # that class anywhere, so the class contributes no `Selection` rather than
    # one with nothing in it (`_grouped_selection` indexes the first landing
    # as the canonical, and an empty one has none to index).
    return Plan(
        root=root,
        selections=(
            *(
                _framework_selection(framework, landings, request.scope)
                for framework in frameworks
                if landings
            ),
            *(
                _bundle_selection(
                    bundle,
                    landings,
                    documents,
                    root,
                    sources,
                    secrets if request.scope is Scope.GLOBAL else MappingProxyType({}),
                    request.scope,
                )
                for bundle in bundles
                if landings or documents
            ),
            *(
                _skill_selection(artifact, landings, request.scope)
                for artifact in skills
                if landings
            ),
            *(
                _mcp_selection(
                    recipe,
                    documents,
                    root,
                    sources.get(recipe.name),
                    secrets if request.scope is Scope.GLOBAL else MappingProxyType({}),
                )
                for recipe in mcps
                if documents
            ),
        ),
        skipped=skipped,
    )


def refuse_broken_documents(plan: Plan, scope: Scope) -> None:
    """Refuse before the first byte if a document this plan grafts into is broken.

    Here rather than in `overpower.writing` because of **`--dry-run`**: the
    report has to mirror the exit code of the real run, and a check that only
    the writer ran would let the dry run answer 0 to a line the real one refuses
    with 3. It is also what makes the refusal land before the first byte on a
    line that mixes a copy with a graft — the writer would already have written
    the skills by the time it reached the document.

    It raises rather than answering, unlike `existing_destinations`: a broken
    file has no second reading a terminal could turn into a question.

    It reads **every write** and not every path, because what makes a document
    unusable is the pair (file, root key): a `mcpServers` that is a string
    parses and still has nowhere to receive a server.

    It walks the **landings** rather than `plan.writes` directly, and takes the
    scope, because *broken* also depends on who reads the file: a trailing comma
    is idiomatic in `.vscode/mcp.json` and fatal in `.mcp.json`. Only the landing
    still knows which runtimes read the place — `Plan.writes` flattens that away
    — which is the same walk, for the same reason, that `pending_activation`
    makes.
    """
    for landing in plan.landings:
        tolerates_jsonc = _tolerates_jsonc(landing.readers, scope)
        for write in landing.writes:
            destination = write.destination
            source = write.source
            if (
                isinstance(destination, DocumentKey)
                and isinstance(source, Fragment | Inputs)
                and destination.path.is_file()
            ):
                readable = _readable(destination.path)
                refuse_if_broken(
                    destination.path, readable, source, tolerates_jsonc=tolerates_jsonc
                )


def stored_secrets(plan: Plan, scope: Scope) -> Mapping[str, str]:
    """Every slot value the documents this plan grafts into are **already** carrying.

    ADR 0024: a value that is there is kept and not asked about a second time.
    Kept has to mean *re-written*, not *left alone* — the graft replaces the whole
    server key, so a slot nobody answers for this run is a slot the reference goes
    back over. Reading the old value here and handing it forward as an answer is
    what makes the second `install` of an unchanged line a no-op instead of a
    quiet demotion of the secret to a placeholder.

    **Only where a value could legitimately be** — machine scope, and a dialect
    that reads its slots out of the environment — so a `${input:<id>}` is never
    mistaken for something a person typed, and a project document is never read
    for a secret it is not allowed to hold.

    *Stored* is decided by comparing against the reference this very recipe would
    render into this very document, so no spelling is hard-coded here and the
    three dialects need no branch: what is not the reference is a value, and the
    reference is asked for rather than remembered.

    **Keyed by variable name, and the first document to answer wins.** That is
    the same identity `askable_slots` counts by — two servers wanting
    `GITHUB_TOKEN` are one question — so a name answered by the document one
    runtime already has is a name the next runtime's document receives without a
    second prompt. Both are the machine's own files, and one secret with one
    value on one machine is the fact both halves are reading.
    """
    if scope is not Scope.GLOBAL:
        return {}
    found: dict[str, str] = {}
    for selection in plan.selections:
        for carried in selection.artifacts:
            if not isinstance(carried, Recipe):
                continue
            for landing in selection.landings:
                for name, value in _stored_at(carried, landing, scope).items():
                    found.setdefault(name, value)
    return found


def _stored_at(recipe: Recipe, landing: Landing, scope: Scope) -> Mapping[str, str]:
    """Every slot of `recipe` that `landing`'s document already answers for."""
    document = _document_at(landing.readers, scope)
    if document is None or not expands_from_environment(document.dialect):
        return {}
    config = _server_config(landing.place, document, recipe.name)
    if config is None:
        return {}
    reference = _rendered_server(recipe, document)
    found: dict[str, str] = {}
    for slot in recipe.slots:
        value = slot_value(config, slot)
        if value and value != slot_value(reference, slot):
            found[slot.name] = value
    return found


def _document_at(readers: Sequence[str], scope: Scope) -> McpDocument | None:
    """The document every runtime reading this landing shares, or `None` for a folder.

    One landing is one place and a place is one document row, so the first
    reader that has one answers for all of them — the same fact `_any_document`
    walks, asked for the row instead of for a yes.
    """
    for key in readers:
        document = mcp_document_of(key, scope)
        if document is not None:
            return document
    return None


def _server_config(path: Path, document: McpDocument, name: str) -> Mapping[str, object] | None:
    """The table `name` already occupies in `path`, or `None` if it occupies none.

    Every way of not being there answers the same `None`: no file, unreadable,
    unparseable, a root key that is not a table, or a server of that name that
    was never written. A broken document is **not** refused here — that is
    `refuse_broken_documents`' job and it already ran on this plan; answering
    `None` twice for one file would be a second exit code for one fact.

    **The strict reader, and not the tolerant one `overpower.inspection` uses**,
    which is the one difference between two functions that otherwise walk the
    same shape. `doctor` reads whatever is on the disk, JSONC included, and has
    refused nothing first. This runs *after* `refuse_broken_documents` on the
    same plan, and every row it can reach spells strict JSON — `_stored_at`
    gates on `expands_from_environment`, and the only JSONC-tolerating row in the
    table is the VS Code one that gate excludes. So a file that reaches here and
    does not parse strictly is one the run already refused, and reading it the
    tolerant way would answer about a document Claude Code itself cannot load.
    """
    if not path.is_file():
        return None
    try:
        parsed = loads_json(read_document(path))
    except (OSError, UnreadableDocumentError, ValueError):
        return None
    if not isinstance(parsed, dict):
        return None
    servers = cast("dict[str, object]", parsed).get(document.root_key)
    if not isinstance(servers, dict):
        return None
    config = cast("dict[str, object]", servers).get(name)
    return cast("dict[str, object]", config) if isinstance(config, dict) else None


def _rendered_server(recipe: Recipe, document: McpDocument) -> Mapping[str, object]:
    """What `recipe` looks like in `document` with nothing answered — the reference shape."""
    first, *_ = render(recipe, document)
    return first.value if isinstance(first, Fragment) else {}


def _readable(path: Path) -> str:
    """`path` read, with a denied read named instead of raised as a surprise.

    The write-time twin of this read is already covered — `overpower.writing`
    catches `OSError` and answers *"wrote N of M, stopped here"* — and this is
    the pre-flight one, which had nothing around it. Unguarded, a config the
    process may not read reached the top handler and was reported as a bug in
    the product.
    """
    try:
        return read_document(path)
    except OSError as denied:
        raise UnreadableDocumentError(path, denied) from denied


class PreconditionFailedError(RefusedError):
    """A precondition the recipe declared, that this machine does not meet.

    ADR 0009's axis, applied here: the invocation is correct — the recipe read,
    the precondition understood — and the answer this machine gives is no.
    Fired by `refuse_unmet_preconditions`, before the first byte, for the same
    `--dry-run` reason `refuse_broken_documents` is: a report that skipped this
    check would be a report about a different machine.
    """

    def __init__(self, recipe: str, precondition: Precondition, reason: str) -> None:
        """Name the recipe, the precondition, and why it does not hold."""
        self.recipe = recipe
        self.precondition = precondition
        super().__init__(f"`{recipe}`: precondition `{precondition.check}` failed — {reason}")


def refuse_unmet_preconditions(plan: Plan, variables: Mapping[str, str]) -> None:
    """Refuse before the first byte if any recipe's preconditions are not met here.

    Alongside `refuse_broken_documents` and for the same two reasons: a
    precondition is a fact of the **machine**, checked once per recipe rather
    than once per write, so this walks `selection.artifacts` the way
    `unset_slots` already does rather than `plan.writes` — and it narrows to
    `variables` for the same reason `unset_slots` does: the only machine fact
    any check reads is the environment, so that is the whole of what this
    needs from `Environment`.

    Every check **reads** a fact and never **runs** one — `command_exists`
    walks `PATH` the way `shutil.which` does, and never invokes the command it
    finds. A precondition check that executed anything would be the hole axiom
    1 closes, reopened under the name of a feature.
    """
    for selection in plan.selections:
        for carried in selection.artifacts:
            if not isinstance(carried, Recipe):
                continue
            for precondition in carried.preconditions:
                reason = _unmet_reason(precondition, variables)
                if reason is not None:
                    raise PreconditionFailedError(carried.name, precondition, reason)


def _unmet_reason(precondition: Precondition, variables: Mapping[str, str]) -> str | None:
    """Why `precondition` fails on this machine, or `None` if it holds."""
    match precondition.check:
        case Check.COMMAND_EXISTS:
            found = shutil.which(precondition.value, path=variables.get("PATH"))
            return None if found is not None else f"no `{precondition.value}` on PATH"
        case Check.ENV_SET:
            if precondition.value in variables:
                return None
            return f"`{precondition.value}` is not set in the environment"
        case Check.PATH_EXISTS:
            if Path(precondition.value).exists():
                return None
            return f"`{precondition.value}` does not exist"
        case _ as unreachable:
            assert_never(unreachable)


def pending_activation(plan: Plan, scope: Scope) -> tuple[Path, ...]:
    """Documents whose grafts are born inert until the user approves them.

    ADR 0014: the overpower writes the server and does **not** turn it on, and
    the warning is a requirement rather than a courtesy — without it the product
    ships exactly the failure the research named, a file written, exit 0, and a
    server that never connects with no sign anywhere.

    It answers off the same table that decided the document, so *"where the
    warning is true"* and *"where the file is"* cannot drift apart. Where it is
    not true it says nothing: a warning that appears everywhere is a warning
    nobody reads.
    """
    found = {
        landing.place
        for selection in plan.selections
        for landing in selection.landings
        if any(isinstance(write.destination, DocumentKey) for write in landing.writes)
        and _born_pending(landing.readers, scope)
    }
    return tuple(sorted(found))


def askable_slots(plan: Plan, scope: Scope) -> tuple[str, ...]:
    """Every slot variable this plan would stop and ask a person for (ADR 0024).

    **Two readers, one answer**, which is why it is a function and not a loop
    written twice: `--dry-run` announces *how many* secrets a real run would ask
    about, and the real run walks *which ones*. A count computed apart from the
    walk is a count that can be wrong about the walk, and the report exists to
    describe the run.

    The conditions are the two halves of the rule and nothing else. `scope` is
    the git half — outside the machine scope the document goes to a repository
    and the answer is empty however many slots the plan carries. The dialect half
    is `_lands_where_the_environment_is_read`, shared verbatim with
    `unset_slots`: a target that fills its slots from a vault of its own already
    asks the person itself, and asking twice for one secret is the defect and not
    the feature.

    **Not conditioned on the environment.** A variable that happens to be
    exported in *this* shell is still asked about — it is offered as the default
    instead (`overpower.cli`), because the shell that runs the install is not the
    shell the runtime starts in, and skipping the question on that basis would
    write nothing and claim the configuration was complete.

    Sorted and deduplicated, so two servers wanting one secret are one question.
    """
    if scope is not Scope.GLOBAL or not _lands_where_the_environment_is_read(plan, scope):
        return ()
    return tuple(
        sorted(
            {
                slot.name
                for selection in plan.selections
                for carried in selection.artifacts
                if isinstance(carried, Recipe)
                for slot in carried.slots
            }
        )
    )


def unset_slots(
    plan: Plan, variables: Mapping[str, str], scope: Scope, written: Sequence[str] = ()
) -> tuple[str, ...]:
    """Slot variables this environment does not carry — a warning, never a refusal.

    **The variable has to exist when the runtime starts, not when the overpower
    runs**, so its absence says nothing about the correctness of what was
    written: the file is right either way, and the environment we can read here
    is this shell's, not the editor's.

    It is still said out loud, because of what an absent variable does at the
    other end: measured against a local listener, Claude Code sent
    `Bearer ${NAO_EXISTE}` **literally** on the request, so the server answers
    401 and the cause is a file nobody is looking at.

    **And it is said only where it is true**, which is what `scope` is for. That
    failure is a property of the *dialect* and not of the slot: a
    `${input:<id>}` is filled from a prompt and the OS keychain, so there is no
    variable to be absent and the editor asks. Telling somebody to export a
    variable nothing will read is the same defect as the approval line appearing
    everywhere — a warning nobody can act on, which is a warning nobody reads
    (ADR 0014). Where a plan lands in both kinds of document the warning stands,
    because one of the two really does read the environment.

    Sorted and deduplicated: two servers may need the same variable, and one line
    per variable is what the reader has to act on — the same reading
    `pending_activation` applies to documents.

    `written` is the slots whose **value** went into the document instead of a
    reference (ADR 0024) — empty on every path that existed before the prompt
    did. They drop out because the warning is about a `${VAR}` nothing will
    expand, and there is no `${VAR}` left to expand: telling somebody to export a
    variable already spelled out in the file is a warning nobody can act on,
    which is the same defect ADR 0014 names for the approval line.
    """
    if not _lands_where_the_environment_is_read(plan, scope):
        return ()
    return tuple(
        sorted(
            {
                slot.name
                for selection in plan.selections
                for carried in selection.artifacts
                if isinstance(carried, Recipe)
                for slot in carried.slots
                if slot.name not in variables and slot.name not in written
            }
        )
    )


def _lands_where_the_environment_is_read(plan: Plan, scope: Scope) -> bool:
    """Whether any document this plan grafts into fills its slots from the environment."""
    return any(
        _any_document(
            landing.readers, scope, lambda document: expands_from_environment(document.dialect)
        )
        for selection in plan.selections
        for landing in selection.landings
        if any(isinstance(write.destination, DocumentKey) for write in landing.writes)
    )


def _any_document(
    readers: Sequence[str], scope: Scope, carries: Callable[[McpDocument], bool]
) -> bool:
    """Whether any runtime reading this place lands in a document that `carries`.

    Two questions have this shape, and both are facts of the (runtime, scope)
    pair rather than of the CLI: whether the server is born waiting for a human,
    and whether its slot is read out of the process environment. One walk, so a
    third question arrives as a predicate instead of as a third loop.
    """
    for key in readers:
        document = mcp_document_of(key, scope)
        if document is not None and carries(document):
            return True
    return False


def _born_pending(readers: Sequence[str], scope: Scope) -> bool:
    """Whether any runtime reading this place leaves the server waiting for a human."""
    return _any_document(readers, scope, lambda document: document.born_pending)


def _tolerates_jsonc(readers: Sequence[str], scope: Scope) -> bool:
    """Whether a comment or a trailing comma is legal in the place these runtimes read.

    *Every* and not *any*, which is why this one does not go through
    `_any_document`: a document one runtime forgives and another parses strictly
    is a document the strict one cannot read, so the place is tolerant only when
    nothing reading it is strict. A place no row answers for is strict as well —
    the empty answer has to fall on the side that refuses, because the other
    side of being wrong is a write no runtime ever sees.
    """
    known = [document for key in readers if (document := mcp_document_of(key, scope)) is not None]
    return bool(known) and all(document.tolerates_jsonc for document in known)


def _refuse_a_sourced_recipe_outside_machine_scope(recipes: Sequence[Recipe], scope: Scope) -> None:
    """Refuse the line if any selected recipe with `source:` is asked for outside `--global`.

    Before `_selected_runtimes` and every refusal that follows it: a recipe that
    brings its own clone has nowhere legal to land in project scope regardless
    of which runtime was named, so there is no runtime-shaped question left to
    ask once this one has an answer (ADR 0015).
    """
    if scope is Scope.GLOBAL:
        return
    for recipe in recipes:
        if recipe.source is not None:
            raise SourceRequiresMachineScopeError(recipe.name)


def _refuse_a_runtime_with_no_document(keys: Sequence[str], scope: Scope) -> None:
    """Refuse the line if any selected runtime cannot receive a server in `scope`."""
    for key in keys:
        if mcp_document_of(key, scope) is None:
            raise NoMcpDocumentError(key, scope)


def _refuse_a_runtime_with_no_skills(keys: Sequence[str]) -> None:
    """Refuse the line if any selected runtime has no skills directory at all.

    Filtered by *has a skill destination*, not by membership in
    `RUNTIMES_BY_KEY` (ADR 0018): since `vscode` joined that table with neither
    a project nor a global directory, presence alone stopped proving anything —
    `runtimes_in` made the same move on the screen side, and this is its mirror
    on the refusal side.
    """
    for key in keys:
        runtime = RUNTIMES_BY_KEY.get(key)
        if runtime is None or runtime.project_dir is None:
            raise NoSkillsDestinationError(key)


def _skipped_classes_of(keys: Sequence[str], scope: Scope) -> tuple[SkippedClass, ...]:
    """Every runtime a mixed line carried both classes for, that has a row on only one.

    Called only when the line carries both classes (`plan_for`) — a single
    class still goes through the whole-line refusals above unchanged. Never a
    refusal here: `_selected_runtimes` already turned away any key with no row
    in the union of the two tables for this scope (`RuntimeUnavailableInScopeError`,
    ADR 0009), so a key reaching this loop is missing *at most* one of the two
    — `no_document and no_skills` is a state `_selected_runtimes` has already
    made unreachable, not a case this function has to guard against.

    Filtered by `project_dir is None`, the same reading `_refuse_a_runtime_with_no_skills`
    uses (ADR 0018): `vscode` is a member of `RUNTIMES_BY_KEY` with no destination,
    so membership alone stopped proving a skill row.
    """
    skipped: list[SkippedClass] = []
    for key in keys:
        no_document = mcp_document_of(key, scope) is None
        runtime = RUNTIMES_BY_KEY.get(key)
        no_skills = runtime is None or runtime.project_dir is None
        if no_document:
            skipped.append(SkippedClass(key, MissingClass.MCP))
        elif no_skills:
            skipped.append(SkippedClass(key, MissingClass.SKILLS))
    return tuple(skipped)


def existing_destinations(plan: Plan, request: Request) -> tuple[Path, ...]:
    """Global-scope write destinations already on disk, sorted — a fact, not a verdict.

    Detectable before the first byte — `Path.exists()`, never a write. Global
    scope only, and always empty when `--force` was given: project scope has no
    such question (`overpower.writing` writes unconditionally, by design), and
    `--force` already means "I know, overwrite it" before a caller has anything
    to decide. What used to be decided here — refuse outright — is now the
    caller's call (`overpower.cli._perform`): whether there is a terminal to
    turn this into a question, or `DestinationExistsError` is still the answer,
    https://github.com/ThiagoPanini/overpower/issues/69.

    **The graft class is not asked at all**, and that is a property of the class
    rather than an exemption. What this question protects is equipment that is
    replaced whole — a directory the writer clears and rewrites — and a graft
    replaces nothing: it inserts one key and leaves every other byte of the
    document where it was (ADR 0016), overwriting only an entry carrying the
    same identity, unconditionally and by decision (ADR 0013). Asking here would
    have made the machine documents of
    https://github.com/ThiagoPanini/overpower/issues/81 unusable in the ordinary
    case: `~/.claude.json` exists on every machine that ever ran the runtime, so
    every `--global` graft would have stopped to ask permission to *add* a key.

    **Neither is the clone class**, and for a reason closer to the graft's than
    to the copy's: ADR 0015 already decided reinstalling re-clones
    unconditionally, no cache, no exception — a question this function could
    ask and get answered *"no"* would contradict a decision already made, not
    protect equipment this run might overwrite by mistake.
    """
    if request.scope is not Scope.GLOBAL or request.force:
        return ()
    return tuple(
        sorted(
            {
                write.destination.path
                for write in plan.writes
                if not isinstance(write.destination, DocumentKey)
                and write.mode is not WriteMode.CLONE
                and write.destination.path.exists()
            }
        )
    )


def _framework_selection(
    framework: Framework, places: Mapping[Path, tuple[str, ...]], scope: Scope
) -> Selection:
    """The whole framework — rule 1 — every artifact it carries, in every selected place."""
    return _grouped_selection(framework.name, framework.artifacts, places, scope)


def _bundle_selection(  # noqa: PLR0913, PLR0917 — one landing kind's inputs, then the other's
    bundle: Bundle,
    places: Mapping[Path, tuple[str, ...]],
    documents: Sequence[McpPlace],
    root: Path,
    sources: Mapping[str, Path],
    secrets: Mapping[str, str],
    scope: Scope,
) -> Selection:
    """Exactly what the bundle's manifest names (ADR 0002), split across both landing kinds.

    ADR 0022: a bundle may name a skill and an MCP server in the same manifest,
    so this reaches for both — `_grouped_selection`'s copy landings for the
    artifacts it names, `_mcp_selection`'s graft (and clone) landings for the
    recipes — under the bundle's own name. Each half is all-or-nothing with what
    it is handed, the same guard `plan_for` already applies per class before
    building a `Selection` at all: a half with nowhere to land contributes
    neither a landing nor an entry in `artifacts`, so the screen never promises
    what the write will not do.
    """
    artifacts = tuple(item for item in bundle.artifacts if isinstance(item, Artifact))
    recipes = tuple(item for item in bundle.artifacts if isinstance(item, Recipe))
    copied = (
        _grouped_selection(bundle.name, artifacts, places, scope) if artifacts and places else None
    )
    grafted = (
        tuple(
            landing
            for recipe in recipes
            for landing in _mcp_selection(
                recipe, documents, root, sources.get(recipe.name), secrets
            ).landings
        )
        if recipes and documents
        else ()
    )
    return Selection(
        name=bundle.name,
        artifacts=(
            *(artifacts if copied is not None else ()),
            *(recipes if documents else ()),
        ),
        landings=(*(copied.landings if copied is not None else ()), *grafted),
    )


def _skill_selection(
    artifact: Artifact, places: Mapping[Path, tuple[str, ...]], scope: Scope
) -> Selection:
    """One pool artifact, landing in every selected place."""
    return _grouped_selection(artifact.name, (artifact,), places, scope)


_SOURCE_DIR = (".overpower", "mcp")
"""Where a clone lands under the machine root: `~/.overpower/mcp/<slug>/`.

The same two segments `overpower.remote._LEGACY_MCP_DIR` still names, for a
question that is not this one — there, the address a recipe *used* to be read
from, kept only to refuse it (ADR 0021); here, the address this product writes a
clone to, which ADR 0023 keeps. Two constants and not one shared: they answer
different questions of different modules, and the coincidence of spelling is
what makes sharing them a trap rather than a saving.
"""


def _mcp_selection(
    recipe: Recipe,
    documents: Sequence[McpPlace],
    root: Path,
    cloned: Path | None,
    secrets: Mapping[str, str],
) -> Selection:
    """One MCP server, rendered once per document it lands in.

    Rendering happens **here** and the fragment travels in the plan, so the key
    the screen names and the key the writer inserts are the same value read
    twice — the graft half of *"the writer consumes the plan and nothing beyond
    it"*.

    There is no ladder and no canonical landing: a graft copies nothing, so
    there is nothing for a second place to link to. Every document gets the
    fragment its own dialect asks for.

    `cloned` is the scratch tree `overpower.remote.sources_for` already obtained
    for this recipe, or `None` for a recipe with no `source:`. When it is not
    `None`, the clone is a **second landing** of this same selection — issue #84
    is what the model's *"an artifact may cost more than one write, the second
    possibly outside the repository"* (module docstring) was reserved for — and
    every document's `{source}` resolves to the clone's **destination**, never
    to `cloned` itself: `cloned` is a scratch directory this command's own
    `finally` removes, and a path baked into a committed file must still exist
    tomorrow.
    """
    destination = None if cloned is None else root / Path(*_SOURCE_DIR) / recipe.name
    landings = tuple(_graft_landing(recipe, place, destination, secrets) for place in documents)
    if cloned is None or destination is None:
        return Selection(name=recipe.name, artifacts=(recipe,), landings=landings)
    return Selection(
        name=recipe.name,
        artifacts=(recipe,),
        landings=(_clone_landing(cloned, destination, documents), *landings),
    )


def _clone_landing(cloned: Path, destination: Path, documents: Sequence[McpPlace]) -> Landing:
    """The clone itself: one write, a real copy, counted like any other tree.

    `readers` is the union of every document's own readers — every runtime this
    line asked the server for is a runtime whose rendered fragment points here,
    so every one of them reads what lands at `destination` just as much as it
    reads the document carrying the pointer.
    """
    readers = tuple(dict.fromkeys(reader for place in documents for reader in place.readers))
    return Landing(
        place=destination,
        readers=readers,
        writes=(
            Write(
                source=cloned,
                destination=DirectoryTree(destination),
                mode=WriteMode.CLONE,
                files=_files_in(cloned),
            ),
        ),
    )


def _files_in(tree: Path) -> int:
    """How many files `tree` carries — what the clone's `Write.files` counts."""
    return sum(1 for entry in tree.rglob("*") if entry.is_file())


def _graft_landing(
    recipe: Recipe, place: McpPlace, source: Path | None, secrets: Mapping[str, str]
) -> Landing:
    """The document, everyone who reads it, and every key that lands in it.

    **One landing however many keys**, because a landing is a *place* and the
    keys fall in the same one: a VS Code recipe with a slot writes the server
    under `servers` and the prompt it refers to under `inputs`, and announcing
    two places for one file would say the run touches two.

    The writes are in render order, which is the order the writer performs them,
    so the reference is written before the declaration it points at. Nothing
    depends on that — both are keys of a file nobody has read yet — and it is
    still the order the screen reads best in.

    `source` is the clone's **destination**, threaded through to `render` so
    `{source}` resolves to a path that still exists after this command exits —
    `None` for a recipe with no `source:`, in which recipe the token cannot
    occur at all (`overpower.recipes.SourcelessSubstitutionError`).
    """
    return Landing(
        place=place.path,
        readers=place.readers,
        writes=tuple(
            Write(
                source=graft,
                destination=DocumentKey(place.path, graft.dotted),
                mode=WriteMode.GRAFT,
                # The document is one file however many keys go into it, and the
                # report counts files. The first write is the one that puts it on
                # disk; the rest edit what is already there.
                files=1 if index == 0 else 0,
            )
            for index, graft in enumerate(render(recipe, place.document, source, secrets))
        ),
    )


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
    escada https://github.com/ThiagoPanini/overpower/issues/40 climbs, because
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


def _selected_runtimes(keys: Sequence[str], scope: Scope) -> tuple[str, ...]:
    """The runtime keys named, validated against the closed table and against the scope.

    Two different misses, two different codes. A key outside the table is a typo
    — exit 2, `UnknownRuntimeError`. A key the table has, with no destination of
    **any** class in `scope`, is the scoped sets saying no — exit 3,
    `RuntimeUnavailableInScopeError`, ADR 0009.

    Keys and no longer rows, because a row is a fact of one class and a key is
    what the person typed: `vscode` has an MCP document and no skills directory,
    and answering with a `Runtime` would have meant either inventing one or
    refusing a target the product renders for. Which class each key can actually
    receive is asked **per class**, by the two refusals `plan_for` fires only for
    the classes the line carries.
    """
    if not keys:
        raise NoRuntimeSelectedError
    known = known_runtimes()
    reachable = {runtime.key for runtime in runtimes_in(scope)} | set(mcp_runtimes_in(scope))
    chosen: set[str] = set()
    for key in keys:
        if key not in known:
            raise UnknownRuntimeError(key, known)
        if key not in reachable:
            raise RuntimeUnavailableInScopeError(key, scope)
        chosen.add(key)
    # Back into table order: the order the plan lists places in is the order the
    # writer performs them, and the table is the only order both ends share.
    return tuple(key for key in known if key in chosen)


def _that_take_skills(keys: Sequence[str]) -> tuple[Runtime, ...]:
    """The rows of the skills table these keys name, in the order they were given.

    A key with no skill destination is dropped rather than refused, and the
    drop is not a silent default: `_refuse_a_runtime_with_no_skills` has
    already run whenever the line carries anything of the copy class, so what
    reaches here without one is a graft-only target on a line that asked for no
    skill — and a target with nothing to receive contributes no landing.

    Filtered by `project_dir is not None` and not by membership in
    `RUNTIMES_BY_KEY` (ADR 0018): `vscode` is a member with no destination, and
    handing its row to `places_of` would ask `resolve_project_dir` for a path
    the row does not have.
    """
    return tuple(
        runtime
        for key in keys
        if (runtime := RUNTIMES_BY_KEY.get(key)) is not None and runtime.project_dir is not None
    )


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


def _selected_mcps(names: Sequence[str], catalog: Catalog) -> tuple[Recipe, ...]:
    """The MCP recipes named, deduplicated, in the order they were typed.

    Lookup goes through `Catalog.mcp`, the same closed-list error the other
    three units answer with — one place names what the catalog does not have.
    """
    chosen: dict[str, Recipe] = {}
    for name in names:
        chosen[name] = catalog.mcp(name)
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
