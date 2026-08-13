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

from overpower.recipes import HttpServer, StdioServer
from overpower.runtimes import Dialect

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from overpower.recipes import Recipe, Server
    from overpower.runtimes import McpDocument

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
