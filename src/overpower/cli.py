"""The command line: parsing, the `isatty()` gate, the exit codes, the top handler.

This is the frame every later ticket hangs off, and it replaces the probe of the
`0.0.x` series whole — that one printed four facts and exited 0 with no parsing
at all, which was the right shape for proving a publishing pipeline and the wrong
shape for a product.

**Every byte the product prints leaves through a `rich` console**, never through
`print`, and `T20` in `pyproject.toml` is what keeps that true. The reason is
testability before looks: the snapshot doctrine records a rendered screen, so an
output path that bypasses the console is an output path no snapshot can see.

**The top-level handler is mandatory.** An unhandled exception exits 1 dumping a
rich traceback into the terminal, and shipping that leaks library internals to
whoever typed the command. Exit 1 costs the conversion of an exception into an
error panel, and this module is where that conversion lives — which is also why
`pretty_exceptions_enable` is off: that feature is the defect, not the cure.

The code table is born whole even though v0.1.0 only exercises part of it, and
the axis between **2** and **3** is *whose defect it is*. The `except` order in
`main` is where that axis is decided, and it is the only place: a
`BadInvocationError` is caught before its base class and answers **2**.

`list` is where the selectors first appear — `--ai-framework` with no short flag
because `-f` belongs to `--force`, plus `--skill`/`-s`, `--bundle`/`-b` and
`--mcp`, which has none because it is already three letters. Here each takes
**one** name, because `list` answers about one item; the accumulating form that
`install` needs is a different question and arrives with it.
"""

from __future__ import annotations

from dataclasses import replace
from enum import IntEnum
from importlib import metadata
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import questionary
import typer
from rich.console import Console
from rich.text import Text
from typer.core import TyperGroup

from overpower.discovery import load_catalog
from overpower.errors import BadInvocationError, OverpowerError, RefusedError
from overpower.inspection import Terminal, diagnose
from overpower.packaged import catalog_file, content_root
from overpower.planning import (
    DestinationExistsError,
    Request,
    existing_destinations,
    pending_activation,
    plan_for,
    refuse_broken_documents,
    unset_slots,
)
from overpower.remote import catalog_from
from overpower.rendering import targets_of
from overpower.runtimes import Environment, Scope
from overpower.scope import git_root
from overpower.screens import (
    ACTIVE_MARK,
    AI_FRAMEWORK_FLAG,
    BUNDLE_FLAG,
    MCP_FLAG,
    PROGRAM,
    SKILL_FLAG,
    THEME,
    artifact_screen,
    banner,
    bundle_screen,
    catalog_screen,
    closed,
    doctor_screen,
    error_panel,
    framework_screen,
    installed_screen,
    mcp_screen,
    opened,
    plan_screen,
    railed,
    shortened,
    summary_screen,
)
from overpower.wizard import QUESTIONARY_STYLE, run_wizard
from overpower.writing import execute

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rich.console import RenderableType

    # typer 0.27 **vendors** click under `typer._click`, and the signature of its
    # own `TyperGroup.format_help` is written in those types. Annotating the
    # override with `click.Context` is rejected — correctly, they are different
    # classes — so the annotation follows the base class rather than the package
    # on PyPI. Type-only: nothing at runtime knows where typer keeps its copy,
    # and the day it stops vendoring one this fails in `pyright` at the gate
    # instead of in someone's terminal.
    from typer._click.core import Context as ClickContext
    from typer._click.formatting import HelpFormatter as ClickHelpFormatter

    from overpower.discovery import Catalog
    from overpower.planning import Plan

ABORTED = 130
"""What Ctrl-C costs before it reaches here — the shell's `128 + SIGINT`.

Read in `typer/core.py` of typer 0.27.1 and measured: typer's own `main`
overrides click's and turns `KeyboardInterrupt` into `Exit(130)`, where click
alone would have raised `Abort` and exited **1**. The model of the map puts
Ctrl-C under **1**, *could not run*, so the number is translated once, here,
rather than leaking a fifth code into a table that declares four. No command of
ours exits 130 for any other reason, so the translation cannot swallow a real
answer.
"""

_out = Console(theme=THEME, highlight=False)
_err = Console(theme=THEME, highlight=False, stderr=True)


class ExitCode(IntEnum):
    """What the shell reads back, and what each number promises.

    | code | meaning |
    | --- | --- |
    | 0 | did what was asked |
    | 1 | could not run |
    | 2 | you invoked me wrong |
    | 3 | ran, and the answer is no |

    `3` is the only one that costs code, and it is what makes `--dry-run` and
    `doctor` usable as a CI gate: *"could not compute the plan"* and *"computed
    it, and the answer is no"* have to be distinguishable, or a pipeline cannot
    tell whether to alert the team or try again.
    """

    OK = 0
    CANNOT_RUN = 1
    BAD_INVOCATION = 2
    REFUSED = 3


class TooManySelectorsError(BadInvocationError):
    """More than one selector on a `list` line, which has no single answer.

    `list` bare is the whole catalog and `list --<unit> <name>` is the content of
    **one** item; two selectors would be a question with two answers. Answering
    one of them silently is the class of defect this product exists not to commit
    — the screen says one thing and the result is another — so the command
    refuses and names every flag it was given.

    It lives here and not in the discovery because it is not about the catalog:
    the names may both be perfectly good, and it is the *line* that is wrong.
    """

    def __init__(self, flags: Sequence[str]) -> None:
        """Name every flag that was given, so the line can be cut in one edit."""
        self.flags = tuple(flags)
        given = " and ".join(self.flags)
        super().__init__(f"`list` shows one item at a time, and got {given}")


class UnsupportedRemoteUnitError(BadInvocationError):
    """`--from` on a line that also names an AI Framework, a bundle or an MCP server.

    `--from` is for `--skill` and nothing else yet, and the reason is the same
    one that separates the three copy units: a **skill is the only one that
    exists in the market**, while a bundle and an AI Framework only exist in a
    repository that already knows the overpower. The MCP server is the one that
    will join it — a federated recipe is precisely the channel a home-made MCP
    has none of today — and it joins in
    https://github.com/panlabs-tech/overpower/issues/83. Refusing by name is what
    keeps the flag from silently meaning less than it says.

    It lives here rather than in `overpower.remote` for the same reason
    `TooManySelectorsError` does: nothing about the URL or the names is wrong —
    it is the *line* that has no single answer, so no obtention is attempted.
    """

    def __init__(self, flags: Sequence[str]) -> None:
        """Name every unit flag that cannot travel with `--from`."""
        self.flags = tuple(flags)
        given = " and ".join(self.flags)
        super().__init__(f"`--from` installs skills only, and this line also has {given}")


class NothingToSearchForError(BadInvocationError):
    """`--from` with no `--skill`: a search root, and nothing to look for in it.

    `plan_for` already refuses an empty selection, and this exists because of
    *when* rather than *whether*: reaching that refusal would cost a whole
    repository download first, for a line that could never have installed
    anything. It is the same reasoning that puts `TooManySelectorsError` before
    the catalog is read.
    """

    def __init__(self) -> None:
        """Say which half of the line is missing."""
        super().__init__("`--from` names where to look, and no --skill names what to look for")


class OutsideRepositoryError(BadInvocationError):
    """The default scope needs a git repository, and there is none under `cwd`.

    Axiom 2 — *"the git is the manifest"* — only holds where there is git.
    Inside a repository a wrong scope costs a `git checkout` and `git status`
    says so; outside one, nothing on the machine audits what was written, which
    is the exact hole measured in `gh skill install`: it writes to
    `./.claude/skills/` outside any repository and exits 0, despite its own
    `--help` claiming *"inside the current git repository"*. `--global` names
    the machine on purpose; there is no default that guesses between the two.
    """

    def __init__(self) -> None:
        """Say what is missing and the one flag that supplies it."""
        super().__init__(
            "not inside a git repository: pass --global to write under the home directory"
        )


class _BannerGroup(TyperGroup):
    """The root group, which draws the banner over the help it is about to format.

    The banner lives here and nowhere else on this path, and that is what makes
    the **two gestures of discovery** — a bare `overpower` and `overpower --help`
    — the same screen (https://github.com/panlabs-tech/overpower/issues/8): click
    answers `--help` from an eager option, *before* the callback below ever runs,
    so a banner printed in the callback reaches the bare gesture and misses the
    typed one. Formatting is the one moment both gestures pass through — the bare
    branch reaches it through `ctx.get_help()` — so putting it here also means it
    is printed exactly once on each, with no flag threaded between them.

    Only the **root** group is reclassed, so `overpower list --help` and the other
    two subcommand helps are untouched: a banner over every help screen would be
    the product introducing itself to someone who is already inside it.
    """

    def format_help(self, ctx: ClickContext, formatter: ClickHelpFormatter) -> None:
        """The banner, then whatever click and typer were going to draw anyway."""
        _print_banner()
        super().format_help(ctx, formatter)


app = typer.Typer(
    cls=_BannerGroup,
    name=PROGRAM,
    add_completion=False,
    # A bare `overpower` is not a usage error: it opens the banner and the help
    # and exits 0, by deliberate override.
    invoke_without_command=True,
    no_args_is_help=False,
    # The rich traceback is exactly what the error model forbids.
    pretty_exceptions_enable=False,
    help="Installs curated AI Frameworks into a repository or onto a machine.",
)


@app.callback()
def root(
    ctx: typer.Context,
    *,
    version: Annotated[
        bool, typer.Option("--version", help="Print the version that arrived and exit.")
    ] = False,
) -> None:
    """Open the banner and the help, or answer `--version`."""
    if version:
        # Rule 5: the version of the overpower *is* the version of the catalog it
        # embeds, so this one line is what `uvx overpower@0.1.0` pins.
        _out.print(Text.assemble((PROGRAM, "op.brand"), " ", _version()))
        raise typer.Exit(ExitCode.OK)

    if ctx.invoked_subcommand is None:
        # No banner here: `get_help` reaches `_BannerGroup.format_help`, which draws
        # it — the same one `--help` gets, printed once, from one place.
        #
        # Typer's rich formatter prints the help to its own rich console and
        # returns nothing; the plain formatter returns the text instead. Both
        # paths are honoured, so the help does not depend on which is active.
        rendered = ctx.get_help()
        if rendered:
            _out.print(rendered)
        raise typer.Exit(ExitCode.OK)


@app.command("list")
def list_catalog(
    *,
    ai_framework: Annotated[
        str | None,
        typer.Option(
            AI_FRAMEWORK_FLAG,
            metavar="NAME",
            # No short flag, and the reason is `--force`: `-f` is spoken for by
            # the mode flag of `install`, and a selector that means `--force` on
            # one line and `--ai-framework` on another is worse than typing it.
            help="Show the artifacts inside one AI Framework.",
        ),
    ] = None,
    skill: Annotated[
        str | None,
        typer.Option(SKILL_FLAG, "-s", metavar="NAME", help="Show one pool skill, whole."),
    ] = None,
    bundle: Annotated[
        str | None,
        typer.Option(BUNDLE_FLAG, "-b", metavar="NAME", help="Show what one bundle names."),
    ] = None,
    mcp: Annotated[
        str | None,
        typer.Option(
            MCP_FLAG,
            # No short flag, the same call `install` makes: `--mcp` is already
            # three letters, and `-m` bought against a name that short is a
            # letter spent for nothing.
            metavar="NAME",
            help="Show one MCP server recipe, whole.",
        ),
    ] = None,
) -> None:
    """Show the catalog, or the content of one item of it."""
    given = (
        (AI_FRAMEWORK_FLAG, ai_framework),
        (SKILL_FLAG, skill),
        (BUNDLE_FLAG, bundle),
        (MCP_FLAG, mcp),
    )
    selected = [flag for flag, name in given if name is not None]
    if len(selected) > 1:
        # Before the catalog is read at all: the defect is in the *line*, so the
        # answer cannot depend on the tree being well formed. Reading first would
        # let a broken tree answer 1 — *could not run* — to a question whose real
        # answer is 2, and the two codes exist to be told apart.
        raise TooManySelectorsError(selected)

    catalog = load_catalog(content_root(), catalog_file())
    # Resolved before the banner: a name outside the catalog exits 2, and a
    # banner already on screen would be the product answering before it knew.
    screen = _listed(catalog, ai_framework=ai_framework, skill=skill, bundle=bundle, mcp=mcp)
    _print_banner()
    _out.print(screen)


def _listed(
    catalog: Catalog,
    *,
    ai_framework: str | None,
    skill: str | None,
    bundle: str | None,
    mcp: str | None,
) -> RenderableType:
    """The screen the flags asked for: the whole catalog, or one item of it."""
    if ai_framework is not None:
        return framework_screen(catalog.framework(ai_framework))
    if skill is not None:
        return artifact_screen(catalog.artifact(skill))
    if bundle is not None:
        return bundle_screen(catalog.bundle(bundle))
    if mcp is not None:
        # The one screen that is not read off the item alone: which targets a
        # recipe serves is derived from the table (rule 4), so it is computed
        # here — where the product's own table is — and handed to the screen.
        recipe = catalog.mcp(mcp)
        return mcp_screen(recipe, targets_of(recipe))
    return catalog_screen(catalog)


@app.command()
def install(  # noqa: PLR0913 — one keyword per CLI flag, and the three selectors plus five
    # mode flags land at eight; splitting the signature would not shrink the surface it names.
    *,
    ai_framework: Annotated[
        list[str] | None,
        typer.Option(
            AI_FRAMEWORK_FLAG,
            metavar="NAME",
            # No short flag, and the reason is `--force`: `-f` is spoken for by
            # the mode flag of this command, and a selector that means `--force`
            # on one line and `--ai-framework` on another is worse than typing
            # it. Same call as `list`'s.
            help="AI Frameworks to install, whole. Comma-separated, repeated, or both.",
        ),
    ] = None,
    bundle: Annotated[
        list[str] | None,
        typer.Option(
            BUNDLE_FLAG,
            "-b",
            metavar="NAME",
            help="Bundles to expand into the pool artifacts they name. "
            "Comma-separated, repeated, or both.",
        ),
    ] = None,
    skill: Annotated[
        list[str] | None,
        typer.Option(
            SKILL_FLAG,
            "-s",
            metavar="NAME",
            help="Pool skills to install. Comma-separated, repeated, or both.",
        ),
    ] = None,
    mcp: Annotated[
        list[str] | None,
        typer.Option(
            MCP_FLAG,
            # No short flag: `--mcp` is already three letters, and `-m` bought
            # against a name that short is a letter spent for nothing.
            metavar="NAME",
            help="MCP servers to write into the runtime's configuration. "
            "Comma-separated, repeated, or both.",
        ),
    ] = None,
    runtime: Annotated[
        list[str] | None,
        typer.Option(
            "--runtime",
            metavar="KEY",
            help="Runtimes to equip. Comma-separated, repeated, or both. No default.",
        ),
    ] = None,
    from_: Annotated[
        # No short flag, and no default: absent means the embedded catalog, which
        # is the only other thing it could mean.
        str | None,
        typer.Option(
            "--from",
            metavar="URL",
            help="Take --skill from any GitHub repository instead of the embedded catalog. "
            "The URL is a search root: the repository, a subfolder or the skill's own folder. "
            "`tree/<ref>/<path>` pins a branch, a tag or a SHA.",
        ),
    ] = None,
    global_: Annotated[
        bool,
        typer.Option(
            "--global",
            "-g",
            help="Write under the home directory instead of the repository.",
        ),
    ] = False,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Overwrite a global destination that already exists.",
        ),
    ] = False,
    yes: Annotated[
        bool, typer.Option("--yes", "-y", help="Skip the confirmation, and nothing else.")
    ] = False,
    dry_run: Annotated[
        # No short form, on purpose: an audit flag typed out in full is part of
        # the gesture. It resolves everything and leaves nothing in the target.
        bool,
        typer.Option("--dry-run", help="Print the plan and write nothing."),
    ] = False,
) -> None:
    """Install curated equipment into the current repository, or onto the machine."""
    frameworks = _accumulated(ai_framework)
    bundles = _accumulated(bundle)
    skills = _accumulated(skill)
    mcps = _accumulated(mcp)
    # Before the scope, before the catalog and before any obtention: a line that
    # `--from` cannot answer is a defect of the *line*, and answering it must not
    # depend on there being a git repository, a readable tree or a network.
    _refuse_a_line_from_cannot_answer(from_, frameworks, bundles, mcps, skills)

    environment = Environment.from_process()
    asked = Request(
        ai_frameworks=frameworks,
        bundles=bundles,
        skills=skills,
        mcps=mcps,
        runtimes=_accumulated(runtime),
        force=force,
        dry_run=dry_run,
        yes=yes,
    )
    selected = bool(frameworks or bundles or skills or mcps)
    # **The trigger is the gap, not the empty line**
    # (https://github.com/panlabs-tech/overpower/issues/57): there is a
    # terminal, and what was typed does not add up to a plan — no selection, or
    # no runtime. Without a terminal the flag path below reaches the same two
    # errors it always did, so a partial invocation off a pipe exits 2 without
    # ever touching `questionary`.
    wizarding = _out.is_terminal and not (selected and asked.runtimes)
    # The scope step exists to **scope the runtime step** — the set `--runtime`
    # accepts is a function of it (ADR 0009) — so a line that fixes the runtimes
    # fixes the scope question along with them, and `--global` fixes it outright.
    # The accepted consequence is that `--runtime` alone opens the artifacts step
    # and nothing else: the wizard is one gesture, not a question per absent flag.
    asking_scope = wizarding and not asked.runtimes and not global_

    already_read: Catalog | None = None
    if wizarding:
        # Resolved ahead of the banner and of every question: a line with
        # nowhere legal to write is refused with no screen at all, the same way
        # the flag path refuses from behind `plan_for`.
        scoped = None if asking_scope else _scope_and_root(global_=global_, environment=environment)
        # The banner next: a human about to answer questions reads it as
        # context, unlike the flag path below, where a screen ahead of a
        # refusal would be the product answering before it knew.
        _print_banner()
        _open_session()
        # The artifacts step is the only one that consults a catalog, and a line
        # that already names something never opens it. That is what lets a
        # `--from` line reach the wizard without the embedded catalog ever being
        # read — *"only the remote is consulted"* speaks about that one step,
        # and `--from` requires `--skill`, hence a selection, hence no step.
        if not selected:
            already_read = load_catalog(content_root(), catalog_file())
        outcome = run_wizard(asked, already_read, environment, Path.cwd(), scoped, console=_out)
        if outcome is None:
            _stopped("nothing was written")
            raise typer.Exit(ExitCode.CANNOT_RUN)
        request, root = outcome
    else:
        scope, root = _scope_and_root(global_=global_, environment=environment)
        request = replace(asked, scope=scope)

    if from_ is None:
        # Read here only when the wizard did not already need it: the tree is
        # walked and every `SKILL.md` is read, so twice on one invocation is a
        # real cost and not a tidiness point.
        if already_read is None:
            already_read = load_catalog(content_root(), catalog_file())
        _perform(request, already_read, root, environment, banner=not wizarding)
        return
    # The scratch lives exactly as long as the block, which has to cover the
    # write as well as the plan: the sources of a remote install are inside it.
    with catalog_from(from_, request.skills) as catalog:
        _perform(request, catalog, root, environment, banner=not wizarding)


def _refuse_a_line_from_cannot_answer(
    from_: str | None,
    frameworks: Sequence[str],
    bundles: Sequence[str],
    mcps: Sequence[str],
    skills: Sequence[str],
) -> None:
    """The two ways a `--from` line has no answer, refused before anything is fetched.

    The four sequences are `Request`'s four sibling selectors and would rather
    travel as one, which is what they do everywhere else in this module. They
    cannot here, and the reason is the *order*: this refusal has to land before
    `_scope_and_root` — a line `--from` cannot answer must not need a git
    repository to be told so — and a `Request` built before the scope is resolved
    would carry a scope that is not the one it will run under. Four parameters
    is the smaller lie.
    """
    if from_ is None:
        return
    given = [
        flag
        for flag, names in (
            (AI_FRAMEWORK_FLAG, frameworks),
            (BUNDLE_FLAG, bundles),
            (MCP_FLAG, mcps),
        )
        if names
    ]
    if given:
        raise UnsupportedRemoteUnitError(given)
    if not skills:
        raise NothingToSearchForError


def _perform(
    request: Request,
    catalog: Catalog,
    root: Path,
    environment: Environment,
    *,
    banner: bool = True,
) -> None:
    """Plan against `catalog`, show the plan, and — unless asked not to — write it.

    One body for all three sources, and that is the whole shape of `--from`: it
    decides **where the catalog comes from** and changes nothing about what
    happens to one. A dry run therefore resolves the remote exactly as the real
    run does, which is what keeps it a report about *this* installation.

    `banner` is off for the wizard alone, and the asymmetry is the reason the
    flag exists: the wizard has already drawn it as context for the questions it
    asked, while on a flag line the banner has to wait until behind `plan_for`,
    where a refusal costs no screen at all.
    """
    # Planned before anything is drawn, so a refusal costs no screen: a bad
    # runtime, or a global destination that already exists with no terminal to
    # ask about it, is exit 2 or exit 3 with nothing written and nothing
    # announced. `--dry-run` is a report, never a session, so it never asks
    # either — https://github.com/panlabs-tech/overpower/issues/69.
    plan = plan_for(request, catalog, root, environment)
    # Read before anything is drawn and before the first byte, and on **both**
    # paths: a `--dry-run` that answered 0 to a line the real run refuses with 3
    # would be a report about a different installation
    # (https://github.com/panlabs-tech/overpower/issues/76).
    refuse_broken_documents(plan)
    conflicts = existing_destinations(plan, request)
    if conflicts and (request.dry_run or not _asking(request)):
        raise DestinationExistsError(conflicts)

    if request.dry_run:
        # A report and not a session: `--dry-run` is read, piped and diffed, so
        # it keeps the detailed plan and takes no frame. There is no gate here
        # to fit on a screen, which is the whole reason the gate got shorter.
        if banner:
            _print_banner()
        _out.print(plan_screen(plan))
        # Before the closing line and not after it: `--dry-run` resolves
        # everything, so what it knows about the environment it knows *now*, and
        # a report ends with what it did rather than with an aside.
        _warn_about_unset_slots(plan, environment)
        _out.print(Text.assemble(("dry run", "op.warn"), " ", ("nothing was written", "op.dim")))
        return

    if banner:
        _print_banner()
        _open_session()
    _print_railed()
    # **Short only where it has to fit.** In a terminal this is the gate, and
    # measured at 80x24 the detailed plan loses its first 11 lines — including
    # the head line naming what is being accepted — before `Write these paths?`
    # appears. Under a pipe there is no gate and no 24 rows: the output is a
    # record someone greps or files, so it keeps the artifact list, exactly as
    # `--dry-run` does and exactly as it did before #65. `summary_screen` and
    # `plan_screen` are the same function one flag apart, so whichever is drawn
    # they cannot disagree about a path or a truncation.
    _out.print(summary_screen(plan) if _out.is_terminal else plan_screen(plan))

    if _asking(request):
        _print_railed()
        confirmed = _confirmed_overwrite(conflicts) if conflicts else _confirmed()
        if not confirmed:
            _stopped("nothing was written")
            raise typer.Exit(ExitCode.CANNOT_RUN)

    report = execute(plan)
    if not _out.is_terminal:
        _out.print(
            Text.assemble(
                ("installed", "op.ok"),
                " ",
                (f"{report.writes} writes · {report.files} files", "op.dim"),
            )
        )
    else:
        _print_railed()
        _out.print(installed_screen(plan, report.writes, report.files))
    if report.degraded:
        listed = ", ".join(str(path) for path in report.degraded)
        _out.print(Text.assemble(("degraded to copy", "op.warn"), " ", (listed, "op.dim")))
    _warn_about_unset_slots(plan, environment)
    _warn_about_activation(plan, request.scope, root)
    _finished()


def _warn_about_unset_slots(plan: Plan, environment: Environment) -> None:
    """Name the slot variables this environment does not have, at exit 0.

    A slot is the one thing the overpower **refuses to write**, so the value has
    to come from the environment the *runtime* starts in — which may not be this
    shell, and is not this moment. That is why an absent variable is neither a
    refusal nor a reason to write anything else: the file is correct, and the
    remaining act is the user's.

    Said out loud all the same, because the failure it prevents is silent:
    measured, Claude Code sends an unexpanded `${VAR}` **raw** on the request, so
    what the person sees is a 401 from a server, days later, with nothing
    pointing at the file.
    """
    missing = unset_slots(plan, environment.variables)
    if not missing:
        return
    one = len(missing) == 1
    _warn(
        "not set here",
        f"{', '.join(missing)} — the server reads {'it' if one else 'them'} when the runtime "
        f"starts, so {'this variable is' if one else 'these variables are'} yours to export "
        "before you use the server",
    )


def _warn_about_activation(plan: Plan, scope: Scope, root: Path) -> None:
    """Say that what was just written is not on yet, wherever that is true.

    ADR 0014: the overpower writes the server and does **not** activate it —
    approving it is the user's act, and there is no version of that decision in
    which we could do it for all three targets. So the warning is a
    **requirement**: without it the product ships the exact failure the research
    named — file written, exit 0, server inert, no sign anywhere.

    It comes out at **exit 0**, because the write happened and was correct; what
    is missing is not ours to do. And it comes out only where it is true, which
    is what keeps it read at all.
    """
    pending = pending_activation(plan, scope)
    if not pending:
        return
    listed = ", ".join(shortened(path, root) for path in pending)
    _warn(
        "pending approval",
        f"{listed} is written, and the server does not connect until you approve it — "
        "Claude Code asks the next time it starts in this repository",
    )


def _warn(label: str, prose: str) -> None:
    """One line of *"it worked, and here is what is still yours to do"*.

    Both warnings of the graft have the same shape because they are the same
    kind of statement — exit 0, the write was correct, and the remaining act is
    the user's — so they are drawn once. A second spelling of a warning would be
    a second thing to keep looking like the product.
    """
    _out.print(Text.assemble((label, "op.warn"), " ", (prose, "op.dim")))


@app.command()
def doctor() -> None:
    """Report the terminal, and the integrity of what is installed."""
    environment = Environment.from_process()
    # Both scopes, in one output, and therefore no `--global` here: the command
    # answers *"how is what was installed"*, and equipment lives in the
    # repository and on the machine at the same time. A flag that switched
    # between the two halves would make it two outputs.
    #
    # No git is not a refusal, unlike `install`: `git_root` answering `None`
    # takes the project half off the screen and leaves the machine on it.
    diagnosis = diagnose(_terminal(environment), git_root(Path.cwd()), environment)

    _print_banner()
    _out.print(doctor_screen(diagnosis))

    if not diagnosis.healthy:
        # 3 and never 1: the command ran, computed the answer, and the answer is
        # no. That distinction is the whole reason `doctor` works as a CI gate.
        raise typer.Exit(ExitCode.REFUSED)


def _terminal(environment: Environment) -> Terminal:
    """The console as facts, read here because this module is the one that owns it.

    `NO_COLOR` comes through `Environment` and not `os.environ`: `from_process`
    is the single place in the package that touches the process environment, and
    reading it twice would be two answers to one question.

    `color_system` and `NO_COLOR` are both reported because they are not the same
    fact — rich still names the palette it detected while refusing to use it —
    and *"my screen came out strange"* is answered by seeing both.
    """
    return Terminal(
        tty=_out.is_terminal,
        colour=_out.color_system or "none",
        width=_out.width,
        no_color=environment.variables.get("NO_COLOR"),
    )


def _scope_and_root(*, global_: bool, environment: Environment) -> tuple[Scope, Path]:
    """The scope this invocation writes in, and what its destinations hang off.

    `--global` names the machine and needs no git at all. Otherwise the default
    is project scope, and it needs one: axiom 2 — *"the git is the manifest"* —
    only holds inside a repository, so outside one the scope has to be explicit
    rather than guessed.
    """
    if global_:
        return Scope.GLOBAL, environment.home
    if git_root(Path.cwd()) is None:
        raise OutsideRepositoryError
    return Scope.PROJECT, Path.cwd()


def main(argv: Sequence[str] | None = None) -> int:
    """The console script, and the only place an exception stops being one.

    `argv` exists for the tests: the entry point calls it with nothing and click
    reads `sys.argv`.
    """
    try:
        app(args=None if argv is None else list(argv), prog_name=PROGRAM)
    except SystemExit as stopped:
        # The framework's own exits: `--help` and `--version` at 0, a usage error
        # at 2, and Ctrl-C at 130, which `_code` translates. The number is read
        # off the exception and never re-derived here.
        return _code(stopped.code)
    except BadInvocationError as wrong:
        # Before the base class on purpose: this `except` order *is* the axis
        # between 1 and 2, and it is the only place the two are told apart.
        return _failed(str(wrong), ExitCode.BAD_INVOCATION)
    except RefusedError as refused:
        # Same reasoning, one rung down: before `OverpowerError` so 3 is told
        # apart from 1 the same way 2 already is.
        return _failed(str(refused), ExitCode.REFUSED)
    except OverpowerError as failure:
        return _failed(str(failure))
    except Exception as bug:  # noqa: BLE001 — the top handler catches everything by design
        return _failed(f"{type(bug).__name__}: {bug}", unexpected=True)
    return ExitCode.OK


DONE = "Done!  Review what landed before use; it runs with full agent permission."
"""The sign-off, and the one thing on it that is not a pleasantry.

`npx skills` closes on *"Review skills before use; they run with full agent
permissions"*, and the warning is inherited for the same reason the screen was:
what lands here is instructions a coding agent will execute, from a curation
this program vendors rather than authors.
"""


def _print_banner() -> None:
    """The banner is a terminal courtesy, so it is gated on being in one.

    Under a pipe there is no banner and no ANSI: the output has to stay readable
    on the other end, which is where `grep` and a file are.
    """
    if not _out.is_terminal:
        return
    _out.print(banner(_version(), _out.width))


def _open_session() -> None:
    """`┌   overpower install` — the frame the steps hang off.

    Gated on being in a terminal for the reason the banner is: a rail is a
    device for reading a sequence of questions, and under a pipe there are no
    questions and the output goes to `grep`. That gate is what keeps the piped
    contract of this command byte-identical to what it was before #65.
    """
    if not _out.is_terminal:
        return
    _out.print(opened(f"{PROGRAM} install"))


def _print_railed() -> None:
    """One rail, between a frame and whatever the session prints next."""
    if not _out.is_terminal:
        return
    _out.print(railed())


def _stopped(message: str) -> None:
    """A run that ends having written nothing, closed rather than merely reported."""
    if _out.is_terminal:
        _out.print(closed(message))
        return
    _out.print(Text(message, style="op.dim"))


def _finished() -> None:
    """`└  Done!  …` — the session ends, and only in a terminal does it have one."""
    if not _out.is_terminal:
        return
    _out.print(closed(DONE))


def _accumulated(values: Sequence[str] | None) -> tuple[str, ...]:
    """Comma and repeated flag, both accepted, both accumulating.

    It is what `ruff --select E,F,W` and `gh pr create --reviewer a,b --reviewer c`
    taught people to type, so both spellings arrive at the same tuple and the
    rest of the program never learns which was used.
    """
    if not values:
        return ()
    return tuple(part.strip() for value in values for part in value.split(",") if part.strip())


def _asking(request: Request) -> bool:
    """Whether this run stops to confirm before the first byte.

    Two ways out, and they are not the same one. `--yes` skips the confirmation
    and nothing else — choosing between writing in the repository and writing in
    `~/` is not a yes-or-no question. And **without a terminal the command runs
    without needing `--yes` at all**: v0.1.0 removes nothing, so it stands next
    to `pip` and not next to `apt-get`. `--yes` stays *accepted* there as a
    no-op, so the same line runs identically in a terminal and in CI.
    """
    return _out.is_terminal and not request.yes


def _confirmed() -> bool:
    """Ask, and read the answer as a yes or anything else.

    The copy is English for a mechanical reason before an aesthetic one: read in
    the source of `questionary`, the echo of `confirm` comes from a module
    constant and the keys are fixed at `y`/`n`, with no binding for `s` — in
    pt-BR the user would press `s` for *"sim"*, nothing would happen, and the
    answer would echo `Yes`.

    `ask()` answers `None` when the prompt is interrupted, which is the same
    gesture as declining and is treated as one.
    """
    return bool(
        questionary.confirm(
            "Write these paths?", default=True, qmark=f"{ACTIVE_MARK} ", style=QUESTIONARY_STYLE
        ).ask()
    )


def _confirmed_overwrite(conflicts: Sequence[Path]) -> bool:
    """The same gate as `_confirmed`, naming what saying yes would clobber.

    One prompt, not two (https://github.com/panlabs-tech/overpower/issues/69):
    a caller that already knows some destinations exist folds that fact into
    the single yes-or-no gate instead of stacking a second one in front of it —
    so this is what `_perform` calls *instead of* `_confirmed`, never in
    addition to it. `default=False`, unlike `_confirmed`'s `True`: the plain
    gate defaults to *go* because nothing is at stake yet, and this one
    defaults to *stop* because *yes* overwrites files that were already there.
    """
    listed = ", ".join(str(path) for path in conflicts)
    message = (
        f"{len(conflicts)} of these paths already exist and will be overwritten: "
        f"{listed}. Write these paths?"
    )
    return bool(
        questionary.confirm(
            message, default=False, qmark=f"{ACTIVE_MARK} ", style=QUESTIONARY_STYLE
        ).ask()
    )


def _failed(message: str, code: ExitCode = ExitCode.CANNOT_RUN, *, unexpected: bool = False) -> int:
    """The panel, and the last place a message is still a message.

    `Text`, never markup: the message carries paths and exception text, and both
    routinely contain `[`. Measured, as markup a path of `/tmp/[wip]/pool/sklls`
    renders `/tmp//pool/sklls` — the *wrong path*, which is the one thing the
    message exists to name — and `/tmp/[/2024]/SKILL.md` raises `MarkupError`
    from inside the handler, which is how a traceback escapes the one function
    written to stop it.
    """
    body = Text(message)
    if unexpected:
        body = Text.assemble(
            body,
            "\n\n",
            ("This is a bug in the overpower, not in what you typed.", "op.dim"),
        )
    _err.print(error_panel(body))
    return code


def _code(code: int | str | None) -> int:
    """Whatever `SystemExit` carried, as a number the shell can read."""
    if code is None:
        return ExitCode.OK
    if code == ABORTED:
        return ExitCode.CANNOT_RUN
    if isinstance(code, int):
        return code
    return _failed(code)


def _version() -> str:
    """The version that arrived, read from installed metadata and not a constant.

    Reading the metadata is what proves the `dist-info` travelled intact; a
    literal here would answer even when nothing was installed.
    """
    try:
        return metadata.version("overpower")
    except metadata.PackageNotFoundError:  # pragma: no cover — installed in every cell
        return "uninstalled (running from source)"
