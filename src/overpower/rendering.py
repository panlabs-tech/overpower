"""`(Recipe, document)` → the fragment to graft. A pure function over values.

**The contract is logical, never literal** — rule 4 of the model. The recipe
carries transport, command or URL, and slots as **name and role**; *how* any of
that is spelled belongs to the target, and this module is where the two meet. A
recipe that stored `"${GITHUB_TOKEN}"` would be right in one target and silently
broken in the other two: measured, `${VAR}` reaches the server process raw in VS
Code and in the Copilot CLI, and `${env:VAR}` reaches the network raw in Claude
Code (`docs/research/mcp-config-formats.md`).

**A slot is written as a reference and a literal as itself**, which is the line
`[server.env]` draws: the overpower refuses to write a secret and does write the
address of a panel. Nothing here reads the environment, so nothing here can leak
one — resolving a slot to its value is not a feature this module is missing, it
is the defect it exists not to have.

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

from overpower.recipes import BearerSlot, EnvSlot, HeaderSlot, HttpServer, StdioServer
from overpower.runtimes import Dialect

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from overpower.recipes import Recipe, Slot
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


AUTHORIZATION = "Authorization"
BEARER_SCHEME = "Bearer"
"""The header a `bearer` slot becomes, assembled here and never in the recipe.

Keeping the word out of the recipe is what makes the role portable: a target
that spells the same intent with a field instead of a string — Codex's
`bearer_token_env_var` — is served from the very same declaration, with no new
field and no second reading of what the recipe meant.
"""


def render(recipe: Recipe, document: McpDocument) -> Fragment:
    """The fragment `recipe` becomes inside `document`."""
    match document.dialect:
        case Dialect.CLAUDE:
            return Fragment(root_key=document.root_key, name=recipe.name, value=_claude(recipe))
        case _ as unreachable:
            assert_never(unreachable)


def _claude(recipe: Recipe) -> Mapping[str, JsonValue]:
    """The Claude-style spelling: an explicit `type`, and the fields it admits.

    `type` is written even though the loader defaults to stdio without it, and
    that is deliberate: measured, the same file is read by three runtimes and
    they infer the transport by three different rules, so the one field that
    ends the guessing costs nothing to write.
    """
    match recipe.server:
        case HttpServer(url):
            rendered: dict[str, JsonValue] = {"type": "http", "url": url}
            headers = _claude_headers(recipe.slots)
            if headers:
                rendered["headers"] = headers
            return rendered
        case StdioServer(command, args, environment):
            rendered = {"type": "stdio", "command": command}
            if args:
                rendered["args"] = list(args)
            variables = _claude_environment(environment, recipe.slots)
            if variables:
                rendered["env"] = variables
            return rendered
        case _ as unreachable:
            assert_never(unreachable)


def _claude_environment(
    literals: Mapping[str, str], slots: Sequence[Slot]
) -> Mapping[str, JsonValue]:
    """The `env` table: what is written because it can be, then what never is.

    The whole distinction of the class, in one table. `literals` are values that
    are **not** secret — the address of a panel — and they arrive written, so the
    server knows where to talk; a slot arrives as a reference the runtime
    expands, so the secret stays in the environment where it already was.

    The two cannot collide: a recipe naming one variable both ways is refused by
    the reader, which is what lets this be a merge rather than a decision.
    """
    return {
        **literals,
        **{slot.name: _claude_reference(slot.name) for slot in slots if isinstance(slot, EnvSlot)},
    }


def _claude_headers(slots: Sequence[Slot]) -> Mapping[str, JsonValue]:
    """The `headers` table of an HTTP server, one entry per slot.

    An `EnvSlot` never reaches here: an HTTP server launches no process, so the
    reader refuses that pairing **by name** (`MismatchedSlotRoleError`) rather
    than leaving this function to drop a secret in silence.
    """
    return dict(_claude_header(slot) for slot in slots if not isinstance(slot, EnvSlot))


def _claude_header(slot: HeaderSlot | BearerSlot) -> tuple[str, JsonValue]:
    """One header, named by the recipe or by the scheme, filled by reference."""
    match slot:
        case BearerSlot(name):
            return AUTHORIZATION, f"{BEARER_SCHEME} {_claude_reference(name)}"
        case HeaderSlot(name, header):
            return header, _claude_reference(name)
        case _ as unreachable:
            assert_never(unreachable)


def _claude_reference(name: str) -> str:
    """`${VAR}` — the spelling this runtime expands when it reads the file.

    **Never `${VAR:-default}`.** There is no default in the contract, and the
    syntax for one is a measured trap: it is Claude Code's alone, and the same
    `.mcp.json` is read by VS Code and by the Copilot CLI, where the whole string
    reaches the server process **literally**. The file parses, the install is
    green, and the failure lands on the first call. Two files of this
    organisation carry `${COOLIFY_BASE_URL:-https://vps.panlabs.tech}` today.

    A variable that is not set is not this module's problem and cannot be: the
    renderer reads no environment, which is also why it cannot leak one. The
    warning about an unset variable is the CLI's, at exit 0
    (`overpower.planning.unset_slots`).
    """
    return f"${{{name}}}"
