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
from typing import TYPE_CHECKING

import pytest
import questionary

from overpower import wizard
from overpower.discovery import load_catalog
from overpower.planning import Request
from overpower.runtimes import Environment, Scope
from tests.support.project import catalog_of

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

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


def test_runtime_choices_are_scoped_and_never_disabled() -> None:
    project_choices = _real_choices(wizard.runtime_choices(Scope.PROJECT, frozenset()))
    global_choices = _real_choices(wizard.runtime_choices(Scope.GLOBAL, frozenset()))

    assert len(project_choices) == 76
    assert len(global_choices) == 74
    assert all(choice.disabled is None for choice in (*project_choices, *global_choices))


def test_runtime_choices_pre_check_exactly_what_was_detected() -> None:
    choices = _real_choices(wizard.runtime_choices(Scope.PROJECT, frozenset({"claude-code"})))

    checked = {choice.value for choice in choices if choice.checked}
    assert checked == {"claude-code"}


def test_runtime_choices_group_the_universal_set_under_one_heading() -> None:
    choices = wizard.runtime_choices(Scope.PROJECT, frozenset())

    separators = [c for c in choices if isinstance(c, questionary.Separator)]
    assert any("Universal" in separator.line for separator in separators)


def test_ask_runtimes_returns_the_pick_as_a_tuple(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wizard.questionary, "checkbox", _answering(["claude-code", "cursor"]))

    result = wizard.ask_runtimes(Scope.PROJECT, tmp_path, _environment(tmp_path))

    assert result == ("claude-code", "cursor")


def test_ask_runtimes_returns_none_on_interruption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wizard.questionary, "checkbox", _answering(None))

    assert wizard.ask_runtimes(Scope.PROJECT, tmp_path, _environment(tmp_path)) is None


# --------------------------------------------------------------------------- #
# the three steps together: the same `Request` the flags would build
# --------------------------------------------------------------------------- #


def _project_scope(cwd: Path, _environment: Environment) -> tuple[Scope, Path]:
    return Scope.PROJECT, cwd


def _fixed_runtimes(_scope: Scope, _root: Path, _environment: Environment) -> tuple[str, ...]:
    return ("claude-code",)


def test_run_wizard_builds_the_same_request_type_the_flags_would(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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

    outcome = wizard.run_wizard(catalog, environment, tmp_path)

    assert outcome is not None
    request, root = outcome
    assert isinstance(request, Request)
    assert request == Request(ai_frameworks=("fw",), runtimes=("claude-code",), scope=Scope.PROJECT)
    assert root == tmp_path


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

    assert wizard.run_wizard(catalog, Environment.from_process(), tmp_path) is None


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
sys.exit(cli.main(["install", "--yes"]))
"""
"""Runs inside the child. Captures the `Request` the real `questionary` under
the PTY produced as `key=value` lines — no `json`, which `TID251` reserves for
`overpower.jsonio` — then hands back an empty `Plan` so the process exits
clean without writing anything: the test is about the seam, not `execute`."""


def _parsed(text: str) -> dict[str, str]:
    """`key=value` lines back into a mapping, `,`-joined values still joined."""
    return dict(line.split("=", 1) for line in text.splitlines() if line)


def _drive(cwd: Path, home: Path, captured: Path, keys: str) -> None:
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
        argv = [sys.executable, "-c", _CHILD_SCRIPT, str(captured)]
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
    curated name that a refresh could rename. Runtimes are equally
    deterministic off the runtime table itself: the first row, `aider-desk`,
    is in the universal group, shown first.
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
    assert data["runtimes"] == "aider-desk"
