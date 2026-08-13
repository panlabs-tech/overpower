"""The tree is the catalog, and one written file carries what the tree cannot know.

Mirror of `src/overpower/discovery.py` and `src/overpower/written.py`. The two
share a test module because they answer one question between them — *what does
the overpower know how to install* — and the name is the one the test doctrine
fixed for the discovery mirror.

Every tree here is built in `tmp_path`: the disk is real, always (ADR 0010). The
only test that reads the tree shipped in the package is the wiring one at the
bottom, and it asserts that the two packaged roots resolve — never what today's
curation put inside them.
"""

from __future__ import annotations

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
from overpower.written import read_written_catalog

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

LONG_DESCRIPTION = "a" * 517
"""The worst case of *"the whole description, never truncated"*.

517 characters is the maximum measured across the promoted skills in
https://github.com/panlabs-tech/overpower/issues/10, and the pool skill that
ships in v0.1.0 was chosen for having exactly that description
(https://github.com/panlabs-tech/overpower/issues/45).
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
    path = tmp_path / "catalog" / "catalog.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8", newline="\n")
    return path


def write_mcp(tmp_path: Path, name: str, url: str = "https://mcp.example.com/mcp") -> Path:
    """One recipe, in the third discovery root — beside the written file.

    It never lands, so it cannot live under the root whose invariant is *100%
    lands*; it lives in the root that lands nothing, one file per server.
    """
    path = tmp_path / "catalog" / "mcps" / f"{name}.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'description = "The {name} server."\ntransport = "http"\n\n[server]\nurl = "{url}"\n',
        encoding="utf-8",
        newline="\n",
    )
    return path


WRITTEN = """
[bundles.api-python]
description = "Equipment for working on a Python API."
items = ["panlabs-python-standards"]

[frameworks.matt-pocock]
description = "The promoted skills."
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


def test_a_quoted_description_arrives_without_its_quotes(tmp_path: Path) -> None:
    content = tmp_path / "content"
    write_skill(content / "pool" / "skills", "quoted", '"Grills a decision: relentlessly."')

    pool = discover_pool(content / "pool")

    assert pool[0].description == "Grills a decision: relentlessly."


def test_a_description_wrapped_over_several_lines_arrives_folded(tmp_path: Path) -> None:
    # given
    content = tmp_path / "content"
    skill = content / "pool" / "skills" / "folded"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: folded\ndescription: first half\n  second half\nname2: x\n---\n",
        encoding="utf-8",
        newline="\n",
    )

    pool = discover_pool(content / "pool")

    assert pool[0].description == "first half second half"


def test_a_skill_without_a_description_names_the_file_that_lacks_it(tmp_path: Path) -> None:
    # given
    content = tmp_path / "content"
    skill = content / "pool" / "skills" / "mute"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: mute\n---\n", encoding="utf-8", newline="\n")

    with pytest.raises(OverpowerError) as raised:
        discover_pool(content / "pool")

    assert str(skill / "SKILL.md") in str(raised.value)


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


def test_a_written_file_that_is_not_a_table_of_tables_says_so(tmp_path: Path) -> None:
    """The decoder returns `object`, so a malformed file fails here and not later."""
    with pytest.raises(OverpowerError) as raised:
        read_written_catalog(write_catalog_file(tmp_path, "bundles = 1\n"))

    assert "bundles" in str(raised.value)


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
        '[bundles.api-python]\ndescription = "d"\nitems = ["ghost"]\n'
        '\n[frameworks.matt-pocock]\ndescription = "d"\n',
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
# the third root: MCP recipes
# --------------------------------------------------------------------------- #


def test_a_recipe_dropped_in_the_third_root_is_discovered_by_walking(tmp_path: Path) -> None:
    """Rule 8 again, one root over: adding a server is adding a file."""
    # given
    content = write_content(tmp_path)
    catalog_path = write_catalog_file(tmp_path, WRITTEN)
    write_mcp(tmp_path, "cloudflare")

    catalog = load_catalog(content, catalog_path)

    assert [recipe.name for recipe in catalog.mcps] == ["cloudflare"]
    assert catalog.mcp("cloudflare").description == "The cloudflare server."


def test_recipes_come_back_sorted_by_slug(tmp_path: Path) -> None:
    """`iterdir` answers in the filesystem's order, and a screen needs one of ours."""
    # given
    content = write_content(tmp_path)
    catalog_path = write_catalog_file(tmp_path, WRITTEN)
    for name in ("hostinger-vps", "cloudflare", "github"):
        write_mcp(tmp_path, name)

    catalog = load_catalog(content, catalog_path)

    assert [recipe.name for recipe in catalog.mcps] == ["cloudflare", "github", "hostinger-vps"]


def test_a_file_that_is_not_a_recipe_is_not_an_mcp(tmp_path: Path) -> None:
    """The same blind spot #10 measured for a loose file in a type folder."""
    # given
    content = write_content(tmp_path)
    catalog_path = write_catalog_file(tmp_path, WRITTEN)
    write_mcp(tmp_path, "cloudflare")
    (tmp_path / "catalog" / "mcps" / "README.md").write_text("not a recipe\n", encoding="utf-8")

    catalog = load_catalog(content, catalog_path)

    assert [recipe.name for recipe in catalog.mcps] == ["cloudflare"]


def test_a_catalog_root_with_no_recipes_at_all_is_a_catalog_with_no_mcps(tmp_path: Path) -> None:
    """A tree may legitimately carry none, so the absent root is not a failure."""
    catalog = load_catalog(write_content(tmp_path), write_catalog_file(tmp_path, WRITTEN))

    assert catalog.mcps == ()


def test_an_mcp_name_the_catalog_does_not_have_carries_the_whole_closed_list(
    tmp_path: Path,
) -> None:
    # given
    write_mcp(tmp_path, "cloudflare")
    catalog = load_catalog(write_content(tmp_path), write_catalog_file(tmp_path, WRITTEN))

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
