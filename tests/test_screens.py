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

import io
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from rich.console import Console

from overpower.discovery import Artifact, ArtifactType, Bundle, Catalog, Framework, load_catalog
from overpower.inspection import (
    DanglingLink,
    Diagnosis,
    Divergence,
    Landed,
    LinkTurnedText,
    Terminal,
)
from overpower.packaged import catalog_file, content_root
from overpower.planning import (
    DirectoryTree,
    DocumentKey,
    Landing,
    Plan,
    Selection,
    Write,
    WriteMode,
)
from overpower.runtimes import Scope
from overpower.screens import (
    BANNER,
    THEME,
    artifact_screen,
    banner,
    bundle_screen,
    catalog_screen,
    doctor_screen,
    framework_screen,
    human,
    plan_screen,
)
from tests.support.screens import WIDTHS, console, render
from tests.support.snapshots import assert_matches_snapshot

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

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


ROOT = Path("project")
"""The target a recorded plan hangs off. Relative, and never touched: the screen
shows destinations relative to it, so this is path arithmetic and not a disk."""

UNIVERSAL_READERS = (
    "cursor",
    "codex",
    "github-copilot",
    *(f"reader-{index:02d}" for index in range(16)),
)
"""19 runtimes reading one place, which is the case the screen exists for.

`.agents/skills` is shared by 19 of the 76 rows, so a plan that named the
runtime instead of the path would promise Cursor and deliver twenty (ADR 0008).
Three names and a `(+16)` is what the reader gets instead.
"""


def landing(place: str, readers: Sequence[str], carried: Sequence[Artifact]) -> Landing:
    return Landing(
        place=ROOT / place,
        readers=tuple(readers),
        writes=tuple(
            Write(
                source=Path("content") / "pool" / "skills" / inside.name,
                destination=DirectoryTree(ROOT / place / inside.name),
                mode=WriteMode.COPY,
                files=inside.files,
            )
            for inside in carried
        ),
    )


def selected(name: str, carried: Sequence[Artifact]) -> Selection:
    return Selection(
        name=name,
        artifacts=tuple(carried),
        landings=(
            landing(".agents/skills", UNIVERSAL_READERS, carried),
            landing(".claude/skills", ("claude-code",), carried),
        ),
    )


def planned_framework() -> tuple[Artifact, ...]:
    """What the framework selection of the recorded plan carries.

    Its own artifacts and not `recorded_framework`'s, for one reason: **no name
    may repeat across the two selections of the plan**. A name carried twice
    would make *"this row belongs to that selection"* unassertable — the row
    reads identically under either head line — and the plan is precisely the
    screen where two selections stand next to each other. Three types and three
    lengths still, so the type column is recorded padded to its widest member.

    **The recording pairs an `agent` and a `command` with `.claude/skills/`, and
    that is today's product, not a claim about where they belong.** In v0.1.0 the
    place is a function of (runtime, scope) alone — `runtimes._place_of` takes no
    type — so this is exactly what the planner emits for a mixed framework. The
    (type) half of rule 8 grows teeth when a destination table for the other types
    exists; the day it does, this fixture is one of the things that has to move,
    and it says so here rather than being read as an endorsement.
    """
    return (
        artifact("code-reviewer", "Reviews a diff.", 1, 2_048, ArtifactType.AGENT),
        artifact("tdd", "Red-green-refactor.", 2, 948, ArtifactType.SKILL),
        artifact("setup-matt-pocock-skills", "Wires the repo.", 1, 6_144, ArtifactType.COMMAND),
    )


def recorded_plan() -> Plan:
    """The plan the screens are recorded against: fixed, and ours.

    Two selections, so the blank line between them is recorded; two landings
    each, so the collapse of many runtimes into one path is recorded; and both
    spellings of the file count — `4 files` and `1 file` — because those are the
    formatting paths an edit could break in silence.

    The first selection carries **three artifacts of three types**, which is what
    the stacked list is for (#58): a plan that only ever showed one artifact per
    selection would record neither the type column padded to its widest member
    nor the case a reader opens the list *for* — a framework that installs whole.
    The second carries one artifact of its own name, which is the pool skill, and
    it is recorded because that repetition is a deliberate position rather than a
    case the screen forgot.
    """
    return Plan(
        root=ROOT,
        selections=(
            selected("matt-pocock", planned_framework()),
            selected("grilling", (artifact("grilling", "Grills a decision.", files=1, size=948),)),
        ),
    )


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_every_planned_path_appears_in_the_rendered_plan(width: int) -> None:
    """No write may be invisible: the screen is the promise the disk has to keep."""
    plan = recorded_plan()

    joined = unwrapped(render(plan_screen(plan), width))

    for selection in plan.selections:
        assert selection.name in joined
        for landed in selection.landings:
            assert f"{landed.place.relative_to(ROOT).as_posix()}/" in joined


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_plan_names_who_reads_each_path(width: int) -> None:
    """`.agents/skills/ ← cursor, codex, github-copilot (+16)`, never just a runtime.

    Content and not layout, because layout is the snapshot's job: at 60 columns
    the reader list wraps around the right-aligned file count, and asserting the
    one-line spelling here would be asserting the width.
    """
    joined = unwrapped(render(plan_screen(recorded_plan()), width))

    for reader in ("cursor", "codex", "github-copilot", "claude-code"):
        assert reader in joined
    assert "(+16)" in joined


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_plan_names_every_artifact_it_will_write(width: int) -> None:
    """#58: the plan is the last gate before the write, so it says *which* ones.

    The same stacked grid `list` draws — the type as the prefix, one artifact per
    line — and asserted as the *whole* row rather than as a name found somewhere,
    which is what makes the prefix part of the promise: a framework may mix
    skill, command and agent, and a bare list of names would not say which is
    which.
    """
    plan = recorded_plan()

    rendered = rows(render(plan_screen(plan), width))

    for selection in plan.selections:
        stacked = [f"{inside.type} {inside.name}" for inside in selection.artifacts]
        assert [row for row in rendered if row in stacked] == stacked


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_plan_lists_the_artifacts_between_the_selection_and_where_it_lands(
    width: int,
) -> None:
    """Head line, then what it carries, then where it lands — in that order.

    The order is the reading order of the decision: *what did I ask for*, *what
    does that turn out to be*, *where does it go*. A list printed after the paths
    would be a list read after the question it answers.
    """
    rendered = rows(render(plan_screen(recorded_plan()), width))

    head = next(index for index, row in enumerate(rendered) if row.startswith("matt-pocock "))
    listed = next(index for index, row in enumerate(rendered) if row == "agent code-reviewer")
    place = next(index for index, row in enumerate(rendered) if row.startswith(".agents/skills/"))
    assert head < listed < place


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_every_artifact_name_in_the_plan_arrives_whole(width: int) -> None:
    """A name that cannot be read back is a name that cannot be typed back.

    The stacked list is what `--skill <name>` is copied out of, so the property
    is the one the catalog screen already holds for a description. At the two
    recorded widths a name still fits on its line, so *whole* can be asserted as
    the literal string; the widths where it stops fitting are the next test's,
    because a name folded across two lines is not a name that was cut.
    """
    plan = recorded_plan()

    rendered = render(plan_screen(plan), width)

    joined = unwrapped(rendered)
    for selection in plan.selections:
        for inside in selection.artifacts:
            assert inside.name in joined


@pytest.mark.parametrize(
    "width",
    [*WIDTH_CASES, pytest.param(40, id="40cols"), pytest.param(30, id="30cols")],
)
def test_no_artifact_name_in_the_plan_is_ellipsised_at_any_width(width: int) -> None:
    """*"Em largura nenhuma"* (#58), so the two recorded widths are not the test.

    Measured before `_contents` folded: at 40 columns the plan printed
    `skill improve-codebase-archite…`, and neither recorded width could see it —
    every name of the catalog fits on its line at 60. The narrow widths are here
    because they are the ones where a grid decides between wrapping and cutting,
    and cutting is what turns a plan into a name nobody can type back.
    """
    rendered = render(plan_screen(recorded_plan()), width)

    assert "…" not in rendered


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_no_rendered_line_of_the_plan_exceeds_the_terminal_width(width: int) -> None:
    rendered = render(plan_screen(recorded_plan()), width)

    assert [line for line in rendered.splitlines() if len(line) > width] == []
    assert "…" not in rendered


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_plan_screen_matches_its_snapshot(request: pytest.FixtureRequest, width: int) -> None:
    rendered = render(plan_screen(recorded_plan()), width)

    assert_matches_snapshot(request, f"plan-{width}", rendered)


@pytest.mark.parametrize(
    ("encoding", "expected"),
    [pytest.param("utf-8", "←", id="utf-8"), pytest.param("cp1252", "<-", id="cp1252")],
)
def test_the_arrow_follows_what_the_encoding_can_carry(encoding: str, expected: str) -> None:
    """Measured: `←` is not in cp1252, which is what a pipe on Windows takes.

    Rich writes text straight to the file, so a hard-coded arrow raises
    `UnicodeEncodeError` out of the middle of the screen — on three of the nine
    cells and nowhere else. Writing to a stream that carries the encoding is the
    only honest measurement, and the write itself is half the assertion.
    """
    stream = io.TextIOWrapper(io.BytesIO(), encoding=encoding, newline="")
    target = Console(
        file=stream,
        record=True,
        width=80,
        force_terminal=True,
        legacy_windows=False,
        no_color=True,
        highlight=False,
        theme=THEME,
    )

    target.print(plan_screen(recorded_plan()))

    assert expected in target.export_text(clear=False, styles=False)


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


@pytest.mark.parametrize(
    "width",
    [pytest.param(80, id="80cols"), pytest.param(60, id="60cols"), pytest.param(40, id="40cols")],
)
def test_the_banner_teaches_the_alias_at_every_width(width: int) -> None:
    """#58: the tip travels with the banner, so it survives the narrow branch too.

    40 columns is below `BANNER_WIDTH`, where the art is dropped for a single
    line — and the shortcut is not art. The line is typed out here rather than
    read off the module: what is promised is the shell line someone pastes, and
    a constant asserted against itself promises nothing.
    """
    rendered = render(banner("0.1.0", width=width), width=width)

    assert "alias op='overpower'" in " ".join(rendered.split())


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


# --------------------------------------------------------------------------- #
# the `doctor`: the terminal, and the integrity of what landed
# --------------------------------------------------------------------------- #


DOCTOR_HOME = Path("home")
"""What the machine half hangs off. Relative and never touched, like `ROOT`:
the screen shortens a path against it, so this is arithmetic and not a disk."""

CLAUDE_SKILLS = ROOT / ".claude" / "skills"
AGENTS_SKILLS = ROOT / ".agents" / "skills"
CURSOR_SKILLS = DOCTOR_HOME / ".cursor" / "skills"


def landed(
    place: Path, name: str, scope: Scope = Scope.PROJECT, digest: str | None = "a"
) -> Landed:
    return Landed(
        name=name, scope=scope, destination=DirectoryTree(place / name), fingerprint=digest
    )


def recorded_diagnosis() -> Diagnosis:
    """The `doctor` output the screens are recorded against: fixed, and ours.

    All three findings at once, because they are three different shapes on the
    page — one place and a target, one place and a file inside it, and a list of
    places under one name — and a recording that carried only one of them would
    leave the other two free to move unseen.

    Both scopes too: a project path shortens against the repository and a machine
    path against the home, and a screen that reported both roots the same way
    would be a screen a reader has to guess at.
    """
    return Diagnosis(
        terminal=Terminal(tty=True, colour="truecolor", width=80, no_color=None),
        root=ROOT,
        home=DOCTOR_HOME,
        landed=(
            landed(CLAUDE_SKILLS, "grilling"),
            landed(CLAUDE_SKILLS, "panlabs-python-standards"),
            landed(AGENTS_SKILLS, "grilling"),
            landed(AGENTS_SKILLS, "panlabs-python-standards", digest="b"),
            landed(CURSOR_SKILLS, "grilling", Scope.GLOBAL, digest=None),
        ),
        findings=(
            DanglingLink(
                destination=DirectoryTree(CURSOR_SKILLS / "grilling"),
                points_at="../../.claude/skills/grilling",
            ),
            LinkTurnedText(
                destination=DirectoryTree(CLAUDE_SKILLS / "grilling"),
                inside=CLAUDE_SKILLS / "grilling" / "alias.md",
                points_at="SKILL.md",
            ),
            Divergence(
                name="panlabs-python-standards",
                scope=Scope.PROJECT,
                destinations=(
                    DirectoryTree(CLAUDE_SKILLS / "panlabs-python-standards"),
                    DirectoryTree(AGENTS_SKILLS / "panlabs-python-standards"),
                ),
            ),
        ),
    )


def recorded_healthy_diagnosis() -> Diagnosis:
    """The screen a green CI run gets, which is the one most people ever see.

    A screen of its own and not a variant of the one above: `--dry-run` and
    `doctor` are the two commands read by a pipeline, and *nothing is wrong* has
    to be as unmistakable as *something is*.
    """
    return Diagnosis(
        terminal=Terminal(tty=False, colour="none", width=80, no_color="1"),
        root=ROOT,
        home=DOCTOR_HOME,
        landed=(landed(CLAUDE_SKILLS, "grilling"), landed(AGENTS_SKILLS, "grilling")),
        findings=(),
    )


DIAGNOSIS_CASES = [
    pytest.param(case, width, id=f"{state}-{width}cols")
    for state, case in (("found", recorded_diagnosis), ("healthy", recorded_healthy_diagnosis))
    for width in WIDTHS
]

SNAPSHOT_CASES = [
    pytest.param(name, case, width, id=f"{name}-{width}cols")
    for name, case in (
        ("doctor", recorded_diagnosis),
        ("doctor-healthy", recorded_healthy_diagnosis),
    )
    for width in WIDTHS
]
"""The recorded screens, carrying their own file name.

The name is a parameter and not something the test recovers by comparing the
callable it was handed: a snapshot file is identity, so the id in the report and
the file on disk have to come from one place.
"""


@pytest.mark.parametrize(("case", "width"), DIAGNOSIS_CASES)
def test_no_rendered_line_of_the_doctor_screen_exceeds_the_terminal_width(
    case: Callable[[], Diagnosis], width: int
) -> None:
    """A path is the whole of what a diagnosis asks someone to act on.

    So it re-wraps and is never cut — the same property the catalog screen holds
    for a description, asserted here on the screen whose content is paths.
    """
    rendered = render(doctor_screen(case()), width)

    assert [line for line in rendered.splitlines() if len(line) > width] == []
    assert "…" not in rendered


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_doctor_screen_names_every_place_it_found_something_in(width: int) -> None:
    """No finding may be invisible, and a path is how a finding gets acted on."""
    diagnosis = recorded_diagnosis()

    joined = unwrapped(render(doctor_screen(diagnosis), width))

    assert "~/.cursor/skills/grilling/" in joined
    assert "alias.md" in joined
    for place in (".claude/skills", ".agents/skills"):
        assert f"{place}/panlabs-python-standards/" in joined


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_doctor_screen_counts_artifacts_and_places_separately(width: int) -> None:
    """Two numbers and never one: an artifact occupies as many places as it landed in.

    A single number would be the screen assuming one artifact costs one write,
    which is the shape `domain.md` locks against for the graft — where one
    artifact costs a second write, possibly outside the repository.
    """
    joined = unwrapped(render(doctor_screen(recorded_diagnosis()), width))

    assert "3 artifacts · 5 places" in joined


def test_the_doctor_screen_spells_a_destination_that_is_a_document_key() -> None:
    """The graft class exists in the model, and the `doctor` can already say it.

    Built by hand because nothing in the v0.1.0 catalog produces one — there is
    no MCP server and no hook — exactly as `test_writing.py` builds one to assert
    that the write path refuses it by name. A report that could only spell a
    folder would be a report v0.2 has to replace instead of extend.
    """
    # given
    grafted = DocumentKey(path=ROOT / ".mcp.json", key="context7")
    diagnosis = Diagnosis(
        terminal=Terminal(tty=False, colour="none", width=80, no_color=None),
        root=ROOT,
        home=DOCTOR_HOME,
        landed=(
            Landed(name="context7", scope=Scope.PROJECT, destination=grafted, fingerprint=None),
        ),
        findings=(DanglingLink(destination=grafted, points_at=None),),
    )

    joined = unwrapped(render(doctor_screen(diagnosis), 80))

    assert ".mcp.json#context7" in joined


@pytest.mark.parametrize(("name", "case", "width"), SNAPSHOT_CASES)
def test_the_doctor_screen_matches_its_snapshot(
    request: pytest.FixtureRequest, name: str, case: Callable[[], Diagnosis], width: int
) -> None:
    rendered = render(doctor_screen(case()), width)

    assert_matches_snapshot(request, f"{name}-{width}", rendered)
