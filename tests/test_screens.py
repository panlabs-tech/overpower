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
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from rich.console import Console, Group

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
from overpower.recipes import (
    BearerSlot,
    Check,
    EnvSlot,
    HeaderSlot,
    HttpServer,
    Precondition,
    Recipe,
    StdioServer,
    role_of,
)
from overpower.rendering import Fragment, Target, targets_of
from overpower.runtimes import Scope
from overpower.screens import (
    BANNER,
    PROGRAM,
    RAIL,
    THEME,
    artifact_screen,
    banner,
    bundle_screen,
    catalog_screen,
    closed,
    doctor_screen,
    framework_screen,
    human,
    installed_screen,
    mcp_screen,
    noted,
    opened,
    plan_screen,
    railed,
    stepped,
    summary_screen,
)
from tests.support.screens import WIDTHS, console, render
from tests.support.snapshots import assert_matches_snapshot

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from rich.console import RenderableType

WIDTH_CASES = [pytest.param(width, id=f"{width}cols") for width in WIDTHS]

TERMINAL_ROWS = 24
"""The rows of the terminal every visual budget in #65 is measured against."""

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
        *(recipe.description for recipe in catalog.mcps),
    ]


def commands_of(catalog: Catalog) -> list[str]:
    """Every line the catalog screen owes, spelled out rather than built from the product.

    The literals are the assertion: a helper that composed them out of
    `overpower.screens`' own pieces would agree with the screen by construction
    and could only ever prove that the screen agrees with itself.
    """
    return [
        *(
            line
            for framework in catalog.frameworks
            for line in (
                f"overpower install --ai-framework {framework.name}",
                f"overpower list --ai-framework {framework.name}",
            )
        ),
        *(f"overpower install --skill {artifact.name}" for artifact in catalog.pool),
        *(
            line
            for bundle in catalog.bundles
            for line in (
                f"overpower install --bundle {bundle.name}",
                f"overpower list --bundle {bundle.name}",
            )
        ),
        *(
            line
            for recipe in catalog.mcps
            for line in (
                f"overpower install --mcp {recipe.name}",
                f"overpower list --mcp {recipe.name}",
            )
        ),
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


MCP_LONG = (
    "A remote MCP server reached over streamable HTTP, described at the length a "
    "description reaches when it has to say what the server touches: it carries no "
    "secret in the file, because the connection authorises in the browser the first "
    "time an agent uses it, and nothing here has to be filled in before it works."
)
"""The wrapping case of the recipe screen. Its shape is the shipped one; its
bytes are ours, so no curation refresh can move a recorded screen."""

MCP_TARGET = Target(runtime="claude-code", scope=Scope.PROJECT)


def recorded_recipe() -> Recipe:
    """The HTTP recipe the detail screen is recorded against: fixed, and ours."""
    return Recipe(
        name="cloudflare",
        path=Path("cloudflare.toml"),
        description=MCP_LONG,
        server=HttpServer(url="https://mcp.cloudflare.com/mcp"),
    )


RECORDED_TARGETS = targets_of(recorded_recipe())
"""What the recorded recipe screens are drawn with — the real answer, not a hand pair.

**Used to be one pair, spelled here rather than derived** — the reasoning was
that a recording moving when the table grew would spend the signal that says
which screens a change had licence to move, and the wiring was asserted through
the command in `test_cli.py` instead. That is exactly what let the cartesian
product go unrecorded (#98): `targets_of` genuinely answers six pairs since
https://github.com/panlabs-tech/overpower/issues/80, and a fixture that answered
one could never have shown a screen paying for the other five, or the day the
factoring in `_target_facts` stopped matching what the table actually returns.
The signal a moving recording buys is worth less than the bug a static one hid.
"""


def recorded_stdio_recipe() -> Recipe:
    """The stdio recipe, and it carries every field that transport admits.

    A command, its arguments and one value of `[server.env]` — which is the
    distinction the schema exists for: the address of a panel is **not** a
    secret, so it is written literally, while a secret is a slot the product
    refuses to write (https://github.com/panlabs-tech/overpower/issues/78).
    Recorded separately from the HTTP one because the two draw different rows,
    and a screen with rows nobody recorded is a screen free to move unseen.

    It carries **a slot and a precondition** because the recorded HTTP recipe
    carries neither: between the two, both states of each row are recorded — the
    row drawn, and the row correctly absent. Recording only the empty state is
    what let two rows the spec asks for be missing without a snapshot moving.
    """
    return Recipe(
        name="coolify",
        path=Path("coolify.toml"),
        description="Drives a Coolify panel from the agent: applications, deployments and logs.",
        server=StdioServer(
            command="uvx",
            args=("mcp-server-coolify", "--panel"),
            env={"COOLIFY_BASE_URL": "https://vps.panlabs.tech"},
        ),
        slots=(EnvSlot(name="COOLIFY_ACCESS_TOKEN"),),
        preconditions=(Precondition(check=Check.COMMAND_EXISTS, value="npx"),),
    )


RECIPE_CASES = [
    pytest.param(case, width, id=f"{transport}-{width}cols")
    for transport, case in (("http", recorded_recipe), ("stdio", recorded_stdio_recipe))
    for width in WIDTHS
]
"""The two shapes of recipe, as callables, the way `DETAIL_CASES` carries units.

A property that has to hold for both is written once and reads the same for
each — and when one goes red the id says which transport drew the line that
broke, which a loop inside one case cannot.
"""


def recorded() -> Catalog:
    """The catalog the screens are recorded against: fixed, and ours.

    The numbers exercise the three units of `human` and both spellings of the
    file count — `948 B · 1 file`, `229.0 KiB · 8 files`, `2.00 MiB · 3 files` —
    which are exactly the formatting paths an edit could break silently.

    The MCP block carries the recipe that weighs nothing, which is the whole
    reason its head line reads a transport where the other three read bytes.
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
        mcps=(recorded_recipe(),),
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
        # Every selection of *this* plan carries copies, and the narrowing says
        # so: what a recipe answers instead is the graft plan's own test.
        stacked = [
            f"{inside.type} {inside.name}"
            for inside in selection.artifacts
            if isinstance(inside, Artifact)
        ]
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


# --------------------------------------------------------------------------- #
# the graft line: a document, a key, and who reads it
# --------------------------------------------------------------------------- #

CLOUDFLARE_URL = "https://mcp.cloudflare.com/mcp"


def recorded_graft() -> Plan:
    """A plan of the second operation: one key, inside a document that is the user's.

    Its own fixture rather than a third selection on `recorded_plan`, and for the
    reason the doctrine gives for one file per screen: the graft line is what
    this ticket adds, so a change to it has to move **its** recording and leave
    the copy plan's at 0%.
    """
    recipe = Recipe(
        name="cloudflare",
        path=Path("cloudflare.toml"),
        description="Cloudflare's remote MCP server, over streamable HTTP.",
        server=HttpServer(url=CLOUDFLARE_URL),
    )
    document = ROOT / ".mcp.json"
    return Plan(
        root=ROOT,
        selections=(
            Selection(
                name="cloudflare",
                artifacts=(recipe,),
                landings=(
                    Landing(
                        place=document,
                        readers=("claude-code",),
                        writes=(
                            Write(
                                source=Fragment(
                                    root_key="mcpServers",
                                    name="cloudflare",
                                    value={"type": "http", "url": CLOUDFLARE_URL},
                                ),
                                destination=DocumentKey(document, "mcpServers.cloudflare"),
                                mode=WriteMode.GRAFT,
                                files=1,
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_plan_names_the_document_and_the_key_it_will_write(width: int) -> None:
    """`.mcp.json › mcpServers.cloudflare ← claude-code`, and the key is the point.

    Under unconditional overwriting (ADR 0013) this line is the whole of the
    reader's defence: a server of the same name is replaced without a question
    and without `--force`, so naming the exact key before the write is what makes
    that decision defensible rather than a surprise.
    """
    joined = unwrapped(render(plan_screen(recorded_graft()), width))

    assert ".mcp.json › mcpServers.cloudflare" in joined
    assert "claude-code" in joined


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_plan_names_the_server_as_what_it_is(width: int) -> None:
    """The stacked list is one grid for both classes, and the noun comes from the data.

    A recipe is not an `Artifact` — it is a declaration with no weight — so what
    the type column shows for one is the answer of the same function that shows
    `skill` for a copy, never a second grid with a second truncation rule.
    """
    rendered = rows(render(plan_screen(recorded_graft()), width))

    assert "mcp server cloudflare" in rendered


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_document_of_a_graft_is_not_spelled_as_a_folder(width: int) -> None:
    """A trailing separator says *folder*, and a graft lands in a file plus a key."""
    joined = unwrapped(render(plan_screen(recorded_graft()), width))

    assert ".mcp.json/" not in joined


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_graft_is_counted_in_keys_and_never_in_paths(width: int) -> None:
    """It creates no path, so counting files there would count something else."""
    joined = unwrapped(render(plan_screen(recorded_graft()), width))

    assert "1 key" in joined
    assert "1 file" not in joined


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_no_rendered_line_of_the_graft_plan_exceeds_the_terminal_width(width: int) -> None:
    rendered = render(plan_screen(recorded_graft()), width)

    assert [line for line in rendered.splitlines() if len(line) > width] == []
    assert "…" not in rendered


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_graft_plan_matches_its_snapshot(request: pytest.FixtureRequest, width: int) -> None:
    rendered = render(plan_screen(recorded_graft()), width)

    assert_matches_snapshot(request, f"plan-graft-{width}", rendered)


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_gate_names_the_document_and_the_key_of_a_graft(width: int) -> None:
    """The gate is the plan one flag apart — it must not degrade the graft on the way."""
    joined = unwrapped(render(summary_screen(recorded_graft()), width))

    assert ".mcp.json › mcpServers.cloudflare" in joined


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_summary_screen_of_a_graft_matches_its_snapshot(
    request: pytest.FixtureRequest, width: int
) -> None:
    rendered = render(summary_screen(recorded_graft()), width)

    assert_matches_snapshot(request, f"summary-graft-{width}", rendered)


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_closing_panel_recovers_the_key_a_graft_wrote(width: int) -> None:
    """#98: the closing screen used to degrade a graft to its bare document path.

    `document › key` is the one line that names what actually landed — under
    unconditional overwriting (ADR 0013) it is the reader's only record of which
    entry was replaced, and it must survive to the very last screen or the
    record it closes with says less than the write did.
    """
    joined = unwrapped(render(installed_screen(recorded_graft(), writes=1, files=1), width))

    assert ".mcp.json › mcpServers.cloudflare" in joined


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_installed_screen_of_a_graft_matches_its_snapshot(
    request: pytest.FixtureRequest, width: int
) -> None:
    rendered = render(installed_screen(recorded_graft(), writes=1, files=1), width)

    assert_matches_snapshot(request, f"installed-graft-{width}", rendered)


# --------------------------------------------------------------------------- #
# #65: the session — the gate, the close, and the punctuation between them
# --------------------------------------------------------------------------- #


def session_screen() -> RenderableType:
    """Every session line in the order `install` prints them, as one recordable screen.

    One screen and not five snapshots, because what the recording is for is the
    **rhythm** — the rail before each mark, the answer indented under its
    question — and that is a property of the sequence rather than of any line
    in it.
    """
    return Group(
        opened("overpower install"),
        noted("31 artifacts available"),
        stepped("Where should this install write to?", "This project"),
        railed(),
        closed("Done!  Review what landed before use; it runs with full agent permission."),
    )


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_session_screen_matches_its_snapshot(
    request: pytest.FixtureRequest, width: int
) -> None:
    rendered = render(session_screen(), width)

    assert_matches_snapshot(request, f"session-{width}", rendered)


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_summary_screen_matches_its_snapshot(
    request: pytest.FixtureRequest, width: int
) -> None:
    rendered = render(summary_screen(recorded_plan()), width)

    assert_matches_snapshot(request, f"summary-{width}", rendered)


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_installed_screen_matches_its_snapshot(
    request: pytest.FixtureRequest, width: int
) -> None:
    rendered = render(installed_screen(recorded_plan(), writes=50, files=148), width)

    assert_matches_snapshot(request, f"installed-{width}", rendered)


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_every_planned_path_appears_on_the_gate_as_well_as_on_the_plan(width: int) -> None:
    """The half of #58 that #65 kept: the gate is shorter, and no path is shorter.

    The artifact list is what left the gate — measured, 34 lines against a
    24-row terminal — and a path may never leave it, because the path is the
    whole of what is being accepted.
    """
    plan = recorded_plan()

    joined = unwrapped(render(summary_screen(plan), width))

    for selection in plan.selections:
        for landing in selection.landings:
            assert landing.place.relative_to(ROOT).as_posix() in joined


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_gate_is_shorter_than_the_plan_it_summarises(width: int) -> None:
    """The measurement that reopened #58's position, asserted rather than remembered.

    At 80 columns the detailed plan of `matt-pocock` is 34 lines against a
    terminal of 24, so the head line naming what is being accepted had scrolled
    by the time the question appeared. The gate has to fit; the audit does not.
    """
    plan = recorded_plan()

    gate = render(summary_screen(plan), width).splitlines()
    audit = render(plan_screen(plan), width).splitlines()

    assert len(gate) < len(audit)
    assert len(gate) <= TERMINAL_ROWS


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_no_rendered_line_of_the_session_exceeds_the_terminal_width(width: int) -> None:
    """The rail and the two frames re-wrap with the terminal, so width is an input."""
    for screen in (
        session_screen(),
        summary_screen(recorded_plan()),
        installed_screen(recorded_plan(), writes=50, files=148),
    ):
        rendered = render(screen, width)
        assert [line for line in rendered.splitlines() if len(line) > width] == []
        assert "…" not in rendered


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_a_framed_screen_hangs_off_the_rail_instead_of_floating_beside_it(width: int) -> None:
    """The one property `rich`'s own `Panel` cannot draw, and the reason `_RailPanel` exists.

    A `Panel` owns all four corners, so it would open on `╭` and close on `╰` —
    a sibling of the session rather than a step inside it. What says *inside* is
    the mark on the title line and the tee that closes back onto the rail.
    """
    lines = render(summary_screen(recorded_plan()), width).splitlines()

    assert lines[0].startswith("◇")
    assert lines[-1].startswith("├")
    assert all(line.startswith((RAIL, "◇", "├")) for line in lines if line)


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


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_catalog_screen_prints_the_line_that_installs_every_item(width: int) -> None:
    """The journey closes here: what `list` shows, it also says how to ask for.

    An AI Framework and a bundle carry something to open, so each of them gets
    the inspection line as well; a pool skill has no artifact inside it to list,
    so one line is the whole of it.
    """
    catalog = shipped()

    joined = unwrapped(render(catalog_screen(catalog), width))

    for command in commands_of(catalog):
        assert command in joined


def test_a_pool_skill_is_not_offered_a_line_that_lists_what_is_inside_it() -> None:
    """There is nothing inside a skill to list, so the second line would be a dead end."""
    catalog = shipped()

    joined = unwrapped(render(catalog_screen(catalog), 80))

    for pool_artifact in catalog.pool:
        assert f"overpower list --skill {pool_artifact.name}" not in joined


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_no_printed_command_carries_a_shell_prompt(width: int) -> None:
    """Measured: with a `$` in front, the selected line pastes back broken.

    Asserted per row rather than over the whole screen, because a `$` inside a
    description is data and says nothing about this property.
    """
    rendered = render(catalog_screen(shipped()), width)

    assert [row for row in rows(rendered) if row.startswith("$")] == []


def test_no_printed_command_wraps_or_carries_a_label_at_eighty_columns() -> None:
    """One row, and the row *is* the command — which is what the two refusals buy.

    A wrapped command loses the half below the fold, and a label column costs
    the width that made it fit: measured at 60 columns the panel body is 54
    characters and `overpower install --skill panlabs-python-standards`
    indented already occupies exactly that. The words `install` and `list`
    inside the command are the label.
    """
    catalog = shipped()

    printed = rows(render(catalog_screen(catalog), 80))

    for command in commands_of(catalog):
        assert command in printed


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_framework_screen_prints_only_the_line_that_installs_it(width: int) -> None:
    """Printing `list --ai-framework <name>` inside the output of that very command is a no-op."""
    framework = shipped().frameworks[0]

    joined = unwrapped(render(framework_screen(framework), width))

    assert f"overpower install --ai-framework {framework.name}" in joined
    assert f"overpower list --ai-framework {framework.name}" not in joined


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_bundle_screen_prints_only_the_line_that_installs_it(width: int) -> None:
    bundle = shipped().bundles[0]

    joined = unwrapped(render(bundle_screen(bundle), width))

    assert f"overpower install --bundle {bundle.name}" in joined
    assert f"overpower list --bundle {bundle.name}" not in joined


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_skill_screen_prints_the_line_that_installs_it(width: int) -> None:
    skill = shipped().pool[0]

    joined = unwrapped(render(artifact_screen(skill), width))

    assert f"overpower install --skill {skill.name}" in joined


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


# --------------------------------------------------------------------------- #
# the showcase: the same screen, of a repository rather than of the wheel
# --------------------------------------------------------------------------- #

SHOWCASE_URL = "https://github.com/owner/repo"
"""The search root the showcase was obtained from, and therefore the tail of
every line it prints. It is a plausible length rather than a short one on
purpose: `overpower install --skill <name> --from <url>` is the longest line the
product prints anywhere, and 60 columns is where that has to be proven."""


def recorded_showcase() -> Catalog:
    """The catalog a `--from` obtention builds: three of the four units, and no fourth.

    A remote catalog carries **no framework** — `--from` never reaches one, and
    since #137 that is the only unit it cannot — so this fixture is the shape the
    anchored walk actually returns, not `recorded()` with fields blanked. That is
    what makes the snapshot able to record the block omission at all: with
    `recorded()` there would be nothing empty to drop.

    The bundle is in it because the bundle block is where the origin makes the
    **longest** line this screen can print — `overpower install --bundle
    api-python --from <url>` — and the width property is measured on the longest
    line or it is not measured. Its `items` are the two skills above it, which is
    the only shape a federated manifest can have: `items` resolve against the
    skills the same repository offers.
    """
    offered = (
        artifact("grilling", "Grills a decision until it gets sharp.", files=1, size=948),
        artifact("heavy-reference", "A reference big enough to read in MiB.", 3, 2_097_152),
    )
    return Catalog(
        frameworks=(),
        pool=offered,
        bundles=(
            Bundle(
                name="api-python",
                description="Equipment for working on a Python API.",
                artifacts=offered,
            ),
        ),
        mcps=(recorded_recipe(),),
    )


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_showcase_matches_its_snapshot(request: pytest.FixtureRequest, width: int) -> None:
    """A screen of its own, because it is one: blocks drop out and every line grows a flag."""
    rendered = render(catalog_screen(recorded_showcase(), SHOWCASE_URL), width)

    assert_matches_snapshot(request, f"showcase-{width}", rendered)


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_no_showcase_line_exceeds_the_terminal_width(width: int) -> None:
    """The one property the origin could break, measured where it is longest.

    Every printed command on this screen carries `--from <url>` that the catalog
    screen's does not, so the showcase is where a line first has room to run off
    the right edge — and at 60 columns it is the whole budget.
    """
    rendered = render(catalog_screen(recorded_showcase(), SHOWCASE_URL), width)

    assert [line for line in rendered.splitlines() if len(line) > width] == []


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_no_showcase_description_is_truncated(width: int) -> None:
    """The property that chose the variant, held under the longer lines."""
    catalog = recorded_showcase()

    rendered = render(catalog_screen(catalog, SHOWCASE_URL), width)

    joined = unwrapped(rendered)
    for description in descriptions_of(catalog):
        assert " ".join(description.split()) in joined
    assert "…" not in rendered


def test_the_showcase_drops_the_block_a_repository_has_no_category_for() -> None:
    """The framework block is the one that cannot appear: it is a folder of this wheel.

    Off the wheel an empty bundle list is a real shape of *this* catalog and its
    heading tells the truth about it. On a showcase a heading over nothing would
    be the screen inventing a category — so an empty block is dropped, and the
    framework block is empty by construction rather than by circumstance.
    """
    joined = unwrapped(render(catalog_screen(recorded_showcase(), SHOWCASE_URL), 80))

    assert "AI Frameworks" not in joined
    assert "Bundles" in joined
    assert "Pool skills" in joined
    assert "MCP servers" in joined


def test_the_showcase_of_a_repository_with_no_manifest_drops_the_bundle_block_too() -> None:
    """The manifest is optional, so its block is dropped by circumstance and not by rule.

    The sibling above proves the framework heading can never appear; this one
    proves the bundle heading appears **only** when there is a manifest to draw
    it from, which is what keeps the drop a property of emptiness rather than a
    second rule about which units the showcase believes in.
    """
    unmanifested = replace(recorded_showcase(), bundles=())

    joined = unwrapped(render(catalog_screen(unmanifested, SHOWCASE_URL), 80))

    assert "Bundles" not in joined
    assert "Pool skills" in joined
    assert "MCP servers" in joined


def test_the_catalog_screen_keeps_every_block_it_always_had() -> None:
    """The other half: the omission is the showcase's, and it may not leak onto the wheel."""
    catalog = Catalog(frameworks=(), pool=(artifact("grilling", "Only this."),), bundles=())

    joined = unwrapped(render(catalog_screen(catalog), 80))

    assert "AI Frameworks" in joined
    assert "Bundles" in joined
    assert "MCP servers" in joined


def test_every_showcase_line_carries_the_origin_it_came_from() -> None:
    """An item read through `--from` is not in the catalog, so the line without it exits 2.

    Asserted over **every** command the screen prints rather than over one,
    because the failure mode is a block that was missed while its siblings were
    threaded. Read off `unwrapped`, which is where a line that the frame broke in
    two is a line again — the same reading `test_no_showcase_line_exceeds_the
    _terminal_width` deliberately does *not* do.
    """
    catalog = recorded_showcase()

    joined = unwrapped(render(catalog_screen(catalog, SHOWCASE_URL), 80))

    for artifact_offered in catalog.pool:
        assert f"{PROGRAM} install --skill {artifact_offered.name} --from {SHOWCASE_URL}" in joined
    for bundle in catalog.bundles:
        assert f"{PROGRAM} install --bundle {bundle.name} --from {SHOWCASE_URL}" in joined
        assert f"{PROGRAM} list --bundle {bundle.name} --from {SHOWCASE_URL}" in joined
    for recipe in catalog.mcps:
        assert f"{PROGRAM} install --mcp {recipe.name} --from {SHOWCASE_URL}" in joined
        assert f"{PROGRAM} list --mcp {recipe.name} --from {SHOWCASE_URL}" in joined
    # And not one command more than the origins: a line the threading missed
    # would raise the first count without raising the second.
    assert joined.count(f"{PROGRAM} ") == joined.count(f"--from {SHOWCASE_URL}")


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


# --------------------------------------------------------------------------- #
# the MCP server: a block of its own, and the recipe whole
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_catalog_screen_gives_the_mcp_servers_a_block_of_their_own(width: int) -> None:
    """The class has to exist on the screen without anyone reading documentation.

    Run against the catalog that **ships**, like the other properties of the
    catalog screen: what is asserted is that every recipe the tree carries
    reaches the block, and the tree is what decides which those are (rule 8).
    """
    catalog = shipped()

    joined = unwrapped(render(catalog_screen(catalog), width))

    assert "MCP servers" in joined
    assert catalog.mcps, "the shipped catalog carries no recipe to show"
    for recipe in catalog.mcps:
        assert recipe.name in joined
        assert " ".join(recipe.description.split()) in joined


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_mcp_screen_shows_the_description_whole(width: int) -> None:
    """The rule the catalog screen already obeys, on the screen a server is judged on.

    A recipe wires a server into an agent, so *"what am I about to connect"* is
    read here — and a description read in halves is one somebody has to go and
    look up elsewhere.
    """
    recipe = recorded_recipe()

    rendered = render(mcp_screen(recipe, RECORDED_TARGETS), width)

    assert " ".join(recipe.description.split()) in unwrapped(rendered)
    assert "…" not in rendered


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_mcp_screen_names_the_transport_and_the_url_of_an_http_recipe(width: int) -> None:
    """Transport on the head line, where the other three units say what they weigh.

    A recipe weighs nothing — it never lands — so what stands in the place a
    size occupies is the fact that decides how the server is reached.
    """
    rendered = rows(render(mcp_screen(recorded_recipe(), RECORDED_TARGETS), width))

    assert "cloudflare http" in rendered
    assert "url https://mcp.cloudflare.com/mcp" in rendered


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_mcp_screen_names_the_command_the_arguments_and_the_environment(width: int) -> None:
    """The stdio half: what will be launched, and what it is launched with.

    `[server.env]` is on the screen because it is written **literally** into the
    user's file, and a value that lands is a value the reader has to see before
    accepting it.
    """
    rendered = rows(render(mcp_screen(recorded_stdio_recipe(), RECORDED_TARGETS), width))

    assert "coolify stdio" in rendered
    assert "command uvx" in rendered
    assert "args mcp-server-coolify --panel" in rendered
    assert "env COOLIFY_BASE_URL https://vps.panlabs.tech" in rendered


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_mcp_screen_names_the_slots_the_recipe_requires_and_the_role_of_each(
    width: int,
) -> None:
    """History 3, and the whole point of it is *before* rather than *after*.

    *"Which slots it requires and the role of each, so I know what secrets I
    need before installing, and do not find out from a 401 afterwards."* The
    name alone would not answer it: a secret bound into a header and a secret
    exported into the environment are two different things to go and arrange,
    and the role is the half that says which.

    The `--dry-run` of `install` is not this row and never was — it is under a
    different verb, it is conditional on the variable being unset, and it never
    names the role at all.
    """
    rendered = rows(render(mcp_screen(recorded_stdio_recipe(), RECORDED_TARGETS), width))

    assert "slots COOLIFY_ACCESS_TOKEN env" in rendered


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_mcp_screen_names_the_preconditions_the_recipe_declares(width: int) -> None:
    """History 5: what this machine has to already have, read before installing.

    The only other surface for a precondition is the refusal that `install`
    raises, which is exactly the *"find out afterwards"* the history exists to
    end. Both halves are on the row because a check with no value names no fact
    — `command_exists` is a question, `npx` is what it asks about.

    The label is `needs` and not `preconditions` for a reason the row next to it
    pays for: measured at 60 columns, the longer word pushes every value right
    and folds the `[server.env]` address mid-token. `_recipe_facts` carries the
    whole argument.
    """
    rendered = rows(render(mcp_screen(recorded_stdio_recipe(), RECORDED_TARGETS), width))

    assert "needs command_exists npx" in rendered


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_a_recipe_declaring_no_slot_and_no_precondition_draws_neither_row(width: int) -> None:
    """The rule `_declared` already keeps: never a row the reader has to interpret.

    An empty `slots` row would read as *"a secret is needed and the product
    could not say which"*, which is worse than the silence it replaces — and it
    is the state the recorded HTTP recipe is in, deliberately.
    """
    rendered = rows(render(mcp_screen(recorded_recipe(), RECORDED_TARGETS), width))

    assert [row for row in rendered if row.startswith(("slots ", "needs "))] == []


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_every_role_a_slot_can_carry_reaches_the_screen(width: int) -> None:
    """Three roles, three spellings on the row, and none of them invented here.

    `bearer` and `header` are separate members for a reason the renderer cares
    about, so a screen that collapsed them would be describing a recipe the
    product does not have. Asserted over the closed set rather than over one
    example, so a fourth role cannot arrive with no row to draw.
    """
    recipe = Recipe(
        name="acme",
        path=Path("acme.toml"),
        description="Three secrets, one per role.",
        server=HttpServer(url="https://mcp.acme.test/mcp"),
        slots=(
            BearerSlot(name="ACME_TOKEN"),
            HeaderSlot(name="ACME_KEY", header="X-Acme-Key"),
        ),
    )

    rendered = rows(render(mcp_screen(recipe, RECORDED_TARGETS), width))

    assert "slots ACME_TOKEN bearer" in rendered
    assert "ACME_KEY header" in rendered
    assert "slots COOLIFY_ACCESS_TOKEN env" in rows(
        render(mcp_screen(recorded_stdio_recipe(), RECORDED_TARGETS), width)
    )


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_what_a_shipped_recipe_declares_reaches_the_screen_that_evaluates_it(
    width: int,
) -> None:
    """The two rows above, against the catalog that actually ships.

    Everything else on this screen is drawn from recipes recorded here, whose
    bytes are ours so curation cannot move a recording. That is the right trade
    for layout and the wrong one for *this* property: the rows were missing for
    as long as they were, in part, because no fixture declared a slot or a
    precondition — so a screen test built only on fixtures could go green over a
    catalog nobody had looked at.

    A rule and not an inventory, in the shape `test_catalog.py` uses: whatever
    the four recipes declare has to be on their screen. It says nothing about
    which recipes exist or what they require, so curation is free to change both
    — it goes red only if something declared stops being shown.
    """
    recipes = shipped().mcps

    assert recipes
    for recipe in recipes:
        rendered = rows(render(mcp_screen(recipe, targets_of(recipe)), width))
        joined = " ".join(rendered)
        for slot in recipe.slots:
            assert slot.name in joined, f"{recipe.name}: {slot.name}"
            assert str(role_of(slot)) in joined, f"{recipe.name}: role of {slot.name}"
        for precondition in recipe.preconditions:
            assert str(precondition.check) in joined, f"{recipe.name}: {precondition.check}"
            assert precondition.value in joined, f"{recipe.name}: {precondition.value}"


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_mcp_screen_names_which_targets_the_recipe_serves(width: int) -> None:
    """The question that decides whether a server serves the reader at all.

    Target and scope are two axes (#98): `targets` names the runtimes, `scopes`
    names where they read — never a runtime alone, because `claude-code` reads
    `.mcp.json` in a repository and reads nothing on the machine, so naming only
    the runtime would promise the half that does not exist.
    """
    rendered = rows(render(mcp_screen(recorded_recipe(), RECORDED_TARGETS), width))

    targets = next(row for row in rendered if row.startswith("targets "))
    scopes = next(row for row in rendered if row.startswith("scopes "))
    assert "claude-code" in targets
    assert "project" in scopes


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_two_scopes_of_one_runtime_factor_into_two_lines_not_two_pairs(width: int) -> None:
    """The cartesian product #98 measured: six lines for three targets, paid for one.

    `claude-code` in both scopes used to cost a row per pair; the two axes
    factor into one `targets` row and one `scopes` row, each runtime and each
    scope named exactly once.
    """
    machine = Target(runtime="claude-code", scope=Scope.GLOBAL)

    rendered = rows(render(mcp_screen(recorded_recipe(), (MCP_TARGET, machine)), width))

    assert "targets claude-code" in rendered
    assert sum(1 for row in rendered if "claude-code" in row) == 1
    assert "scopes project, global" in rendered


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_a_recipe_no_target_can_serve_says_so_rather_than_showing_nothing(width: int) -> None:
    """An empty answer is an answer, and it is the one that decides *"not for me"*.

    A blank row would read as a screen that failed to draw; the word is what
    says the product looked and found no target — which is the state a recipe
    reaches when no runtime this product writes can spell it.
    """
    rendered = rows(render(mcp_screen(recorded_recipe(), ()), width))

    assert "targets none" in rendered


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_mcp_screen_names_every_scope_the_table_has_a_document_for(
    width: int,
) -> None:
    """The screen promises exactly what the table can deliver — no more, no less.

    It used to assert that `global` never appeared, because no machine document
    existed; https://github.com/panlabs-tech/overpower/issues/81 is where it
    gained three. The property is the same one either way and it is derived, not
    typed: the screen is handed `targets_of`, so a scope reaches it only by
    being on the table.
    """
    rendered = render(mcp_screen(recorded_recipe(), targets_of(recorded_recipe())), width)

    assert "global" in rendered
    assert "project" in rendered


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_mcp_screen_prints_the_line_that_installs_it(width: int) -> None:
    """And not the one that opens it: it is the output of that very command."""
    joined = unwrapped(render(mcp_screen(recorded_recipe(), RECORDED_TARGETS), width))

    assert "overpower install --mcp cloudflare" in joined
    assert "overpower list --mcp cloudflare" not in joined


@pytest.mark.parametrize(("case", "width"), RECIPE_CASES)
def test_no_rendered_line_of_an_mcp_screen_exceeds_the_terminal_width(
    case: Callable[[], Recipe], width: int
) -> None:
    """Both shapes of recipe, because they draw different rows.

    A URL and a command line are both single unbreakable runs of characters, and
    a narrow terminal is exactly where a grid decides between wrapping and
    cutting — cutting is what turns a command into one nobody can read back.
    """
    rendered = render(mcp_screen(case(), RECORDED_TARGETS), width)

    assert [line for line in rendered.splitlines() if len(line) > width] == []
    assert "…" not in rendered


def test_a_recipe_no_target_can_serve_says_it_in_the_ink_of_a_warning() -> None:
    """The one word on a `list` screen that is not a fact about equipment.

    Colour is asserted structurally and never recorded — the snapshots are
    colourless by doctrine — so this is the only place *"`none` is not just
    another answer"* can be said. `op.warn` is the ink the `doctor` flags a
    finding in, and it means the same thing here: reading stops for your case.
    """
    target = console(80)

    segments = [
        segment
        for segment in target.render(mcp_screen(recorded_recipe(), ()))
        if "none" in segment.text
    ]

    assert segments, "the empty answer never made it to a segment"
    assert all(
        segment.style is not None and segment.style.color is not None for segment in segments
    )
    assert all(segment.style == THEME.styles["op.warn"] for segment in segments)


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_mcp_screen_matches_its_snapshot(request: pytest.FixtureRequest, width: int) -> None:
    rendered = render(mcp_screen(recorded_recipe(), RECORDED_TARGETS), width)

    assert_matches_snapshot(request, f"list-mcp-{width}", rendered)


@pytest.mark.parametrize("width", WIDTH_CASES)
def test_the_stdio_mcp_screen_matches_its_snapshot(
    request: pytest.FixtureRequest, width: int
) -> None:
    rendered = render(mcp_screen(recorded_stdio_recipe(), RECORDED_TARGETS), width)

    assert_matches_snapshot(request, f"list-mcp-stdio-{width}", rendered)


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
        notices=(),
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
        notices=(),
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


def test_the_doctor_screen_spells_a_destination_the_way_the_plan_spells_it() -> None:
    """One spelling of *a key inside a document*, and both screens use it.

    Built by hand with a `DanglingLink` rather than through an MCP install,
    because the punctuation is not the `doctor`'s to choose regardless of which
    finding carries the destination: the plan prints
    `.mcp.json › mcpServers.cloudflare` before a write, and a report that spelled
    the same thing differently afterwards would make a reader compare two
    notations to answer one question.
    """
    # given
    grafted = DocumentKey(path=ROOT / ".mcp.json", key="mcpServers.context7")
    diagnosis = Diagnosis(
        terminal=Terminal(tty=False, colour="none", width=80, no_color=None),
        root=ROOT,
        home=DOCTOR_HOME,
        landed=(
            Landed(name="context7", scope=Scope.PROJECT, destination=grafted, fingerprint=None),
        ),
        findings=(DanglingLink(destination=grafted, points_at=None),),
        notices=(),
    )

    joined = unwrapped(render(doctor_screen(diagnosis), 80))

    assert ".mcp.json › mcpServers.context7" in joined


@pytest.mark.parametrize(("name", "case", "width"), SNAPSHOT_CASES)
def test_the_doctor_screen_matches_its_snapshot(
    request: pytest.FixtureRequest, name: str, case: Callable[[], Diagnosis], width: int
) -> None:
    rendered = render(doctor_screen(case()), width)

    assert_matches_snapshot(request, f"{name}-{width}", rendered)
