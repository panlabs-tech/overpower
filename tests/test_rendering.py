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
"""

from __future__ import annotations

from pathlib import Path

from overpower.recipes import HttpServer, Recipe, StdioServer
from overpower.rendering import render
from overpower.runtimes import MCP_DOCUMENTS, Scope

CLAUDE_PROJECT = MCP_DOCUMENTS[("claude-code", Scope.PROJECT)]
"""The one row the table has, read from the table rather than rebuilt here.

A fixture that spelled `mcpServers` itself could only prove the renderer agrees
with the test; read off the table, it proves the renderer agrees with the row
that decides where the file is.
"""


def recipe(name: str, server: HttpServer | StdioServer) -> Recipe:
    return Recipe(name=name, path=Path(f"{name}.toml"), description="A server.", server=server)


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
