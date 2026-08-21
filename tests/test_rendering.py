"""The renderer: values in, the grafts out, and no disk anywhere.

Mirror of `src/overpower/rendering.py`. Nothing here is built on a filesystem
and nothing needs a double — the renderer is a pure function, and what it
consumes is a value the reader already validated. The doctrine says so in as
many words: *"no double is born for the renderer; what needs a fixture is the
recipe, which is a value."*

This is where the matrix of target by dialect is asserted. Three columns —
Claude Code (https://github.com/ThiagoPanini/overpower/issues/76), VS Code
(https://github.com/ThiagoPanini/overpower/issues/79) and Devin
(https://github.com/ThiagoPanini/overpower/issues/80) — and the assertions are
about **what each column spells**: the root key it lands under, how it
discriminates the transport, the fields each transport carries, and the grafts
one recipe becomes.

Claude and Devin share a root key and disagree about everything else past it,
which is the point of reading them side by side. Claude Code writes an explicit
`type` and expands `${VAR}`; VS Code writes `servers` and a slot as two grafts,
`${input:<id>}` plus an `inputs[]` entry; Devin writes `transport` on HTTP only,
infers stdio from `command`, and expands `${env:VAR}` — the third spelling in a
trio of three targets, so rule 4 leaves this slice firmer than it arrived.

It is also where *"which targets a recipe serves"* is proved to be **derived**
(rule 4): the answer is read off the table of documents, so the same recipe —
untouched, byte for byte — answers differently when the table changes.
"""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING

import pytest

from overpower.recipes import (
    BearerSlot,
    EnvSlot,
    HeaderSlot,
    HttpServer,
    Recipe,
    Runner,
    Slot,
    Source,
    StdioServer,
    Transport,
)
from overpower.rendering import (
    CLAUDE_TRANSPORTS,
    DEVIN_TRANSPORTS,
    VSCODE_TRANSPORTS,
    Fragment,
    Inputs,
    Target,
    render,
    targets_of,
)
from overpower.runtimes import MCP_DOCUMENTS, McpDocument, Scope

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from overpower.rendering import JsonValue

CLAUDE_PROJECT = MCP_DOCUMENTS[("claude-code", Scope.PROJECT)]
"""The Claude row, read from the table rather than rebuilt here.

A fixture that spelled `mcpServers` itself could only prove the renderer agrees
with the test; read off the table, it proves the renderer agrees with the row
that decides where the file is.
"""

CLAUDE_GLOBAL = MCP_DOCUMENTS[("claude-code", Scope.GLOBAL)]
"""The row the git does not reach, which is the only one a value is written into.

Read off the table like its project sibling, and named apart from it because
ADR 0024 turns on the difference: `~/.claude.json` is not in anybody's
repository, and `.mcp.json` is.
"""

VSCODE_PROJECT = MCP_DOCUMENTS[("vscode", Scope.PROJECT)]
"""The VS Code row, read from the table for the same reason."""

DEVIN_PROJECT = MCP_DOCUMENTS[("devin", Scope.PROJECT)]
"""The Devin row, read the same way and for the same reason.

It shares `mcpServers` with Claude's — which is exactly why it must come off
the table: two rows that agree on the root key and disagree on the spelling are
the case a hand-written fixture makes look like one row.
"""


def recipe(name: str, server: HttpServer | StdioServer, *slots: Slot) -> Recipe:
    return Recipe(
        name=name,
        path=Path(f"{name}.toml"),
        description="A server.",
        server=server,
        slots=slots,
    )


def server_of(
    asked: Recipe, document: McpDocument, secrets: Mapping[str, str] = MappingProxyType({})
) -> Fragment:
    """The server graft, which is the first one and in one dialect the only one.

    A recipe becomes **one or more** grafts in a document — VS Code takes a
    second one, in `inputs[]` — so the tests that are about the server say which
    graft they mean instead of indexing a tuple in fifteen places.
    """
    first, *_ = render(asked, document, secrets)
    assert isinstance(first, Fragment), "the server graft is always the first one"
    return first


def inputs_of(
    asked: Recipe, document: McpDocument, secrets: Mapping[str, str] = MappingProxyType({})
) -> Inputs | None:
    """The `inputs[]` graft, or `None` where the dialect asks for none."""
    found = [graft for graft in render(asked, document, secrets) if isinstance(graft, Inputs)]
    assert len(found) <= 1, "one document takes one `inputs` graft, however many slots feed it"
    return found[0] if found else None


def test_an_http_server_renders_its_url_under_an_explicit_type() -> None:
    """`type` is written even where the loader would infer it.

    Measured: the same `.mcp.json` is read by three runtimes and they infer the
    transport by three different rules, so the one field that ends the guessing
    costs nothing to write.
    """
    fragment = server_of(
        recipe("cloudflare", HttpServer(url="https://mcp.example.com/mcp")), CLAUDE_PROJECT
    )

    assert fragment.value == {"type": "http", "url": "https://mcp.example.com/mcp"}


def test_a_stdio_server_renders_its_command_its_args_and_its_environment() -> None:
    server = StdioServer(
        command="uvx", args=("mcp-server-git", "."), env={"PANEL": "https://panel.example.com"}
    )

    fragment = server_of(recipe("git", server), CLAUDE_PROJECT)

    assert fragment.value == {
        "type": "stdio",
        "command": "uvx",
        "args": ["mcp-server-git", "."],
        "env": {"PANEL": "https://panel.example.com"},
    }


def test_a_stdio_server_with_nothing_to_say_writes_no_empty_fields() -> None:
    """An `"args": []` nobody asked for is a field the reader has to interpret."""
    fragment = server_of(recipe("bare", StdioServer(command="uvx")), CLAUDE_PROJECT)

    assert fragment.value == {"type": "stdio", "command": "uvx"}


def test_the_fragment_names_the_root_key_the_document_reads() -> None:
    fragment = server_of(recipe("cloudflare", HttpServer(url="https://x/mcp")), CLAUDE_PROJECT)

    assert fragment.root_key == "mcpServers"
    assert fragment.name == "cloudflare"


def test_the_fragment_spells_the_whole_key_path_and_not_just_the_leaf() -> None:
    """It is what the plan prints, and under unconditional overwriting (ADR 0013)
    that line is the reader's only chance to notice the key is theirs."""
    fragment = server_of(recipe("cloudflare", HttpServer(url="https://x/mcp")), CLAUDE_PROJECT)

    assert fragment.dotted == "mcpServers.cloudflare"


def test_the_same_recipe_renders_the_same_fragment_every_time() -> None:
    """No clock, no environment, no disk: the renderer is a function of its inputs."""
    asked = recipe("cloudflare", HttpServer(url="https://x/mcp"))

    assert render(asked, CLAUDE_PROJECT) == render(asked, CLAUDE_PROJECT)


# --------------------------------------------------------------------------- #
# the three roles, and the spelling each target expands
# --------------------------------------------------------------------------- #


def test_an_env_slot_renders_as_the_reference_this_target_expands() -> None:
    """`${VAR}` is Claude Code's spelling, and the value never appears.

    The name is all the recipe carries; the spelling belongs to the target. In
    VS Code the same name becomes `${input:<id>}` and in Devin `${env:VAR}`, so a
    recipe that stored any of the three would be right once and silently wrong
    twice.
    """
    fragment = server_of(
        recipe("hostinger-vps", StdioServer(command="npx"), EnvSlot(name="HOSTINGER_API_TOKEN")),
        CLAUDE_PROJECT,
    )

    assert fragment.value["env"] == {"HOSTINGER_API_TOKEN": "${HOSTINGER_API_TOKEN}"}


def test_a_literal_and_a_slot_share_the_environment_table_without_mixing() -> None:
    """The whole distinction, in one table: the address is written, the token is not.

    It is the measured case that showed a schema of slots alone cannot render
    this server — the address of the panel is not a secret, and treating it as
    one would bring the server up not knowing where to talk.
    """
    server = StdioServer(command="npx", env={"COOLIFY_BASE_URL": "https://vps.panlabs.tech"})

    fragment = server_of(
        recipe("coolify", server, EnvSlot(name="COOLIFY_ACCESS_TOKEN")), CLAUDE_PROJECT
    )

    assert fragment.value["env"] == {
        "COOLIFY_BASE_URL": "https://vps.panlabs.tech",
        "COOLIFY_ACCESS_TOKEN": "${COOLIFY_ACCESS_TOKEN}",
    }


def test_a_bearer_slot_assembles_the_authorization_header_out_of_the_role() -> None:
    """The word `Bearer` is the renderer's, never the recipe's.

    That is what will let a target which assembles the header itself — Codex's
    `bearer_token_env_var` — be served out of this same recipe with no new field.
    """
    fragment = server_of(
        recipe(
            "github",
            HttpServer(url="https://api.githubcopilot.com/mcp"),
            BearerSlot(name="GITHUB_PAT_TOKEN"),
        ),
        CLAUDE_PROJECT,
    )

    assert fragment.value["headers"] == {"Authorization": "Bearer ${GITHUB_PAT_TOKEN}"}


def test_a_header_slot_fills_the_header_it_names() -> None:
    fragment = server_of(
        recipe(
            "paneled",
            HttpServer(url="https://panel.example.com/mcp"),
            HeaderSlot(name="PANEL_TOKEN", header="X-Panel-Token"),
        ),
        CLAUDE_PROJECT,
    )

    assert fragment.value["headers"] == {"X-Panel-Token": "${PANEL_TOKEN}"}


def test_a_recipe_with_no_slot_gets_no_empty_table_to_interpret() -> None:
    """Cloudflare authorises in the browser: there is nothing to fill in, so nothing is written."""
    asked = recipe("cloudflare", HttpServer(url="https://mcp.cloudflare.com/mcp"))

    fragment = server_of(asked, CLAUDE_PROJECT)

    assert fragment.value == {"type": "http", "url": "https://mcp.cloudflare.com/mcp"}


@pytest.mark.parametrize(
    "slotted",
    [
        pytest.param(recipe("env", StdioServer(command="npx"), EnvSlot(name="TOKEN")), id="env"),
        pytest.param(
            recipe("bearer", HttpServer(url="https://x/mcp"), BearerSlot(name="TOKEN")), id="bearer"
        ),
        pytest.param(
            recipe(
                "header",
                HttpServer(url="https://x/mcp"),
                HeaderSlot(name="TOKEN", header="X-Panel-Token"),
            ),
            id="header",
        ),
    ],
)
def test_no_role_ever_renders_a_default(slotted: Recipe) -> None:
    """There is no default in the contract, and the syntax for one is a trap.

    `${VAR:-default}` is Claude Code's alone. In VS Code and in the Copilot CLI —
    which read the very same `.mcp.json` — it reaches the server process
    **literally**: the file parses, the run is green, and the failure appears on
    the first call. Two files of this organisation carry it today.
    """
    rendered = str(server_of(slotted, CLAUDE_PROJECT).value)

    assert "${TOKEN}" in rendered
    assert ":-" not in rendered


@pytest.mark.parametrize(
    "slotted",
    [
        pytest.param(recipe("env", StdioServer(command="npx"), EnvSlot(name="TOKEN")), id="env"),
        pytest.param(
            recipe("bearer", HttpServer(url="https://x/mcp"), BearerSlot(name="TOKEN")), id="bearer"
        ),
    ],
)
def test_a_slot_is_a_reference_and_never_the_value_behind_it(
    slotted: Recipe, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The renderer does not read the environment, so it cannot leak it.

    A value set in the process is exactly the case in which a resolving renderer
    would write the secret into a versioned file, at exit 0.
    """
    monkeypatch.setenv("TOKEN", "SUPER-SECRET-42")

    rendered = str(server_of(slotted, CLAUDE_PROJECT).value)

    assert "SUPER-SECRET-42" not in rendered


# --------------------------------------------------------------------------- #
# the VS Code dialect: `servers`, `${input:}`, and the vault behind `password`
# --------------------------------------------------------------------------- #


def test_the_vscode_fragment_lands_under_the_root_key_that_document_reads() -> None:
    """`servers`, and getting it wrong is the measured silent failure.

    Trap 5 of the research: `mcpServers` inside `.vscode/mcp.json` is a file that
    parses, installs green, and is **inert** — the editor reads a key that is not
    there and says nothing.
    """
    fragment = server_of(recipe("cloudflare", HttpServer(url="https://x/mcp")), VSCODE_PROJECT)

    assert fragment.root_key == "servers"
    assert fragment.dotted == "servers.cloudflare"


def test_a_slot_becomes_a_prompt_reference_and_never_an_environment_one() -> None:
    """`${input:<id>}`, and **never** `${env:VAR}` — the second one is trap 3.

    Measured: VS Code resolves `${env:X}` against the environment of its own
    process, and a variable that is not there becomes the **empty string**, in
    silence. The server comes up unauthenticated and the failure lands on the
    first call, far from the cause. The prompt reference cannot fail that way —
    the editor asks.
    """
    fragment = server_of(
        recipe("git", StdioServer(command="uvx"), EnvSlot(name="GIT_TOKEN")), VSCODE_PROJECT
    )

    assert fragment.value["env"] == {"GIT_TOKEN": "${input:git-token}"}
    assert "${env:" not in str(fragment.value)


def test_a_slot_adds_the_input_that_puts_the_secret_in_the_operating_system_vault() -> None:
    """`password: true` is not cosmetic — it is what turns the encryption on.

    Measured (trap 10): with it, what the user types is encrypted under a key in
    the OS keychain and the ciphertext goes to `state.vscdb`. **Without it the
    value goes in plain text** to the same database. Neither one puts the secret
    in the repository, which is what makes committing the file safe — but only
    one of them makes it safe on the machine.
    """
    inputs = inputs_of(
        recipe("git", StdioServer(command="uvx"), EnvSlot(name="GIT_TOKEN")), VSCODE_PROJECT
    )

    assert inputs is not None
    assert inputs.entries == (
        {"type": "promptString", "id": "git-token", "description": "GIT_TOKEN", "password": True},
    )


def test_the_server_and_its_input_are_two_grafts_of_the_same_recipe() -> None:
    """One recipe, one document, **two keys** — the shape this dialect imposes.

    The reference and the thing it refers to live under different root keys, so
    what a recipe becomes in a document stopped being a single fragment here.
    They are one landing all the same, because they fall in the same file.
    """
    grafts = render(
        recipe("git", StdioServer(command="uvx"), EnvSlot(name="GIT_TOKEN")), VSCODE_PROJECT
    )

    assert tuple(graft.dotted for graft in grafts) == ("servers.git", "inputs")


def test_a_recipe_with_no_slot_asks_for_no_input_at_all() -> None:
    """An empty `inputs[]` is a prompt the user would have to interpret.

    Cloudflare authorises in the browser: there is nothing to fill in, so the
    second graft does not exist rather than existing empty.
    """
    asked = recipe("cloudflare", HttpServer(url="https://mcp.cloudflare.com/mcp"))

    assert inputs_of(asked, VSCODE_PROJECT) is None
    assert len(render(asked, VSCODE_PROJECT)) == 1


def test_a_bearer_slot_assembles_the_header_out_of_the_prompt_reference() -> None:
    """The scheme is the renderer's word and the spelling is the target's.

    Both halves move independently, and this is the case that shows it: the same
    `BearerSlot` that spelled `Bearer ${TOKEN}` one dialect over spells
    `Bearer ${input:token}` here, with nothing in the recipe touched.
    """
    fragment = server_of(
        recipe(
            "github",
            HttpServer(url="https://api.githubcopilot.com/mcp"),
            BearerSlot(name="GITHUB_PAT_TOKEN"),
        ),
        VSCODE_PROJECT,
    )

    assert fragment.value["headers"] == {"Authorization": "Bearer ${input:github-pat-token}"}


def test_every_slot_of_a_recipe_becomes_its_own_input() -> None:
    """Two secrets are two prompts, and the literal beside them is still written.

    The `inputs[]` block is a list and the server's table is a table, so the two
    are asserted together: what belongs in the prompt is only what the recipe
    called a slot.
    """
    server = StdioServer(command="npx", env={"COOLIFY_BASE_URL": "https://vps.panlabs.tech"})
    asked = recipe("coolify", server, EnvSlot(name="COOLIFY_ACCESS_TOKEN"), EnvSlot(name="EXTRA"))

    fragment = server_of(asked, VSCODE_PROJECT)
    inputs = inputs_of(asked, VSCODE_PROJECT)

    assert fragment.value["env"] == {
        "COOLIFY_BASE_URL": "https://vps.panlabs.tech",
        "COOLIFY_ACCESS_TOKEN": "${input:coolify-access-token}",
        "EXTRA": "${input:extra}",
    }
    assert inputs is not None
    assert tuple(entry["id"] for entry in inputs.entries) == ("coolify-access-token", "extra")


def test_the_input_is_identified_by_the_field_the_writer_deduplicates_on() -> None:
    """The plan carries *how* two entries are the same entry, so the writer need not know.

    Two recipes wanting `GITHUB_TOKEN` want **one** prompt, and the append that
    keeps it at one has to be told which field decides. Carrying it here is the
    graft half of *"the writer consumes the plan and nothing beyond it"*.
    """
    inputs = inputs_of(
        recipe("git", StdioServer(command="uvx"), EnvSlot(name="GIT_TOKEN")), VSCODE_PROJECT
    )

    assert inputs is not None
    assert inputs.identity == "id"
    assert inputs.root_key == "inputs"


def test_the_two_dialects_spell_one_recipe_two_ways_with_the_recipe_untouched() -> None:
    """Rule 4 at the point it costs the most: the same slot, two grafias.

    Measured, the two are mutually illegible and **fail in runtime, never in
    parse**: `${GIT_TOKEN}` in the VS Code file is not expanded, and
    `${input:git-token}` in `.mcp.json` reaches the network raw. A recipe that
    stored either string would be right once and silently wrong once.
    """
    asked = recipe("git", StdioServer(command="uvx"), EnvSlot(name="GIT_TOKEN"))

    assert server_of(asked, CLAUDE_PROJECT).value["env"] == {"GIT_TOKEN": "${GIT_TOKEN}"}
    assert server_of(asked, VSCODE_PROJECT).value["env"] == {"GIT_TOKEN": "${input:git-token}"}


# --------------------------------------------------------------------------- #
# the Devin dialect: the same root key, and none of the same spellings
# --------------------------------------------------------------------------- #


def test_the_devin_dialect_lands_under_the_root_key_its_document_names() -> None:
    """`mcpServers`, same word as Claude Code's — and the only thing they share.

    Read off the row rather than asserted as a constant, because the interesting
    property is that two rows agreeing on the root key still disagree on
    everything under it.
    """
    fragment = server_of(recipe("cloudflare", HttpServer(url="https://x/mcp")), DEVIN_PROJECT)

    assert fragment.root_key == DEVIN_PROJECT.root_key == "mcpServers"
    assert fragment.dotted == "mcpServers.cloudflare"


def test_a_devin_http_server_names_the_transport_in_a_field_of_its_own() -> None:
    """`transport`, not `type` — the same fact spelled with a different key.

    Vendor documentation, not measurement, for this specific field
    (`docs/research/mcp-config-formats.md` § Adendo 2026-08-13): the `transport`
    values themselves come from the doc, not from running the binary against an
    account — that slice stayed the weaker grade of evidence even after the
    binary was installed and measured for a sibling question (§ Medição
    2026-08-14). `transport` defaults to `"http"` when absent, and it is written
    anyway for the reason `type` is: the field that ends the guessing costs
    nothing.
    """
    fragment = server_of(
        recipe("cloudflare", HttpServer(url="https://mcp.example.com/mcp")), DEVIN_PROJECT
    )

    assert fragment.value == {"transport": "http", "url": "https://mcp.example.com/mcp"}


def test_a_devin_stdio_server_carries_no_discriminator_because_none_is_documented() -> None:
    """The loader infers stdio from `command`, and there is no `transport` value for it.

    Documented transports are `"http"` and `"sse"`; stdio has no spelling. Making
    one up — `"transport": "stdio"` — would be an unknown value in a target whose
    behaviour on unknown values is **measured, not just inferred from the
    silent neighbours** (`docs/research/mcp-config-formats.md` § Medição
    2026-08-14): Devin swallows unrecognized fields at exit 0, same as they do —
    and goes one step further, reporting malformed JSON as "no servers
    configured" rather than surfacing a parse error. So the field is absent,
    which is the documented shape.
    """
    server = StdioServer(
        command="uvx", args=("mcp-server-git", "."), env={"PANEL": "https://panel.example.com"}
    )

    fragment = server_of(recipe("git", server), DEVIN_PROJECT)

    assert fragment.value == {
        "command": "uvx",
        "args": ["mcp-server-git", "."],
        "env": {"PANEL": "https://panel.example.com"},
    }
    assert "transport" not in fragment.value


def test_a_devin_stdio_server_with_nothing_to_say_writes_no_empty_fields() -> None:
    fragment = server_of(recipe("bare", StdioServer(command="uvx")), DEVIN_PROJECT)

    assert fragment.value == {"command": "uvx"}


def test_a_devin_env_slot_renders_the_third_spelling_of_the_trio() -> None:
    """`${env:VAR}`, which is Cursor's and VS Code's word and not Claude Code's.

    Three targets, three spellings of one name — this is the row that makes rule
    4 an argument rather than a preference. A recipe that stored `${VAR}` would
    be right in `.mcp.json` and reach this server process **literally**, which is
    the measured Copilot CLI failure wearing a different file name.

    **Open doubt, stated rather than papered over.** The vendor documents the
    expansion *"for sensitive fields such as `oauthClientSecret`"*; whether it
    reaches `env` stayed unmeasured even after the binary was installed
    (`docs/research/mcp-config-formats.md` § Medição 2026-08-14) — the MCP
    server process this reference resolves into only spawns inside an
    authenticated session, and no account was reachable from a sandbox. If it
    does not reach, this string arrives raw at the server. The alternative —
    writing the secret's value — is the defect this class exists not to have,
    so the reference is written either way.
    """
    fragment = server_of(
        recipe("hostinger-vps", StdioServer(command="npx"), EnvSlot(name="HOSTINGER_API_TOKEN")),
        DEVIN_PROJECT,
    )

    assert fragment.value["env"] == {"HOSTINGER_API_TOKEN": "${env:HOSTINGER_API_TOKEN}"}


def test_a_devin_literal_and_a_slot_share_the_environment_table_without_mixing() -> None:
    """The address of the panel is written; the token is a reference. Same table."""
    server = StdioServer(command="npx", env={"COOLIFY_BASE_URL": "https://vps.panlabs.tech"})

    fragment = server_of(
        recipe("coolify", server, EnvSlot(name="COOLIFY_ACCESS_TOKEN")), DEVIN_PROJECT
    )

    assert fragment.value["env"] == {
        "COOLIFY_BASE_URL": "https://vps.panlabs.tech",
        "COOLIFY_ACCESS_TOKEN": "${env:COOLIFY_ACCESS_TOKEN}",
    }


def test_a_devin_bearer_slot_assembles_the_authorization_header_out_of_the_role() -> None:
    """The word `Bearer` is the renderer's in both dialects; only the reference moves."""
    fragment = server_of(
        recipe(
            "github",
            HttpServer(url="https://api.githubcopilot.com/mcp"),
            BearerSlot(name="GITHUB_PAT_TOKEN"),
        ),
        DEVIN_PROJECT,
    )

    assert fragment.value["headers"] == {"Authorization": "Bearer ${env:GITHUB_PAT_TOKEN}"}


def test_a_devin_header_slot_fills_the_header_it_names() -> None:
    fragment = server_of(
        recipe(
            "paneled",
            HttpServer(url="https://panel.example.com/mcp"),
            HeaderSlot(name="PANEL_TOKEN", header="X-Panel-Token"),
        ),
        DEVIN_PROJECT,
    )

    assert fragment.value["headers"] == {"X-Panel-Token": "${env:PANEL_TOKEN}"}


def test_the_legacy_transport_devin_would_accept_never_reaches_the_file() -> None:
    """Devin reads `sse`; nothing in this product can ask for it (`Transport`).

    Refusal lives at the **recipe**, not at the target: the closed set has two
    members, so there is no value a recipe could carry that renders to `"sse"`.
    Asserted from the outside — every member of the closed set, rendered, and the
    deprecated word absent from all of it — because *"the enum has two members"*
    is a fact about the enum and this is a fact about the file.
    """
    written = {
        str(server_of(recipe("probe", server), DEVIN_PROJECT).value)
        for server in SERVERS_BY_TRANSPORT.values()
    }

    assert all("sse" not in fragment for fragment in written)


def test_the_devin_dialect_writes_no_field_that_has_no_reader() -> None:
    """`disabled`, `oauthClientId` and `${file:/path}` are documented and unwritten.

    A field with no consumer is a field that goes stale unnoticed — the reasoning
    `McpDocument` states about the file type. `${file:}` in particular is a
    mechanism no other measured target has, and adopting it would put a secret's
    **location** in a committed file on the strength of a doc nobody could run.
    """
    server = StdioServer(command="npx", env={"PANEL": "https://panel.example.com"})

    written = str(server_of(recipe("coolify", server, EnvSlot(name="TOKEN")), DEVIN_PROJECT).value)

    assert "disabled" not in written
    assert "oauth" not in written
    assert "${file:" not in written


@pytest.mark.parametrize(
    "slotted",
    [
        pytest.param(recipe("env", StdioServer(command="npx"), EnvSlot(name="TOKEN")), id="env"),
        pytest.param(
            recipe("bearer", HttpServer(url="https://x/mcp"), BearerSlot(name="TOKEN")), id="bearer"
        ),
    ],
)
def test_the_vscode_dialect_never_reads_the_environment_either(
    slotted: Recipe, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The second dialect is a second chance to leak, and it does not take it."""
    monkeypatch.setenv("TOKEN", "SUPER-SECRET-42")

    assert "SUPER-SECRET-42" not in str(render(slotted, VSCODE_PROJECT))


@pytest.mark.parametrize(
    "slotted",
    [
        pytest.param(recipe("env", StdioServer(command="npx"), EnvSlot(name="TOKEN")), id="env"),
        pytest.param(
            recipe("bearer", HttpServer(url="https://x/mcp"), BearerSlot(name="TOKEN")), id="bearer"
        ),
    ],
)
def test_a_devin_slot_is_a_reference_and_never_the_value_behind_it(
    slotted: Recipe, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One dialect that resolved would be enough to ship the defect, so both are asserted."""
    monkeypatch.setenv("TOKEN", "SUPER-SECRET-42")

    rendered = str(server_of(slotted, DEVIN_PROJECT).value)

    assert "SUPER-SECRET-42" not in rendered
    assert "${env:TOKEN}" in rendered
    assert ":-" not in rendered


# --------------------------------------------------------------------------- #
# which targets a recipe serves — derived, never declared
# --------------------------------------------------------------------------- #

CLAUDE_TARGET = Target(runtime="claude-code", scope=Scope.PROJECT)
"""The pair the tracer bullet measured first."""

VSCODE_TARGET = Target(runtime="vscode", scope=Scope.PROJECT)
"""The second pair, and the one that makes the matrix a matrix."""

DEVIN_TARGET = Target(runtime="devin", scope=Scope.PROJECT)
"""The third pair, read off the table in the order it declares them."""

MACHINE_TARGETS = (
    Target(runtime="claude-code", scope=Scope.GLOBAL),
    Target(runtime="vscode", scope=Scope.GLOBAL),
    Target(runtime="devin", scope=Scope.GLOBAL),
)
"""The same three runtimes in machine scope (#81) — six pairs, three dialects."""

EVERY_TARGET = (CLAUDE_TARGET, VSCODE_TARGET, DEVIN_TARGET, *MACHINE_TARGETS)
"""Every pair on the table, in the order the table declares them."""


def test_a_recipe_is_offered_every_pair_whose_document_can_spell_it() -> None:
    """The answer is a walk of the table, in table order, so it is every row on it."""
    served = targets_of(recipe("cloudflare", HttpServer(url="https://x/mcp")))

    assert served == EVERY_TARGET


def sourced_recipe() -> Recipe:
    """A recipe that brings its own source code, resolved by its own runner."""
    return Recipe(
        name="acme",
        path=Path("acme.toml"),
        description="A server this repository resolves from its own source.",
        server=StdioServer(command="uvx", args=("--from", "git+https://x/y@v1", "acme")),
        source=Source(git="https://x/y", ref="v1", runner=Runner.UVX, entrypoint="acme"),
    )


def test_a_recipe_that_brings_its_own_source_keeps_both_scopes() -> None:
    """ADR 0023: the address renders a static command, so no scope is closed for it.

    ADR 0015 restricted a `source:` recipe to `--global` because the rendered
    command carried the absolute path of a clone; ADR 0023 removed the clone,
    and with it the one fact that made project scope unreachable.
    """
    served = targets_of(sourced_recipe())

    assert {target.scope for target in served} == {Scope.PROJECT, Scope.GLOBAL}


SERVERS_BY_TRANSPORT = {
    Transport.HTTP: HttpServer(url="https://x/mcp"),
    Transport.STDIO: StdioServer(command="uvx"),
}
"""One server per member of the closed set of transports.

Keyed by the member rather than listed, so a third transport arrives as a red
test here instead of as a case nobody wrote.
"""


def test_both_transports_are_served_by_every_target_that_spells_both() -> None:
    """They coincide, and the *reason* they coincide is the point of the test.

    All three documents discriminate the transport with an explicit field —
    `type` in `.mcp.json` and in `.vscode/mcp.json`, both measured, `transport`
    in `.devin/mcp_config.json`, from vendor documentation — so the honest answer
    for `stdio` and for `http` is the same set. The two are asserted side by side
    rather than in one parametrised case so that the day a dialect lands that
    writes only one of them, exactly one of these goes red and names which half
    moved.

    **The known limit, still stated.** Three dialects that all write both leaves
    the transport half of the derivation short of observable: a predicate that
    ignored the transport entirely would keep every test in this file green. What
    is pinned today is the capability against the renderer that has to honour it
    — the test below, now per dialect — and the table half, which
    `test_the_answer_follows_the_table_and_never_the_recipe` moves for real. A
    target that spells one binding is what would make the rest observable.
    """
    over_http = targets_of(recipe("cloudflare", HttpServer(url="https://x/mcp")))
    over_stdio = targets_of(recipe("git", StdioServer(command="uvx")))

    assert over_http == EVERY_TARGET
    assert over_stdio == EVERY_TARGET


def _type_discriminator(value: Mapping[str, JsonValue]) -> str:
    """What `.mcp.json` and `.vscode/mcp.json` are read as: the explicit field, always present."""
    return str(value["type"])


def _devin_discriminator(value: Mapping[str, JsonValue]) -> str:
    """What `.devin/mcp_config.json` will be read as, by the loader's own rule.

    `transport` when it is there, and otherwise stdio inferred from `command` —
    which is the documented inference, transcribed here so the read-back checks
    the file against the loader rather than against the writer.
    """
    if "transport" in value:
        return str(value["transport"])
    assert "command" in value, "a server with no transport field and no command reads as nothing"
    return str(Transport.STDIO)


DIALECTS = [
    pytest.param(CLAUDE_PROJECT, CLAUDE_TRANSPORTS, _type_discriminator, id="claude"),
    pytest.param(VSCODE_PROJECT, VSCODE_TRANSPORTS, _type_discriminator, id="vscode"),
    pytest.param(DEVIN_PROJECT, DEVIN_TRANSPORTS, _devin_discriminator, id="devin"),
]
"""Each dialect with the set it claims and the rule its loader reads it back by.

One case per dialect and never a loop inside one test: a dialect whose promise
and renderer drift apart has to go red **by name**, and a single case covering
all three would only say that one of them did.
"""


@pytest.mark.parametrize(("document", "claimed", "discriminator"), DIALECTS)
def test_the_capability_table_claims_exactly_what_the_dialect_writes(
    document: McpDocument,
    claimed: frozenset[Transport],
    discriminator: Callable[[Mapping[str, JsonValue]], str],
) -> None:
    """The `*_TRANSPORTS` set is a promise, and the renderer is who keeps it.

    The two are one edit apart and drift in silence: a transport added to the
    set without a branch in the renderer offers a target that cannot be written,
    and a branch removed without shrinking the set does the same. So the claim
    is read back out of the **rendered fragment** — what will be in the user's
    file — and compared with the set that decides who is offered.

    Parametrised over the dialects rather than written once per dialect, because
    the claim is about the *pairing* and not about either half: a new dialect is
    a row here and no new prose.

    **Every member of the closed set is rendered, never only the claimed ones.**
    Measured while writing this: filtering the left side by the claimed set makes
    both sides shrink together, so narrowing the set to `{http}` left the test
    green — the same self-consistency P3 refuses in the sdist gate.
    """
    assert set(SERVERS_BY_TRANSPORT) == set(Transport), "a transport with no server to render"

    written = {
        discriminator(server_of(recipe("probe", server), document).value)
        for server in SERVERS_BY_TRANSPORT.values()
    }

    assert written == {str(transport) for transport in claimed}


def test_the_answer_follows_the_table_and_never_the_recipe() -> None:
    """Rule 4, asserted rather than promised: **the same recipe, two answers**.

    A declared field would go stale in silence the day a runtime gained the
    capability, and leave the recipe lying about itself. What proves the field
    does not exist is not its absence — it is that the answer moves when the
    table moves and the recipe is not touched.
    """
    asked = recipe("cloudflare", HttpServer(url="https://x/mcp"))

    assert targets_of(asked, {}) == ()
    assert targets_of(asked, MCP_DOCUMENTS) == EVERY_TARGET


def test_a_second_scope_on_the_table_becomes_another_target() -> None:
    """A pair is (runtime, scope), so the machine scope tripled the answer — not the recipe.

    https://github.com/ThiagoPanini/overpower/issues/81 was the day this test
    was written for. The same recipe is offered six pairs now, and the file that
    moved is the table: `targets_of` is handed a project-only table and answers
    three, handed the real one and answers six.
    """
    project_only = {
        (key, scope): document
        for (key, scope), document in MCP_DOCUMENTS.items()
        if scope is Scope.PROJECT
    }
    asked = recipe("cloudflare", HttpServer(url="https://x/mcp"))

    assert targets_of(asked, project_only) == (CLAUDE_TARGET, VSCODE_TARGET, DEVIN_TARGET)
    assert targets_of(asked, MCP_DOCUMENTS) == EVERY_TARGET


# --------------------------------------------------------------------------- #
# the value handed in, and the one target that declines it (ADR 0024)
# --------------------------------------------------------------------------- #


def test_an_env_slot_takes_the_value_it_was_handed_instead_of_the_reference() -> None:
    """ADR 0024: where the git does not reach, the secret is written and not pointed at.

    The renderer still reads no environment and touches no disk — the value
    arrives as an argument, decided by the caller that asked for it, which is
    what keeps *"the writer consumes the plan and nothing beyond it"* true.
    """
    asked = recipe("hostinger-vps", StdioServer(command="npx"), EnvSlot(name="HOSTINGER_TOKEN"))

    fragment = server_of(asked, CLAUDE_GLOBAL, secrets={"HOSTINGER_TOKEN": "hp_live_x"})

    assert fragment.value["env"] == {"HOSTINGER_TOKEN": "hp_live_x"}


def test_a_literal_and_a_filled_slot_still_share_the_environment_table() -> None:
    """The merge rule does not change when the slot stops being a reference."""
    server = StdioServer(command="npx", env={"COOLIFY_BASE_URL": "https://vps.panlabs.tech"})
    asked = recipe("coolify", server, EnvSlot(name="COOLIFY_ACCESS_TOKEN"))

    fragment = server_of(asked, CLAUDE_GLOBAL, secrets={"COOLIFY_ACCESS_TOKEN": "ct_live_x"})

    assert fragment.value["env"] == {
        "COOLIFY_BASE_URL": "https://vps.panlabs.tech",
        "COOLIFY_ACCESS_TOKEN": "ct_live_x",
    }


def test_a_bearer_slot_assembles_the_header_out_of_the_value_it_was_handed() -> None:
    """`Bearer` is still the renderer's word; only what follows it changed."""
    asked = recipe(
        "github",
        HttpServer(url="https://api.githubcopilot.com/mcp"),
        BearerSlot(name="GITHUB_PAT_TOKEN"),
    )

    fragment = server_of(asked, CLAUDE_GLOBAL, secrets={"GITHUB_PAT_TOKEN": "ghp_x"})

    assert fragment.value["headers"] == {"Authorization": "Bearer ghp_x"}


def test_a_header_slot_carries_the_value_it_was_handed() -> None:
    asked = recipe(
        "paneled",
        HttpServer(url="https://panel.example.com/mcp"),
        HeaderSlot(name="PANEL_TOKEN", header="X-Panel-Token"),
    )

    fragment = server_of(asked, CLAUDE_GLOBAL, secrets={"PANEL_TOKEN": "pt_live_x"})

    assert fragment.value["headers"] == {"X-Panel-Token": "pt_live_x"}


def test_a_slot_nobody_handed_a_value_for_stays_the_reference() -> None:
    """The interactive branch is added on top of the old one, never in place of it.

    A recipe with two slots and one answer writes one value and one reference,
    which is also what an empty answer produces (ADR 0024): the secret leaves
    the file without the product growing a verb for removing it.
    """
    asked = recipe(
        "paneled",
        StdioServer(command="npx"),
        EnvSlot(name="PANEL_TOKEN"),
        EnvSlot(name="OTHER_TOKEN"),
    )

    fragment = server_of(asked, CLAUDE_GLOBAL, secrets={"PANEL_TOKEN": "pt_live_x"})

    assert fragment.value["env"] == {"PANEL_TOKEN": "pt_live_x", "OTHER_TOKEN": "${OTHER_TOKEN}"}


def test_a_devin_slot_takes_the_value_the_same_way_the_claude_one_does() -> None:
    """Both dialects expand out of the environment, so both take the value instead.

    Which is the whole of the rule: the target that cannot store it better is
    the target that receives it.
    """
    asked = recipe("hostinger-vps", StdioServer(command="npx"), EnvSlot(name="HOSTINGER_TOKEN"))

    fragment = server_of(asked, DEVIN_PROJECT, secrets={"HOSTINGER_TOKEN": "hp_live_x"})

    assert fragment.value["env"] == {"HOSTINGER_TOKEN": "hp_live_x"}


def test_the_target_that_keeps_the_secret_in_the_vault_never_takes_the_value() -> None:
    """The measured exception of ADR 0024, and the reason the rule has two halves.

    `inputs[]` with `password: true` is the one spelling in the whole space that
    puts the secret under the protection of the operating system. Writing the
    value into `.vscode/mcp.json` would be strictly **worse** than what the
    product already does, so this target keeps its prompt and is handed nothing.
    """
    asked = recipe("paneled", StdioServer(command="npx"), EnvSlot(name="PANEL_TOKEN"))
    secrets = {"PANEL_TOKEN": "pt_live_x"}

    fragment = server_of(asked, VSCODE_PROJECT, secrets=secrets)
    prompts = inputs_of(asked, VSCODE_PROJECT, secrets)

    assert fragment.value["env"] == {"PANEL_TOKEN": "${input:panel-token}"}
    assert prompts is not None, "the prompt is the mechanism, and it survives the value"
    assert prompts.entries == (
        {
            "type": "promptString",
            "id": "panel-token",
            "description": "PANEL_TOKEN",
            "password": True,
        },
    )
