"""The table is a transcription, so most of what is worth asserting is shape.

The counts below are the ones the map states out loud — in
https://github.com/panlabs-tech/overpower/issues/18, in ADR 0008 and in
`docs/agents/domain.md`. Pinning them here is what turns "76 runtimes, 55
project paths" from prose into something that breaks when a refresh changes it.
"""

from __future__ import annotations

import sys
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

import pytest

from overpower.runtimes import (
    MCP_DOCUMENTS,
    RUNTIMES,
    RUNTIMES_BY_KEY,
    UNIVERSAL_PROJECT_DIR,
    Environment,
    Evidence,
    Runtime,
    Scope,
    detected_runtimes,
    mcp_document_of,
    mcp_places_of,
    mcp_runtimes_in,
    places_of,
    resolve_global_dir,
    resolve_project_dir,
    runtimes_in,
    universal_place,
    universal_runtimes,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

# A POSIX-looking literal is NOT an absolute path on Windows:
# `WindowsPath("/home/dev").is_absolute()` is False, because it carries no
# drive. That is real product behaviour and not a quirk to route around —
# `_override` ignores a non-absolute override on purpose — so the fixtures get
# anchored per platform instead, and the assertions stay about the *table*
# rather than about the path syntax of whichever runner ran them.
#
# The switch is `sys.platform` and never an environment variable: a variable can
# go missing from the workflow and leave the suite green while asserting
# nothing. Found by the first run of the 3x3 matrix, in the exact cell the test
# doctrine predicted it would be found in.
_ANCHOR = "C:/" if sys.platform == "win32" else "/"


def absolute(*parts: str) -> Path:
    """An absolute path on the platform running the test."""
    return Path(_ANCHOR, *parts)


HOME = absolute("home", "dev")
REPO = absolute("srv", "repo")


def environment(
    variables: Mapping[str, str] | None = None,
    present: frozenset[Path] = frozenset(),
    platform: str = sys.platform,
) -> Environment:
    """An environment with nothing set and nothing on disk unless asked.

    `platform` defaults to the one running the test, so a case that is not about
    the operating system stays about the table. The matrix cases name it, which
    is what lets one runner assert all nine of them.
    """
    return Environment(
        home=HOME,
        variables=variables or {},
        directory_exists=present.__contains__,
        platform=platform,
    )


def runtime(key: str) -> Runtime:
    """The row for `key`."""
    return RUNTIMES_BY_KEY[key]


# --- the numbers the map states -------------------------------------------


def test_table_size_matches_the_transcribed_upstream() -> None:
    assert len(RUNTIMES) == 76


def test_the_mcp_table_is_not_a_subset_of_the_skills_transcription() -> None:
    """The two axes are two tables, and neither one contains the other.

    This is the decision https://github.com/panlabs-tech/overpower/issues/79
    forced, pinned as a fact rather than left as prose. `vscode` owns
    `.vscode/mcp.json` — no other runtime reads it — and upstream declares **no
    skills row** for it, which is why the count above is still 76: a transcription
    that grew a row of our own would stop being a transcription, and the numbers
    the map states out loud would be measuring two different things at once.

    The other direction is asserted at the same time, because it is what makes
    this a pair of tables and not a hierarchy: `cursor` has a skills row and no
    MCP document anywhere.
    """
    grafts = {key for key, _ in MCP_DOCUMENTS}

    assert "vscode" in grafts
    assert "vscode" not in RUNTIMES_BY_KEY
    assert "cursor" in RUNTIMES_BY_KEY
    assert "cursor" not in grafts


def test_the_mcp_runtimes_of_a_scope_come_off_the_mcp_table() -> None:
    """Read from the table that decides, never filtered out of the other one.

    Filtering `runtimes_in` was the shape before the second target, and it worked
    only while every MCP runtime happened to have a skills row. It would drop
    `vscode` in silence — the target would exist, render, and be unnameable.
    """
    assert set(mcp_runtimes_in(Scope.PROJECT)) == {"claude-code", "vscode", "devin"}
    assert set(mcp_runtimes_in(Scope.GLOBAL)) == {"claude-code", "vscode", "devin"}


def test_every_key_is_unique() -> None:
    assert len(RUNTIMES_BY_KEY) == len(RUNTIMES)


def test_distinct_project_paths_are_fewer_than_runtimes() -> None:
    assert len({r.project_dir.relative for r in RUNTIMES}) == 55


def test_universal_project_path_is_shared_by_nineteen_runtimes() -> None:
    universal = [r for r in RUNTIMES if r.project_dir.relative == UNIVERSAL_PROJECT_DIR]
    assert len(universal) == 19


def test_two_runtimes_declare_no_global_destination() -> None:
    without = sorted(r.key for r in RUNTIMES if r.global_dir is None)
    assert without == ["eve", "promptscript"]


def test_distinct_global_paths_under_a_default_environment() -> None:
    """66, not the 68 the map quotes.

    The 68 counts `undefined` as a value and counts two spellings of
    `~/.agents/skills` — upstream writes it both as `join(home, '.agents',
    'skills')` and as `join(home, '.agents/skills')` — as two paths.
    """
    resolved = {resolve_global_dir(r, environment()) for r in RUNTIMES}
    assert None in resolved
    assert len(resolved - {None}) == 66


def test_agents_skills_is_the_most_shared_global_path() -> None:
    env = environment()
    sharing = [r.key for r in RUNTIMES if resolve_global_dir(r, env) == HOME / ".agents" / "skills"]
    assert sorted(sharing) == ["cline", "dexto", "kimi-code-cli", "loaf", "warp", "zed"]


# --- the set `--runtime` accepts, which is a function of the scope ----------
#
# ADR 0009. The last test in this block is the one that carries the guarantee;
# the counts above it are what makes a refresh that changes the table break
# here instead of on a user's machine.


def test_project_scope_accepts_every_runtime() -> None:
    assert runtimes_in(Scope.PROJECT) == RUNTIMES


def test_global_scope_accepts_seventy_four_of_the_seventy_six() -> None:
    assert len(runtimes_in(Scope.GLOBAL)) == 74


def test_global_scope_drops_exactly_the_two_without_a_destination() -> None:
    offered = {r.key for r in runtimes_in(Scope.GLOBAL)}
    assert {r.key for r in RUNTIMES} - offered == {"eve", "promptscript"}


def test_global_scope_preserves_upstream_declaration_order() -> None:
    dropped = {"eve", "promptscript"}
    assert [r.key for r in runtimes_in(Scope.GLOBAL)] == [
        r.key for r in RUNTIMES if r.key not in dropped
    ]


def test_every_runtime_offered_in_a_scope_has_somewhere_to_land() -> None:
    """The guarantee the rule buys: nothing reaches the screen with no destination.

    A runtime offered but unwritable is the failure ADR 0008 measured in the
    `npx skills` screen. Asserting it over the *whole* offered set — rather
    than over the two known keys — is what keeps it true after a refresh.
    """
    env = environment()
    assert all(resolve_global_dir(r, env) is not None for r in runtimes_in(Scope.GLOBAL))
    root = REPO
    assert all(resolve_project_dir(r, root).is_absolute() for r in runtimes_in(Scope.PROJECT))


# --- the universal group, which is a function of the scope as well ----------
#
# ADR 0011. The group is what the wizard locks as *always included*, so its
# membership is not a taxonomy question: the heading names a place, and its
# members are whoever reads that place **in that scope** — nineteen in project,
# six in global.


def test_the_universal_group_in_project_scope_is_everyone_who_reads_that_path() -> None:
    reads_it = [r.key for r in RUNTIMES if r.project_dir.relative == UNIVERSAL_PROJECT_DIR]

    grouped = [r.key for r in universal_runtimes(Scope.PROJECT)]

    assert grouped == reads_it
    assert len(grouped) == 19


def test_the_universal_group_in_global_scope_is_the_six_that_read_it_under_the_home() -> None:
    """The correction ADR 0011 buys: the other thirteen land somewhere of their own.

    `codex` goes to `~/.codex/skills`, `cursor` to `~/.cursor/skills`, `amp` to
    `~/.config/agents/skills`. A heading claiming those three read
    `~/.agents/skills` is the *"screen says one thing, disk says another"* class
    ADR 0008 exists to refuse, arriving through the screen.
    """
    grouped = [r.key for r in universal_runtimes(Scope.GLOBAL)]

    assert grouped == ["cline", "dexto", "kimi-code-cli", "loaf", "warp", "zed"]


@pytest.mark.parametrize(
    "scope",
    [pytest.param(Scope.PROJECT, id="project"), pytest.param(Scope.GLOBAL, id="global")],
)
def test_the_universal_heading_names_a_place_every_member_reads(scope: Scope) -> None:
    """The property the whole group exists for, asserted over membership and not over a count."""
    env = environment()

    members = universal_runtimes(scope)

    places = {
        resolve_project_dir(r, REPO) if scope is Scope.PROJECT else resolve_global_dir(r, env)
        for r in members
    }
    root = REPO if scope is Scope.PROJECT else HOME
    assert places == {root / ".agents" / "skills"}


@pytest.mark.parametrize(
    "scope",
    [pytest.param(Scope.PROJECT, id="project"), pytest.param(Scope.GLOBAL, id="global")],
)
def test_the_universal_group_is_never_empty_in_either_scope(scope: Scope) -> None:
    """ADR 0011's consequence: the wizard can no longer produce an empty runtime selection.

    `NoRuntimeSelectedError` therefore becomes reachable only through the flag
    path, which was always what it was for.
    """
    assert universal_runtimes(scope)


def test_the_universal_place_is_spelled_against_the_root_of_its_scope() -> None:
    """The heading has to say where it writes, and the two roots are not the same word."""
    assert universal_place(Scope.PROJECT) == ".agents/skills"
    assert universal_place(Scope.GLOBAL) == "~/.agents/skills"


@pytest.mark.parametrize(
    ("scope", "total"),
    [
        pytest.param(Scope.PROJECT, 76, id="project"),
        pytest.param(Scope.GLOBAL, 74, id="global"),
    ],
)
def test_the_universal_group_and_the_rest_partition_the_scoped_table(
    scope: Scope, total: int
) -> None:
    """Nothing is offered twice and nothing is dropped: 19 + 57 in project, 6 + 68 in global."""
    members = {r.key for r in universal_runtimes(scope)}
    offered = {r.key for r in runtimes_in(scope)}

    assert members <= offered
    assert len(offered - members) == total - len(members)


# --- evidence --------------------------------------------------------------


def test_only_four_project_paths_were_verified_in_primary_source() -> None:
    measured = sorted(r.key for r in RUNTIMES if r.project_dir.evidence is Evidence.MEASURED)
    assert measured == ["claude-code", "codex", "cursor", "github-copilot"]


def test_only_one_global_path_was_verified_in_primary_source() -> None:
    measured = sorted(
        r.key
        for r in RUNTIMES
        if r.global_dir is not None and r.global_dir.evidence is Evidence.MEASURED
    )
    assert measured == ["claude-code"]


def test_vs_code_has_no_row_although_the_map_measured_it() -> None:
    """Recorded as a test because it is the one gap a reader would assume away."""
    assert not [r for r in RUNTIMES if "code" in r.key and "vs" in r.display_name.lower()]
    assert "vscode" not in RUNTIMES_BY_KEY


# --- project resolution ----------------------------------------------------


def test_project_path_is_joined_under_the_given_root() -> None:
    root = REPO
    assert resolve_project_dir(runtime("claude-code"), root) == root / ".claude" / "skills"


@pytest.mark.parametrize("row", RUNTIMES, ids=[r.key for r in RUNTIMES])
def test_project_path_never_leaves_a_separator_inside_one_component(
    row: Runtime,
) -> None:
    """The guard that makes the transcription correct on Windows.

    Upstream spells every path with `/`. Handing `.factory/skills` to a path API
    as a single component is what would produce a directory literally named
    `factory/skills`, and on Windows a junction API that only accepts `str`
    would then be handed the wrong string.
    """
    resolved = resolve_project_dir(row, REPO)
    expected = len(PurePosixPath(row.project_dir.relative).parts)
    assert resolved.parts[-expected:] == PurePosixPath(row.project_dir.relative).parts
    assert all("/" not in part and "\\" not in part for part in resolved.parts[1:])


@pytest.mark.parametrize("row", RUNTIMES, ids=[r.key for r in RUNTIMES])
def test_project_path_is_relative_to_the_root(row: Runtime) -> None:
    root = REPO
    assert resolve_project_dir(row, root).is_relative_to(root)


# --- global resolution -----------------------------------------------------


def test_home_anchored_path_hangs_off_the_home() -> None:
    assert resolve_global_dir(runtime("cursor"), environment()) == HOME / ".cursor" / "skills"


def test_runtime_without_global_destination_resolves_to_none() -> None:
    assert resolve_global_dir(runtime("eve"), environment()) is None


def test_xdg_config_home_defaults_to_dot_config() -> None:
    resolved = resolve_global_dir(runtime("devin"), environment())
    assert resolved == HOME / ".config" / "devin" / "skills"


def test_xdg_config_home_is_honoured_when_absolute() -> None:
    env = environment({"XDG_CONFIG_HOME": str(absolute("etc", "xdg"))})
    assert resolve_global_dir(runtime("devin"), env) == absolute("etc", "xdg", "devin", "skills")


def test_blank_override_falls_back_instead_of_naming_a_directory_of_spaces() -> None:
    env = environment({"XDG_CONFIG_HOME": "   "})
    assert resolve_global_dir(runtime("devin"), env) == HOME / ".config" / "devin" / "skills"


def test_relative_override_is_ignored_so_a_global_install_stays_global() -> None:
    """Upstream would resolve this against the working directory."""
    env = environment({"XDG_CONFIG_HOME": ".config"})
    resolved = resolve_global_dir(runtime("devin"), env)
    assert resolved == HOME / ".config" / "devin" / "skills"
    assert resolved is not None
    assert resolved.is_absolute()


def test_tool_specific_override_wins_over_its_home_fallback() -> None:
    env = environment({"CODEX_HOME": str(absolute("opt", "codex"))})
    assert resolve_global_dir(runtime("codex"), env) == absolute("opt", "codex", "skills")


def test_tool_specific_override_falls_back_to_the_home() -> None:
    assert resolve_global_dir(runtime("codex"), environment()) == HOME / ".codex" / "skills"


def test_claude_config_dir_is_the_override_for_claude_code() -> None:
    env = environment({"CLAUDE_CONFIG_DIR": str(absolute("opt", "claude"))})
    assert resolve_global_dir(runtime("claude-code"), env) == absolute("opt", "claude", "skills")


def test_openclaw_prefers_a_legacy_directory_that_exists() -> None:
    env = environment(present=frozenset({HOME / ".clawdbot"}))
    assert resolve_global_dir(runtime("openclaw"), env) == HOME / ".clawdbot" / "skills"


def test_openclaw_prefers_the_current_name_when_both_exist() -> None:
    env = environment(present=frozenset({HOME / ".openclaw", HOME / ".moltbot"}))
    assert resolve_global_dir(runtime("openclaw"), env) == HOME / ".openclaw" / "skills"


def test_openclaw_falls_back_to_the_current_name_when_nothing_exists() -> None:
    assert resolve_global_dir(runtime("openclaw"), environment()) == HOME / ".openclaw" / "skills"


def test_only_openclaw_consults_the_filesystem() -> None:
    """Resolution is otherwise pure, which is what keeps the table cheap to test."""
    consulted: list[Path] = []

    def record(path: Path) -> bool:
        consulted.append(path)
        return False

    env = Environment(home=HOME, variables={}, directory_exists=record, platform=sys.platform)
    for row in RUNTIMES:
        consulted.clear()
        resolve_global_dir(row, env)
        assert consulted == [] or row.key == "openclaw"


# --- machine documents: the 3x3 matrix of https://github.com/panlabs-tech/overpower/issues/81


WINDOWS, MACOS, LINUX = "win32", "darwin", "linux"

MACHINE_CELLS = (
    # `~/.claude.json`, the same file on all three: the home is the anchor, and
    # the operating system never moves it.
    ("claude-code", WINDOWS, (".claude.json",)),
    ("claude-code", MACOS, (".claude.json",)),
    ("claude-code", LINUX, (".claude.json",)),
    # The VS Code user profile, which is a different directory per system and
    # the same file name in all of them.
    ("vscode", WINDOWS, ("AppData", "Roaming", "Code", "User", "mcp.json")),
    ("vscode", MACOS, ("Library", "Application Support", "Code", "User", "mcp.json")),
    ("vscode", LINUX, (".config", "Code", "User", "mcp.json")),
    # Devin moves on Windows only.
    ("devin", WINDOWS, ("AppData", "Roaming", "devin", "mcp_config.json")),
    ("devin", MACOS, (".config", "devin", "mcp_config.json")),
    ("devin", LINUX, (".config", "devin", "mcp_config.json")),
)
"""Every cell of the matrix, under a home with no variable set."""


@pytest.mark.parametrize(
    ("key", "platform", "under_home"),
    MACHINE_CELLS,
    ids=[f"{key}-{platform}" for key, platform, _ in MACHINE_CELLS],
)
def test_the_machine_document_of_every_cell_resolves_under_the_home(
    key: str, platform: str, under_home: tuple[str, ...]
) -> None:
    """The nine cells, asserted on one runner.

    `platform` is a value of `Environment` for the same reason `home` and
    `variables` are: *where to write* is decided from facts that arrive, so a
    matrix the CI runs one cell of at a time is still assertable whole. The
    runner's own `sys.platform` reaches this only through `from_process`.

    `REPO` is passed as the root on purpose — a machine document hangs off an
    anchor, and a resolution that quietly used the repository would show up here
    as a path under `REPO` rather than under `HOME`.
    """
    (place,) = mcp_places_of([key], Scope.GLOBAL, REPO, environment(platform=platform))

    assert place.path == HOME.joinpath(*under_home)
    assert place.readers == (key,)


def test_the_windows_profile_follows_appdata_when_it_is_absolute() -> None:
    env = environment({"APPDATA": str(absolute("Users", "dev", "Roaming"))}, platform=WINDOWS)
    (place,) = mcp_places_of(["vscode"], Scope.GLOBAL, REPO, env)
    assert place.path == absolute("Users", "dev", "Roaming", "Code", "User", "mcp.json")


def test_the_linux_profile_follows_xdg_config_home_when_it_is_absolute() -> None:
    env = environment({"XDG_CONFIG_HOME": str(absolute("etc", "xdg"))}, platform=LINUX)
    (place,) = mcp_places_of(["devin"], Scope.GLOBAL, REPO, env)
    assert place.path == absolute("etc", "xdg", "devin", "mcp_config.json")


def test_an_unknown_platform_resolves_the_way_the_other_unixes_do() -> None:
    """`sys.platform` is an open set — `freebsd14` has to land somewhere honest."""
    (place,) = mcp_places_of(["vscode"], Scope.GLOBAL, REPO, environment(platform="freebsd14"))
    assert place.path == HOME / ".config" / "Code" / "User" / "mcp.json"


def test_the_machine_rows_keep_the_root_key_and_dialect_of_their_target() -> None:
    """Scope moves the file, never the format: the dialect is a fact of the target."""
    for key in ("claude-code", "vscode", "devin"):
        project = mcp_document_of(key, Scope.PROJECT)
        machine = mcp_document_of(key, Scope.GLOBAL)
        assert project is not None
        assert machine is not None
        assert machine.root_key == project.root_key
        assert machine.dialect is project.dialect


def test_no_machine_document_is_born_pending() -> None:
    """ADR 0014: the server in the personal file is the user's own, so nothing waits.

    The warning falls out of this row rather than out of an `if` in the CLI —
    `pending_activation` asks the same table that decided the file.
    """
    machine = [document for (_, scope), document in MCP_DOCUMENTS.items() if scope is Scope.GLOBAL]
    assert len(machine) == 3
    assert not any(document.born_pending for document in machine)


def test_a_project_document_still_hangs_off_the_repository() -> None:
    """The row decides the base, not the scope argument — rule 8, both axes."""
    (place,) = mcp_places_of(["claude-code"], Scope.PROJECT, REPO, environment())
    assert place.path == REPO / ".mcp.json"


@pytest.mark.parametrize("row", RUNTIMES, ids=[r.key for r in RUNTIMES])
def test_global_path_is_absolute_when_it_exists(row: Runtime) -> None:
    resolved = resolve_global_dir(row, environment())
    assert resolved is None or resolved.is_absolute()


# --- grouping runtimes by the place they read ------------------------------


def test_places_of_collapses_runtimes_that_read_the_same_directory() -> None:
    """19 of the 76 rows read `.agents/skills`, and collapsing them is the point.

    Both callers depend on it for different reasons — the plan is honest about
    what a selection costs (ADR 0008: announcing *"Cursor"* would promise one
    target and deliver twenty), and the `doctor` walks each place once instead
    of nineteen times.
    """
    universal = [row for row in RUNTIMES if row.project_dir.relative == UNIVERSAL_PROJECT_DIR]

    places = places_of(RUNTIMES, Scope.PROJECT, REPO, environment())

    assert places[resolve_project_dir(universal[0], REPO)] == tuple(row.key for row in universal)


def test_places_of_answers_in_the_order_of_the_table() -> None:
    """The order is the whole contract: it is what the screen and the writer share.

    In global scope it decides more than presentation — the first place is the
    canonical copy of the ladder (#40), and every other one links to it.
    """
    chosen = tuple(RUNTIMES_BY_KEY[key] for key in ("claude-code", "cursor", "codex"))

    ordered = places_of(chosen, Scope.PROJECT, REPO, environment())

    expected = [resolve_project_dir(row, REPO) for row in RUNTIMES if row in chosen]
    assert list(ordered) == list(dict.fromkeys(expected))


def test_places_of_in_global_scope_hangs_off_the_environment_and_not_the_root() -> None:
    """A global place is anchored by the table, so the root it is handed is inert."""
    chosen = (RUNTIMES_BY_KEY["claude-code"],)

    places = places_of(chosen, Scope.GLOBAL, REPO, environment())

    assert list(places) == [HOME / ".claude" / "skills"]


# --- the wizard's pre-mark: detected_runtimes -------------------------------
#
# No state file (ADR 0008): pre-checking comes from what already exists, read
# through `environment.directory_exists` and never a bare `Path.is_dir()`, so
# these stay as testable as every other resolution above.


def test_project_scope_pre_checks_only_the_runtime_whose_directory_exists() -> None:
    env = environment(present=frozenset({REPO / ".claude" / "skills"}))
    assert detected_runtimes(Scope.PROJECT, REPO, env) == frozenset({"claude-code"})


def test_project_scope_with_nothing_on_disk_detects_nothing() -> None:
    assert detected_runtimes(Scope.PROJECT, REPO, environment()) == frozenset()


def test_project_scope_falls_back_to_home_when_the_repository_has_no_runtime_directory() -> None:
    """The one divergence from upstream ADR 0008 names: 65 of 76 probe `~` outright.

    Here the project is asked first — it is what the *repository* carries —
    and only a repository with zero signal falls back to the machine.
    """
    env = environment(present=frozenset({HOME / ".cursor" / "skills"}))
    assert detected_runtimes(Scope.PROJECT, REPO, env) == frozenset({"cursor"})


def test_a_repository_with_any_runtime_directory_does_not_fall_back() -> None:
    """One project signal is enough to trust the project over the machine."""
    env = environment(present=frozenset({REPO / ".claude" / "skills", HOME / ".cursor" / "skills"}))
    assert detected_runtimes(Scope.PROJECT, REPO, env) == frozenset({"claude-code"})


def test_global_scope_probes_home_directly_and_never_the_project() -> None:
    env = environment(present=frozenset({REPO / ".claude" / "skills"}))
    assert detected_runtimes(Scope.GLOBAL, REPO, env) == frozenset()


def test_global_scope_pre_checks_what_is_already_under_home() -> None:
    env = environment(present=frozenset({HOME / ".cursor" / "skills"}))
    assert detected_runtimes(Scope.GLOBAL, REPO, env) == frozenset({"cursor"})


def test_detection_never_offers_a_runtime_the_scope_would_refuse() -> None:
    """`eve` and `promptscript` have no global destination (ADR 0009).

    Everything is marked present, which is the adversarial case: if the two
    rows could ever appear, this is where they would. `_present_at` only ever
    iterates `runtimes_in(scope)`, so they cannot — asserted over the whole
    scoped set rather than the two known keys, the way
    `test_every_runtime_offered_in_a_scope_has_somewhere_to_land` already is.
    """
    env = Environment(
        home=HOME, variables={}, directory_exists=lambda _path: True, platform=sys.platform
    )
    detected = detected_runtimes(Scope.GLOBAL, REPO, env)
    assert detected == {r.key for r in runtimes_in(Scope.GLOBAL)}
