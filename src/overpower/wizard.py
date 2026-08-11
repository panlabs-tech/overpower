"""The wizard: a terminal, a line that does not add up to a plan, one `Request` out.

Artifacts, then scope, then runtimes, then confirmation
(https://github.com/panlabs-tech/overpower/issues/41). The order is not
aesthetic: the runtime probe depends on scope — project probes the target
repository, global probes `~` — so asking runtimes before scope would probe
the wrong root (ADR 0008). Confirmation is the fourth step and needs no code
here: it is the same plan screen and the same `y`/`n` the flag path already
draws, once this module hands `overpower.cli` the same `Request` type the
flags would have built.

**The trigger is the gap and not the empty line**
(https://github.com/panlabs-tech/overpower/issues/57): a line missing a
selection *or* a runtime opens the wizard, and the wizard opens only the steps
that line left open. `install --ai-framework matt-pocock` therefore asks scope
and runtimes and never artifacts, which is what makes the command the catalog
prints a command that works when it is pasted back.

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

from dataclasses import replace
from typing import TYPE_CHECKING

import questionary

from overpower.runtimes import (
    Scope,
    detected_runtimes,
    runtimes_in,
    universal_place,
    universal_runtimes,
)
from overpower.scope import git_root

if TYPE_CHECKING:
    from pathlib import Path

    from overpower.discovery import Catalog
    from overpower.planning import Request
    from overpower.runtimes import Environment, Runtime

ALWAYS_INCLUDED = "always included"
"""What the locked section says of itself, on its heading and on every row of it.

One string and not two, because the heading and the row are the same claim seen
from two distances, and a screen that spelled it twice could spell it two ways.
"""


def run_wizard(
    asked: Request,
    catalog: Catalog | None,
    environment: Environment,
    cwd: Path,
    scoped: tuple[Scope, Path] | None,
) -> tuple[Request, Path] | None:
    """`asked` with its gaps filled, or `None` when the user backs out of any step.

    **Gaps, not steps** (https://github.com/panlabs-tech/overpower/issues/57):
    what the flags already fixed is not asked again, and what they did not is
    asked in the order #18 locked — artifacts, scope, runtimes, confirmation.
    `catalog` is `None` exactly when the artifacts step cannot open, and
    `scoped` is `None` exactly when the scope step is the caller's to ask;
    both are decided in `overpower.cli`, which is where the flags are.

    It **replaces into the request it was handed** rather than building a new
    one, and that is what keeps `--dry-run`, `--force` and `--yes` — which are
    not wizard steps — travelling through untouched. What comes out is
    indistinguishable from what the equivalent flag line would have built,
    which is what lets the selection logic be tested over values instead of
    over keystrokes.

    `.ask()` answers `None` on interruption — the same gesture `_confirmed()`
    already treats as a decline — and that meaning is threaded through here
    unchanged: backing out of any one step abandons the whole wizard rather
    than resuming at the previous one, which is the same all-or-nothing shape
    the final confirmation already has.
    """
    ai_frameworks, bundles, skills = asked.ai_frameworks, asked.bundles, asked.skills
    if not (ai_frameworks or bundles or skills):
        if catalog is None:  # pragma: no cover — `overpower.cli` decides the two together
            message = "the artifacts step opened with no catalog to read"
            raise AssertionError(message)
        picked = ask_artifacts(catalog)
        if picked is None:
            return None
        ai_frameworks, bundles, skills = picked

    if scoped is None:
        answered = ask_scope(cwd, environment)
        if answered is None:
            return None
        scope, root = answered
    else:
        scope, root = scoped

    runtimes = asked.runtimes
    if not runtimes:
        chosen = ask_runtimes(scope, root, environment)
        if chosen is None:
            return None
        runtimes = chosen

    return (
        replace(
            asked,
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
    """Which runtimes read this equipment — the locked group, plus whatever is picked.

    Asked even when detection pre-marks exactly one runtime: pre-marking is a
    convenience, not a decision made on the user's behalf, and a single
    detected runtime is exactly the case where a silent default would be
    loneliest.

    **The lock is of the screen, not of the plan** (ADR 0011): the keys of the
    universal group travel in the `Request` this step feeds, exactly like a key
    somebody ticked, so `overpower install --runtime claude-code` on the flag
    line still writes `.claude/skills/` and nothing else. A lock that were a
    planning rule would make that flag write two trees, and the flag would stop
    saying what it does.

    The union is taken over the **scoped table's order** and through a set, so
    the answer is deterministic and names nothing twice — which matters because
    a locked line can still come back in the pick: `questionary` moves the
    pointer to the top of the filtered list when a search character arrives,
    and the top of a filtered list may be a disabled row.
    """
    picked = questionary.checkbox(
        "Which runtimes should read this equipment?",
        choices=runtime_choices(scope, detected_runtimes(scope, root, environment)),
        # The search is what makes a 76-row list navigable: measured on
        # questionary 2.1.1, `dev` reduces it to 2 rows, `copilot` to 1 and
        # `claude` to 1, against 22 lines visible at 80x24. It costs two things,
        # both fixed in the library and both taken knowingly.
        #
        # `j`/`k` stop navigating — `ValueError: Cannot use j/k keys with prefix
        # filter search, since j/k can be part of the prefix.` The arrow keys and
        # the Emacs pair survive, and `j`/`k` are a binding this project never
        # committed to.
        #
        # And **the filter is of the list, not of one section**: `Separator`
        # subclasses `Choice`, so a search hides the group headings along with
        # whatever missed, and the locked rows are filtered like any other. It
        # cannot be scoped from here. What it costs is the heading disappearing
        # while its rows are still on screen — which is the second reason each
        # locked row carries its own `always included` label rather than leaning
        # on the heading for it.
        use_search_filter=True,
        use_jk_keys=False,
    ).ask()
    if picked is None:
        return None
    chosen: tuple[str, ...] = tuple(picked)
    included = {*(runtime.key for runtime in universal_runtimes(scope)), *chosen}
    return tuple(runtime.key for runtime in runtimes_in(scope) if runtime.key in included)


def runtime_choices(
    scope: Scope, detected: frozenset[str]
) -> list[questionary.Separator | questionary.Choice]:
    """The scoped table (ADR 0009), the universal group locked on top of it (ADR 0011).

    `runtimes_in(scope)` is the one implementation the screen and the flag
    validator both consume, so global scope never offers the two runtimes with
    no destination there. `universal_runtimes(scope)` is the same arrangement
    one level in: the group is shown as an **informative section** — *always
    included*, not selectable — and its membership is read off the place of
    **that** scope, which is 19 rows in project and 6 in global.

    The heading carries the place, the lock and the count, because that is the
    whole of what the section buys: a pre-ticked line and a locked line differ
    by one tap of the space bar, and what the second one buys is the reader
    understanding, without counting boxes, that one path equips twenty runtimes
    at once.

    Neither section is ever empty — the table has 55 distinct project paths, and
    the group has 19 and 6 members — so neither is guarded. The group being
    non-empty is what makes an empty runtime selection unreachable from the
    wizard, which is ADR 0011's own consequence.
    """
    locked = universal_runtimes(scope)
    included = {runtime.key for runtime in locked}
    additional = [runtime for runtime in runtimes_in(scope) if runtime.key not in included]
    return [
        questionary.Separator(
            f"-- Universal ({universal_place(scope)})  {ALWAYS_INCLUDED}  {len(locked)} runtimes --"
        ),
        *(_locked(runtime) for runtime in locked),
        questionary.Separator("-- Additional agents --"),
        *(_choice(runtime, detected) for runtime in additional),
    ]


def _locked(runtime: Runtime) -> questionary.Choice:
    """One member of the group: shown, and not offered.

    `disabled` carries the reason and never `True`, and the difference is
    visible: measured in `questionary` 2.1.1, a boolean renders `- Amp` while a
    string renders `- Amp (always included)`. The heading says it once for the
    section and the row says it again, because there are two ways to be looking
    at these rows without their heading: 19 members plus a heading is more than
    a terminal shows at 80x24, and a search filters the heading away along with
    whatever missed. Either way the alternative is a line with no checkbox and
    no reason.
    """
    return questionary.Choice(runtime.display_name, value=runtime.key, disabled=ALWAYS_INCLUDED)


def _choice(runtime: Runtime, detected: frozenset[str]) -> questionary.Choice:
    """One runtime that is a real choice, pre-checked by detection."""
    return questionary.Choice(
        runtime.display_name, value=runtime.key, checked=runtime.key in detected
    )
