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

The vocabulary of this version is **`description`, `transport` and `[server]`**,
which is the tracer bullet's slice
(https://github.com/panlabs-tech/overpower/issues/76). `[[slots]]`,
`[[preconditions]]`, `[source]` and `instructions` are the slices after it, and
until they arrive a recipe that declares one is refused **by name** rather than
read half-way: silent partial acceptance is exactly the class of defect the
graft exists not to commit, and it is the reason the unknown-field check is a
closed allowlist rather than a `get` per known key.

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

_RECIPE_KEYS = frozenset({DESCRIPTION_KEY, TRANSPORT_KEY, SERVER_KEY})
"""The closed set of top-level keys this version implements."""

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


@dataclass(frozen=True)
class StdioServer:
    """A server the client launches: a command, its arguments and its environment.

    `env` carries **values that are not secret**, literally — the address of a
    panel is not a secret, and treating it as a slot would mean never writing it,
    so the server would come up not knowing where to talk. What the overpower
    refuses to write is a slot, and slots arrive with
    https://github.com/panlabs-tech/overpower/issues/78.
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
    return Recipe(
        name=path.stem,
        path=path,
        description=_text(path, DESCRIPTION_KEY, document.get(DESCRIPTION_KEY)),
        server=_server(path, transport, document.get(SERVER_KEY)),
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
