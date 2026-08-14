"""A recipe that gets past the reader is a recipe that renders.

Mirror of `src/overpower/recipes.py`, over real files in `tmp_path` — the disk
is real, always (ADR 0010), and a recipe *is* a file.

The subject is one property with two halves: a well-formed recipe becomes a
value, and everything else becomes a **named** error. Never a partial
acceptance: a recipe read half-way is a server installed with half a contract,
which fails at runtime far from the cause and is the exact class the graft exists
not to commit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from overpower.recipes import (
    ForbiddenTransportError,
    HttpServer,
    MalformedRecipeError,
    SourcelessSubstitutionError,
    StdioServer,
    Transport,
    UnknownRecipeFieldError,
    read_recipe,
)

if TYPE_CHECKING:
    from pathlib import Path

HTTP = """\
description = "A server reached over HTTP."
transport = "http"

[server]
url = "https://mcp.example.com/mcp"
"""

STDIO = """\
description = "A server the client launches."
transport = "stdio"

[server]
command = "uvx"
args = ["mcp-server-git", "--repository", "."]

[server.env]
PANEL_URL = "https://panel.example.com"
"""


def write_recipe(tmp_path: Path, name: str, text: str) -> Path:
    """One recipe file, exactly as the catalog root carries it."""
    path = tmp_path / f"{name}.toml"
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def test_an_http_recipe_becomes_a_value_carrying_its_url(tmp_path: Path) -> None:
    recipe = read_recipe(write_recipe(tmp_path, "cloudflare", HTTP))

    assert recipe.description == "A server reached over HTTP."
    assert recipe.transport is Transport.HTTP
    assert recipe.server == HttpServer(url="https://mcp.example.com/mcp")


def test_a_stdio_recipe_carries_its_command_its_args_and_its_environment(tmp_path: Path) -> None:
    """`[server.env]` is configuration and not a secret: it is written literally.

    The distinction came from a real server — the address of a panel is not a
    secret, and a schema that could only hold slots would refuse to write it,
    bringing the server up not knowing where to talk.
    """
    recipe = read_recipe(write_recipe(tmp_path, "coolify", STDIO))

    assert recipe.transport is Transport.STDIO
    assert recipe.server == StdioServer(
        command="uvx",
        args=("mcp-server-git", "--repository", "."),
        env={"PANEL_URL": "https://panel.example.com"},
    )


def test_the_slug_comes_from_the_file_name_and_never_from_a_field(tmp_path: Path) -> None:
    """Rule 8: the tree is the catalog, so the name is where the file is."""
    recipe = read_recipe(write_recipe(tmp_path, "hostinger-vps", HTTP))

    assert recipe.name == "hostinger-vps"


@pytest.mark.parametrize(
    "transport",
    [
        pytest.param("sse", id="sse"),
        pytest.param("ws", id="ws"),
        pytest.param("streamable-http", id="streamable-http"),
        pytest.param("STDIO", id="wrong-case"),
    ],
)
def test_a_transport_outside_the_closed_set_is_refused_naming_it(
    tmp_path: Path, transport: str
) -> None:
    """Refused at the recipe, because the target will not refuse it.

    Measured: `type = "sse"` is an unknown field in the Codex config, silently
    swallowed, and the server then connects as streamable HTTP with no message
    and no exit code. `sse` is deprecated in the current revision of the spec and
    `ws` exists in one target only.
    """
    path = write_recipe(
        tmp_path, "odd", HTTP.replace('transport = "http"', f'transport = "{transport}"')
    )

    with pytest.raises(ForbiddenTransportError) as refused:
        read_recipe(path)

    assert refused.value.transport == transport
    assert "stdio, http" in str(refused.value).replace("http, stdio", "stdio, http")


@pytest.mark.parametrize(
    "field",
    [
        pytest.param("[[slots]]\nname = 'TOKEN'\nrole = 'env'\n", id="slots"),
        pytest.param("[[preconditions]]\ncheck = 'command_exists'\nvalue = 'uv'\n", id="precond"),
        pytest.param('[source]\nsubdir = "."\n', id="source"),
        pytest.param('instructions = "ask the team"\n', id="instructions"),
        pytest.param('transports = "http"\n', id="typo"),
        pytest.param('targets = ["claude-code"]\n', id="targets"),
    ],
)
def test_a_field_this_version_cannot_render_is_refused_by_name(tmp_path: Path, field: str) -> None:
    """Ignoring it would install a server with half its contract, at exit 0.

    `targets` is on the list for a different reason from the rest, and it is the
    only one that will **never** arrive: which targets a recipe serves is
    derived from (transport, slot roles, target) and is a table in code — rule 4
    — so a recipe that declared one would be a recipe allowed to lie about
    itself the day a runtime gained the capability. The answer lives in
    `overpower.rendering.targets_of`; here it is refused at the door.
    """
    path = write_recipe(tmp_path, "ahead", f"{HTTP}\n{field}")

    with pytest.raises(UnknownRecipeFieldError) as refused:
        read_recipe(path)

    assert refused.value.path == path


def test_a_field_the_declared_transport_has_no_reader_for_is_refused(tmp_path: Path) -> None:
    """A `url` under `stdio` is a line to change, not a value to correct."""
    path = write_recipe(
        tmp_path,
        "mixed",
        'description = "x"\ntransport = "stdio"\n\n[server]\ncommand = "uvx"\nurl = "https://x/mcp"\n',
    )

    with pytest.raises(UnknownRecipeFieldError) as refused:
        read_recipe(path)

    assert refused.value.key == "server.url"


def test_the_source_token_with_no_source_to_resolve_it_is_refused_by_name(tmp_path: Path) -> None:
    """Written through literally, the server launches against a directory called `{source}`."""
    path = write_recipe(
        tmp_path,
        "homegrown",
        'description = "x"\ntransport = "stdio"\n\n[server]\ncommand = "uv"\n'
        'args = ["run", "--project", "{source}", "server.py"]\n',
    )

    with pytest.raises(SourcelessSubstitutionError) as refused:
        read_recipe(path)

    assert refused.value.key == "server.args"


@pytest.mark.parametrize(
    ("text", "key"),
    [
        pytest.param(
            'transport = "http"\n\n[server]\nurl = "https://x/mcp"\n',
            "description",
            id="no-description",
        ),
        pytest.param(
            'description = "x"\n\n[server]\nurl = "https://x/mcp"\n', "transport", id="no-transport"
        ),
        pytest.param('description = "x"\ntransport = "http"\n', "server", id="no-server"),
        pytest.param(
            'description = "x"\ntransport = "http"\n\n[server]\n', "server.url", id="no-url"
        ),
        pytest.param(
            'description = ""\ntransport = "http"\n\n[server]\nurl = "https://x/mcp"\n',
            "description",
            id="empty-description",
        ),
    ],
)
def test_a_malformed_recipe_names_the_file_and_the_field(
    tmp_path: Path, text: str, key: str
) -> None:
    path = write_recipe(tmp_path, "broken", text)

    with pytest.raises(MalformedRecipeError) as refused:
        read_recipe(path)

    assert refused.value.key == key
    assert str(path) in str(refused.value)


def test_a_file_that_is_not_toml_names_the_recipe_that_would_not_parse(tmp_path: Path) -> None:
    """`tomllib` reports a line and a column and never the file.

    Which recipe would not parse is the first thing whoever reads that message
    needs, and the more so once the file is somebody else's.
    """
    path = write_recipe(tmp_path, "notatoml", "this is not = = toml\n")

    with pytest.raises(MalformedRecipeError) as refused:
        read_recipe(path)

    assert str(path) in str(refused.value)
