"""TOML in, a `Recipe` out: the reader, and the whole of a recipe's validation.

A **recipe** is the logical declaration of an MCP server — transport, command or
URL, and (from the slices after this one) slots, preconditions and source. It
**never lands**: what lands is the fragment rendered out of it, which is why it
lives under the root that never lands (`catalog/mcps/<slug>.toml`) and not under
`content/`, whose invariant is *100% lands* (`docs/agents/domain.md`).

**A recipe that gets past this module is a recipe that renders.** Every rule the
contract has is checked here — the closed set of transports, the fields each
transport admits, and the one substitution token — so `overpower.rendering` is a
total function over what this returns rather than a second validator that could
disagree with the first.

The vocabulary of this version is **`description`, `transport`, `[server]` and
`[[slots]]`** (https://github.com/panlabs-tech/overpower/issues/76 and /78).
`[[preconditions]]`, `[source]` and `instructions` are the slices after it, and
until they arrive a recipe that declares one is refused **by name** rather than
read half-way: silent partial acceptance is exactly the class of defect the
graft exists not to commit, and it is the reason the unknown-field check is a
closed allowlist rather than a `get` per known key.

**A recipe carries a secret and a configuration, and the difference is the whole
point**: a slot is what the overpower **refuses to write**, `[server.env]` is
what it writes because it can. The distinction came from a measured server —
`COOLIFY_BASE_URL` is the address of a panel, not a secret, and a schema that
could only hold slots would never write it, bringing the server up not knowing
where to talk. It is the same line the official MCP registry draws with
`isSecret`.

**The decoder returns `object`, and that is a tripwire rather than a style** —
the same discipline `overpower.written` runs on, measured in
https://github.com/panlabs-tech/overpower/issues/2: pyright strict has a blind
spot on `Any`, so `return data["name"]` inside a `-> str` function type-checks
and blows up at runtime. `tomllib.load` hands back `dict[str, Any]`, so the
decode is confined to `_loads` and every field is narrowed in the open.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import TYPE_CHECKING, assert_never, cast

from overpower.errors import OverpowerError, RefusedError

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from pathlib import Path

RECIPE_SUFFIX = ".toml"
"""One file per MCP, and the stem is the slug `--mcp` names."""

SOURCE_TOKEN = "{source}"  # noqa: S105 — a substitution token, not a credential
"""The **only** substitution token, and the one thing we resolve rather than the runtime.

It stands for the absolute path of the clone a recipe with `[source]` brings, so
a recipe can name a directory whose path it cannot know. It is not a slot and it
is not runtime interpolation — measured, each target spells interpolation
differently and one of them has none at all
(`docs/research/mcp-config-formats.md`).

`[source]` itself belongs to https://github.com/panlabs-tech/overpower/issues/84,
so in this version every use of the token is a use without it, which the spec
calls a malformed recipe.
"""

DESCRIPTION_KEY = "description"
TRANSPORT_KEY = "transport"
SERVER_KEY = "server"
SLOTS_KEY = "slots"

_RECIPE_KEYS = frozenset({DESCRIPTION_KEY, TRANSPORT_KEY, SERVER_KEY, SLOTS_KEY})
"""The closed set of top-level keys this version implements."""

_NAME_FIELD = "name"
_ROLE_FIELD = "role"
_HEADER_FIELD = "header"

_SLOT_KEYS = frozenset({_NAME_FIELD, _ROLE_FIELD, _HEADER_FIELD})
"""What a slot is made of: a variable, a role, and — for one role — a header."""

NO_ENVIRONMENT: Mapping[str, str] = MappingProxyType({})
"""The default `[server.env]`: empty, and immutable so it can be one value.

A `field(default_factory=dict)` would answer the same thing and cost the
reader a mutable default to reason about — this is a frozen value class, and
the empty case is a constant.
"""

_STDIO_KEYS = frozenset({"command", "args", "env"})
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


AUTHORIZATION = "Authorization"
"""The header a `bearer` slot fills, and a fact of the scheme rather than of a target.

It lives here and not in the renderer because the **reader** needs it: two
`bearer` slots fill this one header, and catching that is what keeps a secret
from disappearing into a table. How the header is *written* — the word `Bearer`
in Claude Code, a `bearer_token_env_var` field in Codex — stays the renderer's.
"""


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

    `name` is the file's stem and never a field: the tree is the catalog
    (rule 8, ADR 0006), so the slug `--mcp` names comes from the filename the
    same way a skill's name comes from its directory.
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
    """The recipe parsed as TOML and is not shaped like a recipe.

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

    def __init__(self, path: Path, transport: str) -> None:
        """Name the recipe, the transport it declared, and the two that exist."""
        self.path = path
        self.transport = transport
        allowed = ", ".join(sorted(member.value for member in Transport))
        super().__init__(
            f"{path}: transport `{transport}` is not one this product writes; the set is: {allowed}"
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


class CollidingSlotError(OverpowerError):
    """Two declarations of one place, where the renderer could only keep one.

    The place, never the name: two `bearer` slots carry two different variables
    and fill the **same** header, and a table built out of them would silently
    keep the last. So would a slot whose variable `[server.env]` already writes —
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


class SourcelessSubstitutionError(OverpowerError):
    """`{source}` in a recipe that declares no `[source]` to resolve it against.

    The token stands for the path of a clone, so a recipe that uses it without
    declaring where the code comes from names a directory that will never exist.
    Writing it through literally is the silent half of this defect: the server
    would be launched against a directory called `{source}`.
    """

    def __init__(self, path: Path, key: str) -> None:
        """Name the recipe and the field the token was found in."""
        self.path = path
        self.key = key
        super().__init__(
            f"{path}: `{key}` uses {SOURCE_TOKEN} and the recipe declares no [source] to resolve it"
        )


def read_recipe(path: Path) -> Recipe:
    """The recipe at `path`, whole, or the named error that says why it is not one."""
    document = _table(path, "the file", _loads(path, path.read_text(encoding="utf-8")), "a table")
    _known(path, "", document, _RECIPE_KEYS)
    transport = _transport(path, document.get(TRANSPORT_KEY))
    server = _server(path, transport, document.get(SERVER_KEY))
    return Recipe(
        name=path.stem,
        path=path,
        description=_text(path, DESCRIPTION_KEY, document.get(DESCRIPTION_KEY)),
        server=server,
        slots=_slots(path, transport, server, document.get(SLOTS_KEY, [])),
    )


def _transport(path: Path, value: object) -> Transport:
    """The declared transport, as a member of the closed set."""
    if not isinstance(value, str):
        raise MalformedRecipeError(path, TRANSPORT_KEY, "a string")
    if value not in {member.value for member in Transport}:
        raise ForbiddenTransportError(path, value)
    return Transport(value)


def _server(path: Path, transport: Transport, value: object) -> Server:
    """The `[server]` table, read in the shape its transport admits.

    The transport decides which fields exist, so a `url` under `stdio` is an
    unknown field rather than a field with a wrong value — which is what makes
    the message point at the line that has to change.
    """
    table = _table(path, SERVER_KEY, value, "a table")
    match transport:
        case Transport.STDIO:
            _known(path, f"{SERVER_KEY}.", table, _STDIO_KEYS)
            args = _strings(path, f"{SERVER_KEY}.args", table.get("args", []))
            return StdioServer(
                command=_field(path, f"{SERVER_KEY}.command", table.get("command")),
                args=tuple(_sourceless(path, f"{SERVER_KEY}.args", item) for item in args),
                env=_environment(path, table.get("env", {})),
            )
        case Transport.HTTP:
            _known(path, f"{SERVER_KEY}.", table, _HTTP_KEYS)
            return HttpServer(url=_field(path, f"{SERVER_KEY}.url", table.get("url")))
        case _ as unreachable:
            assert_never(unreachable)


def _slots(path: Path, transport: Transport, server: Server, value: object) -> tuple[Slot, ...]:
    """`[[slots]]`, each one read whole, and no two of them filling one place.

    **Uniqueness is of the place a slot fills, never of the name it carries**,
    and the difference is the whole reason this check exists: two `bearer` slots
    carry different variables and fill the *same* header, so a renderer building
    a table would keep one of them and drop the other at exit 0 — a secret gone
    from a file nobody re-reads. `[server.env]` joins the same comparison,
    because a literal and a slot end up as keys of one table too.
    """
    if not isinstance(value, list):
        raise MalformedRecipeError(path, SLOTS_KEY, "a list of tables")
    written = server.env if isinstance(server, StdioServer) else NO_ENVIRONMENT
    # A literal fills the variable it names, and only a stdio server has any —
    # so this is the whole of the `[server.env]` side of the comparison.
    taken = dict.fromkeys(written, f"`[{SERVER_KEY}.env]`")
    slots: list[Slot] = []
    for index, entry in enumerate(cast("list[object]", value)):
        key = f"{SLOTS_KEY}[{index}]"
        slot = _slot(path, key, transport, entry)
        place = _filled(slot)
        held = taken.get(place)
        if held is not None:
            raise CollidingSlotError(path, key, place, held)
        taken[place] = key
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
    name = _field(path, f"{key}.{_NAME_FIELD}", table.get(_NAME_FIELD))
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
            return HeaderSlot(name=name, header=_field(path, f"{key}.{_HEADER_FIELD}", header))
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


def _environment(path: Path, value: object) -> Mapping[str, str]:
    """`[server.env]`: literal values only, and every one of them a string."""
    key = f"{SERVER_KEY}.env"
    table = _table(path, key, value, "a table of strings")
    return {name: _field(path, f"{key}.{name}", entry) for name, entry in table.items()}


def _field(path: Path, key: str, value: object) -> str:
    """A required string field, narrowed and checked for the one token we resolve."""
    return _sourceless(path, key, _text(path, key, value))


def _sourceless(path: Path, key: str, value: str) -> str:
    """`value`, unless it reaches for a clone this version cannot give it."""
    if SOURCE_TOKEN in value:
        raise SourcelessSubstitutionError(path, key)
    return value


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
    """A TOML table, typed.

    The cast is not a shrug: TOML has **no** key type but string, so `dict[str,
    object]` is what the format guarantees and `isinstance` cannot express. The
    values stay `object` — that is the point of the whole module.
    """
    if not isinstance(value, dict):
        raise MalformedRecipeError(path, key, expected)
    return cast("dict[str, object]", value)


def _loads(path: Path, text: str) -> object:
    """The whole decode surface, and it declares `object` on purpose.

    A syntax error is renamed on the way out: `tomllib` reports the line and the
    column and never the file, and *which recipe* is the first thing the reader
    of that message needs — the more so once the file is somebody else's
    (https://github.com/panlabs-tech/overpower/issues/83).
    """
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError as broken:
        raise MalformedRecipeError(path, "the file", f"valid TOML ({broken})") from broken
