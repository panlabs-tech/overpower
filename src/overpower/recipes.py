"""A subtree of the manifest in, a `Recipe` out: the whole of a recipe's validation.

A **recipe** is the logical declaration of an MCP server — transport, command or
URL, and (from the slices after this one) slots, preconditions and source. It
**never lands**: what lands is the fragment rendered out of it, which is why it
lives under the root that never lands and not under `content/`, whose invariant
is *100% lands* (`docs/agents/domain.md`).

**One file, one format, one reader** (ADR 0021). A recipe is an entry of the
`mcp:` key of the one written file — `catalog/catalog.yaml` inside the wheel,
`.overpower.yaml` at the root of a homemade repository — so this module opens
nothing: `overpower.written` decodes the document once and hands each entry down
here as an already-parsed subtree. That is what makes *the same reader* a fact of
the code rather than a promise: there is one decoder, one contract, and no
second validator that could admit on one side what the other refuses.

**A recipe that gets past this module is a recipe that renders.** Every rule the
contract has is checked here — the closed set of transports, the fields each
transport admits, and the command a `source:` address derives — so
`overpower.rendering` is a total function over what this returns rather than a
second validator that could disagree with the first.

The vocabulary of this version is **`description`, `transport`, `server:`,
`slots:`, `preconditions:`, `instructions` and `source:`**
(https://github.com/ThiagoPanini/overpower/issues/76, /78, /82 and /84). A
recipe that declares a field outside this set is refused **by name** rather
than read half-way: silent partial acceptance is exactly the class of defect
the graft exists not to commit, and it is the reason the unknown-field check
is a closed allowlist rather than a `get` per known key.

**A recipe carries a secret and a configuration, and the difference is the whole
point**: a slot is what the overpower **refuses to write**, `server.env:` is
what it writes because it can. The distinction came from a measured server —
`COOLIFY_BASE_URL` is the address of a panel, not a secret, and a schema that
could only hold slots would never write it, bringing the server up not knowing
where to talk. It is the same line the official MCP registry draws with
`isSecret`.

**What arrives is `object`, and that is a tripwire rather than a style** — the
same discipline `overpower.written` runs on, measured in
https://github.com/ThiagoPanini/overpower/issues/2: pyright strict has a blind
spot on `Any`, so `return data["name"]` inside a `-> str` function type-checks
and blows up at runtime. The subtree crosses in as `object` and every field is
narrowed in the open, on this side of the boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import TYPE_CHECKING, assert_never, cast

from overpower.errors import OverpowerError, RefusedError

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from pathlib import Path

MCP_KEY = "mcp"
"""The key of the written file the recipes live under, and the slug is the entry's name.

Declared here rather than in `overpower.written` because it is the recipe's own
address: the module that owns the contract owns where the contract is written,
and the assembler of the document imports the name from it. It is also what every
message inside a recipe is prefixed with — one file now holds several recipes, so
`transport` alone would cost the reader a bisection to find which one.
"""

DESCRIPTION_KEY = "description"
TRANSPORT_KEY = "transport"
SERVER_KEY = "server"
SLOTS_KEY = "slots"
PRECONDITIONS_KEY = "preconditions"
INSTRUCTIONS_KEY = "instructions"
SOURCE_KEY = "source"

_RECIPE_KEYS = frozenset(
    {
        DESCRIPTION_KEY,
        TRANSPORT_KEY,
        SERVER_KEY,
        SLOTS_KEY,
        PRECONDITIONS_KEY,
        INSTRUCTIONS_KEY,
        SOURCE_KEY,
    }
)
"""The closed set of top-level keys this version implements."""

_NAME_FIELD = "name"
_ROLE_FIELD = "role"
_HEADER_FIELD = "header"

_SLOT_KEYS = frozenset({_NAME_FIELD, _ROLE_FIELD, _HEADER_FIELD})
"""What a slot is made of: a variable, a role, and — for one role — a header."""

_CHECK_FIELD = "check"
_VALUE_FIELD = "value"

_PRECONDITION_KEYS = frozenset({_CHECK_FIELD, _VALUE_FIELD})
"""What a precondition is made of: which check, and what it checks for."""

_GIT_FIELD = "git"
_REF_FIELD = "ref"
_RUNNER_FIELD = "runner"
_ENTRYPOINT_FIELD = "entrypoint"

_SOURCE_KEYS = frozenset({_GIT_FIELD, _REF_FIELD, _RUNNER_FIELD, _ENTRYPOINT_FIELD})
"""What `source:` is made of: the repository, the ref pinned to it, the runner
that resolves it, and the entrypoint the runner launches (ADR 0023).

`ref` has no default: measured against a real remote, `npx` with no ref ran the
HEAD of a repository that has a tag — a server that changes behaviour with
nobody having changed anything, in a version written nowhere. Declaring it a
plain field and never a default is what makes that impossible to reach.
"""


class Runner(StrEnum):
    """What resolves a `source:` address into a running process — closed at two.

    Each member is a fetch-and-run tool this product already trusts to install
    nothing itself (axiom 1 admits no script from a recipe): `uvx` and `npx`
    both fetch the entrypoint at the pinned `ref` and run it, and neither is a
    general-purpose installer this recipe could smuggle a second command past.
    A third member is one row in this table and one render branch, never a
    field a recipe could spell freely — the hole a free-form `command` on a
    federated recipe would reopen (ADR 0023's second considered option).
    """

    UVX = "uvx"
    NPX = "npx"


@dataclass(frozen=True)
class Source:
    """The address of code a server's process is resolved from, never cloned.

    Fully static: every field here is a string the recipe declared, so the
    command it renders to needs nothing this reader does not already have —
    unlike the clone ADR 0015 drew and ADR 0023 replaced, no scope, no runtime
    and no disk decide what it says.
    """

    git: str
    ref: str
    runner: Runner
    entrypoint: str


NO_ENVIRONMENT: Mapping[str, str] = MappingProxyType({})
"""The default `server.env`: empty, and immutable so it can be one value.

A `field(default_factory=dict)` would answer the same thing and cost the
reader a mutable default to reason about — this is a frozen value class, and
the empty case is a constant.
"""

_STDIO_KEYS = frozenset({"command", "args", "env"})
_SOURCED_STDIO_KEYS = frozenset({"args", "env"})
"""What `server:` admits when `source:` is declared — `command` is derived from it."""

_HTTP_KEYS = frozenset({"url"})


class Transport(StrEnum):
    """How a client talks to the server, and the set is closed at two.

    The current revision of the MCP spec defines exactly these two bindings.
    `sse` was formally deprecated in `2026-07-28` (SEP-2596) and `ws` exists in
    one target only — from whose own listing it then disappears — so both are
    refused **at the recipe**, by name. The reason refusal happens here and not
    at the target is measured: `type = "sse"` in the Codex config is an unknown
    field, silently swallowed, and the server connects as streamable HTTP with
    no message and no exit code (`docs/research/mcp-config-formats.md`). A
    target that will not refuse is a target we cannot let reach the question.
    """

    STDIO = "stdio"
    HTTP = "http"


class Role(StrEnum):
    """What a secret *does* for the server, which is all a recipe may say about it.

    Never the spelling of any target: measured, the same name is written
    `${VAR}`, `${input:<id>}` and `${env:VAR}` across the three targets of this
    spec, and one of them has no interpolation at all — so a recipe that carried
    a spelling would be right once and silently wrong twice
    (`docs/research/mcp-config-formats.md`).

    The set is closed at three, and each member pairs with exactly one transport:
    a process gets a variable, a request gets a header. `bearer` exists as its
    own member rather than as a `header` whose value happens to start with the
    word: it is the role that lets a target which assembles the header itself —
    Codex's `bearer_token_env_var` — be served from this same recipe with **no
    new field**.
    """

    ENV = "env"
    """A variable in the environment of the process the client launches."""

    HEADER = "header"
    """A header of the request the client makes, named by the recipe."""

    BEARER = "bearer"
    """`Authorization: Bearer <secret>`, assembled by the renderer."""


class Check(StrEnum):
    """A machine fact the overpower reads for itself, and the set is closed at three.

    This is the whole of what a federated recipe may ask for: existence of a
    command on `PATH`, of a variable in the environment, of a path on disk.
    Every member is answered by **reading**, never by **running** — `command_exists`
    walks `PATH` the way `shutil.which` does and never invokes what it finds — and
    that is not a style choice: axiom 1 admits no script from a recipe, and a
    vocabulary that could grow a member which executes would be the remote-code
    hole wearing the name of a feature. `install --mcp x --from <url>` running
    code out of that repository would be arbitrary remote execution behind a
    one-liner, and nothing here does that, not even behind `--yes`.
    """

    COMMAND_EXISTS = "command_exists"
    """Whether a name resolves on `PATH` — the shape almost every stdio server needs."""

    ENV_SET = "env_set"
    """Whether a variable is present in the environment the overpower runs in."""

    PATH_EXISTS = "path_exists"
    """Whether a path is present on disk — a socket, a config file, a binary."""


@dataclass(frozen=True)
class Precondition:
    """One fact about the machine the recipe requires before it is written.

    `value` is what the check reads — a command's name, a variable's name, a
    path — and never a value read *from* the machine: nothing a precondition
    finds travels back into the recipe or the rendered fragment.
    """

    check: Check
    value: str


AUTHORIZATION = "Authorization"
"""The header a `bearer` slot fills, and a fact of the scheme rather than of a target.

It lives here and not in the renderer because the **reader** needs it: two
`bearer` slots fill this one header, and catching that is what keeps a secret
from disappearing into a table. How the header is *written* — the word `Bearer`
in Claude Code, a `bearer_token_env_var` field in Codex — stays the renderer's.
"""


def input_id(name: str) -> str:
    """`GIT_TOKEN` → `git-token`, the identifier shape the measured files use.

    Derived from the slot name and never stored beside it, so the recipe carries
    one name for one secret: two recipes that need `GITHUB_TOKEN` derive the same
    id, land on the same entry, and the person is asked once.

    **It lives here for the reason `AUTHORIZATION` does**, and it moved here for
    exactly that reason: the derivation is not injective — it lowercases and
    folds `_` to `-` — so two slot names can reach one identifier, and the
    entries are replaced by it. The renderer building that list would keep the
    last and fill both references with it. Only the **reader** can catch that,
    because only the reader sees all the slots at once.

    A target's *spelling* is still the renderer's — `${input:<id>}` is written
    there, and nothing here knows the syntax that wraps this string.
    """
    return name.lower().replace("_", "-")


def carrier_of(role: Role) -> Transport:
    """The transport that has somewhere to put a secret with this role.

    One implementation of the pairing, so the refusal and the message it prints
    cannot disagree, and a fourth role is a hole the type checker points at
    rather than two conditions somebody has to remember to edit together.

    A server reached over HTTP launches no process, so it has no environment to
    receive a variable; a server launched as a process makes no request, so it
    has no header to carry one. Every measured target agrees, because there is
    nothing here for them to disagree about.
    """
    match role:
        case Role.ENV:
            return Transport.STDIO
        case Role.HEADER | Role.BEARER:
            return Transport.HTTP
        case _ as unreachable:
            assert_never(unreachable)


@dataclass(frozen=True)
class EnvSlot:
    """A secret the server reads out of its own environment."""

    name: str


@dataclass(frozen=True)
class HeaderSlot:
    """A secret that travels in a header the recipe names.

    Two names, and only one of them is the variable: `header` is what goes on the
    wire, `name` is what holds the value. Collapsing them would work for exactly
    the servers whose header happens to be spelled like a variable.
    """

    name: str
    header: str


@dataclass(frozen=True)
class BearerSlot:
    """A secret the renderer turns into `Authorization: Bearer <secret>`.

    The word `Bearer` never appears in a recipe — it is a fact of the scheme and
    not of any one server, and keeping it here is what makes the role portable to
    a target that spells the same intent with a field instead of a string.
    """

    name: str


Slot = EnvSlot | HeaderSlot | BearerSlot
"""The place of a secret in a recipe: a name, and what that name is for.

Three dataclasses rather than one with a role field and an optional header, for
the same reason `Server` is two: a value that could spell *header without a
header* would make the renderer re-validate what the reader already decided.
"""


def role_of(slot: Slot) -> Role:
    """The role a slot was declared with, read back off the shape it became.

    The reader spends the word: `role = "env"` becomes an `EnvSlot`, and after
    that nothing carries the spelling. A screen that has to say *what secrets to
    arrange before installing* needs it back, and it is recovered here — beside
    `carrier_of`, on the module that owns the shape — so that a fourth slot is a
    hole the type checker points at rather than a `match` somewhere else that
    quietly answers nothing for it.
    """
    match slot:
        case EnvSlot():
            return Role.ENV
        case HeaderSlot():
            return Role.HEADER
        case BearerSlot():
            return Role.BEARER
        case _ as unreachable:
            assert_never(unreachable)


@dataclass(frozen=True)
class StdioServer:
    """A server the client launches: a command, its arguments and its environment.

    `env` carries **values that are not secret**, literally — the address of a
    panel is not a secret, and treating it as a slot would mean never writing it,
    so the server would come up not knowing where to talk. What the overpower
    refuses to write is a slot (`Role`), and the two never name the same
    variable: the reader refuses a recipe that says both about one name.
    """

    command: str
    args: tuple[str, ...] = ()
    env: Mapping[str, str] = NO_ENVIRONMENT


@dataclass(frozen=True)
class HttpServer:
    """A server the client connects to over streamable HTTP."""

    url: str


Server = StdioServer | HttpServer
"""What the recipe declares, in the shape the transport it declared admits.

Two dataclasses rather than one with optional halves: `command` and `url` are
not alternatives of one field, they are two different servers, and a value that
can spell *neither* or *both* is a value the renderer would have to re-validate.
"""


@dataclass(frozen=True)
class Recipe:
    """One MCP server, declared logically — never in the spelling of any target.

    `name` is the entry's key under `mcp:` and never a field of its own, which
    is rule 8 (ADR 0006) said in the one place a recipe has instead of a tree: a
    recipe has no folder to take a name from — it never lands — so the slug
    `--mcp` names is where the declaration sits, not something declared twice.

    `path` is the written file the entry came out of, carried only so a message
    can name it. Two recipes now share one file, which is why every key in a
    message is prefixed `mcp.<slug>.`.
    """

    name: str
    path: Path
    description: str
    server: Server
    slots: tuple[Slot, ...] = ()
    """The secrets this server needs, in declaration order, and never their values.

    Order is the recipe's, so the rendered fragment is a function of the file and
    of nothing else — two recipes that declare the same slots in a different
    order are two different files and produce two different documents, which is
    what makes the diff of a re-install empty.
    """

    preconditions: tuple[Precondition, ...] = ()
    """What this machine must already have, checked before the first byte is written."""

    instructions: str | None = None
    """Prose the author left for what the overpower cannot automate — asking a
    credential, naming who on the team holds it. `None` when the recipe has none."""

    source: Source | None = None
    """The address of code this server's process resolves itself from, or `None`.

    Its presence is what already decided `server` (ADR 0023): `_server` derives
    `command` and the leading `args` from it rather than reading them off the
    document, because `runner`, `git`, `ref` and `entrypoint` are the whole of
    what `uvx --from git+…` or `npx --package git+…` needs, and every one of
    them is already here — no scope, no runtime and no disk get a say.
    """

    @property
    def transport(self) -> Transport:
        """The transport this recipe's server speaks, recovered from its shape.

        Derived rather than stored, so the two cannot disagree: the reader
        already refused every server whose fields did not match its declared
        transport, and a second copy of the answer would be a second thing to
        keep true.
        """
        match self.server:
            case StdioServer():
                return Transport.STDIO
            case HttpServer():
                return Transport.HTTP
            case _ as unreachable:
                assert_never(unreachable)


class MalformedRecipeError(OverpowerError):
    """The document parsed as YAML and this entry of it is not shaped like a recipe.

    It names the file **and the field**, because a recipe is read by the person
    who wrote it — the curator here, the author of a federated one later — and
    *"malformed"* without the field is a message that costs a bisection.
    """

    def __init__(self, path: Path, key: str, expected: str) -> None:
        """Name the file, the key, and what that key should have been."""
        self.path = path
        self.key = key
        super().__init__(f"{path}: `{key}` should be {expected}")


class UnknownRecipeFieldError(OverpowerError):
    """A field this version of the recipe vocabulary does not implement.

    Refused rather than ignored, and that is the whole position: a recipe that
    declares a slot this version cannot render would otherwise install a server
    with the secret **missing**, exit 0, and fail at runtime far from the cause.
    """

    def __init__(self, path: Path, key: str, known: Iterable[str]) -> None:
        """Name the field that has no reader, and the whole set that does."""
        self.path = path
        self.key = key
        listed = ", ".join(sorted(known))
        super().__init__(f"{path}: `{key}` is not a field this version reads; the set is: {listed}")


class ForbiddenTransportError(RefusedError):
    """A transport outside the closed set — exit 3, and the transport is named.

    Exit **3** and not 2: nothing about the invocation is wrong, the product
    read the recipe, computed the answer, and the answer is no. It is the code
    the spec of the graft assigns to *"transporte proibido na receita"*.
    """

    def __init__(self, path: Path, key: str, transport: str) -> None:
        """Name the recipe, the transport it declared, and the two that exist."""
        self.path = path
        self.key = key
        self.transport = transport
        allowed = ", ".join(sorted(member.value for member in Transport))
        super().__init__(
            f"{path}: `{key}` is `{transport}`, which is not a transport this product writes; "
            f"the set is: {allowed}"
        )


class ForbiddenRunnerError(RefusedError):
    """A `source.runner` outside the closed set — exit 3, and the runner is named.

    `_transport`'s own axis, moved to the field ADR 0023 gave it: the value is
    well-formed, the product read it, computed the answer, and the answer is no
    — a runner outside `uvx`/`npx` is not this reader's to invent a render for.
    """

    def __init__(self, path: Path, key: str, runner: str) -> None:
        """Name the recipe, the runner it declared, and the two that exist."""
        self.path = path
        self.key = key
        self.runner = runner
        allowed = ", ".join(sorted(member.value for member in Runner))
        super().__init__(
            f"{path}: `{key}` is `{runner}`, which is not a runner this product resolves; "
            f"the set is: {allowed}"
        )


class DerivedFieldDeclaredError(OverpowerError):
    """A field `source:` already determines, declared anyway.

    `transport`, `server.command` and the runner's own `command_exists`
    precondition are the runner said twice (ADR 0023): `source.runner` already
    fixes all three, so a value declared here could only ever agree with it or
    silently drift from it the day one of the two is edited alone. Refused
    before either becomes possible — rule 4, *what is derivable is derived,
    never declared*.
    """

    def __init__(self, path: Path, key: str, derived_from: str) -> None:
        """Name the recipe, the field that must not be declared, and what derives it."""
        self.path = path
        self.key = key
        super().__init__(
            f"{path}: `{key}` is derived from `{derived_from}` and must not be declared"
        )


class UnknownSlotRoleError(OverpowerError):
    """A slot role outside the closed set of three.

    Malformed and not refused (`ForbiddenTransportError`), and the axis is
    whether the value names something real: `sse` **is** a transport, one this
    product declines to write, so the answer is *no* and the code is 3. A role
    called `secret` is not a role at all — it is a typo in a file, and the fix is
    a line, not a decision.

    Ignoring it would be the worst of the three answers: the slot would vanish,
    the server would install without its secret, and the failure would arrive at
    runtime as a 401 far from the file that caused it.
    """

    def __init__(self, path: Path, key: str, role: str) -> None:
        """Name the slot, the role it declared, and the three that exist."""
        self.path = path
        self.key = key
        self.role = role
        listed = ", ".join(sorted(member.value for member in Role))
        super().__init__(f"{path}: `{key}` is `{role}`, which is no role; the set is: {listed}")


class UnknownPreconditionCheckError(OverpowerError):
    """A precondition `check` outside the closed set of three the overpower implements.

    Malformed and not refused (`ForbiddenTransportError`'s axis): the value does
    not name a real check, so it is a typo in a file rather than a requirement
    this product declines to verify. Ignoring it would be the worst answer —
    the author would believe a requirement is declared when nothing checks it,
    and the server would fail at runtime with no line to point at.
    """

    def __init__(self, path: Path, key: str, check: str) -> None:
        """Name the precondition, the check it declared, and the three that exist."""
        self.path = path
        self.key = key
        self.check = check
        listed = ", ".join(sorted(member.value for member in Check))
        super().__init__(f"{path}: `{key}` is `{check}`, which is no check; the set is: {listed}")


class CollidingSlotError(OverpowerError):
    """Two declarations of one place, where the renderer could only keep one.

    The place, never the name: two `bearer` slots carry two different variables
    and fill the **same** header, and a table built out of them would silently
    keep the last. So would a slot whose variable `server.env` already writes —
    there the loser is either *the address never lands* or *the secret does*.

    Refused here so that the renderer has no such branch at all. Every other
    resolution of the contradiction is a choice made on the author's behalf, at
    exit 0, in a file they will not read again.
    """

    def __init__(self, path: Path, key: str, place: str, held: str) -> None:
        """Name the slot, what it would fill, and who already fills it."""
        self.path = path
        self.key = key
        self.place = place
        super().__init__(f"{path}: `{key}` fills `{place}`, and {held} already does")


class MismatchedSlotRoleError(OverpowerError):
    """A role the declared transport has nowhere to put.

    The pairing is a fact of the **transport** and not of any target: a server
    reached over HTTP launches no process, so it has no environment to receive a
    variable; a server launched as a process makes no request, so it has no
    header to carry one. Every measured target agrees, because there is nothing
    for them to disagree about (`docs/research/mcp-config-formats.md`).

    So it is caught here rather than in the renderer, which would otherwise have
    to answer what to do with a secret that has nowhere to go — and the only
    answers available there are *drop it in silence* or *be a second validator
    that can disagree with the first*.
    """

    def __init__(self, path: Path, key: str, role: Role, transport: Transport) -> None:
        """Name the slot, the role, the transport, and which transport the role wants."""
        self.path = path
        self.key = key
        self.role = role
        self.transport = transport
        wanted = carrier_of(role)
        super().__init__(
            f"{path}: `{key}` is `{role}`, and a `{transport}` server has nowhere to carry it; "
            f"the role `{role}` needs transport `{wanted}`"
        )


def recipe_from(path: Path, name: str, value: object) -> Recipe:
    """The entry `mcp.<name>` of the document at `path`, whole, or the named error.

    `value` is the already-decoded subtree, because the decoding happened once
    for the whole file in `overpower.written`. `path` and `name` travel only so
    that a message can say *which file* and *which recipe* — the two things the
    reader of the message needs before the field is any use to them.
    """
    at = f"{MCP_KEY}.{name}"
    document = _table(path, at, value, "a table")
    _known(path, f"{at}.", document, _RECIPE_KEYS)
    source = _source(path, at, document)
    transport = _transport(path, at, document, source=source)
    server = _server(path, at, transport, document.get(SERVER_KEY), source=source)
    return Recipe(
        name=name,
        path=path,
        description=_text(path, f"{at}.{DESCRIPTION_KEY}", document.get(DESCRIPTION_KEY)),
        server=server,
        slots=_slots(path, at, transport, server, document.get(SLOTS_KEY, [])),
        preconditions=_preconditions(path, at, document.get(PRECONDITIONS_KEY, []), source=source),
        instructions=_instructions(path, at, document),
        source=source,
    )


def _source(path: Path, at: str, document: Mapping[str, object]) -> Source | None:
    """`source:`, or `None` when the recipe brings no code of its own to resolve.

    **Absent, not empty**, and the format is what makes the difference sayable.
    YAML answers `None` to a key written with nothing under it, so `source:`
    alone on a line is a declaration somebody started and did not finish — it
    falls through to the refusal that names the field, instead of quietly
    meaning *no source at all*. TOML had no null and could not tell the two
    apart; reading the emptier one as absence would be exactly the silent
    partial acceptance this module exists to refuse.
    """
    if SOURCE_KEY not in document:
        return None
    key = f"{at}.{SOURCE_KEY}"
    table = _table(path, key, document[SOURCE_KEY], "a table")
    _known(path, f"{key}.", table, _SOURCE_KEYS)
    return Source(
        git=_text(path, f"{key}.{_GIT_FIELD}", table.get(_GIT_FIELD)),
        ref=_text(path, f"{key}.{_REF_FIELD}", table.get(_REF_FIELD)),
        runner=_runner(path, f"{key}.{_RUNNER_FIELD}", table.get(_RUNNER_FIELD)),
        entrypoint=_text(path, f"{key}.{_ENTRYPOINT_FIELD}", table.get(_ENTRYPOINT_FIELD)),
    )


def _runner(path: Path, key: str, value: object) -> Runner:
    """The declared runner, as a member of the closed set — `_transport`'s own axis."""
    if not isinstance(value, str):
        raise MalformedRecipeError(path, key, "a string")
    if value not in {member.value for member in Runner}:
        raise ForbiddenRunnerError(path, key, value)
    return Runner(value)


def _transport(
    path: Path, at: str, document: Mapping[str, object], *, source: Source | None
) -> Transport:
    """The declared transport, as a member of the closed set — or the one `source` derives.

    A recipe with `source:` never declares this at all: `source.runner` already
    fixes it at stdio (ADR 0023) — a server a runner resolves and launches has
    no other shape to take — so a value here could only ever repeat that or
    drift from it the day one of the two is edited alone.
    """
    key = f"{at}.{TRANSPORT_KEY}"
    if source is not None:
        if TRANSPORT_KEY in document:
            raise DerivedFieldDeclaredError(path, key, f"{at}.{SOURCE_KEY}.{_RUNNER_FIELD}")
        return Transport.STDIO
    value = document.get(TRANSPORT_KEY)
    if not isinstance(value, str):
        raise MalformedRecipeError(path, key, "a string")
    if value not in {member.value for member in Transport}:
        raise ForbiddenTransportError(path, key, value)
    return Transport(value)


def _sourced_command(source: Source) -> tuple[str, tuple[str, ...]]:
    """`(runner, leading args)` — the address `source` names, resolved by its own runner.

    Measured in ADR 0023: `uvx` and `npx` agree on fetching `git+<url>` at a
    pinned ref and disagree on how the ref is spelled onto it — `@ref` against
    `#ref` — which is the one thing a third runner would bring its own branch
    for, and the whole reason this is a `match` and not one shared template.
    """
    match source.runner:
        case Runner.UVX:
            return "uvx", ("--from", f"git+{source.git}@{source.ref}", source.entrypoint)
        case Runner.NPX:
            return "npx", (
                "--yes",
                "--package",
                f"git+{source.git}#{source.ref}",
                source.entrypoint,
            )
        case _ as unreachable:
            assert_never(unreachable)


def _server(
    path: Path, at: str, transport: Transport, value: object, *, source: Source | None
) -> Server:
    """The `server:` table, read in the shape its transport admits.

    The transport decides which fields exist, so a `url` under `stdio` is an
    unknown field rather than a field with a wrong value — which is what makes
    the message point at the line that has to change.

    A sourced recipe may omit `server:` entirely — ADR 0023's own examples do,
    since `args` and `env` are the only fields it still declares and a recipe
    with neither has nothing left to say there.
    """
    key = f"{at}.{SERVER_KEY}"
    table = {} if source is not None and value is None else _table(path, key, value, "a table")
    match transport:
        case Transport.STDIO:
            if source is not None:
                if "command" in table:
                    raise DerivedFieldDeclaredError(
                        path, f"{key}.command", f"{at}.{SOURCE_KEY}.{_RUNNER_FIELD}"
                    )
                _known(path, f"{key}.", table, _SOURCED_STDIO_KEYS)
                command, leading = _sourced_command(source)
                declared = _strings(path, f"{key}.args", table.get("args", []))
                return StdioServer(
                    command=command,
                    args=(*leading, *declared),
                    env=_environment(path, f"{key}.env", table.get("env", {})),
                )
            _known(path, f"{key}.", table, _STDIO_KEYS)
            return StdioServer(
                command=_text(path, f"{key}.command", table.get("command")),
                args=_strings(path, f"{key}.args", table.get("args", [])),
                env=_environment(path, f"{key}.env", table.get("env", {})),
            )
        case Transport.HTTP:
            _known(path, f"{key}.", table, _HTTP_KEYS)
            return HttpServer(url=_text(path, f"{key}.url", table.get("url")))
        case _ as unreachable:
            assert_never(unreachable)


def _slots(
    path: Path, at: str, transport: Transport, server: Server, value: object
) -> tuple[Slot, ...]:
    """`slots:`, each one read whole, and no two of them filling one place.

    **Uniqueness is of the place a slot fills, never of the name it carries**,
    and the difference is the whole reason this check exists: two `bearer` slots
    carry different variables and fill the *same* header, so a renderer building
    a table would keep one of them and drop the other at exit 0 — a secret gone
    from a file nobody re-reads. `server.env` joins the same comparison,
    because a literal and a slot end up as keys of one table too.

    **A slot occupies two places, not one**, and the second is the prompt. One
    measured target declares its prompts in a list beside the servers and refers
    to them by `input_id` of the name — a derivation that is not injective — so
    two slots filling two *different* headers can still reach one prompt and
    overwrite each other. That collision is invisible to `_filled`, which is
    right about the places and blind to the names, so it is caught beside it.
    """
    if not isinstance(value, list):
        raise MalformedRecipeError(path, f"{at}.{SLOTS_KEY}", "a list of tables")
    written = server.env if isinstance(server, StdioServer) else NO_ENVIRONMENT
    # A literal fills the variable it names, and only a stdio server has any —
    # so this is the whole of the `server.env` side of the comparison.
    taken = dict.fromkeys(written, f"`{SERVER_KEY}.env`")
    slots: list[Slot] = []
    # A second namespace and not a second entry in `taken`: a prompt identifier
    # and a variable name are different places that happen to be strings, and
    # one map would refuse a recipe whose variable spells another's prompt id.
    prompted: dict[str, tuple[str, str]] = {}
    for index, entry in enumerate(cast("list[object]", value)):
        key = f"{at}.{SLOTS_KEY}[{index}]"
        slot = _slot(path, key, transport, entry)
        place = _filled(slot)
        held = taken.get(place)
        if held is not None:
            raise CollidingSlotError(path, key, place, held)
        prompt = input_id(slot.name)
        asked = prompted.get(prompt)
        # The **same** name reaching one prompt is the point of deriving it: one
        # secret, asked once, filling both places. Only two *different* names
        # reaching one prompt lose something — the second declaration replaces
        # the first, and the prompt then describes one of the two.
        if asked is not None and asked[0] != slot.name:
            raise CollidingSlotError(path, key, prompt, asked[1])
        taken[place] = key
        prompted[prompt] = (slot.name, key)
        slots.append(slot)
    return tuple(slots)


def _filled(slot: Slot) -> str:
    """What a slot occupies in the rendered server — the thing two of them can share.

    A variable for an `env` slot, a header for the two roles that travel in
    one. `Authorization` is the answer for `bearer` because that is a fact of
    the **scheme** and not of a target: every target that has the role at all
    fills that header with it, including the one that assembles it from a field.

    Compared case-insensitively for the header roles, because HTTP field names
    are case-insensitive (RFC 9110 §5.1) — `authorization` and `Authorization`
    are one header, and a comparison that missed that would let the collision
    through in the one spelling somebody would actually use to sneak past it.
    """
    match slot:
        case EnvSlot(name):
            return name
        case HeaderSlot(_, header):
            return header.lower()
        case BearerSlot():
            return AUTHORIZATION.lower()
        case _ as unreachable:
            assert_never(unreachable)


def _slot(path: Path, key: str, transport: Transport, value: object) -> Slot:
    """One slot: the variable that holds the secret, and what that secret is for."""
    table = _table(path, key, value, "a table")
    _known(path, f"{key}.", table, _SLOT_KEYS)
    name = _text(path, f"{key}.{_NAME_FIELD}", table.get(_NAME_FIELD))
    role = _role(path, f"{key}.{_ROLE_FIELD}", transport, table.get(_ROLE_FIELD))
    header = table.get(_HEADER_FIELD)
    if role is not Role.HEADER and header is not None:
        raise MalformedRecipeError(
            path, f"{key}.{_HEADER_FIELD}", f"absent: only the role `{Role.HEADER}` names one"
        )
    match role:
        case Role.ENV:
            return EnvSlot(name=name)
        case Role.BEARER:
            return BearerSlot(name=name)
        case Role.HEADER:
            return HeaderSlot(name=name, header=_text(path, f"{key}.{_HEADER_FIELD}", header))
        case _ as unreachable:
            assert_never(unreachable)


def _role(path: Path, key: str, transport: Transport, value: object) -> Role:
    """The declared role, as a member of the closed set the transport can carry.

    Missing and *absent* are answered before *unknown*: `role = ""` is a line
    nobody finished writing, and telling its author that the empty string is no
    role would be true and useless.
    """
    declared = _text(path, key, value)
    if declared not in {member.value for member in Role}:
        raise UnknownSlotRoleError(path, key, declared)
    role = Role(declared)
    if carrier_of(role) is not transport:
        raise MismatchedSlotRoleError(path, key, role, transport)
    return role


def _preconditions(
    path: Path, at: str, value: object, *, source: Source | None
) -> tuple[Precondition, ...]:
    """`preconditions:`, each one read whole, in declaration order."""
    key = f"{at}.{PRECONDITIONS_KEY}"
    if not isinstance(value, list):
        raise MalformedRecipeError(path, key, "a list of tables")
    return tuple(
        _precondition(path, f"{key}[{index}]", entry, at=at, source=source)
        for index, entry in enumerate(cast("list[object]", value))
    )


def _precondition(
    path: Path, key: str, value: object, *, at: str, source: Source | None
) -> Precondition:
    """One precondition: the check, out of the closed set, and what it checks for.

    `command_exists` against `source.runner`'s own value is refused **here**,
    by name (ADR 0023): it is the runner said a second time, in a field the
    reader has no way to keep in step with the one that already fixes it —
    every other check and every other value still declares normally.
    """
    table = _table(path, key, value, "a table")
    _known(path, f"{key}.", table, _PRECONDITION_KEYS)
    declared = _text(path, f"{key}.{_CHECK_FIELD}", table.get(_CHECK_FIELD))
    if declared not in {member.value for member in Check}:
        raise UnknownPreconditionCheckError(path, f"{key}.{_CHECK_FIELD}", declared)
    check = Check(declared)
    checked = _text(path, f"{key}.{_VALUE_FIELD}", table.get(_VALUE_FIELD))
    if source is not None and check is Check.COMMAND_EXISTS and checked == source.runner.value:
        raise DerivedFieldDeclaredError(
            path, f"{key}.{_VALUE_FIELD}", f"{at}.{SOURCE_KEY}.{_RUNNER_FIELD}"
        )
    return Precondition(check=check, value=checked)


def _instructions(path: Path, at: str, document: Mapping[str, object]) -> str | None:
    """The prose the author left, or `None` — the only field that is optional and not a list.

    Membership and not emptiness, for the reason `_source` carries: `instructions:`
    with nothing under it is a line half written, not a recipe that has none.
    """
    if INSTRUCTIONS_KEY not in document:
        return None
    return _text(path, f"{at}.{INSTRUCTIONS_KEY}", document[INSTRUCTIONS_KEY])


def _environment(path: Path, key: str, value: object) -> Mapping[str, str]:
    """`server.env`: literal values only, and every one of them a string."""
    table = _table(path, key, value, "a table of strings")
    return {name: _text(path, f"{key}.{name}", entry) for name, entry in table.items()}


def _known(path: Path, prefix: str, table: Mapping[str, object], allowed: frozenset[str]) -> None:
    """Refuse the first field outside `allowed`, sorted so the message is stable."""
    for name in sorted(table):
        if name not in allowed:
            raise UnknownRecipeFieldError(path, f"{prefix}{name}", allowed)


def _strings(path: Path, key: str, value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise MalformedRecipeError(path, key, "a list of strings")
    items = cast("list[object]", value)
    if not all(isinstance(item, str) for item in items):
        raise MalformedRecipeError(path, key, "a list of strings")
    return tuple(str(item) for item in items)


def _text(path: Path, key: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MalformedRecipeError(path, key, "a non-empty string")
    return value


def _table(path: Path, key: str, value: object, expected: str) -> dict[str, object]:
    """A mapping whose keys were **checked**, twin of `overpower.written._table`.

    Checked and not cast, and the format is why: TOML had no key type but string,
    so the cast this used to be was telling the truth. YAML has one — `1:` decodes
    to an integer and `true:` to a boolean — so the same cast would now be a lie,
    living in the module whose only reason to exist is being the type tripwire.
    The values stay `object`, which is the point of the whole module.

    **A twin and not a shared helper, declared rather than overlooked.** What
    differs between the two is the error class, and the error class is the one
    thing a caller of either module catches by name — sharing the body means
    passing the exception in as a parameter, which is a helper parameterised on
    the only thing that distinguishes its two uses. Four lines of narrowing, said
    twice, cost less than that; what must not diverge is the *contract*, and that
    one really is in one place.
    """
    if not isinstance(value, dict):
        raise MalformedRecipeError(path, key, expected)
    checked: dict[str, object] = {}
    for name, entry in cast("dict[object, object]", value).items():
        if not isinstance(name, str):
            raise MalformedRecipeError(path, f"{key}.{name!r}", "a name")
        checked[name] = entry
    return checked
