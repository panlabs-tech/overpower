"""The wizard: `install` bare in a terminal, four steps, one `Request` out.

Artifacts, then scope, then runtimes, then confirmation
(https://github.com/panlabs-tech/overpower/issues/41). The order is not
aesthetic: the runtime probe depends on scope — project probes the target
repository, global probes `~` — so asking runtimes before scope would probe
the wrong root (ADR 0008). Confirmation is the fourth step and needs no code
here: it is the same plan screen and the same `y`/`n` the flag path already
draws, once this module hands `overpower.cli` the same `Request` type the
flags would have built.

Each `ask_*` function is the seam: one `questionary` call, `.ask()`ed, and
nothing else around it. Flow tests stub it directly — it supplies indirect
input, it does not emulate `questionary`'s own behaviour, so it is a Stub and
the house ruler excludes Stub from contract testing by name
(`docs/agents/testing.md`, §7). Public rather than underscored, the way
`overpower.runtimes.runtimes_in` is: what a test calls directly cannot also be
private, under `pyright --strict`. What proves the wiring down to the real
library is the one PTY test next to this module's tests, POSIX only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import questionary

from overpower.planning import Request
from overpower.runtimes import UNIVERSAL_PROJECT_DIR, Scope, detected_runtimes, runtimes_in
from overpower.scope import git_root

if TYPE_CHECKING:
    from pathlib import Path

    from overpower.discovery import Catalog
    from overpower.runtimes import Environment, Runtime


def run_wizard(
    catalog: Catalog, environment: Environment, cwd: Path
) -> tuple[Request, Path] | None:
    """The three steps this module owns, or `None` when the user backs out of any of them.

    `.ask()` answers `None` on interruption — the same gesture `_confirmed()`
    already treats as a decline — and that meaning is threaded through here
    unchanged: backing out of any one step abandons the whole wizard rather
    than resuming at the previous one, which is the same all-or-nothing shape
    the final confirmation already has.
    """
    picked = ask_artifacts(catalog)
    if picked is None:
        return None
    ai_frameworks, bundles, skills = picked

    scoped = ask_scope(cwd, environment)
    if scoped is None:
        return None
    scope, root = scoped

    runtimes = ask_runtimes(scope, root, environment)
    if runtimes is None:
        return None

    return (
        Request(
            ai_frameworks=ai_frameworks,
            bundles=bundles,
            skills=skills,
            runtimes=runtimes,
            scope=scope,
        ),
        root,
    )


def ask_artifacts(
    catalog: Catalog,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]] | None:
    """What to install — the three independent units, one flat multi-select.

    Empty is a legal answer here: an empty pick lands on the same
    `NothingSelectedError` the flag path already raises, once `plan_for` sees
    the `Request` this step feeds — one place names that defect, reached by
    two doors.
    """
    picked = questionary.checkbox(
        "What should this install bring?", choices=artifact_choices(catalog)
    ).ask()
    if picked is None:
        return None
    return (
        tuple(name for kind, name in picked if kind == "framework"),
        tuple(name for kind, name in picked if kind == "bundle"),
        tuple(name for kind, name in picked if kind == "skill"),
    )


def artifact_choices(catalog: Catalog) -> list[questionary.Separator | questionary.Choice]:
    """One flat list, grouped the way the catalog screen already groups the same three units.

    A group with nothing in it prints no heading: an empty bundle list is a
    real catalog shape, not a defect this screen exists to name.
    """
    groups = (
        ("AI Frameworks", tuple(("framework", framework.name) for framework in catalog.frameworks)),
        ("Bundles", tuple(("bundle", bundle.name) for bundle in catalog.bundles)),
        ("Pool skills", tuple(("skill", artifact.name) for artifact in catalog.pool)),
    )
    choices: list[questionary.Separator | questionary.Choice] = []
    for title, entries in groups:
        if not entries:
            continue
        choices.append(questionary.Separator(f"-- {title} --"))
        choices.extend(questionary.Choice(name, value=(kind, name)) for kind, name in entries)
    return choices


def ask_scope(cwd: Path, environment: Environment) -> tuple[Scope, Path] | None:
    """Project or the machine — and outside a repository there is only one legal answer.

    Offering `Project` with nowhere to write would be the anti-pattern ADR
    0008 and ADR 0009 already refuse one layer further down: a screen that
    names what the next step cannot honour. Outside a repository the flag
    path already demands `--global` explicitly (`OutsideRepositoryError`); the
    wizard's equivalent of that explicitness is not asking a question that has
    only one legal answer, rather than asking it and disabling the other one.
    """
    if git_root(cwd) is None:
        return Scope.GLOBAL, environment.home
    picked = questionary.select(
        "Where should this install write to?",
        choices=[
            questionary.Choice("This repository", value=Scope.PROJECT),
            questionary.Choice("This machine (~/), every project", value=Scope.GLOBAL),
        ],
    ).ask()
    if picked is None:
        return None
    return picked, (cwd if picked is Scope.PROJECT else environment.home)


def ask_runtimes(scope: Scope, root: Path, environment: Environment) -> tuple[str, ...] | None:
    """Which runtimes read this equipment — scoped, pre-marked by detection, never locked.

    Asked even when detection pre-marks exactly one runtime: pre-marking is a
    convenience, not a decision made on the user's behalf, and a single
    detected runtime is exactly the case where a silent default would be
    loneliest.
    """
    picked = questionary.checkbox(
        "Which runtimes should read this equipment?",
        choices=runtime_choices(scope, detected_runtimes(scope, root, environment)),
    ).ask()
    if picked is None:
        return None
    return tuple(picked)


def runtime_choices(
    scope: Scope, detected: frozenset[str]
) -> list[questionary.Separator | questionary.Choice]:
    """The scoped table (ADR 0009), universal group first, nothing ever `disabled`.

    `runtimes_in(scope)` is the one implementation the screen and the flag
    validator both consume, so global scope never offers the two runtimes with
    no destination there. The universal group is shown grouped, the way the
    upstream screen groups it, and unlocked in every scope: #9 already removed
    the project canonical that justified the lock upstream carries, and
    global scope never had a fixed canonical to lock either — which selection
    becomes canonical there is a function of what gets picked, not a fact
    knowable before the pick (`overpower.planning`).
    """
    candidates = runtimes_in(scope)
    universal = [runtime for runtime in candidates if runtime.in_universal_list]
    other = [runtime for runtime in candidates if not runtime.in_universal_list]
    choices: list[questionary.Separator | questionary.Choice] = [
        questionary.Separator(f"-- Universal ({UNIVERSAL_PROJECT_DIR}) --"),
        *(_choice(runtime, detected) for runtime in universal),
    ]
    if other:
        choices.append(questionary.Separator("-- Other --"))
        choices.extend(_choice(runtime, detected) for runtime in other)
    return choices


def _choice(runtime: Runtime, detected: frozenset[str]) -> questionary.Choice:
    """One runtime, pre-checked by detection, never `disabled`."""
    return questionary.Choice(
        runtime.display_name, value=runtime.key, checked=runtime.key in detected
    )
