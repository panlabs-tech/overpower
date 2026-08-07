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

import pytest

from overpower.discovery import Artifact, ArtifactType, Bundle, Catalog, Framework, load_catalog
from overpower.packaged import catalog_file, content_root
from overpower.screens import BANNER, banner, catalog_screen, human
from tests.support.screens import WIDTHS, console, render
from tests.support.snapshots import assert_matches_snapshot

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


def artifact(name: str, description: str, files: int = 1, size: int = 1024) -> Artifact:
    return Artifact(
        type=ArtifactType.SKILL,
        name=name,
        path=Path(name),
        description=description,
        files=files,
        size=size,
    )


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


def recorded() -> Catalog:
    """The catalog the screens are recorded against: fixed, and ours.

    The numbers exercise the three units of `human` and both spellings of the
    file count — `948 B · 1 file`, `229.0 KiB · 8 files`, `2.00 MiB · 3 files` —
    which are exactly the formatting paths an edit could break silently.
    """
    ruler = artifact("panlabs-python-standards", LONG, files=8, size=234_458)
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
            ruler,
        ),
        bundles=(
            Bundle(
                name="api-python",
                description="Equipment for working on a Python API.",
                artifacts=(ruler,),
            ),
        ),
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
