"""Mirror of `src/overpower/wizard.py`: the three steps, and the `Request` they build.

Each `ask_*` function is stubbed directly — the seam supplies indirect input,
it does not emulate `questionary`'s own behaviour, so it is Stub and the house
ruler excludes Stub from contract testing by name (`docs/agents/testing.md`,
§7). The one test that reaches the real `questionary`, under a real PTY, lives
at the bottom of this file and proves the wiring rather than the pixels.

Every stub here is a named function with explicit parameter types, never a
bare lambda: `pytest.MonkeyPatch.setattr`'s string-keyed overload types its
`value` as `object`, so a lambda's unannotated parameters stay `Unknown` under
`pyright --strict` with nothing to infer them from — the same reason
`test_cli.py`'s own stubs (`explode(*_: object, **__: object)`) are named.
"""

from __future__ import annotations

import contextlib
import os
import select
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import questionary
from questionary.prompts.common import InquirerControl

from overpower import wizard
from overpower.discovery import load_catalog
from overpower.packaged import catalog_file, content_root
from overpower.planning import Request
from overpower.runtimes import (
    RUNTIMES,
    UNIVERSAL_PROJECT_DIR,
    Environment,
    Scope,
    runtimes_in,
    universal_runtimes,
)
from tests.support.project import catalog_of

if TYPE_CHECKING:
    from collections.abc import Callable

    from overpower.discovery import Catalog


class _Answered:
    """A `questionary` `Question` stand-in: `.ask()` and nothing else.

    What the real object does beyond `.ask()` — draw, read keys, redraw — is
    exactly what this module does not emulate, which is the whole reason it is
    a Stub rather than a Fake.
    """

    def __init__(self, value: object) -> None:
        self._value = value

    def ask(self) -> object:
        return self._value


def _answering(value: object) -> Callable[..., _Answered]:
    """A `questionary.checkbox`/`.select` replacement, ignoring its arguments."""

    def _prompt(*_args: object, **_kwargs: object) -> _Answered:
        return _Answered(value)

    return _prompt


def _real_choices(
    choices: list[questionary.Separator | questionary.Choice],
) -> list[questionary.Choice]:
    """Every choice that is not a group heading — `Separator` is a `Choice` subclass."""
    return [choice for choice in choices if not isinstance(choice, questionary.Separator)]


# --------------------------------------------------------------------------- #
# step 1: artifacts
# --------------------------------------------------------------------------- #


def test_artifact_choices_group_the_three_units_with_one_separator_each(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    content = catalog_of(
        tmp_path,
        monkeypatch,
        "alpha",
        "beta",
        frameworks={"fw": ["fa"]},
        bundles={"bun": ["alpha"]},
    )
    catalog = load_catalog(content, tmp_path / "packaged" / "catalog.toml")

    choices = wizard.artifact_choices(catalog)

    separators = [c for c in choices if isinstance(c, questionary.Separator)]
    assert len(separators) == 3
    values = {choice.value for choice in _real_choices(choices)}
    assert values == {("framework", "fw"), ("bundle", "bun"), ("skill", "alpha"), ("skill", "beta")}


def test_artifact_choices_prints_no_heading_for_an_empty_unit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No bundle and no framework here — a real catalog shape, not a defect."""
    content = catalog_of(tmp_path, monkeypatch, "solo")
    catalog = load_catalog(content, tmp_path / "packaged" / "catalog.toml")

    choices = wizard.artifact_choices(catalog)

    assert len([c for c in choices if isinstance(c, questionary.Separator)]) == 1
    assert [choice.value for choice in _real_choices(choices)] == [("skill", "solo")]


def test_ask_artifacts_partitions_the_pick_by_kind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    content = catalog_of(
        tmp_path, monkeypatch, "alpha", frameworks={"fw": ["fa"]}, bundles={"bun": ["alpha"]}
    )
    catalog = load_catalog(content, tmp_path / "packaged" / "catalog.toml")
    picked = [("framework", "fw"), ("skill", "alpha")]
    monkeypatch.setattr(wizard.questionary, "checkbox", _answering(picked))

    result = wizard.ask_artifacts(catalog)

    assert result == (("fw",), (), ("alpha",))


def test_ask_artifacts_empty_pick_is_a_legal_answer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nothing chosen lands on the same `NothingSelectedError` the flags reach."""
    content = catalog_of(tmp_path, monkeypatch, "alpha")
    catalog = load_catalog(content, tmp_path / "packaged" / "catalog.toml")
    monkeypatch.setattr(wizard.questionary, "checkbox", _answering([]))

    assert wizard.ask_artifacts(catalog) == ((), (), ())


def test_ask_artifacts_returns_none_on_interruption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    content = catalog_of(tmp_path, monkeypatch, "alpha")
    catalog = load_catalog(content, tmp_path / "packaged" / "catalog.toml")
    monkeypatch.setattr(wizard.questionary, "checkbox", _answering(None))

    assert wizard.ask_artifacts(catalog) is None


# --------------------------------------------------------------------------- #
# step 2: scope
# --------------------------------------------------------------------------- #


def _environment(home: Path) -> Environment:
    def _nothing_exists(_path: Path) -> bool:
        return False

    return Environment(home=home, variables={}, directory_exists=_nothing_exists)


def test_ask_scope_inside_a_repository_offers_both(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".git").mkdir()
    seen: dict[str, object] = {}

    def fake_select(_message: str, choices: object) -> _Answered:
        seen["choices"] = choices
        return _Answered(Scope.GLOBAL)

    monkeypatch.setattr(wizard.questionary, "select", fake_select)
    environment = _environment(tmp_path / "home")

    outcome = wizard.ask_scope(tmp_path, environment)

    assert outcome is not None
    scope, root = outcome
    assert scope is Scope.GLOBAL
    assert root == environment.home
    assert len(seen["choices"]) == 2  # type: ignore[arg-type]


def test_ask_scope_project_choice_writes_under_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".git").mkdir()
    monkeypatch.setattr(wizard.questionary, "select", _answering(Scope.PROJECT))
    environment = _environment(tmp_path / "home")

    outcome = wizard.ask_scope(tmp_path, environment)

    assert outcome is not None
    scope, root = outcome
    assert scope is Scope.PROJECT
    assert root == tmp_path


def test_ask_scope_returns_none_on_interruption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".git").mkdir()
    monkeypatch.setattr(wizard.questionary, "select", _answering(None))

    assert wizard.ask_scope(tmp_path, _environment(tmp_path / "home")) is None


def test_ask_scope_outside_a_repository_has_one_answer_and_asks_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Offering `Project` with nowhere to write is the lie ADR 0008/0009 already refuse."""
    bare = tmp_path / "no-repo-here"
    bare.mkdir()
    asked: list[object] = []

    def refuse_to_ask(*_args: object, **_kwargs: object) -> _Answered:
        asked.append(1)
        return _Answered(None)

    monkeypatch.setattr(wizard.questionary, "select", refuse_to_ask)
    environment = _environment(tmp_path / "home")

    result = wizard.ask_scope(bare, environment)

    assert result == (Scope.GLOBAL, environment.home)
    assert asked == []


# --------------------------------------------------------------------------- #
# step 3: runtimes
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("scope", "offered"),
    [
        pytest.param(Scope.PROJECT, 76, id="project"),
        pytest.param(Scope.GLOBAL, 74, id="global"),
    ],
)
def test_runtime_choices_are_scoped_and_only_the_universal_group_is_locked(
    scope: Scope, offered: int
) -> None:
    choices = _real_choices(wizard.runtime_choices(scope, frozenset()))

    assert len(choices) == offered
    locked = {choice.value for choice in choices if choice.disabled is not None}
    assert locked == {runtime.key for runtime in universal_runtimes(scope)}


@pytest.mark.parametrize(
    ("scope", "members"),
    [pytest.param(Scope.PROJECT, 19, id="project"), pytest.param(Scope.GLOBAL, 6, id="global")],
)
def test_the_universal_group_is_an_unselectable_section_in_both_scopes(
    scope: Scope, members: int
) -> None:
    """ADR 0011: *always included*, not a line to tick — and its size follows the scope."""
    choices = wizard.runtime_choices(scope, frozenset())

    grouped = _under(choices, "Universal")
    assert len(grouped) == members
    locked = [c for c in _real_choices(choices) if c.value in grouped]
    assert all(choice.disabled for choice in locked)


@pytest.mark.parametrize(
    ("scope", "place"),
    [
        pytest.param(Scope.PROJECT, ".agents/skills", id="project"),
        pytest.param(Scope.GLOBAL, "~/.agents/skills", id="global"),
    ],
)
def test_the_universal_heading_names_the_place_of_its_own_scope(scope: Scope, place: str) -> None:
    """The defect ADR 0011 corrects: the global screen used to announce the *project* path.

    Eighteen names under `~/.agents/skills` would claim that folder equips the
    eighteen. It equips six.
    """
    choices = wizard.runtime_choices(scope, frozenset())

    headings = [c.line for c in choices if isinstance(c, questionary.Separator)]
    assert any(f"Universal ({place})" in heading for heading in headings)


def test_the_universal_heading_says_it_is_always_included_and_counts_its_members() -> None:
    """*Always included* and a number is what the reader gets instead of counting boxes."""
    choices = wizard.runtime_choices(Scope.PROJECT, frozenset())

    heading = next(
        c.line for c in choices if isinstance(c, questionary.Separator) and "Universal" in c.line
    )
    assert "always included" in heading
    assert "19 runtimes" in heading


def test_runtime_choices_pre_check_exactly_what_was_detected() -> None:
    choices = _real_choices(wizard.runtime_choices(Scope.PROJECT, frozenset({"claude-code"})))

    checked = {choice.value for choice in choices if choice.checked}
    assert checked == {"claude-code"}


def test_a_locked_runtime_is_never_pre_checked_because_it_is_not_a_choice() -> None:
    """Detection pre-marks a decision; a locked line has none to pre-mark."""
    detected = frozenset({"cursor", "claude-code"})

    choices = _real_choices(wizard.runtime_choices(Scope.PROJECT, detected))

    checked = {choice.value for choice in choices if choice.checked}
    assert checked == {"claude-code"}  # `cursor` reads `.agents/skills`, so it is locked


def test_the_universal_heading_covers_exactly_the_runtimes_that_read_that_path() -> None:
    """The heading names a path, so its members are whoever reads it — nobody else.

    Asserted over membership and not merely over the presence of the heading,
    which is the assertion whose absence let the group be built from
    `in_universal_list`: that flag is `False` on two rows, so it gathered 74
    runtimes under `.agents/skills` when 19 read it.
    """
    # given
    reads_the_path = [
        runtime.key
        for runtime in runtimes_in(Scope.PROJECT)
        if runtime.project_dir.relative == UNIVERSAL_PROJECT_DIR
    ]

    choices = wizard.runtime_choices(Scope.PROJECT, frozenset())

    grouped = _under(choices, "Universal")
    assert grouped == reads_the_path
    assert len(grouped) == len(RUNTIMES) - len(_under(choices, "Additional agents"))


def test_no_runtime_is_grouped_under_a_path_it_does_not_read() -> None:
    """The measured shape of the defect: `claude-code` reads `.claude/skills`.

    Named individually because the three of them are the ones a reader
    recognises, and because a count alone would not say *which* rows moved.
    """
    choices = wizard.runtime_choices(Scope.PROJECT, frozenset())

    grouped = _under(choices, "Universal")
    assert "claude-code" not in grouped
    assert "droid" not in grouped
    assert "astrbot" not in grouped


def _under(choices: list[questionary.Separator | questionary.Choice], heading: str) -> list[str]:
    """Every runtime key listed under the heading containing `heading`, until the next one."""
    keys: list[str] = []
    collecting = False
    for choice in choices:
        if isinstance(choice, questionary.Separator):
            collecting = heading in choice.line
            continue
        if collecting:
            keys.append(str(choice.value))
    return keys


def _in_table_order(scope: Scope, keys: set[str]) -> tuple[str, ...]:
    """`keys`, sorted by where the table declares each one.

    Spelled as a **sort** and never as a filter over `runtimes_in(scope)`,
    because the filter is the expression `ask_runtimes` itself returns: an
    expectation built that way would agree with the product by construction
    instead of by being right. It is the same refusal `commands_of` states in
    `test_screens.py`.
    """
    order = [runtime.key for runtime in runtimes_in(scope)]
    return tuple(sorted(keys, key=order.index))


def test_ask_runtimes_answers_the_locked_group_plus_whatever_was_picked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The lock is of the screen; the keys travel in the `Request` like any other.

    Two independent properties rather than one equality: **what** comes back, as
    a set, and **that it is ordered** by the table — which is what the plan and
    the writer both consume.
    """
    monkeypatch.setattr(wizard.questionary, "checkbox", _answering(["claude-code"]))
    locked = {runtime.key for runtime in universal_runtimes(Scope.PROJECT)}

    result = wizard.ask_runtimes(Scope.PROJECT, tmp_path, _environment(tmp_path))

    assert result is not None
    assert set(result) == locked | {"claude-code"}
    assert result == _in_table_order(Scope.PROJECT, set(result))


def test_ask_runtimes_with_nothing_picked_still_answers_the_locked_group(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ADR 0011: the wizard can no longer produce an empty runtime selection."""
    monkeypatch.setattr(wizard.questionary, "checkbox", _answering([]))

    result = wizard.ask_runtimes(Scope.PROJECT, tmp_path, _environment(tmp_path))

    assert result == tuple(runtime.key for runtime in universal_runtimes(Scope.PROJECT))


def test_a_locked_key_that_comes_back_in_the_pick_is_not_named_twice(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """It can happen: `questionary` points at row 0 of the filtered list, disabled or not.

    So the union is taken through a set rather than by concatenation, and
    `cursor` — which reads `.agents/skills` and is therefore locked in project
    scope — arrives once.
    """
    monkeypatch.setattr(wizard.questionary, "checkbox", _answering(["cursor"]))

    result = wizard.ask_runtimes(Scope.PROJECT, tmp_path, _environment(tmp_path))

    assert result is not None
    assert result == tuple(runtime.key for runtime in universal_runtimes(Scope.PROJECT))
    assert result.count("cursor") == 1


def test_ask_runtimes_returns_none_on_interruption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wizard.questionary, "checkbox", _answering(None))

    assert wizard.ask_runtimes(Scope.PROJECT, tmp_path, _environment(tmp_path)) is None


def test_the_runtime_list_is_searchable_and_pays_for_it_with_the_j_and_k_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The price is fixed in the library, so it is asserted as a pair and not one flag.

    `ValueError: Cannot use j/k keys with prefix filter search, since j/k can be
    part of the prefix.`
    """
    seen: dict[str, object] = {}

    def fake_checkbox(_message: str, choices: object, **kwargs: object) -> _Answered:
        seen.update(kwargs)
        seen["choices"] = choices
        return _Answered([])

    monkeypatch.setattr(wizard.questionary, "checkbox", fake_checkbox)

    wizard.ask_runtimes(Scope.PROJECT, tmp_path, _environment(tmp_path))

    assert seen["use_search_filter"] is True
    assert seen["use_jk_keys"] is False


@pytest.mark.parametrize(
    ("typed", "narrowed"),
    [
        pytest.param("laude", ["Claude Code"], id="prefix of nothing"),
        pytest.param("copilot", ["GitHub Copilot"], id="second word"),
        pytest.param("dev", ["Devin for Terminal", "Rovo Dev"], id="two survivors"),
    ],
)
def test_typing_matches_in_the_middle_of_a_name_and_not_only_at_its_start(
    typed: str, narrowed: list[str]
) -> None:
    """The half of the search a prefix filter would not have bought, over the real filter.

    `InquirerControl` is the class `questionary.checkbox` builds internally and
    `filtered_choices` is the code path a keystroke reaches, so this is the
    product's own path minus the `Application` — which is exactly what lets the
    property be asserted on all nine cells, since building the whole question
    needs a console the Windows cells do not give a `pytest` child.

    The three cases reproduce the measurement the ticket carries against
    questionary 2.1.1 — 22 lines visible at 80x24, `dev` down to 2, `copilot` to
    1 — and `laude` is the one that separates a substring match from a prefix
    match, being the start of no name at all.
    """
    control = InquirerControl(wizard.runtime_choices(Scope.PROJECT, frozenset()))
    control.search_filter = typed

    assert [choice.title for choice in control.filtered_choices] == narrowed


def test_a_search_that_matches_nothing_leaves_the_whole_list_standing() -> None:
    """Measured: `questionary` falls back to every choice rather than to an empty screen."""
    control = InquirerControl(wizard.runtime_choices(Scope.PROJECT, frozenset()))
    control.search_filter = "zzz"

    assert len(control.filtered_choices) == len(control.choices)


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="prompt_toolkit's Win32 output needs a real console screen buffer, "
    "docs/agents/testing.md §2",
)
def test_the_real_questionary_builds_the_locked_and_searchable_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only `.ask()` is stubbed, so the question itself is built by the real library.

    Two refusals fire at construction and nowhere else, and both are exactly
    what this ticket walked into: the `ValueError` above, and `InquirerControl`
    rejecting an initial selection that is not selectable — which a section of
    locked rows sitting at the top of the list walks straight into if the
    pointer is allowed to start on one.

    **A third declared absence**, alongside the PTY test and the
    unprivileged-symlink case: building the question builds a `prompt_toolkit`
    `Application`, and its Win32 output raises `NoConsoleScreenBufferError` in a
    process with no console screen buffer — which is what a `pytest` child on
    the hosted runner is. Measured on the three Windows cells of the matrix; a
    real Windows terminal has the buffer, so the product path is unaffected.
    Switched on `sys.platform` and never on an environment variable, so the
    requirement cannot go missing from the workflow.
    """

    def answered(_self: object) -> list[str]:
        return ["claude-code"]

    monkeypatch.setattr(questionary.Question, "ask", answered)

    result = wizard.ask_runtimes(Scope.PROJECT, tmp_path, _environment(tmp_path))

    assert result is not None
    assert "claude-code" in result


# --------------------------------------------------------------------------- #
# the three steps together: the same `Request` the flags would build
# --------------------------------------------------------------------------- #


def _project_scope(cwd: Path, _environment: Environment) -> tuple[Scope, Path]:
    return Scope.PROJECT, cwd


def _fixed_runtimes(_scope: Scope, _root: Path, _environment: Environment) -> tuple[str, ...]:
    return ("claude-code",)


def test_run_wizard_builds_the_same_request_the_equivalent_flag_line_would(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Proven over values, which is the whole point of the seam being a Stub.

    The literal on the right is the request
    `install --ai-framework fw --runtime claude-code` builds, spelled out rather
    than derived, so the two are compared and not merely observed to agree.
    """

    def picked_framework(
        _catalog: Catalog,
    ) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
        return (("fw",), (), ())

    # given
    content = catalog_of(tmp_path, monkeypatch, "alpha", frameworks={"fw": ["fa"]})
    catalog = load_catalog(content, tmp_path / "packaged" / "catalog.toml")
    monkeypatch.setattr(wizard, "ask_artifacts", picked_framework)
    monkeypatch.setattr(wizard, "ask_scope", _project_scope)
    monkeypatch.setattr(wizard, "ask_runtimes", _fixed_runtimes)
    environment = Environment.from_process()

    outcome = wizard.run_wizard(Request(), catalog, environment, tmp_path, None)

    assert outcome is not None
    request, root = outcome
    assert isinstance(request, Request)
    assert request == Request(ai_frameworks=("fw",), runtimes=("claude-code",), scope=Scope.PROJECT)
    assert root == tmp_path


def test_run_wizard_carries_the_mode_flags_of_the_line_through_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--dry-run`, `--force` and `--yes` are not steps, and nothing here may drop them.

    Asserted against the real `run_wizard` and not against a stub of it: a
    version that built a fresh `Request` instead of replacing into the one it
    was handed would lose all three in silence, and only this side of the seam
    can see that.
    """
    # given
    content = catalog_of(tmp_path, monkeypatch, "alpha")
    catalog = load_catalog(content, tmp_path / "packaged" / "catalog.toml")
    monkeypatch.setattr(wizard, "ask_scope", _project_scope)
    monkeypatch.setattr(wizard, "ask_runtimes", _fixed_runtimes)
    asked = Request(skills=("alpha",), force=True, dry_run=True, yes=True)

    outcome = wizard.run_wizard(asked, catalog, Environment.from_process(), tmp_path, None)

    assert outcome is not None
    request, _ = outcome
    assert request == replace(asked, runtimes=("claude-code",), scope=Scope.PROJECT)


@pytest.mark.parametrize(
    ("asked", "scoped", "opened"),
    [
        pytest.param(Request(), None, ["artifacts", "scope", "runtimes"], id="bare"),
        pytest.param(
            Request(skills=("alpha",)), None, ["scope", "runtimes"], id="no runtime on the line"
        ),
        pytest.param(
            Request(runtimes=("claude-code",)),
            (Scope.PROJECT, Path()),
            ["artifacts"],
            id="no selection on the line",
        ),
    ],
)
def test_run_wizard_opens_only_the_steps_the_request_left_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    asked: Request,
    scoped: tuple[Scope, Path] | None,
    opened: list[str],
) -> None:
    """The same table the CLI is asserted against, one layer in and over values."""
    # given
    content = catalog_of(tmp_path, monkeypatch, "alpha")
    catalog = load_catalog(content, tmp_path / "packaged" / "catalog.toml")
    steps: list[str] = []

    def picked_skill(
        _catalog: Catalog,
    ) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
        steps.append("artifacts")
        return ((), (), ("alpha",))

    def scope_step(cwd: Path, environment: Environment) -> tuple[Scope, Path]:
        steps.append("scope")
        return _project_scope(cwd, environment)

    def runtime_step(scope: Scope, root: Path, environment: Environment) -> tuple[str, ...]:
        steps.append("runtimes")
        return _fixed_runtimes(scope, root, environment)

    monkeypatch.setattr(wizard, "ask_artifacts", picked_skill)
    monkeypatch.setattr(wizard, "ask_scope", scope_step)
    monkeypatch.setattr(wizard, "ask_runtimes", runtime_step)

    outcome = wizard.run_wizard(asked, catalog, Environment.from_process(), tmp_path, scoped)

    assert outcome is not None
    assert steps == opened


@pytest.mark.parametrize(
    "stage",
    [
        pytest.param("ask_artifacts", id="artifacts"),
        pytest.param("ask_scope", id="scope"),
        pytest.param("ask_runtimes", id="runtimes"),
    ],
)
def test_run_wizard_returns_none_when_any_step_is_abandoned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    """Backing out of one step abandons the whole wizard — the same shape as declining."""

    def picked_skill(
        _catalog: Catalog,
    ) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
        return ((), (), ("alpha",))

    def abandoned(*_args: object, **_kwargs: object) -> None:
        return None

    content = catalog_of(tmp_path, monkeypatch, "alpha")
    catalog = load_catalog(content, tmp_path / "packaged" / "catalog.toml")
    monkeypatch.setattr(wizard, "ask_artifacts", picked_skill)
    monkeypatch.setattr(wizard, "ask_scope", _project_scope)
    monkeypatch.setattr(wizard, "ask_runtimes", _fixed_runtimes)
    monkeypatch.setattr(wizard, stage, abandoned)

    assert wizard.run_wizard(Request(), catalog, Environment.from_process(), tmp_path, None) is None


# --------------------------------------------------------------------------- #
# the wiring, proven once, under a real PTY — POSIX only (docs/agents/testing.md, §7)
# --------------------------------------------------------------------------- #

_CHILD_SCRIPT = """
import sys
from overpower import cli, planning

captured_path = sys.argv[1]

def capture(request, catalog, root, environment):
    with open(captured_path, "w", encoding="utf-8") as fh:
        fh.write("ai_frameworks=" + ",".join(request.ai_frameworks) + "\\n")
        fh.write("bundles=" + ",".join(request.bundles) + "\\n")
        fh.write("skills=" + ",".join(request.skills) + "\\n")
        fh.write("runtimes=" + ",".join(request.runtimes) + "\\n")
        fh.write("scope=" + str(request.scope) + "\\n")
    return planning.Plan(root=root, selections=())

cli.plan_for = capture
sys.exit(cli.main(["install", "--yes"] + sys.argv[2:]))
"""
"""Runs inside the child. Captures the `Request` the real `questionary` under
the PTY produced as `key=value` lines — no `json`, which `TID251` reserves for
`overpower.jsonio` — then hands back an empty `Plan` so the process exits
clean without writing anything: the test is about the seam, not `execute`.

Everything past the capture path is appended to the command line, which is what
lets the same child drive both the bare invocation and a partial one."""


def _parsed(text: str) -> dict[str, str]:
    """`key=value` lines back into a mapping, `,`-joined values still joined."""
    return dict(line.split("=", 1) for line in text.splitlines() if line)


def _drive(cwd: Path, home: Path, captured: Path, keys: str, *flags: str) -> None:
    """Fork a PTY, run the real `install`, and feed it `keys` as the screens ask for them.

    Adapted from the throwaway PTY driver of #12
    (`prototype/terminal-experience/drive.py`), which measured that
    `questionary` needs an actual terminal — a pipe raises `EOFError`.
    """
    import pty  # noqa: PLC0415 — POSIX-only module, imported only where this runs

    env = dict(os.environ, HOME=str(home), USERPROFILE=str(home))
    env.update(COLUMNS="80", LINES="40", TERM="xterm-256color")
    pid, fd = pty.fork()
    if pid == 0:  # pragma: no cover — runs in the child, a separate process
        os.chdir(cwd)
        argv = [sys.executable, "-c", _CHILD_SCRIPT, str(captured), *flags]
        os.execvpe(sys.executable, argv, env)  # noqa: S606 — replaces this forked child, not a shell

    sent = 0
    deadline = time.time() + 25
    while time.time() < deadline and not captured.exists():
        ready, _, _ = select.select([fd], [], [], 0.4)
        if ready:
            try:
                if not os.read(fd, 65536):
                    break
            except OSError:
                break
        elif sent < len(keys):
            time.sleep(0.5)
            os.write(fd, keys[sent].encode())
            sent += 1

    os.close(fd)
    with contextlib.suppress(ChildProcessError, OSError):
        os.waitpid(pid, 0)


@pytest.mark.skipif(sys.platform == "win32", reason="pty is POSIX only, docs/agents/testing.md §7")
def test_the_real_wizard_under_a_pty_produces_the_expected_request(tmp_path: Path) -> None:
    """The one test that proves the wiring down to the real `questionary`, not the pixels.

    Against the real shipped catalog — one AI Framework, one pool skill, one
    bundle — so the first artifact choice is deterministic without pinning a
    curated name that a refresh could rename. Runtimes are equally deterministic
    off the runtime table itself: the universal group is shown first and every
    row of it is locked, so the pointer opens on the first row of *Additional
    agents*, which in table order is `aider-desk`. What comes back is therefore
    the locked group plus that one — and both halves are computed from the table
    here rather than typed, so a refresh moves them together.
    """
    # given
    cwd = tmp_path / "project"
    cwd.mkdir()
    (cwd / ".git").mkdir()
    home = tmp_path / "home"
    home.mkdir()
    captured = tmp_path / "captured.txt"
    keys = " \r\r \r"  # artifacts: toggle, submit — scope: default — runtimes: toggle, submit

    _drive(cwd, home, captured, keys)

    assert captured.exists(), "the child never reached plan_for within the deadline"
    data = _parsed(captured.read_text(encoding="utf-8"))
    assert len(data["ai_frameworks"].split(",")) == 1
    assert data["bundles"] == ""
    assert data["skills"] == ""
    assert data["scope"] == "project"
    assert data["runtimes"] == ",".join(_locked_plus_the_first_additional(Scope.PROJECT))


@pytest.mark.skipif(sys.platform == "win32", reason="pty is POSIX only, docs/agents/testing.md §7")
def test_the_real_wizard_under_a_pty_opens_only_the_gap_a_partial_line_leaves(
    tmp_path: Path,
) -> None:
    """The other half of the same wiring: the line the catalog prints, pasted back.

    `install --ai-framework <name>` names what to install and no runtime, so
    two screens open and the artifacts one does not — and the proof that it did
    not is the framework arriving **unchanged**, since the only thing that could
    have replaced it is a pick made on a screen that never ran.

    Two keystrokes drive it, against three for the bare line, and that
    difference *is* the assertion: the same keys sent to the old wizard would
    have answered the artifacts screen instead.
    """
    # given
    framework = load_catalog(content_root(), catalog_file()).frameworks[0]
    cwd = tmp_path / "project"
    cwd.mkdir()
    (cwd / ".git").mkdir()
    home = tmp_path / "home"
    home.mkdir()
    captured = tmp_path / "captured.txt"
    keys = "\r \r"  # scope: default — runtimes: toggle, submit

    _drive(cwd, home, captured, keys, "--ai-framework", framework.name)

    assert captured.exists(), "the child never reached plan_for within the deadline"
    data = _parsed(captured.read_text(encoding="utf-8"))
    assert data["ai_frameworks"] == framework.name
    assert data["skills"] == ""
    assert data["bundles"] == ""
    assert data["scope"] == "project"
    assert data["runtimes"] == ",".join(_locked_plus_the_first_additional(Scope.PROJECT))


def _locked_plus_the_first_additional(scope: Scope) -> tuple[str, ...]:
    """What one tap of the space bar on an untouched runtime screen produces.

    The locked group is in whatever the pick was; the pointer starts on the
    first selectable row, which is the first member of *Additional agents*.
    """
    locked = {runtime.key for runtime in universal_runtimes(scope)}
    first = next(runtime.key for runtime in runtimes_in(scope) if runtime.key not in locked)
    return _in_table_order(scope, locked | {first})
