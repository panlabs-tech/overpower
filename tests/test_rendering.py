"""The renderer: values in, one fragment out, and no disk anywhere.

Mirror of `src/overpower/rendering.py`. Nothing here is built on a filesystem
and nothing needs a double — the renderer is a pure function, and what it
consumes is a value the reader already validated. The doctrine says so in as
many words: *"no double is born for the renderer; what needs a fixture is the
recipe, which is a value."*

This is where the matrix of target by dialect is asserted. One target today
(https://github.com/panlabs-tech/overpower/issues/76), so the matrix has one
column and the assertions are about **what that column spells** — the root key
it lands under, the explicit `type`, and the fields each transport carries.

It is also where *"which targets a recipe serves"* is proved to be **derived**
(rule 4): the answer is read off the table of documents, so the same recipe —
untouched, byte for byte — answers differently when the table changes.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from overpower.recipes import (
    BearerSlot,
    EnvSlot,
    HeaderSlot,
    HttpServer,
    Recipe,
    Slot,
    StdioServer,
    Transport,
)
from overpower.rendering import CLAUDE_TRANSPORTS, Target, render, targets_of
from overpower.runtimes import MCP_DOCUMENTS, Scope

CLAUDE_PROJECT = MCP_DOCUMENTS[("claude-code", Scope.PROJECT)]
"""The one row the table has, read from the table rather than rebuilt here.

A fixture that spelled `mcpServers` itself could only prove the renderer agrees
with the test; read off the table, it proves the renderer agrees with the row
that decides where the file is.
"""


def recipe(name: str, server: HttpServer | StdioServer, *slots: Slot) -> Recipe:
    return Recipe(
        name=name,
        path=Path(f"{name}.toml"),
        description="A server.",
        server=server,
        slots=slots,
    )


def test_an_http_server_renders_its_url_under_an_explicit_type() -> None:
    """`type` is written even where the loader would infer it.

    Measured: the same `.mcp.json` is read by three runtimes and they infer the
    transport by three different rules, so the one field that ends the guessing
    costs nothing to write.
    """
    fragment = render(
        recipe("cloudflare", HttpServer(url="https://mcp.example.com/mcp")), CLAUDE_PROJECT
    )

    assert fragment.value == {"type": "http", "url": "https://mcp.example.com/mcp"}


def test_a_stdio_server_renders_its_command_its_args_and_its_environment() -> None:
    server = StdioServer(
        command="uvx", args=("mcp-server-git", "."), env={"PANEL": "https://panel.example.com"}
    )

    fragment = render(recipe("git", server), CLAUDE_PROJECT)

    assert fragment.value == {
        "type": "stdio",
        "command": "uvx",
        "args": ["mcp-server-git", "."],
        "env": {"PANEL": "https://panel.example.com"},
    }


def test_a_stdio_server_with_nothing_to_say_writes_no_empty_fields() -> None:
    """An `"args": []` nobody asked for is a field the reader has to interpret."""
    fragment = render(recipe("bare", StdioServer(command="uvx")), CLAUDE_PROJECT)

    assert fragment.value == {"type": "stdio", "command": "uvx"}


def test_the_fragment_names_the_root_key_the_document_reads() -> None:
    fragment = render(recipe("cloudflare", HttpServer(url="https://x/mcp")), CLAUDE_PROJECT)

    assert fragment.root_key == "mcpServers"
    assert fragment.name == "cloudflare"


def test_the_fragment_spells_the_whole_key_path_and_not_just_the_leaf() -> None:
    """It is what the plan prints, and under unconditional overwriting (ADR 0013)
    that line is the reader's only chance to notice the key is theirs."""
    fragment = render(recipe("cloudflare", HttpServer(url="https://x/mcp")), CLAUDE_PROJECT)

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
    fragment = render(
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

    fragment = render(
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
    fragment = render(
        recipe(
            "github",
            HttpServer(url="https://api.githubcopilot.com/mcp"),
            BearerSlot(name="GITHUB_PAT_TOKEN"),
        ),
        CLAUDE_PROJECT,
    )

    assert fragment.value["headers"] == {"Authorization": "Bearer ${GITHUB_PAT_TOKEN}"}


def test_a_header_slot_fills_the_header_it_names() -> None:
    fragment = render(
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

    fragment = render(asked, CLAUDE_PROJECT)

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
    rendered = str(render(slotted, CLAUDE_PROJECT).value)

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

    rendered = str(render(slotted, CLAUDE_PROJECT).value)

    assert "SUPER-SECRET-42" not in rendered


# --------------------------------------------------------------------------- #
# which targets a recipe serves — derived, never declared
# --------------------------------------------------------------------------- #

CLAUDE_TARGET = Target(runtime="claude-code", scope=Scope.PROJECT)
"""The one pair the table has today, which is therefore the whole answer."""


def test_a_recipe_is_offered_every_pair_whose_document_can_spell_it() -> None:
    """The answer is a walk of the table, so today it is the one row on it."""
    served = targets_of(recipe("cloudflare", HttpServer(url="https://x/mcp")))

    assert served == (CLAUDE_TARGET,)


SERVERS_BY_TRANSPORT = {
    Transport.HTTP: HttpServer(url="https://x/mcp"),
    Transport.STDIO: StdioServer(command="uvx"),
}
"""One server per member of the closed set of transports.

Keyed by the member rather than listed, so a third transport arrives as a red
test here instead of as a case nobody wrote.
"""


def test_both_transports_are_served_by_the_one_target_that_is_measured() -> None:
    """They coincide, and the *reason* they coincide is the point of the test.

    `.mcp.json` discriminates the transport with an explicit `type` and writes
    both bindings — measured (`docs/research/mcp-config-formats.md`) — so the
    honest answer for `stdio` and for `http` is the same set. The two are
    asserted side by side rather than in one parametrised case so that the day a
    dialect lands that writes only one of them, exactly one of these two tests
    goes red and names which half moved.

    **The known limit, stated rather than papered over.** With one dialect that
    writes both, *no recipe can tell the transport half of the derivation from a
    tautology*: a predicate that ignored the transport entirely would keep every
    test in this file green. What can be pinned today is the capability itself
    against the renderer that has to honour it — the test below — and the table
    half, which `test_the_answer_follows_the_table_and_never_the_recipe` moves
    for real. The transport half becomes observable with the second target
    (https://github.com/panlabs-tech/overpower/issues/79).
    """
    over_http = targets_of(recipe("cloudflare", HttpServer(url="https://x/mcp")))
    over_stdio = targets_of(recipe("git", StdioServer(command="uvx")))

    assert over_http == (CLAUDE_TARGET,)
    assert over_stdio == (CLAUDE_TARGET,)


def test_the_capability_table_claims_exactly_what_the_dialect_writes() -> None:
    """`CLAUDE_TRANSPORTS` is a promise, and `_claude` is who keeps it.

    The two are one edit apart and drift in silence: a transport added to the
    set without a branch in the renderer offers a target that cannot be written,
    and a branch removed without shrinking the set does the same. So the claim
    is read back out of the **rendered fragment** — the `type` that will be in
    the user's file — and compared with the set that decides who is offered.

    **Every member of the closed set is rendered, never only the claimed ones.**
    Measured while writing this: filtering the left side by `CLAUDE_TRANSPORTS`
    makes both sides shrink together, so narrowing the set to `{http}` left the
    test green — the same self-consistency P3 refuses in the sdist gate.
    """
    assert set(SERVERS_BY_TRANSPORT) == set(Transport), "a transport with no server to render"

    written = {
        str(render(recipe("probe", server), CLAUDE_PROJECT).value["type"])
        for server in SERVERS_BY_TRANSPORT.values()
    }

    assert written == {str(transport) for transport in CLAUDE_TRANSPORTS}


def test_the_answer_follows_the_table_and_never_the_recipe() -> None:
    """Rule 4, asserted rather than promised: **the same recipe, two answers**.

    A declared field would go stale in silence the day a runtime gained the
    capability, and leave the recipe lying about itself. What proves the field
    does not exist is not its absence — it is that the answer moves when the
    table moves and the recipe is not touched.
    """
    asked = recipe("cloudflare", HttpServer(url="https://x/mcp"))

    assert targets_of(asked, {}) == ()
    assert targets_of(asked, MCP_DOCUMENTS) == (CLAUDE_TARGET,)


def test_a_second_scope_on_the_table_becomes_a_second_target() -> None:
    """The machine scope has no MCP document yet, and the day it has one this grows.

    https://github.com/panlabs-tech/overpower/issues/81 is that day. The row is
    built here out of the row that exists, so the test says *"one more pair"*
    and not *"one more format"* — the second half is the dialect's, and it is
    asserted where the dialect is.
    """
    machine = replace(CLAUDE_PROJECT, born_pending=False)
    documents = {**MCP_DOCUMENTS, ("claude-code", Scope.GLOBAL): machine}

    served = targets_of(recipe("cloudflare", HttpServer(url="https://x/mcp")), documents)

    assert served == (CLAUDE_TARGET, Target(runtime="claude-code", scope=Scope.GLOBAL))
