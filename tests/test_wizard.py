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
import io
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
from rich.console import Console

from overpower import wizard
from overpower.discovery import load_catalog
from overpower.packaged import catalog_file, content_root
from overpower.planning import Request
from overpower.runtimes import (
    UNIVERSAL_PROJECT_DIR,
    Environment,
    Scope,
    mcp_document_of,
    mcp_runtimes_in,
    runtimes_in,
    universal_runtimes,
)
from overpower.screens import RAIL, THEME
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


def _console() -> Console:
    """A console that renders into nothing, for the steps that narrate the session.

    `run_wizard` and `ask_scope` print the rail and the collapsed step through
    the one console `overpower.cli` owns. What they print is asserted where it
    is drawn — `tests/test_screens.py` — so here it only has to go somewhere
    that is not the test's own output.
    """
    return Console(file=io.StringIO(), theme=THEME, highlight=False, width=80)


def _environment(home: Path) -> Environment:
    def _nothing_exists(_path: Path) -> bool:
        return False

    return Environment(
        home=home, variables={}, directory_exists=_nothing_exists, platform=sys.platform
    )


def test_ask_scope_inside_a_repository_offers_both(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".git").mkdir()
    seen: dict[str, object] = {}

    def fake_select(_message: str, choices: object, **_kwargs: object) -> _Answered:
        seen["choices"] = choices
        return _Answered(Scope.GLOBAL)

    monkeypatch.setattr(wizard.questionary, "select", fake_select)
    environment = _environment(tmp_path / "home")

    outcome = wizard.ask_scope(tmp_path, environment, _console())

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

    outcome = wizard.ask_scope(tmp_path, environment, _console())

    assert outcome is not None
    scope, root = outcome
    assert scope is Scope.PROJECT
    assert root == tmp_path


def test_ask_scope_returns_none_on_interruption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".git").mkdir()
    monkeypatch.setattr(wizard.questionary, "select", _answering(None))

    assert wizard.ask_scope(tmp_path, _environment(tmp_path / "home"), _console()) is None


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

    result = wizard.ask_scope(bare, environment, _console())

    assert result == (Scope.GLOBAL, environment.home)
    assert asked == []


# --------------------------------------------------------------------------- #
# step 3: runtimes
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("scope", "offered"),
    [
        pytest.param(Scope.PROJECT, 57, id="project"),
        pytest.param(Scope.GLOBAL, 68, id="global"),
    ],
)
def test_runtime_choices_are_scoped_and_offer_everything_the_group_does_not_cover(
    scope: Scope, offered: int
) -> None:
    """#65: the locked group left the control, so every row of the list can be ticked.

    Three properties and not one count, because the count alone would pass on a
    list that had lost rows: nothing offered is disabled, nothing offered is
    already covered by the group, and the two together are the scoped table
    whole.
    """
    choices = wizard.runtime_choices(scope, frozenset())
    covered = {runtime.key for runtime in universal_runtimes(scope)}
    offered_keys = {choice.value for choice in choices}

    assert len(choices) == offered
    assert all(choice.disabled is None for choice in choices)
    assert offered_keys.isdisjoint(covered)
    assert offered_keys | covered == {runtime.key for runtime in runtimes_in(scope)}


@pytest.mark.parametrize(
    ("scope", "members"),
    [pytest.param(Scope.PROJECT, 19, id="project"), pytest.param(Scope.GLOBAL, 6, id="global")],
)
def test_the_universal_group_is_static_text_and_never_a_line_to_tick(
    scope: Scope, members: int
) -> None:
    """ADR 0011 survives #65: the group is shown, counted, and offered to nobody.

    The membership is asserted against the block's own count rather than
    against rows, because since #65 the block **names four and counts the
    rest** — which is the change that gave the step its viewport back.
    """
    covered = {runtime.key for runtime in universal_runtimes(scope)}
    assert len(covered) == members

    text = _block_text(scope)
    assert f"{members} runtimes" in text
    assert covered.isdisjoint({c.value for c in wizard.runtime_choices(scope, frozenset())})


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
    assert f"Universal ({place})" in _block_text(scope)


def test_the_universal_heading_says_it_is_always_included_and_counts_its_members() -> None:
    """*Always included* and a number is what the reader gets instead of counting boxes."""
    text = _block_text(Scope.PROJECT)

    assert wizard.ALWAYS_INCLUDED in text
    assert "19 runtimes" in text


def test_runtime_choices_pre_check_exactly_what_was_detected() -> None:
    choices = _real_choices(wizard.runtime_choices(Scope.PROJECT, frozenset({"claude-code"})))

    checked = {choice.value for choice in choices if choice.checked}
    assert checked == {"claude-code"}


def test_a_locked_runtime_is_never_pre_checked_because_it_is_not_a_choice() -> None:
    """Detection pre-marks a decision; a covered runtime has none to pre-mark."""
    detected = frozenset({"cursor", "claude-code"})

    choices = wizard.runtime_choices(Scope.PROJECT, detected)

    checked = {choice.value for choice in choices if choice.checked}
    assert checked == {"claude-code"}  # `cursor` reads `.agents/skills`, so it is covered


def test_the_universal_heading_covers_exactly_the_runtimes_that_read_that_path() -> None:
    """The heading names a path, so its members are whoever reads it — nobody else.

    Asserted over membership and not merely over the presence of the heading,
    which is the assertion whose absence let the group be built from
    `in_universal_list`: that flag is `False` on two rows, so it gathered 74
    runtimes under `.agents/skills` when 19 read it.
    """
    # given
    reads_the_path = {
        runtime.key
        for runtime in runtimes_in(Scope.PROJECT)
        if runtime.project_dir is not None and runtime.project_dir.relative == UNIVERSAL_PROJECT_DIR
    }

    offered = {choice.value for choice in wizard.runtime_choices(Scope.PROJECT, frozenset())}

    assert {runtime.key for runtime in universal_runtimes(Scope.PROJECT)} == reads_the_path
    assert offered == {runtime.key for runtime in runtimes_in(Scope.PROJECT)} - reads_the_path


def test_no_runtime_is_grouped_under_a_path_it_does_not_read() -> None:
    """The measured shape of the defect: `claude-code` reads `.claude/skills`.

    Named individually because the three of them are the ones a reader
    recognises, and because a count alone would not say *which* rows moved.
    """
    offered = {choice.value for choice in wizard.runtime_choices(Scope.PROJECT, frozenset())}

    assert "claude-code" in offered
    assert "droid" in offered
    assert "astrbot" in offered


def _block_text(scope: Scope) -> str:
    """The static universal block, flattened to the text it puts on screen."""
    return "".join(fragment[1] for fragment in wizard.locked_block(scope)())


TERMINAL_ROWS = 24
"""The default terminal, and the height every budget below is measured against."""

QUESTION_ROWS = 1
COUNTER_ROWS = 1
FOOTER_ROWS = 3
"""What the step spends outside the static block and the list: the question, the
`↓ N more` line, and the three of the live footer — a rail, the `Selected:` line
and the closing `└`."""

NPX_VISIBLE_ROWS = 8
"""What `npx skills add` keeps on screen, and therefore the floor for the viewport."""


def test_the_runtime_step_fits_a_twenty_four_row_terminal() -> None:
    """The defect #65 exists for, asserted as a budget so all nine cells run it.

    Measured before: the step drew **19 locked rows**, two separators and a
    two-line hint, filling 23 of the 24 rows of a default terminal and leaving
    **one** selectable row on screen — with the row detection had pre-ticked
    below the fold and nothing saying 55 more existed.

    A budget and not a screen recording, and the limit is declared rather than
    hidden: what a byte stream from a PTY cannot prove is *visibility*, because
    the old layout wrote all 57 rows too and simply let the terminal scroll them
    away. Arithmetic is what separates *written* from *on screen*, so this is
    the guard, and the PTY test below proves only that the layout reaches a real
    terminal.

    It runs against the **project** scope because that is the larger of the two
    groups — 19 members against 6 — so the scope that fits is the scope that
    binds.
    """
    static = _block_text(Scope.PROJECT).count("\n") + 1

    spent = QUESTION_ROWS + static + wizard.VIEWPORT + COUNTER_ROWS + FOOTER_ROWS

    assert spent <= TERMINAL_ROWS
    assert wizard.VIEWPORT >= NPX_VISIBLE_ROWS


@pytest.mark.parametrize(
    "scope", [pytest.param(Scope.PROJECT, id="project"), pytest.param(Scope.GLOBAL, id="global")]
)
def test_the_static_block_names_a_few_and_counts_the_rest(scope: Scope) -> None:
    """Bounded however large the group grows, which is what keeps the budget above true.

    Naming all 19 is exactly what cost the step its viewport: the block is
    **informative**, and what it informs about is the single path on its
    heading, so it has to be recognisable rather than exhaustive.
    """
    text = _block_text(scope)
    members = len(universal_runtimes(scope))

    named = [line for line in text.splitlines() if "•" in line]

    assert len(named) <= wizard.LOCKED_SHOWN
    assert f"{members - wizard.LOCKED_SHOWN} more" in text


@pytest.mark.parametrize(
    "scope", [pytest.param(Scope.PROJECT, id="project"), pytest.param(Scope.GLOBAL, id="global")]
)
def test_every_line_of_the_static_block_sits_on_the_rail(scope: Scope) -> None:
    """The rail is what makes the step read as one gesture, so no line may fall off it."""
    lines = [line for line in _block_text(scope).splitlines() if line]

    assert all(line.startswith(RAIL) for line in lines)


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


# --------------------------------------------------------------------------- #
# #97: the graft class gets its own runtime step — no universal group,
# labelled by file, counted by its own table.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "scope", [pytest.param(Scope.PROJECT, id="project"), pytest.param(Scope.GLOBAL, id="global")]
)
def test_mcp_runtime_choices_offer_only_mcp_documents_in_scope_with_no_universal_group(
    scope: Scope,
) -> None:
    choices = wizard.mcp_runtime_choices(scope, frozenset())

    assert {choice.value for choice in choices} == set(mcp_runtimes_in(scope))
    assert all(choice.disabled is None for choice in choices)


def test_mcp_runtime_choices_label_each_row_by_the_file_it_receives() -> None:
    choices = wizard.mcp_runtime_choices(Scope.PROJECT, frozenset())

    by_key = {choice.value: str(choice.title) for choice in choices}
    document = mcp_document_of("vscode", Scope.PROJECT)
    assert document is not None
    assert document.relative in by_key["vscode"]
    assert "VS Code" in by_key["vscode"]


def test_mcp_runtime_choices_pre_check_exactly_what_was_detected() -> None:
    choices = wizard.mcp_runtime_choices(Scope.PROJECT, frozenset({"vscode"}))

    checked = {choice.value for choice in choices if choice.checked}
    assert checked == {"vscode"}


def test_ask_mcp_runtimes_answers_only_what_was_picked_with_no_locked_group(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The mirror of `ask_runtimes`'s union, minus the union: nothing is added unasked."""
    monkeypatch.setattr(wizard.questionary, "checkbox", _answering(["vscode"]))

    result = wizard.ask_mcp_runtimes(Scope.PROJECT, tmp_path, _environment(tmp_path))

    assert result == ("vscode",)


def test_ask_mcp_runtimes_with_nothing_picked_answers_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No universal group means an empty pick is a genuinely empty answer."""
    monkeypatch.setattr(wizard.questionary, "checkbox", _answering([]))

    result = wizard.ask_mcp_runtimes(Scope.PROJECT, tmp_path, _environment(tmp_path))

    assert result == ()


def test_ask_mcp_runtimes_returns_none_on_interruption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wizard.questionary, "checkbox", _answering(None))

    assert wizard.ask_mcp_runtimes(Scope.PROJECT, tmp_path, _environment(tmp_path)) is None


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
        pytest.param("terminal", ["Devin for Terminal"], id="second word"),
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
    questionary 2.1.1 — `dev` down to 2, `terminal` to 1 — and `laude` is the
    one that separates a substring match from a prefix match, being the start of
    no name at all. `copilot` was the original second-word case and is no longer
    one: since #65 the universal group is not in the list, and GitHub Copilot
    reads `.agents/skills` in project scope, so it has no row to find.
    """
    control = InquirerControl(list(wizard.runtime_choices(Scope.PROJECT, frozenset())))
    control.search_filter = typed

    assert [_named(choice) for choice in control.filtered_choices] == narrowed


def _named(choice: questionary.Choice) -> str:
    """A row's runtime name, without the tree `_choice` appends to it.

    Since #65 the title is `Cursor (.agents/skills)`, because the plan speaks in
    paths and the row that chooses one may not hide it. The search therefore
    matches the path too — measured, `.claude` narrows to one row — and that is
    a gain rather than a cost; what it is not is a reason to assert names with
    a path glued on.
    """
    return str(choice.title).split(" (")[0]


def test_a_search_that_matches_nothing_leaves_the_whole_list_standing() -> None:
    """Measured: `questionary` falls back to every choice rather than to an empty screen."""
    control = InquirerControl(list(wizard.runtime_choices(Scope.PROJECT, frozenset())))
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


def _project_scope(cwd: Path, _environment: Environment, _console: Console) -> tuple[Scope, Path]:
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

    outcome = wizard.run_wizard(Request(), catalog, environment, tmp_path, None, console=_console())

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

    outcome = wizard.run_wizard(
        asked, catalog, Environment.from_process(), tmp_path, None, console=_console()
    )

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

    def scope_step(cwd: Path, environment: Environment, console: Console) -> tuple[Scope, Path]:
        steps.append("scope")
        return _project_scope(cwd, environment, console)

    def runtime_step(scope: Scope, root: Path, environment: Environment) -> tuple[str, ...]:
        steps.append("runtimes")
        return _fixed_runtimes(scope, root, environment)

    monkeypatch.setattr(wizard, "ask_artifacts", picked_skill)
    monkeypatch.setattr(wizard, "ask_scope", scope_step)
    monkeypatch.setattr(wizard, "ask_runtimes", runtime_step)

    outcome = wizard.run_wizard(
        asked, catalog, Environment.from_process(), tmp_path, scoped, console=_console()
    )

    assert outcome is not None
    assert steps == opened


def _fixed_mcp_runtimes(_scope: Scope, _root: Path, _environment: Environment) -> tuple[str, ...]:
    return ("claude-code",)


def _never_called(*_args: object, **_kwargs: object) -> object:
    message = "this step must not open on a line that already answered it"
    raise AssertionError(message)


def _never_ask_runtimes(*_args: object, **_kwargs: object) -> tuple[str, ...]:
    message = "a line that carries `mcps` must open the graft class's own runtime step"
    raise AssertionError(message)


def test_run_wizard_opens_the_mcp_runtime_step_for_a_line_that_carries_mcps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """#97: `--mcp` with no `--runtime` reaches `ask_mcp_runtimes`, never the skills step.

    A mixed line (skills and MCP, no `--runtime`) never reaches `run_wizard` at
    all — `overpower.cli` refuses it before the wizard opens — so `asked.mcps`
    truthy here is always the whole line, and the artifacts step is skipped the
    same way a filled `asked.skills` already skips it.
    """
    # given
    asked = Request(mcps=("cloudflare",))
    monkeypatch.setattr(wizard, "ask_artifacts", _never_called)
    monkeypatch.setattr(wizard, "ask_scope", _project_scope)
    monkeypatch.setattr(wizard, "ask_runtimes", _never_ask_runtimes)
    monkeypatch.setattr(wizard, "ask_mcp_runtimes", _fixed_mcp_runtimes)

    outcome = wizard.run_wizard(
        asked, None, Environment.from_process(), tmp_path, None, console=_console()
    )

    assert outcome is not None
    request, _ = outcome
    assert request.runtimes == ("claude-code",)
    assert request.mcps == ("cloudflare",)


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

    assert (
        wizard.run_wizard(
            Request(), catalog, Environment.from_process(), tmp_path, None, console=_console()
        )
        is None
    )


# --------------------------------------------------------------------------- #
# the wiring, proven once, under a real PTY — POSIX only (docs/agents/testing.md, §7)
# --------------------------------------------------------------------------- #

_CHILD_SCRIPT = """
import sys
from overpower import cli, planning

captured_path = sys.argv[1]

def capture(request, catalog, root, environment, sources=None):
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


def _drive(cwd: Path, home: Path, captured: Path, keys: str, *flags: str) -> bytes:
    """Fork a PTY, run the real `install`, and feed it `keys` as the screens ask for them.

    Adapted from the throwaway PTY driver of #12
    (`prototype/terminal-experience/drive.py`), which measured that
    `questionary` needs an actual terminal — a pipe raises `EOFError`.

    It answers everything the child drew, which is what lets one test assert the
    `Request` and another assert that the railed layout of #65 reached a real
    terminal at all. What the bytes cannot say is what was *visible* — the old
    layout wrote every row too and let the terminal scroll them — so the
    visibility budget is asserted arithmetically instead.
    """
    import pty  # noqa: PLC0415 — POSIX-only module, imported only where this runs

    env = dict(os.environ, HOME=str(home), USERPROFILE=str(home))
    env.update(COLUMNS="80", LINES="40", TERM="xterm-256color")
    pid, fd = pty.fork()
    if pid == 0:  # pragma: no cover — runs in the child, a separate process
        os.chdir(cwd)
        argv = [sys.executable, "-c", _CHILD_SCRIPT, str(captured), *flags]
        os.execvpe(sys.executable, argv, env)  # noqa: S606 — replaces this forked child, not a shell

    drawn = bytearray()
    sent = 0
    deadline = time.time() + 25
    while time.time() < deadline and not captured.exists():
        ready, _, _ = select.select([fd], [], [], 0.4)
        if ready:
            try:
                chunk = os.read(fd, 65536)
            except OSError:
                break
            if not chunk:
                break
            drawn.extend(chunk)
        elif sent < len(keys):
            time.sleep(0.5)
            os.write(fd, keys[sent].encode())
            sent += 1

    os.close(fd)
    with contextlib.suppress(ChildProcessError, OSError):
        os.waitpid(pid, 0)
    return bytes(drawn)


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


@pytest.mark.skipif(sys.platform == "win32", reason="pty is POSIX only, docs/agents/testing.md §7")
def test_the_railed_layout_reaches_a_real_terminal(tmp_path: Path) -> None:
    """The layout replacement of #65, proven end to end rather than in a unit.

    `common.create_inquirer_layout` is replaced at call time, so everything
    below it — the static block, the viewport, the counter and the live footer —
    exists only if the real `questionary` picked the replacement up. A unit test
    of `locked_block` cannot see that; this can, because these four strings can
    only be on the wire if the substituted layout drew them.

    **What it deliberately does not assert is visibility.** The old layout wrote
    all 57 rows too and let the terminal scroll them away, so presence in a byte
    stream proves nothing about what fitted —
    `test_the_runtime_step_fits_a_twenty_four_row_terminal` is where that lives.
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

    drawn = _drive(cwd, home, captured, keys, "--ai-framework", framework.name).decode(
        "utf-8", "replace"
    )

    assert captured.exists(), "the child never reached plan_for within the deadline"
    assert RAIL in drawn, "the rail never reached the terminal"
    assert wizard.ALWAYS_INCLUDED in drawn, "the static universal block never drew"
    assert "more" in drawn, "the `N more` counter never drew"
    assert "Selected:" in drawn, "the live footer never drew"
