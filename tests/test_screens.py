"""Structure at the gate, snapshot per screen — the test doctrine's §6, applied.

The two halves are on purpose. Measured in
https://github.com/panlabs-tech/overpower/issues/12: **colour does not break
tests and layout does** — changing the brand colour broke zero of nine tests,
because the snapshot froze layout and not colour. So the properties that carry
meaning are asserted structurally here, where an aesthetic tweak cannot move
them, and the bytes are recorded per screen, at 80 and 60 columns, without
colour.

**The structural half runs against the catalog that ships**, and that is the
ticket's own instruction: the truncation property is to be asserted *"com a
descrição de 517 caracteres do pool como caso"*, and the pool skill of v0.1.0 was
picked for having exactly that description — the maximum measured across the
promoted skills (https://github.com/panlabs-tech/overpower/issues/45).

**The recorded half runs against a fixture**, and that is not a shortcut — it is
what makes a snapshot assertable at all. Measured on the Windows cells of the
matrix: a screen built from the shipped tree carries the *byte sizes of the
checkout*, and git rewrites line endings on checkout, so the same commit renders
`199.4 KiB` on Linux and something else on Windows. A recording that cannot be
identical on the nine cells is not a recording. The second reason is the one #12
bought snapshots for: at one file per screen the reviewer sees exactly which
screens a change had licence to move, and a screen that also moves when the
*content* moves gives that signal away.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from overpower.discovery import Artifact, ArtifactType, Bundle, Catalog, Framework, load_catalog
from overpower.packaged import catalog_file, content_root
from overpower.screens import (
    BANNER,
    artifact_screen,
    banner,
    bundle_screen,
    catalog_screen,
    framework_screen,
    human,
)
from tests.support.screens import WIDTHS, console, render
from tests.support.snapshots import assert_matches_snapshot

if TYPE_CHECKING:
    from collections.abc import Callable

    from rich.console import RenderableType

WIDTH_CASES = [pytest.param(width, id=f"{width}cols") for width in WIDTHS]

BANNER_COLUMNS = 50
BANNER_ROWS = 5


def shipped() -> Catalog:
    """The catalog that ships inside the package."""
    return load_catalog(content_root(), catalog_file())


def descriptions_of(catalog: Catalog) -> list[str]:
    return [
        *(framework.description for framework in catalog.frameworks),
        *(artifact.description for artifact in catalog.pool),
        *(bundle.description for bundle in catalog.bundles),
    ]


def unwrapped(rendered: str) -> str:
    """The screen with its frame and its re-wrapping undone.

    A description is allowed to wrap — it is *not* allowed to be cut, and the
    difference is only visible after joining the lines back up.
    """
    lines = [line.strip().strip("│").strip() for line in rendered.splitlines()]
    return " ".join(" ".join(line.split()) for line in lines if line)


def rows(rendered: str) -> list[str]:
    """The screen as rows, with the frame off and every run of spaces collapsed.

    A stacked line reads `skill grilling` here whatever the type column happens
    to be padded to, so the assertion is *the type is the prefix of that line*
    rather than *the type appears somewhere on the screen*.
    """
    return [" ".join(line.strip().strip("│").split()) for line in rendered.splitlines()]


def artifact(
    name: str,
    description: str,
    files: int = 1,
    size: int = 1024,
    artifact_type: ArtifactType = ArtifactType.SKILL,
) -> Artifact:
    return Artifact(
        type=artifact_type,
        name=name,
        path=Path(name),
        description=description,
        files=files,
        size=size,
    )


def framework_case(catalog: Catalog) -> tuple[RenderableType, str]:
    """One detail screen and the description it has to show whole."""
    framework = catalog.frameworks[0]
    return framework_screen(framework), framework.description


def bundle_case(catalog: Catalog) -> tuple[RenderableType, str]:
    bundle = catalog.bundles[0]
    return bundle_screen(bundle), bundle.description


def skill_case(catalog: Catalog) -> tuple[RenderableType, str]:
    skill = catalog.pool[0]
    return artifact_screen(skill), skill.description


DETAIL_CASES = [
    pytest.param(case, width, id=f"{unit}-{width}cols")
    for unit, case in (
        ("framework", framework_case),
        ("bundle", bundle_case),
        ("skill", skill_case),
    )
    for width in WIDTHS
]
"""The three detail screens, as callables rather than as names of a cascade.

Each one is `(Catalog) -> (screen, description)`, so a property that has to hold
across all three is written once and reads the same for each — and adding a
fourth unit is adding a function, not a branch in a dispatcher.
"""


LONG = (
    "A description long enough to wrap at both recorded widths, written out in "
    "full because the property under test is that it arrives whole: the maximum "
    "measured across the promoted skills is 517 characters, cutting at the first "
    "sentence leaves most of them above one line, and a catalog whose "
    "descriptions are cut is a catalog that has to be looked up somewhere else. "
    "It also carries an em dash — and a colon, so the parser and the renderer "
    "are both exercised on something other than plain words."
)
"""The wrapping case of the recorded screen. Its shape is the shipped one; its
bytes are ours, so no curation refresh can move a recorded screen."""


def ruler() -> Artifact:
    """The pool artifact whose description is the wrapping case at both widths."""
    return artifact("panlabs-python-standards", LONG, files=8, size=234_458)


def recorded() -> Catalog:
    """The catalog the screens are recorded against: fixed, and ours.

    The numbers exercise the three units of `human` and both spellings of the
    file count — `948 B · 1 file`, `229.0 KiB · 8 files`, `2.00 MiB · 3 files` —
    which are exactly the formatting paths an edit could break silently.
    """
    return Catalog(
        frameworks=(
            Framework(
                name="matt-pocock",
                path=Path("matt-pocock"),
                description="Agent skills for real engineering: specs, tickets, TDD, review.",
                artifacts=(artifact("grilling", "Inside the framework.", files=74, size=204_186),),
            ),
        ),
        pool=(
            artifact("grilling", "Grills a decision until it gets sharp.", files=1, size=948),
            artifact("heavy-reference", "A reference big enough to read in MiB.", 3, 2_097_152),
            ruler(),
        ),
        bundles=(
            Bundle(
                name="api-python",
                description="Equipment for working on a Python API.",
                artifacts=(ruler(),),
            ),
        ),
    )


def recorded_framework() -> Framework:
    """The framework the detail screen is recorded against, and it mixes types.

    Three types on purpose: the prefix column is driven by the data and not by
    the assumption that a framework is a bag of skills — #11 measured hook files
    landing alongside skills upstream, and rule 1 makes a framework install
    *whole*, so what "whole" means has to be readable before it is accepted.

    The names are of three different lengths so the recording shows the type
    column padded to its widest member. Whether the *shipped* names still fit is
    a different question and a different test — the width one, which runs against
    `shipped()` precisely so no fixture can answer it by choosing short names.
    """
    return Framework(
        name="matt-pocock",
        path=Path("matt-pocock"),
        description="Agent skills for real engineering: specs, tickets, TDD, review.",
        artifacts=(
            artifact("code-reviewer", "Reviews a diff.", 1, 2_048, ArtifactType.AGENT),
            artifact("grilling", "Grills a decision.", 2, 948, ArtifactType.SKILL),
            artifact("setup-matt-pocock-skills", "Wires the repo.", 1, 6_144, ArtifactType.COMMAND),
        ),
    )


def recorded_bundle() -> Bundle:
    """The bundle the detail screen is recorded against.

    Its artifacts are **not** sorted: a bundle is a manifest, so the order on
    screen is the order the curator wrote, and `tdd` before the ruler is what
    proves the screen did not quietly sort them.
    """
    return Bundle(
        name="api-python",
        description="Equipment for working on a Python API.",
        artifacts=(artifact("tdd", "Red-green-refactor.", files=4, size=6_800), ruler()),
    )


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_no_description_is_truncated_at_eighty_or_sixty_columns(width: int) -> None:
    """The property that separated variant F from E: 0 truncations against 2."""
    catalog = shipped()

    rendered = render(catalog_screen(catalog), width)

    joined = unwrapped(rendered)
    for description in descriptions_of(catalog):
        assert " ".join(description.split()) in joined
    assert "…" not in rendered


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_no_rendered_line_exceeds_the_terminal_width(width: int) -> None:
    rendered = render(catalog_screen(shipped()), width)

    assert [line for line in rendered.splitlines() if len(line) > width] == []


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_every_artifact_appears_with_its_size_and_its_file_count(width: int) -> None:
    catalog = shipped()

    joined = unwrapped(render(catalog_screen(catalog), width))

    for framework in catalog.frameworks:
        assert framework.name in joined
        assert f"{human(framework.size)} · {framework.files} file" in joined
    for pool_artifact in catalog.pool:
        assert pool_artifact.name in joined
        assert f"{human(pool_artifact.size)} · {pool_artifact.files} file" in joined


def test_the_section_title_is_not_dim() -> None:
    """#12: rich composes a Panel's `border_style` into its title.

    The border is thin and dim by design, so without `not dim` in the theme the
    heading renders bold DIM magenta — measured `ESC[1;2;35m`. The heading is
    what the thick border used to do and stopped doing, so losing it is losing
    the rank of the screen.
    """
    target = console(80)

    segments = [
        segment
        for segment in target.render(catalog_screen(shipped()))
        if "AI Frameworks" in segment.text
    ]

    assert segments, "the section title never made it to a segment"
    assert all(segment.style is not None and not segment.style.dim for segment in segments)


def test_a_description_that_looks_like_markup_is_printed_and_not_interpreted() -> None:
    """A description is data: it is read off disk, so it can say anything."""
    catalog = Catalog(
        frameworks=(),
        pool=(artifact("bracketed", "Use [bold]this[/] when the tag matters."),),
        bundles=(),
    )

    rendered = render(catalog_screen(catalog), 80)

    assert "[bold]this[/]" in unwrapped(rendered)


def test_the_banner_is_seven_bit_ascii_inside_fifty_columns() -> None:
    """50 x 5, and every byte below 128: the banner has to survive any terminal."""
    lines = BANNER.strip("\n").splitlines()

    assert len(lines) == BANNER_ROWS
    assert max(len(line) for line in lines) <= BANNER_COLUMNS
    assert BANNER.isascii()


def test_a_terminal_too_narrow_for_the_banner_gets_the_short_one() -> None:
    rendered = render(banner("0.1.0", width=40), width=40)

    assert "overpower" in rendered
    assert "_____" not in rendered


def test_the_banner_names_the_version_that_arrived() -> None:
    rendered = render(banner("9.9.9", width=80), width=80)

    assert "9.9.9" in rendered


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_catalog_screen_matches_its_snapshot(
    request: pytest.FixtureRequest, width: int
) -> None:
    rendered = render(catalog_screen(recorded()), width)

    assert_matches_snapshot(request, f"list-{width}", rendered)


def test_a_bundle_says_what_it_names() -> None:
    """A bundle is a manifest, so the names it points at are the content."""
    named = artifact("panlabs-python-standards", "The ruler.")
    catalog = Catalog(
        frameworks=(),
        pool=(named,),
        bundles=(Bundle(name="api-python", description="Equipment.", artifacts=(named,)),),
    )

    joined = unwrapped(render(catalog_screen(catalog), 80))

    assert "api-python" in joined
    assert "Equipment." in joined


# --------------------------------------------------------------------------- #
# the three detail screens: what is inside one item
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(("case", "width"), DETAIL_CASES)
def test_no_detail_screen_has_a_line_wider_than_the_terminal(
    case: Callable[[Catalog], tuple[RenderableType, str]], width: int
) -> None:
    """A narrow terminal is where the frame has the least room to be wrong."""
    screen, _ = case(shipped())

    rendered = render(screen, width)

    assert [line for line in rendered.splitlines() if len(line) > width] == []


@pytest.mark.parametrize(("case", "width"), DETAIL_CASES)
def test_no_detail_screen_truncates_the_description_it_shows(
    case: Callable[[Catalog], tuple[RenderableType, str]], width: int
) -> None:
    """All three re-wrap inside the frame instead of cutting, at 80 and at 60.

    The pool artifact is the extreme case — 517 characters, the maximum measured
    across the promoted skills — but the property is not its alone: a framework
    and a bundle carry a written description on the same screen, and a narrow
    terminal is exactly when a reader most needs the whole of it.
    """
    screen, description = case(shipped())

    rendered = render(screen, width)

    assert " ".join(description.split()) in unwrapped(rendered)
    assert "…" not in rendered


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_framework_screen_prefixes_every_artifact_with_its_type(width: int) -> None:
    """Data-driven, because an AI Framework may mix skill, command and agent."""
    framework = recorded_framework()

    rendered = render(framework_screen(framework), width)

    stacked = [f"{inside.type} {inside.name}" for inside in framework.artifacts]
    assert [row for row in rows(rendered) if row in stacked] == stacked


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_bundle_screen_names_exactly_what_the_manifest_names(width: int) -> None:
    """A bundle is a manifest: the list is the content, in the written order."""
    bundle = recorded_bundle()

    rendered = render(bundle_screen(bundle), width)

    stacked = [f"{inside.type} {inside.name}" for inside in bundle.artifacts]
    assert [row for row in rows(rendered) if row in stacked] == stacked


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_framework_screen_matches_its_snapshot(
    request: pytest.FixtureRequest, width: int
) -> None:
    rendered = render(framework_screen(recorded_framework()), width)

    assert_matches_snapshot(request, f"list-framework-{width}", rendered)


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_bundle_screen_matches_its_snapshot(request: pytest.FixtureRequest, width: int) -> None:
    rendered = render(bundle_screen(recorded_bundle()), width)

    assert_matches_snapshot(request, f"list-bundle-{width}", rendered)


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_skill_screen_matches_its_snapshot(request: pytest.FixtureRequest, width: int) -> None:
    rendered = render(artifact_screen(ruler()), width)

    assert_matches_snapshot(request, f"list-skill-{width}", rendered)


def test_a_framework_says_what_it_weighs() -> None:
    inside = artifact("grilling", "Grills a decision.")
    catalog = Catalog(
        frameworks=(
            Framework(
                name="matt-pocock",
                path=Path("matt-pocock"),
                description="The promoted skills.",
                artifacts=(inside,),
            ),
        ),
        pool=(),
        bundles=(),
    )

    joined = unwrapped(render(catalog_screen(catalog), 80))

    assert "matt-pocock" in joined
    assert f"{human(inside.size)} · 1 file" in joined
