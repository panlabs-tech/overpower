"""The tree is the catalog, and one written file carries what the tree cannot know.

Mirror of `src/overpower/discovery.py` and `src/overpower/written.py`. The two
share a test module because they answer one question between them — *what does
the overpower know how to install* — and the name is the one the test doctrine
fixed for the discovery mirror.

Every tree here is built in `tmp_path`: the disk is real, always (ADR 0010). The
tests that read the tree shipped in the package are the six at the bottom, and
none of them asserts what today's curation put inside it: one says the roots
resolve, one says the root that never lands holds exactly one file, and the other
four assert **rules** the curation has to keep obeying — that an embedded recipe
pins an exact version, that the embedded set reaches every branch the renderer
has, that a recipe launched as a process declares the command that launches it,
and that what the four of them render carries no spelling only one target
understands.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

import pytest

from overpower.discovery import (
    ArtifactType,
    Catalog,
    UnknownArtifactTypeError,
    UnknownNameError,
    discover_frameworks,
    discover_pool,
    load_catalog,
)
from overpower.errors import BadInvocationError, OverpowerError
from overpower.packaged import catalog_file, content_root
from overpower.recipes import MCP_KEY, BearerSlot, Check, EnvSlot, HttpServer, StdioServer
from overpower.rendering import Fragment, Inputs, render
from overpower.runtimes import MCP_DOCUMENTS, Scope
from overpower.written import read_written_catalog

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

LONG_DESCRIPTION = "a" * 517
"""The worst case of *"the whole description, never truncated"*.

517 characters is the maximum measured across the promoted skills in
https://github.com/ThiagoPanini/overpower/issues/10, and the pool skill that
ships in v0.1.0 was chosen for having exactly that description
(https://github.com/ThiagoPanini/overpower/issues/45).
"""


def write_skill(root: Path, name: str, description: str, body: str = "body\n") -> Path:
    """A skill on disk: a directory with a `SKILL.md` carrying frontmatter."""
    skill = root / name
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n{body}",
        encoding="utf-8",
        newline="\n",
    )
    return skill


def write_content(tmp_path: Path) -> Path:
    """A content root with one framework of two skills and one pool skill."""
    content = tmp_path / "content"
    write_skill(content / "pool" / "skills", "panlabs-python-standards", LONG_DESCRIPTION)
    write_skill(content / "frameworks" / "matt-pocock" / "skills", "grilling", "Grills a decision.")
    write_skill(content / "frameworks" / "matt-pocock" / "skills", "tdd", "Red-green-refactor.")
    return content


def write_catalog_file(tmp_path: Path, body: str) -> Path:
    """The one written file, in the sibling root that never lands."""
    path = tmp_path / "catalog" / "catalog.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8", newline="\n")
    return path


def mcp_key(*names: str, url: str = "https://mcp.example.com/mcp") -> str:
    """The `mcp:` key of the written file, one entry per name.

    A recipe never lands, so it has no tree to be discovered in; it is declared
    under a key of the file this module already reads (ADR 0021). Returned as
    text rather than written, because it composes with `WRITTEN` the way a
    document composes — by concatenation.
    """
    lines = [f"{MCP_KEY}:"]
    for name in names:
        lines += [
            f"  {name}:",
            f'    description: "The {name} server."',
            '    transport: "http"',
            "    server:",
            f'      url: "{url}"',
        ]
    return "\n".join(lines) + "\n"


WRITTEN = """
bundles:
  api-python:
    description: Equipment for working on a Python API.
    items: [panlabs-python-standards]

frameworks:
  matt-pocock:
    description: The promoted skills.
"""


# --------------------------------------------------------------------------- #
# discovery
# --------------------------------------------------------------------------- #


def test_a_loose_file_in_the_type_folder_is_not_an_artifact(tmp_path: Path) -> None:
    """#10: the one blind spot of discovery-by-convention. One line of code."""
    # given
    content = write_content(tmp_path)
    (content / "pool" / "skills" / "README.md").write_text("not an artifact\n", encoding="utf-8")

    pool = discover_pool(content / "pool")

    assert [artifact.name for artifact in pool] == ["panlabs-python-standards"]


def test_a_type_directory_outside_the_closed_set_names_the_offending_path(tmp_path: Path) -> None:
    """The set of type names is closed, and a stray directory says which one."""
    # given
    content = write_content(tmp_path)
    stray = content / "pool" / "sklls"
    stray.mkdir()

    with pytest.raises(UnknownArtifactTypeError) as raised:
        discover_pool(content / "pool")

    assert str(stray) in str(raised.value)
    assert isinstance(raised.value, OverpowerError)


def test_a_skill_carries_its_whole_description_from_its_own_skill_md(tmp_path: Path) -> None:
    content = write_content(tmp_path)

    pool = discover_pool(content / "pool")

    assert pool[0].description == LONG_DESCRIPTION


@pytest.mark.parametrize(
    ("frontmatter", "expected"),
    [
        pytest.param("Grills a decision.", "Grills a decision.", id="plain-scalar"),
        pytest.param(
            '"Grills a decision: relentlessly."',
            "Grills a decision: relentlessly.",
            id="scalar-carrying-a-colon",
        ),
        pytest.param(
            ">\n  first half\n  second half",
            "first half second half",
            id="folded-block",
        ),
        pytest.param(
            "|\n  first half\n  second half",
            "first half\nsecond half",
            id="literal-block",
        ),
        pytest.param(
            "first half\n  second half",
            "first half second half",
            id="plain-scalar-over-two-lines",
        ),
    ],
)
def test_a_description_arrives_the_way_yaml_reads_it(
    tmp_path: Path, frontmatter: str, expected: str
) -> None:
    """The shapes a description arrives in, four of them measured across `--from`.

    The two block rows are the correction: the hand-rolled parser this replaced
    kept the marker as the first word of the text, so `description: >` arrived
    as *"> first half second half"*. It was invisible while the product only
    read its own content — 0 of the 26 embedded `SKILL.md` use a block — and it
    becomes a visible defect the day a remote repository's frontmatter renders.

    `>` folds its lines into one and `|` keeps its newline, which is the whole
    difference between the two markers; honouring it is what reading real YAML
    buys. The fifth row is the plain scalar wrapped over two lines, which folds
    for the same reason `>` does and used to be a test of its own.
    """
    content = tmp_path / "content"
    write_skill(content / "pool" / "skills", "described", frontmatter)

    pool = discover_pool(content / "pool")

    assert pool[0].description == expected


def test_a_skill_without_a_description_names_the_file_that_lacks_it(tmp_path: Path) -> None:
    # given
    content = tmp_path / "content"
    skill = content / "pool" / "skills" / "mute"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: mute\n---\n", encoding="utf-8", newline="\n")

    with pytest.raises(OverpowerError) as raised:
        discover_pool(content / "pool")

    assert str(skill / "SKILL.md") in str(raised.value)


def test_frontmatter_that_does_not_parse_names_the_file_and_the_reason(tmp_path: Path) -> None:
    """A real parser refuses where the hand-rolled one guessed, and says why.

    `description: Use when: X` is not YAML — a plain scalar may not carry `: `.
    The refusal repeats the reader's own complaint, which quotes the offending
    line back, so the author fixes what they can see instead of bisecting their
    own file.
    """
    # given
    content = tmp_path / "content"
    skill = write_skill(content / "pool" / "skills", "broken", "Use when: you want a refusal.")

    with pytest.raises(OverpowerError) as raised:
        discover_pool(content / "pool")

    assert str(skill / "SKILL.md") in str(raised.value)
    assert "Use when: you want a refusal." in str(raised.value)


def test_an_artifact_carries_its_size_and_its_file_count(tmp_path: Path) -> None:
    # given
    content = tmp_path / "content"
    skill = write_skill(content / "pool" / "skills", "counted", "Counted.", body="x" * 100)
    (skill / "references").mkdir()
    (skill / "references" / "one.md").write_text("y" * 50, encoding="utf-8", newline="\n")
    expected = sum(path.stat().st_size for path in skill.rglob("*") if path.is_file())

    pool = discover_pool(content / "pool")

    assert pool[0].files == 2
    assert pool[0].size == expected


def test_artifacts_come_back_sorted_by_name(tmp_path: Path) -> None:
    """The order of `iterdir` is the filesystem's; a screen needs one of ours."""
    content = tmp_path / "content"
    for name in ("zulu", "alpha", "mike"):
        write_skill(content / "pool" / "skills", name, f"The {name} skill.")

    pool = discover_pool(content / "pool")

    assert [artifact.name for artifact in pool] == ["alpha", "mike", "zulu"]


def test_a_framework_carries_the_typed_artifacts_below_it(tmp_path: Path) -> None:
    content = write_content(tmp_path)

    frameworks = discover_frameworks(
        content / "frameworks", {"matt-pocock": "The promoted skills."}
    )

    assert [framework.name for framework in frameworks] == ["matt-pocock"]
    assert [(a.type, a.name) for a in frameworks[0].artifacts] == [
        (ArtifactType.SKILL, "grilling"),
        (ArtifactType.SKILL, "tdd"),
    ]


def test_a_framework_weighs_the_sum_of_its_artifacts(tmp_path: Path) -> None:
    content = write_content(tmp_path)

    frameworks = discover_frameworks(
        content / "frameworks", {"matt-pocock": "The promoted skills."}
    )

    assert frameworks[0].files == sum(artifact.files for artifact in frameworks[0].artifacts)
    assert frameworks[0].size == sum(artifact.size for artifact in frameworks[0].artifacts)


def test_a_framework_takes_its_description_from_the_written_file(tmp_path: Path) -> None:
    """A framework has no `SKILL.md`, so this one line is written down."""
    content = write_content(tmp_path)

    frameworks = discover_frameworks(content / "frameworks", {"matt-pocock": "The 22 promoted."})

    assert frameworks[0].description == "The 22 promoted."


def test_a_framework_absent_from_the_written_file_names_itself(tmp_path: Path) -> None:
    content = write_content(tmp_path)

    with pytest.raises(OverpowerError) as raised:
        discover_frameworks(content / "frameworks", {})

    assert "matt-pocock" in str(raised.value)


# --------------------------------------------------------------------------- #
# the written file
# --------------------------------------------------------------------------- #


def test_the_written_file_carries_bundles_and_framework_descriptions(tmp_path: Path) -> None:
    written = read_written_catalog(write_catalog_file(tmp_path, WRITTEN))

    assert written.frameworks == {"matt-pocock": "The promoted skills."}
    assert [bundle.name for bundle in written.bundles] == ["api-python"]
    assert written.bundles[0].items == ("panlabs-python-standards",)


def test_the_written_file_carries_the_recipes_under_the_mcp_key(tmp_path: Path) -> None:
    """One file, one format, one reader (ADR 0021): the recipe is a key of the manifest.

    It is the same key a homemade repository writes in its `.overpower.yaml`, so
    the assertion below is about both provenances at once — there is no second
    place a recipe can come from and no second validator to disagree.
    """
    written = read_written_catalog(
        write_catalog_file(tmp_path, f"{WRITTEN}{mcp_key('cloudflare')}")
    )

    assert [recipe.name for recipe in written.mcps] == ["cloudflare"]
    assert written.mcps[0].server == HttpServer(url="https://mcp.example.com/mcp")


def test_a_key_this_version_does_not_read_is_refused_by_name(tmp_path: Path) -> None:
    """`version:` was considered and refused, and this is what pays for refusing it.

    A closed allowlist answers the field that does not exist by **naming** it,
    which is the better message a version marker would have bought at the cost
    of a line every publisher copies without knowing why (ADR 0021).
    """
    with pytest.raises(OverpowerError) as raised:
        read_written_catalog(write_catalog_file(tmp_path, "version: 1\n"))

    assert "version" in str(raised.value)


def test_a_written_file_that_is_not_a_table_of_tables_says_so(tmp_path: Path) -> None:
    """The decoder returns `object`, so a malformed file fails here and not later."""
    with pytest.raises(OverpowerError) as raised:
        read_written_catalog(write_catalog_file(tmp_path, "bundles: 1\n"))

    assert "bundles" in str(raised.value)


@pytest.mark.parametrize(
    "key",
    [pytest.param("1", id="an-integer"), pytest.param("true", id="a-boolean")],
)
def test_a_written_file_whose_table_key_is_not_a_name_says_so(tmp_path: Path, key: str) -> None:
    """TOML had no key type but string; YAML has, so the key is checked.

    `1:` decodes to the integer `1` and `true:` to the boolean `True`. Under
    TOML this module could cast the table and be telling the truth; under YAML
    the same cast would be a lie living in the one module whose only reason to
    exist is being the type tripwire.
    """
    with pytest.raises(OverpowerError) as raised:
        read_written_catalog(
            write_catalog_file(tmp_path, f"bundles:\n  {key}:\n    description: x\n")
        )

    assert "bundles" in str(raised.value)


def test_a_written_file_that_does_not_parse_at_all_names_the_file(tmp_path: Path) -> None:
    """Unparseable is refused as a named error, never as a library stack.

    It is what the next ticket rests on: the federated manifest is written by a
    stranger, and it reaches this same reader.
    """
    with pytest.raises(OverpowerError) as raised:
        read_written_catalog(write_catalog_file(tmp_path, "bundles:\n  -\n   x: [1,\n"))

    assert "catalog.yaml" in str(raised.value)
    assert "line" in str(raised.value)


def test_a_written_file_with_nothing_in_it_is_an_empty_catalog(tmp_path: Path) -> None:
    """YAML answers `None` to the empty document where TOML answered `{}`.

    An empty manifest is an empty catalog and not a malformed one — the same
    answer the format before it gave, kept on purpose.
    """
    written = read_written_catalog(write_catalog_file(tmp_path, "# nothing yet\n"))

    assert written.bundles == ()
    assert written.frameworks == {}


# --------------------------------------------------------------------------- #
# the catalog the two make together
# --------------------------------------------------------------------------- #


def test_the_catalog_carries_the_three_units(tmp_path: Path) -> None:
    content = write_content(tmp_path)

    catalog = load_catalog(content, write_catalog_file(tmp_path, WRITTEN))

    assert [framework.name for framework in catalog.frameworks] == ["matt-pocock"]
    assert [artifact.name for artifact in catalog.pool] == ["panlabs-python-standards"]
    assert [bundle.name for bundle in catalog.bundles] == ["api-python"]


def test_a_bundle_weighs_the_pool_artifacts_it_names(tmp_path: Path) -> None:
    """A bundle carries no content of its own: its weight is the sum of the names."""
    content = write_content(tmp_path)

    catalog = load_catalog(content, write_catalog_file(tmp_path, WRITTEN))

    named = catalog.pool[0]
    assert catalog.bundles[0].size == named.size
    assert catalog.bundles[0].files == named.files


def test_a_bundle_naming_an_artifact_the_pool_does_not_have_names_both(tmp_path: Path) -> None:
    # given
    content = write_content(tmp_path)
    written = write_catalog_file(
        tmp_path,
        'bundles:\n  api-python:\n    description: "d"\n    items: ["ghost"]\n'
        'frameworks:\n  matt-pocock:\n    description: "d"\n',
    )

    with pytest.raises(OverpowerError) as raised:
        load_catalog(content, written)

    assert "api-python" in str(raised.value)
    assert "ghost" in str(raised.value)


# --------------------------------------------------------------------------- #
# asking the catalog for one item by name
# --------------------------------------------------------------------------- #


def test_the_catalog_finds_each_of_the_three_units_by_name(tmp_path: Path) -> None:
    content = write_content(tmp_path)

    catalog = load_catalog(content, write_catalog_file(tmp_path, WRITTEN))

    assert catalog.framework("matt-pocock").artifacts[0].name == "grilling"
    assert catalog.artifact("panlabs-python-standards").description == LONG_DESCRIPTION
    assert catalog.bundle("api-python").artifacts[0].name == "panlabs-python-standards"


@pytest.mark.parametrize(
    ("lookup", "listed"),
    [
        pytest.param(Catalog.framework, "matt-pocock", id="ai-framework"),
        pytest.param(Catalog.artifact, "panlabs-python-standards", id="pool-artifact"),
        pytest.param(Catalog.bundle, "api-python", id="bundle"),
    ],
)
def test_a_name_the_catalog_does_not_have_carries_the_whole_closed_list(
    tmp_path: Path, lookup: Callable[[Catalog, str], object], listed: str
) -> None:
    """Exit 2 lives on this class, and the list is shown because it is finite."""
    # given
    catalog = load_catalog(write_content(tmp_path), write_catalog_file(tmp_path, WRITTEN))

    with pytest.raises(UnknownNameError) as raised:
        lookup(catalog, "typo")

    assert "typo" in str(raised.value)
    assert listed in str(raised.value)
    assert isinstance(raised.value, BadInvocationError)


def test_a_name_asked_of_an_empty_catalog_says_there_is_none_at_all() -> None:
    """An empty list has no members to show, so the message says that instead."""
    with pytest.raises(UnknownNameError) as raised:
        Catalog(frameworks=(), pool=(), bundles=()).framework("matt-pocock")

    assert "no AI Framework at all" in str(raised.value)


def test_a_skill_added_to_the_tree_appears_without_touching_the_written_file(
    tmp_path: Path,
) -> None:
    """ADR 0006, asserted rather than promised: the tree is the catalog."""
    # given
    content = write_content(tmp_path)
    catalog_file = write_catalog_file(tmp_path, WRITTEN)
    before = catalog_file.read_bytes()

    write_skill(content / "pool" / "skills", "newcomer", "Arrived by mkdir alone.")
    catalog = load_catalog(content, catalog_file)

    assert "newcomer" in [artifact.name for artifact in catalog.pool]
    assert catalog_file.read_bytes() == before


# --------------------------------------------------------------------------- #
# MCP recipes: a key of the written file, and no root of their own
# --------------------------------------------------------------------------- #
#
# There is no walk to test here any more, and its absence is the point. A recipe
# never lands, so it has no tree to be discovered in — it is declared, under
# `mcp:`, in the file the catalog already reads (ADR 0021). The blind spot #10
# measured for a loose file in a type folder went with the folder.


def test_a_recipe_declared_under_the_mcp_key_reaches_the_catalog(tmp_path: Path) -> None:
    """One address locates everything the tree cannot know, recipes included."""
    # given
    content = write_content(tmp_path)
    catalog_path = write_catalog_file(tmp_path, f"{WRITTEN}{mcp_key('cloudflare')}")

    catalog = load_catalog(content, catalog_path)

    assert [recipe.name for recipe in catalog.mcps] == ["cloudflare"]
    assert catalog.mcp("cloudflare").description == "The cloudflare server."


def test_recipes_come_back_sorted_by_slug(tmp_path: Path) -> None:
    """A mapping has no order to preserve, and a screen needs one of ours."""
    # given
    content = write_content(tmp_path)
    declared = mcp_key("hostinger-vps", "cloudflare", "github")
    catalog_path = write_catalog_file(tmp_path, f"{WRITTEN}{declared}")

    catalog = load_catalog(content, catalog_path)

    assert [recipe.name for recipe in catalog.mcps] == ["cloudflare", "github", "hostinger-vps"]


def test_a_written_file_with_no_mcp_key_is_a_catalog_with_no_mcps(tmp_path: Path) -> None:
    """A repository may legitimately declare none, so the absent key is not a failure."""
    catalog = load_catalog(write_content(tmp_path), write_catalog_file(tmp_path, WRITTEN))

    assert catalog.mcps == ()


def test_an_mcp_name_the_catalog_does_not_have_carries_the_whole_closed_list(
    tmp_path: Path,
) -> None:
    # given
    declared = write_catalog_file(tmp_path, f"{WRITTEN}{mcp_key('cloudflare')}")
    catalog = load_catalog(write_content(tmp_path), declared)

    with pytest.raises(UnknownNameError) as raised:
        catalog.mcp("typo")

    assert "cloudflare" in str(raised.value)
    assert isinstance(raised.value, BadInvocationError)


# --------------------------------------------------------------------------- #
# the tree that ships
# --------------------------------------------------------------------------- #


def test_the_packaged_roots_resolve_to_a_loadable_catalog() -> None:
    """Wiring, not content: that the two roots are found, not what is in them.

    Proving the content *arrives inside the wheel* is P1 and P2, and it is not
    observable from pytest — under the `src/` layout the suite imports the source
    tree and would see content the wheel does not have (test doctrine §8).
    """
    catalog = load_catalog(content_root(), catalog_file())

    assert catalog.frameworks
    assert catalog.pool
    assert catalog.bundles
    assert catalog.mcps


PINNED = re.compile(r"@\d+\.\d+\.\d+$")
"""One exact version, at the end of an argument: `major.minor.patch` and nothing else.

`hostinger-api-mcp@0.2.5` and `@masonator/coolify-mcp@2.12.0` match. `pkg@2` does
**not**, and that is the point rather than strictness for its own sake: npm reads
`@2` as a range, so it floats.
"""


def names_a_package(word: str) -> bool:
    """Whether an argument of the launch line names a package to resolve.

    The `@` is the tell, in both spellings npm has: a scope opens with one, a
    version is introduced by one. It does not catch an unscoped name carrying no
    version at all — `npx -y coolify-mcp` reads as a bare word — and that limit
    is why the test below also asserts that a version is pinned *somewhere* on
    the line, rather than resting on this alone.
    """
    return "@" in word


def test_the_root_that_never_lands_ships_exactly_one_file() -> None:
    """The TOML left the product, so `catalog/` is one file again (ADR 0021).

    Asserted as the **whole listing** and not as *"no `.toml` in it"*: what the
    ADR decided is that a repository declares everything it offers in one file,
    and a second file of any name beside this one would be that decision quietly
    coming undone. The recipes are inside it now, so there is nothing left for a
    sibling to be.
    """
    written = catalog_file()

    assert sorted(written.parent.iterdir()) == [written]


def test_every_embedded_stdio_recipe_pins_an_exact_version() -> None:
    """Curation, asserted: an embedded recipe never resolves a package at start-up.

    A server that picks up a new package on every start **changes behaviour with
    nobody having changed anything**, and the version it changed at is written
    down nowhere — which empties rule 5 of the model, *the version of the
    overpower is the version of the catalog*.

    It is a rule of curation and not a field of the schema: a federated recipe
    belongs to whoever wrote it and this product does not police it. What it does
    is not float in its own.
    """
    launched = [
        recipe
        for recipe in load_catalog(content_root(), catalog_file()).mcps
        if isinstance(recipe.server, StdioServer)
    ]

    assert launched
    for recipe in launched:
        server = recipe.server
        assert isinstance(server, StdioServer)
        words = (server.command, *server.args)
        named = [word for word in words if names_a_package(word)]
        assert named, recipe.name
        assert all(PINNED.search(word) for word in named), recipe.name


def test_the_embedded_recipes_exercise_the_matrix_they_were_chosen_for() -> None:
    """The rule the first cut of recipes was chosen by, not the recipes themselves.

    Both transports, a secret in the environment, a secret in a header, a recipe
    with **no** secret at all, and a literal `[server.env]` beside a slot: each is
    a branch of the renderer that an embedded recipe reaches, so a target added
    later cannot pass its own tests while leaving a hole in the shipped catalog.

    The role `header` is deliberately **not** required here. No server this
    organisation runs uses one, and the alternative would be to invent a recipe —
    while the whole point of this set is that none of it is invented: it came out
    of configuration four repositories already keep by hand, which is the very
    configuration the graft exists to stop copying.

    Asserted as **coverage and not as inventory** — `<=`, never `==`. The day
    curation adds a fifth recipe, this test has nothing to say about it; it goes
    red only when a branch stops being reached, which is the only thing it is
    here to notice.
    """
    recipes = load_catalog(content_root(), catalog_file()).mcps
    servers = [recipe.server for recipe in recipes]
    slots = [slot for recipe in recipes for slot in recipe.slots]

    assert {StdioServer, HttpServer} <= {type(server) for server in servers}
    assert {EnvSlot, BearerSlot} <= {type(slot) for slot in slots}
    assert any(not recipe.slots for recipe in recipes)
    assert any(
        isinstance(recipe.server, StdioServer) and recipe.server.env and recipe.slots
        for recipe in recipes
    )


def test_every_embedded_stdio_recipe_declares_the_command_that_launches_it() -> None:
    """Curation, asserted: an embedded recipe never needs tooling it did not declare.

    A recipe launched as a process needs that process to exist, and a machine
    without it is not an error the graft can see: the write succeeds, the exit is
    **0**, and the failure surfaces much later as an obscure error from the agent
    — which is precisely the *"descobrir depois"* that `[[preconditions]]` was
    born to end. What reproved was never *requiring* tooling; it was requiring it
    **without declaring it** (`docs/agents/domain.md`).

    Asserted against the command the recipe itself carries rather than against a
    literal `npx`, so a fifth recipe launched by anything else is held to the
    same rule without this test being edited.
    """
    launched = [
        recipe
        for recipe in load_catalog(content_root(), catalog_file()).mcps
        if isinstance(recipe.server, StdioServer)
    ]

    assert launched
    for recipe in launched:
        server = recipe.server
        assert isinstance(server, StdioServer)
        required = {
            precondition.value
            for precondition in recipe.preconditions
            if precondition.check is Check.COMMAND_EXISTS
        }
        assert server.command in required, recipe.name


def carried_strings(graft: Fragment | Inputs) -> str:
    """Everything a graft would write, as one blob a substring can be looked for in."""
    match graft:
        case Fragment():
            return json.dumps(graft.value)
        case Inputs():
            return json.dumps(graft.entries)


def test_every_embedded_recipe_renders_for_every_dialect_carrying_no_shell_default() -> None:
    """The net under the shipped catalog: the four recipes, actually rendered.

    Nothing rendered an embedded recipe before this. `test_rendering.py` is built
    on values it writes inline — correctly, because the renderer is a pure
    function — so the **literal** path of `[server.env]` was reachable only by
    the recipes nobody exercised, and editing `coolify.toml` to spell its address
    `${COOLIFY_BASE_URL:-https://…}` went in green.

    That spelling is the trap the whole schema exists around: `${VAR:-default}`
    is Claude Code's syntax **alone**, and it reaches the other two targets
    literally, so the server comes up talking to an address with a `:-` in it.
    Rule 4 — *the contract is logical, never literal* — is what this asserts, and
    it asserts it where the contract is broken by curation rather than by code.

    Twelve and not four: every dialect renders every recipe, and a recipe that
    served only some of them would leave a spelling unasserted.
    """
    recipes = load_catalog(content_root(), catalog_file()).mcps
    dialects = ("claude-code", "vscode", "devin")
    documents = [MCP_DOCUMENTS[runtime, Scope.PROJECT] for runtime in dialects]

    rendered = [(recipe, render(recipe, document)) for recipe in recipes for document in documents]

    assert len(rendered) == 12
    for recipe, grafts in rendered:
        assert grafts, recipe.name
        for graft in grafts:
            assert ":-" not in carried_strings(graft), recipe.name
