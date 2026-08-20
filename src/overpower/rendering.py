"""`(Recipe, document)` → the grafts to make. A pure function over values.

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

from overpower.recipes import (
    AUTHORIZATION,
    SOURCE_TOKEN,
    BearerSlot,
    EnvSlot,
    HeaderSlot,
    HttpServer,
    StdioServer,
    Transport,
    input_id,
)
from overpower.runtimes import MCP_DOCUMENTS, Dialect, Scope

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence
    from pathlib import Path

    from overpower.recipes import Recipe, Slot
    from overpower.runtimes import McpDocument

type JsonValue = str | bool | Sequence[JsonValue] | Mapping[str, JsonValue]
"""What a rendered graft is made of, and the set is closed at four.

No number and no null, because nothing in a recipe produces one: a server is
strings, lists of strings and tables of strings all the way down. Widening this
was left as *"a decision for whoever needs it, made where the need is"*, and the
need arrived: `password: true` is a **boolean** in the measured VS Code file, and
the string `"true"` is not the same value — measured, what turns the OS keychain
on is the boolean (`docs/research/mcp-config-formats.md`, trap 10).
"""

type Reference = Callable[[str], str]
"""How one dialect spells *"the value of the slot named this"*.

The one thing that differs between the renderers sharing a field-by-field walk,
so it is the one thing handed in: `${VAR}`, `${input:<id>}` and `${env:VAR}` are
the whole delta, and a second copy of the walk would be one more place for a
field to go missing from.

**It carries the hole `_transports` refuses, and the trade is deliberate.** A
`dict[Dialect, ...]` is rejected two functions down because a new member would
type-check clean against it; a parameter of this type has exactly that shape —
`_devin` handing `_claude_reference` to `_headers` compiles, and no `assert_never`
fires. What catches it is not the type checker but the file: every dialect is
asserted against the bytes it produces, in `tests/test_writing.py`. The
alternative is writing the literal-versus-slot merge rule once per dialect and
trusting three copies to stay the same rule, which is the failure this class
exists not to have.
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
class Inputs:
    """The prompts a document needs before its slots can be filled — the other graft.

    It exists because one dialect spells a slot as a **reference to a declaration
    elsewhere in the same file**: `${input:git-token}` is inert unless an entry
    with that `id` is in `inputs[]`, so the reference and the declaration are two
    keys of one document and a recipe that has a slot becomes two grafts in it.

    A list and not a table, which is why this is not a second `Fragment`: the
    entries have no key of their own, and *"the same entry"* is decided by a
    **field inside them**. `identity` carries which one, so the writer is told
    how to deduplicate rather than knowing — two recipes wanting `GITHUB_TOKEN`
    want one prompt, and the append that keeps it at one is the writer's, from
    the plan and nothing beyond it.
    """

    root_key: str
    entries: tuple[Mapping[str, JsonValue], ...]
    identity: str
    """The field two entries are the same entry by, named for the writer."""

    @property
    def dotted(self) -> str:
        """`inputs` — the whole path, which for a list *is* the root key.

        The same property `Fragment` answers and for the same consumer: it is
        what the plan prints and what the identity assertion reads. A list has no
        leaf to name, so the honest whole path is one segment long.
        """
        return self.root_key


type Graft = Fragment | Inputs
"""One insertion into a document: a key under a table, or entries in a list.

A union rather than one widened type, for the reason `Destination` is one in
`overpower.planning`: the two are written by different mechanics — replace-or-
append **by key** against append-or-replace **by a field of the value** — and a
single type carrying both would make every reader ask which half it holds.
"""


BEARER_SCHEME = "Bearer"
"""The word a `bearer` slot becomes here, and never in the recipe.

The **header** it goes in is a fact of the scheme and lives with the reader
(`overpower.recipes.AUTHORIZATION`), which needs it to catch two slots filling
it. The *spelling* is what belongs here: a target that says the same thing with
a field instead of a string — Codex's `bearer_token_env_var` — is served from
the very same declaration, with no new field and no second reading of what the
recipe meant.
"""


@dataclass(frozen=True)
class Target:
    """One pair a recipe can be written for: a runtime, and the scope it reads in.

    Two fields and never the runtime alone, because the pair is the unit the
    table is keyed by: `claude-code` reads `.mcp.json` in a repository and reads
    nothing at all on the machine
    (https://github.com/ThiagoPanini/overpower/issues/81), so a target that
    named only the runtime would promise the half that does not exist.
    """

    runtime: str
    scope: Scope


CLAUDE_TRANSPORTS = frozenset({Transport.STDIO, Transport.HTTP})
"""What the Claude dialect can spell, which is everything a recipe can say.

Measured (`docs/research/mcp-config-formats.md`): `.mcp.json` discriminates the
transport with an explicit `type` field and writes **both** bindings, so the two
transports coincide *there*. That coincidence is a fact about this one target
and not about the model — the day a dialect lands that writes one of them, or
that cannot spell a slot role, the answer moves **here**, with no recipe touched.
Which is the whole reason it is a table in code and never a field (rule 4).

It is the same set the `CLAUDE` branch of `_server` covers, and `_transports` is
what keeps the two from drifting apart in silence.
"""

VSCODE_TRANSPORTS = frozenset({Transport.STDIO, Transport.HTTP})
"""What the VS Code dialect can spell, and it is the same two.

Written as its own set rather than aliased to the one above, because they are
equal by measurement and not by definition: `.vscode/mcp.json` happens to carry
the same explicit `type` discriminator, and a dialect that loses one of the two
must be able to shrink without dragging the other target with it. The equality
is the fact; sharing the object would make it a rule.
"""

DEVIN_TRANSPORTS = frozenset({Transport.STDIO, Transport.HTTP})
"""What the Devin dialect can spell, which is the same two — for other reasons.

The vendor documents stdio, Streamable HTTP **and** SSE, and this set names the
first two: `sse` is deprecated in the spec and is refused at the recipe
(`overpower.recipes.Transport`), so the widest thing a recipe can ask for is
already the widest thing written here. A target being *able* to read a binding
is not a reason to offer it.

That this set equals `CLAUDE_TRANSPORTS` is a coincidence of two targets and not
a fact about the model — they arrive at it from opposite directions, one by
writing every binding the spec has and the other by declining one it would
accept. Which is why they are two constants and never one.
"""


def _transports(dialect: Dialect) -> frozenset[Transport]:
    """Which transports `dialect` can spell — the capability half of rule 4.

    A `match` and never a mapping lookup, for the reason `Dialect` states on
    itself: the set is closed *and* matched with `assert_never`, so a third
    dialect lands as a hole the type checker names. A `dict[Dialect, ...]`
    subscript would type-check clean against a new member and raise `KeyError`
    from inside `targets_of` — a silent default wearing a table's clothes. It is
    how the second dialect landed, and it worked.
    """
    match dialect:
        case Dialect.CLAUDE:
            return CLAUDE_TRANSPORTS
        case Dialect.VSCODE:
            return VSCODE_TRANSPORTS
        case Dialect.DEVIN:
            return DEVIN_TRANSPORTS
        case _ as unreachable:
            assert_never(unreachable)


def expands_from_environment(dialect: Dialect) -> bool:
    """Whether a slot written for `dialect` is filled out of the process environment.

    The other capability half of rule 4, and it is what decides whether *"this
    variable is not set here"* is advice or noise. `${VAR}` and `${env:VAR}` are
    both read out of the environment of the runtime's own process, so an absent
    variable is a measured failure at the far end — Claude Code sent
    `Bearer ${NAO_EXISTE}` literally on the wire. `${input:<id>}` is read out of a
    prompt and the OS keychain, so there is no variable to be absent: the editor
    asks.

    A `match` on the closed set for the reason every other one here is — a new
    dialect must land as a hole and not as a default, because defaulting either
    way ships a wrong warning at exit 0.
    """
    match dialect:
        case Dialect.CLAUDE:
            return True
        case Dialect.VSCODE:
            return False
        case Dialect.DEVIN:
            return True
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

    **Two terms and not one**, because two different things decide a pair. The
    document decides whether the transport can be spelled at all; the *recipe*
    decides which scopes are open to it, and a recipe with `[source]` clones to
    an absolute path on this machine, which cannot go into the team's repository
    (ADR 0015). `overpower.planning` refuses that pair with exit 3 and the
    wizard declines to offer it — this is the third surface, and a screen that
    offers what the next step is certain to reject is the one place the three
    could disagree.
    """
    return tuple(
        Target(runtime=runtime, scope=scope)
        for (runtime, scope), document in documents.items()
        if recipe.transport in _transports(document.dialect)
        and (recipe.source is None or scope is Scope.GLOBAL)
    )


def render(recipe: Recipe, document: McpDocument, source: Path | None = None) -> tuple[Graft, ...]:
    """Every graft `recipe` becomes inside `document`, in the order they are written.

    A tuple and never one fragment, because one dialect needs two: a VS Code slot
    is a `${input:<id>}` **and** the `inputs[]` entry it points at, under a
    different root key of the same document. The server graft is always first, so
    a reader that wants *"the server"* takes the head rather than filtering.

    Answering with a tuple rather than with an optional field on `Fragment` is
    the same reasoning `Dialect` applies to itself: a third dialect that needs a
    third graft is one more element, and a dialect that needs none is a shorter
    tuple — neither one is a field the other dialects carry as `None`.

    `source` is the absolute path of the clone `recipe.source` brings, resolved
    by the caller (`overpower.planning`) from (root, recipe.name) — no I/O, and
    no filesystem, the same discipline this whole module keeps: the path is
    computed, never read off a disk this function never touches. `None` for a
    recipe that declares no `[source]`, which is every recipe read_recipe would
    let `{source}` appear nowhere in.
    """
    match document.dialect:
        case Dialect.CLAUDE:
            value = _server(recipe, document, source)
            return (Fragment(root_key=document.root_key, name=recipe.name, value=value),)
        case Dialect.VSCODE:
            value = _server(recipe, document, source)
            server = Fragment(root_key=document.root_key, name=recipe.name, value=value)
            prompts = _vscode_inputs(recipe.slots)
            return (server,) if prompts is None else (server, prompts)
        case Dialect.DEVIN:
            value = _devin(recipe, source)
            return (Fragment(root_key=document.root_key, name=recipe.name, value=value),)
        case _ as unreachable:
            assert_never(unreachable)


def _resolved(value: str, source: Path | None) -> str:
    """`value`, with `{source}` replaced by the clone's absolute path.

    The one substitution this product performs, and the reason it can — the
    reader already refused every recipe that uses the token with no `[source]`
    to resolve it against (`overpower.recipes.SourcelessSubstitutionError`), so
    a `source` of `None` reaching here with the token still in `value` is a
    contract this module trusts rather than re-checks.
    """
    return value if source is None else value.replace(SOURCE_TOKEN, str(source))


def _server(recipe: Recipe, document: McpDocument, source: Path | None) -> Mapping[str, JsonValue]:
    """The server table, in the fields both dialects admit and one spells apart.

    `type` is written even though both loaders default to stdio without it, and
    that is deliberate: measured, `.mcp.json` alone is read by three runtimes and
    they infer the transport by three different rules, so the one field that
    ends the guessing costs nothing to write.

    One walk of the fields for both dialects, because measured they differ in
    **exactly one thing** — how a slot is referred to. Writing it twice would put
    the shape of a server in two places, and the second one is where a field goes
    missing the day a recipe grows one.
    """
    reference = _reference(document.dialect)
    match recipe.server:
        case HttpServer(url):
            rendered: dict[str, JsonValue] = {"type": "http", "url": _resolved(url, source)}
            headers = _headers(recipe.slots, reference)
            if headers:
                rendered["headers"] = headers
            return rendered
        case StdioServer(command, args, environment):
            rendered = {"type": "stdio", "command": _resolved(command, source)}
            if args:
                rendered["args"] = [_resolved(arg, source) for arg in args]
            variables = _environment(environment, recipe.slots, reference, source)
            if variables:
                rendered["env"] = variables
            return rendered
        case _ as unreachable:
            assert_never(unreachable)


def _reference(dialect: Dialect) -> Reference:
    """How `dialect` spells a slot, which is the only thing the two disagree on.

    A `match` on the closed set for the reason every other one here is: the day a
    new dialect arrives, this is one of the holes the type checker names, and
    the alternative — a mapping with a default — would silently spell the new
    target in somebody else's syntax. Measured, that failure does not show up in
    a parse: it shows up as a literal `${input:x}` on the network.

    `DEVIN` answers here too even though `_server` never dispatches to it —
    Devin's own shape lives in `_devin`, not behind this table — because a
    partial match would leave `assert_never` unable to prove the closure it
    exists to prove.
    """
    match dialect:
        case Dialect.CLAUDE:
            return _claude_reference
        case Dialect.VSCODE:
            return _vscode_reference
        case Dialect.DEVIN:
            return _devin_reference
        case _ as unreachable:
            assert_never(unreachable)


def _devin(recipe: Recipe, source: Path | None) -> Mapping[str, JsonValue]:
    """The Devin-style spelling: `transport` on HTTP, and nothing at all on stdio.

    The asymmetry is the vendor's, not a shortcut taken here: `transport` is
    documented with the values `"http"` and `"sse"`, and stdio is inferred from
    the presence of `command`. Writing `"transport": "stdio"` would put an
    undocumented value in a file whose behaviour on undocumented values is
    **measured, not just inferred by analogy**
    (`docs/research/mcp-config-formats.md` § Medição 2026-08-14): Devin swallows
    an unrecognized field at exit 0, same class as the other silent neighbours —
    and does it one step further, normalizing even malformed JSON into "no
    servers configured" rather than surfacing a parse error.

    The three fields stdio admits and the three HTTP admits are the same shape
    the Claude dialect writes, which is why the leaves are shared: what differs
    between the two is the discriminator and the reference, and both are named
    right here rather than buried in a branch further down.
    """
    match recipe.server:
        case HttpServer(url):
            rendered: dict[str, JsonValue] = {"transport": "http", "url": _resolved(url, source)}
            headers = _headers(recipe.slots, _devin_reference)
            if headers:
                rendered["headers"] = headers
            return rendered
        case StdioServer(command, args, environment):
            rendered = {"command": _resolved(command, source)}
            if args:
                rendered["args"] = [_resolved(arg, source) for arg in args]
            variables = _environment(environment, recipe.slots, _devin_reference, source)
            if variables:
                rendered["env"] = variables
            return rendered
        case _ as unreachable:
            assert_never(unreachable)


def _environment(
    literals: Mapping[str, str], slots: Sequence[Slot], reference: Reference, source: Path | None
) -> Mapping[str, JsonValue]:
    """The `env` table: what is written because it can be, then what never is.

    The whole distinction of the class, in one table. `literals` are values that
    are **not** secret — the address of a panel — and they arrive written, so the
    server knows where to talk; a slot arrives as a reference the runtime
    expands, so the secret stays where it already was.

    The two cannot collide: a recipe naming one variable both ways is refused by
    the reader, which is what lets this be a merge rather than a decision.

    `reference` is the dialect's, and it is the *only* thing that varies here:
    every target writes this table identically and expands the name by a
    different spelling, so passing the spelling in is what keeps the merge rule
    from being stated once per target and drifting once.
    """
    return {
        **{name: _resolved(value, source) for name, value in literals.items()},
        **{slot.name: reference(slot.name) for slot in slots if isinstance(slot, EnvSlot)},
    }


def _headers(slots: Sequence[Slot], reference: Reference) -> Mapping[str, JsonValue]:
    """The `headers` table of an HTTP server, one entry per slot.

    Two refusals of the reader are what let this be a plain table. An `EnvSlot`
    never reaches here — an HTTP server launches no process, so that pairing is
    refused by name (`MismatchedSlotRoleError`). And no two slots fill one header
    (`CollidingSlotError`), so building a `dict` cannot drop one of them: two
    `bearer` slots would both land on `Authorization`, and the loser would be a
    secret gone at exit 0.
    """
    return dict(_header(slot, reference) for slot in slots if not isinstance(slot, EnvSlot))


def _header(slot: HeaderSlot | BearerSlot, reference: Reference) -> tuple[str, JsonValue]:
    """One header, named by the recipe or by the scheme, filled by reference.

    Shared by every dialect that spells a header as a header. A target that says
    the same thing with a field instead — Codex's `bearer_token_env_var` — does
    not pass through here at all; it writes its own arm, out of the same
    declaration and with no new field on the recipe.
    """
    match slot:
        case BearerSlot(name):
            return AUTHORIZATION, f"{BEARER_SCHEME} {reference(name)}"
        case HeaderSlot(name, header):
            return header, reference(name)
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


INPUTS_KEY = "inputs"
"""The root key VS Code reads its prompts from, beside `servers`.

A constant here and not a column of `McpDocument`, for the reason that table
gives for having no field for the file type: only one dialect has a second root
key, so a column would be `None` on every other row — a field with no reader,
going stale unnoticed. The spelling belongs with the dialect that spells it, the
way `BEARER_SCHEME` does.
"""

INPUT_IDENTITY = "id"
"""The field two prompts are the same prompt by, which the plan carries onward."""

PROMPT_STRING = "promptString"
"""The kind of input a slot becomes: a line the user types, never a pick list.

`promptString` and not `promptCommand`, which runs a shell command to produce the
value — axiom 1 without amendment: no third-party code runs, and a config file
that can execute is exactly the hatch this product does not open.
"""


def _vscode_inputs(slots: Sequence[Slot]) -> Inputs | None:
    """One prompt per slot, or `None` when the recipe asks for no secret at all.

    `None` rather than an empty `Inputs`, because the two say different things to
    everything downstream: an empty one would put `"inputs": []` in the user's
    file and a key in the plan, for a server that has nothing to fill in.
    Cloudflare authorises in the browser, and it is the ordinary case.
    """
    if not slots:
        return None
    return Inputs(
        root_key=INPUTS_KEY,
        entries=tuple(_prompt(slot.name) for slot in slots),
        identity=INPUT_IDENTITY,
    )


def _prompt(name: str) -> Mapping[str, JsonValue]:
    """One `inputs[]` entry, and `password` is the field that does the work.

    Measured (`docs/research/mcp-config-formats.md`, trap 10): with
    `password: true` the value the user types is encrypted under a key held in
    the OS keychain — Keychain, DPAPI or libsecret — and only the ciphertext
    reaches `state.vscdb`. **Without it the same value lands there in plain
    text.** Neither one puts the secret in the repository, which is what makes
    committing `.vscode/mcp.json` safe; only one of them makes it safe on the
    machine, and this renderer has no reason to ever write the other.

    `description` carries the **variable name** rather than prose, because it is
    what the prompt shows: the person is being asked for `GITHUB_TOKEN`, and the
    name of the variable is the only thing that tells them which secret that is.
    """
    return {
        "type": PROMPT_STRING,
        INPUT_IDENTITY: input_id(name),
        "description": name,
        "password": True,
    }


def _vscode_reference(name: str) -> str:
    """`${input:<id>}` — a pointer at the prompt, and **never** `${env:VAR}`.

    The variant that is refused here is the measured one that fails in silence:
    VS Code resolves `${env:X}` against the environment of its own process, and
    a variable that is not there becomes the **empty string** with no error and
    no prompt. `${env:X:-y}` does not help — it looks for a variable literally
    named `X:-y` and returns empty too. The server comes up unauthenticated and
    the failure arrives on the first call, far from the cause.

    The prompt reference cannot fail that way: what is missing, the editor asks
    for, and what is answered goes to the keychain (`_prompt`).
    """
    return f"${{input:{input_id(name)}}}"


def _devin_reference(name: str) -> str:
    """`${env:VAR}` — the third spelling of one name across three targets.

    It is Cursor's and VS Code's word, not Claude Code's, and that is the whole
    argument for rule 4 in one line: a recipe that stored any of the three would
    be right in one file and reach the server process **literally** in the other
    two. The name and the role are the recipe's; the spelling is the target's.

    **Documented for `oauthClientSecret` and `oauthResource`; its reach into
    `env`/`command`/`args` stayed unmeasured**
    (`docs/research/mcp-config-formats.md` § Medição 2026-08-14) — the server
    process this reference would resolve into only spawns inside an
    authenticated agent session, and no account was reachable from a sandbox.
    If it does not reach, the reference arrives raw at the server and the
    failure lands on the first call — loudly, at the far end. The alternative is
    resolving the slot and writing the secret into a committed file, which is
    the defect this class exists not to have, so the reference is written
    either way.

    **Never `${file:/path}`**, which this target has and no other measured one
    does: it would put the location of a secret in a versioned file on the
    strength of documentation nobody here could run, and no recipe carries a path
    to ask it with.
    """
    return f"${{env:{name}}}"
