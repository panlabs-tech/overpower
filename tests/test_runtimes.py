"""The table is a transcription, so most of what is worth asserting is shape.

The counts below are the ones the map states out loud — in
https://github.com/panlabs-tech/overpower/issues/18, in ADR 0008 and in
`docs/agents/domain.md`. Pinning them here is what turns "76 runtimes, 55
project paths" from prose into something that breaks when a refresh changes it.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path, PurePosixPath

import pytest

from overpower.runtimes import (
    RUNTIMES,
    RUNTIMES_BY_KEY,
    UNIVERSAL_PROJECT_DIR,
    Environment,
    Evidence,
    Runtime,
    Scope,
    resolve_global_dir,
    resolve_project_dir,
    runtimes_in,
)

HOME = Path("/home/dev")


def environment(
    variables: Mapping[str, str] | None = None,
    present: frozenset[Path] = frozenset(),
) -> Environment:
    """An environment with nothing set and nothing on disk unless asked."""
    return Environment(
        home=HOME,
        variables=variables or {},
        directory_exists=present.__contains__,
    )


def runtime(key: str) -> Runtime:
    """The row for `key`."""
    return RUNTIMES_BY_KEY[key]


# --- the numbers the map states -------------------------------------------


def test_table_size_matches_the_transcribed_upstream() -> None:
    assert len(RUNTIMES) == 76


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
    sharing = [
        r.key
        for r in RUNTIMES
        if resolve_global_dir(r, env) == HOME / ".agents" / "skills"
    ]
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
    assert all(
        resolve_global_dir(r, env) is not None for r in runtimes_in(Scope.GLOBAL)
    )
    root = Path("/srv/repo")
    assert all(
        resolve_project_dir(r, root).is_absolute() for r in runtimes_in(Scope.PROJECT)
    )


# --- evidence --------------------------------------------------------------


def test_only_four_project_paths_were_verified_in_primary_source() -> None:
    measured = sorted(
        r.key for r in RUNTIMES if r.project_dir.evidence is Evidence.MEASURED
    )
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
    assert not [
        r for r in RUNTIMES if "code" in r.key and "vs" in r.display_name.lower()
    ]
    assert "vscode" not in RUNTIMES_BY_KEY


# --- project resolution ----------------------------------------------------


def test_project_path_is_joined_under_the_given_root() -> None:
    root = Path("/srv/repo")
    assert (
        resolve_project_dir(runtime("claude-code"), root) == root / ".claude" / "skills"
    )


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
    resolved = resolve_project_dir(row, Path("/srv/repo"))
    expected = len(PurePosixPath(row.project_dir.relative).parts)
    assert resolved.parts[-expected:] == PurePosixPath(row.project_dir.relative).parts
    assert all("/" not in part and "\\" not in part for part in resolved.parts[1:])


@pytest.mark.parametrize("row", RUNTIMES, ids=[r.key for r in RUNTIMES])
def test_project_path_is_relative_to_the_root(row: Runtime) -> None:
    root = Path("/srv/repo")
    assert resolve_project_dir(row, root).is_relative_to(root)


# --- global resolution -----------------------------------------------------


def test_home_anchored_path_hangs_off_the_home() -> None:
    assert (
        resolve_global_dir(runtime("cursor"), environment())
        == HOME / ".cursor" / "skills"
    )


def test_runtime_without_global_destination_resolves_to_none() -> None:
    assert resolve_global_dir(runtime("eve"), environment()) is None


def test_xdg_config_home_defaults_to_dot_config() -> None:
    resolved = resolve_global_dir(runtime("devin"), environment())
    assert resolved == HOME / ".config" / "devin" / "skills"


def test_xdg_config_home_is_honoured_when_absolute() -> None:
    env = environment({"XDG_CONFIG_HOME": "/etc/xdg"})
    assert resolve_global_dir(runtime("devin"), env) == Path("/etc/xdg/devin/skills")


def test_blank_override_falls_back_instead_of_naming_a_directory_of_spaces() -> None:
    env = environment({"XDG_CONFIG_HOME": "   "})
    assert (
        resolve_global_dir(runtime("devin"), env)
        == HOME / ".config" / "devin" / "skills"
    )


def test_relative_override_is_ignored_so_a_global_install_stays_global() -> None:
    """Upstream would resolve this against the working directory."""
    env = environment({"XDG_CONFIG_HOME": ".config"})
    resolved = resolve_global_dir(runtime("devin"), env)
    assert resolved == HOME / ".config" / "devin" / "skills"
    assert resolved is not None and resolved.is_absolute()


def test_tool_specific_override_wins_over_its_home_fallback() -> None:
    env = environment({"CODEX_HOME": "/opt/codex"})
    assert resolve_global_dir(runtime("codex"), env) == Path("/opt/codex/skills")


def test_tool_specific_override_falls_back_to_the_home() -> None:
    assert (
        resolve_global_dir(runtime("codex"), environment())
        == HOME / ".codex" / "skills"
    )


def test_claude_config_dir_is_the_override_for_claude_code() -> None:
    env = environment({"CLAUDE_CONFIG_DIR": "/opt/claude"})
    assert resolve_global_dir(runtime("claude-code"), env) == Path("/opt/claude/skills")


def test_openclaw_prefers_a_legacy_directory_that_exists() -> None:
    env = environment(present=frozenset({HOME / ".clawdbot"}))
    assert resolve_global_dir(runtime("openclaw"), env) == HOME / ".clawdbot" / "skills"


def test_openclaw_prefers_the_current_name_when_both_exist() -> None:
    env = environment(present=frozenset({HOME / ".openclaw", HOME / ".moltbot"}))
    assert resolve_global_dir(runtime("openclaw"), env) == HOME / ".openclaw" / "skills"


def test_openclaw_falls_back_to_the_current_name_when_nothing_exists() -> None:
    assert (
        resolve_global_dir(runtime("openclaw"), environment())
        == HOME / ".openclaw" / "skills"
    )


def test_only_openclaw_consults_the_filesystem() -> None:
    """Resolution is otherwise pure, which is what keeps the table cheap to test."""
    consulted: list[Path] = []

    def record(path: Path) -> bool:
        consulted.append(path)
        return False

    env = Environment(home=HOME, variables={}, directory_exists=record)
    for row in RUNTIMES:
        consulted.clear()
        resolve_global_dir(row, env)
        assert consulted == [] or row.key == "openclaw"


@pytest.mark.parametrize("row", RUNTIMES, ids=[r.key for r in RUNTIMES])
def test_global_path_is_absolute_when_it_exists(row: Runtime) -> None:
    resolved = resolve_global_dir(row, environment())
    assert resolved is None or resolved.is_absolute()
