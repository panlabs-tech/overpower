"""`(Recipe, document)` → the fragment to graft. A pure function over values.

**The contract is logical, never literal** — rule 4 of the model. The recipe
carries transport, command or URL; *how* that is spelled belongs to the target,
and this module is where the two meet. A recipe that stored `"${GITHUB_TOKEN}"`
would be right in one target and silently broken in the other two: measured,
`${VAR}` reaches the server process raw in VS Code and in the Copilot CLI, and
`${env:VAR}` reaches the network raw in Claude Code
(`docs/research/mcp-config-formats.md`).

**No I/O, and no filesystem.** What comes out is the value the writer inserts,
and the writer inserts **that and nothing else** — a writer that re-rendered the
recipe could disagree with the plan by construction, which is the same rule that
keeps the copy class honest (`overpower.planning`).

**Which targets a recipe can serve is derived, never declared** — a function of
(transport, slot roles, target), so it is a table in code (`MCP_DOCUMENTS`) for
the same reason a destination is. A field would go stale in silence the day a
runtime gained a capability, and leave the recipe lying about itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, assert_never

from overpower.recipes import HttpServer, StdioServer, Transport
from overpower.runtimes import MCP_DOCUMENTS, Dialect

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from overpower.recipes import Recipe, Server
    from overpower.runtimes import McpDocument, Scope

type JsonValue = str | Sequence[JsonValue] | Mapping[str, JsonValue]
"""What a rendered server is made of, and the set is closed at three.

No number, no boolean and no null, because nothing in a recipe produces one: a
server is strings, lists of strings and tables of strings all the way down.
Widening this is a decision for whoever needs it, made where the need is.
"""


@dataclass(frozen=True)
class Fragment:
    """One rendered server: the document key it occupies, and the value under it.

    It is the **origin of a graft write**, standing where a source path stands
    for a copy. Without it the writer would have to re-render the recipe, and
    *"the writer consumes the plan and nothing beyond it"* is what makes the plan
    and the disk unable to disagree.
    """

    root_key: str
    name: str
    value: Mapping[str, JsonValue]

    @property
    def dotted(self) -> str:
        """`mcpServers.cloudflare` — the whole path, which is what the plan names.

        Why the whole path rather than the leaf is on
        `overpower.planning.DocumentKey.key`, where the datum lives.
        """
        return f"{self.root_key}.{self.name}"


@dataclass(frozen=True)
class Target:
    """One pair a recipe can be written for: a runtime, and the scope it reads in.

    Two fields and never the runtime alone, because the pair is the unit the
    table is keyed by: `claude-code` reads `.mcp.json` in a repository and reads
    nothing at all on the machine
    (https://github.com/panlabs-tech/overpower/issues/81), so a target that
    named only the runtime would promise the half that does not exist.
    """

    runtime: str
    scope: Scope


CLAUDE_TRANSPORTS = frozenset({Transport.STDIO, Transport.HTTP})
"""What the Claude dialect can spell, which today is everything a recipe can say.

Measured (`docs/research/mcp-config-formats.md`): `.mcp.json` discriminates the
transport with an explicit `type` field and writes **both** bindings, so the two
transports coincide *there*. That coincidence is a fact about this one target
and not about the model — the day a dialect lands that writes one of them, or
that cannot spell a slot role, the answer moves **here**, with no recipe touched.
Which is the whole reason it is a table in code and never a field (rule 4).

It is the same set `_claude` matches on, and `_transports` is what keeps the two
from drifting apart in silence.
"""


def _transports(dialect: Dialect) -> frozenset[Transport]:
    """Which transports `dialect` can spell — the capability half of rule 4.

    A `match` and never a mapping lookup, for the reason `Dialect` states on
    itself: the set is closed *and* matched with `assert_never`, so a second
    dialect lands as a hole the type checker names. A `dict[Dialect, ...]`
    subscript would type-check clean against a new member and raise `KeyError`
    from inside `targets_of` — a silent default wearing a table's clothes.
    """
    match dialect:
        case Dialect.CLAUDE:
            return CLAUDE_TRANSPORTS
        case _ as unreachable:
            assert_never(unreachable)


def targets_of(
    recipe: Recipe, documents: Mapping[tuple[str, Scope], McpDocument] = MCP_DOCUMENTS
) -> tuple[Target, ...]:
    """Every (runtime, scope) pair whose document can express `recipe`, in table order.

    **Derived, never declared** — rule 4. A field on the recipe would answer the
    same thing today and go stale in silence the day a runtime gained a
    capability, leaving the recipe lying about itself; read off the table, the
    answer cannot disagree with the table that decides where the file is.

    `documents` defaults to the product's own table and is a parameter for the
    property above: *"the same recipe answers differently when the table
    changes"* is only assertable if the table can be handed in, and a test that
    monkeypatched the module constant would be asserting the patch.
    """
    return tuple(
        Target(runtime=runtime, scope=scope)
        for (runtime, scope), document in documents.items()
        if recipe.transport in _transports(document.dialect)
    )


def render(recipe: Recipe, document: McpDocument) -> Fragment:
    """The fragment `recipe` becomes inside `document`."""
    match document.dialect:
        case Dialect.CLAUDE:
            return Fragment(
                root_key=document.root_key, name=recipe.name, value=_claude(recipe.server)
            )
        case _ as unreachable:
            assert_never(unreachable)


def _claude(server: Server) -> Mapping[str, JsonValue]:
    """The Claude-style spelling: an explicit `type`, and the fields it admits.

    `type` is written even though the loader defaults to stdio without it, and
    that is deliberate: measured, the same file is read by three runtimes and
    they infer the transport by three different rules, so the one field that
    ends the guessing costs nothing to write.
    """
    match server:
        case HttpServer(url):
            return {"type": "http", "url": url}
        case StdioServer(command, args, environment):
            rendered: dict[str, JsonValue] = {"type": "stdio", "command": command}
            if args:
                rendered["args"] = list(args)
            if environment:
                rendered["env"] = dict(environment)
            return rendered
        case _ as unreachable:
            assert_never(unreachable)
