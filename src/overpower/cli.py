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

from contextlib import ExitStack
from dataclasses import replace
from enum import IntEnum
from importlib import metadata
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Annotated

import questionary
import typer
from rich.console import Console
from rich.text import Text
from typer.core import TyperGroup

from overpower.discovery import UnknownNameError, load_catalog
from overpower.errors import BadInvocationError, OverpowerError, RefusedError
from overpower.inspection import Terminal, diagnose
from overpower.packaged import catalog_file, content_root
from overpower.planning import (
    DestinationExistsError,
    MissingClass,
    Request,
    existing_destinations,
    pending_activation,
    plan_for,
    refuse_broken_documents,
    refuse_unmet_preconditions,
    unset_slots,
)
from overpower.recipes import Recipe
from overpower.remote import catalog_from, sources_for
from overpower.rendering import targets_of
from overpower.runtimes import Environment, Scope
from overpower.scope import git_root
from overpower.screens import (
    ACTIVE_MARK,
    AI_FRAMEWORK_FLAG,
    BUNDLE_FLAG,
    FROM_FLAG,
    MCP_FLAG,
    PROGRAM,
    SKILL_FLAG,
    THEME,
    artifact_screen,
    banner,
    bundle_screen,
    catalog_screen,
    closed,
    counted,
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
    from collections.abc import Mapping, Sequence

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


REMOTELY_ABSENT = (
    f"an AI Framework does not exist remotely: it is a folder of the overpower's own "
    f"wheel, and {AI_FRAMEWORK_FLAG} names one of those"
)
"""Why the last unit off `--from` is a decision and not a queue position.

Spelled once and said by both refusals below, because the two differ only in
their verb and a reason that drifted between them would be two answers to one
question. **The wording is the decision** (#137): a skill, an MCP recipe and now
a bundle all cross, so what is left is not *"not yet"* — it is a unit whose
whole definition is *the equipment this wheel ships*, which nothing in a
third-party repository can hold. A reader who took this for an adjournment
would go looking for the ticket that lifts it, and there is none.
"""


class UnsupportedRemoteUnitError(BadInvocationError):
    """`--from` on an `install` line that also names an AI Framework.

    The list this refuses used to hold two units and now holds one. A federated
    recipe was the channel a home-made MCP had none of
    (https://github.com/panlabs-tech/overpower/issues/83), and the federated
    manifest is the one a home-made **bundle** had none of
    (https://github.com/panlabs-tech/overpower/issues/137); both crossed. The
    AI Framework does not follow, and `REMOTELY_ABSENT` is why.

    It lives here rather than in `overpower.remote` for the same reason
    `TooManySelectorsError` does: nothing about the URL or the names is wrong —
    it is the *line* that has no single answer, so no obtention is attempted.
    """

    def __init__(self) -> None:
        """Name what `--from` installs, and why the one flag left out is left out."""
        super().__init__(f"`--from` installs skills, MCP servers and bundles — {REMOTELY_ABSENT}")


class NothingToSearchForError(BadInvocationError):
    """`--from` with no unit, **off a pipe**: a search root, and nothing to look for in it.

    `plan_for` already refuses an empty selection, and this exists because of
    *when* rather than *whether*: reaching that refusal would cost a whole
    repository download first, for a line that could never have installed
    anything. It is the same reasoning that puts `TooManySelectorsError` before
    the catalog is read.

    Since #135 it is **conditional on there being no terminal**, and that is not
    a weakening of the rule but the same rule under a new fact: a bare `--from`
    line now *means* the showcase, and the showcase is a step of the wizard. Where
    a wizard can open, the line has something to look for after all; where one
    cannot, the line has the shape it always had and earns the refusal it always
    did — still before any obtention, since the terminal is known long before one.
    """

    def __init__(self) -> None:
        """Say which halves of the line are missing."""
        super().__init__(
            "`--from` names where to look, and no --skill and no --mcp name what to look for"
        )


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


class MixedClassesWithoutRuntimeError(BadInvocationError):
    """A skill and an MCP server on one line, with no `--runtime` to split them.

    Since ADR 0018 the runtime step has two distinct shapes, one per class —
    the skills step locks the universal group, the graft step has none — and a
    line naming both has no single shape for the wizard to open. `--runtime`
    named explicitly settles which runtimes each class reaches without asking
    the step to be two things at once; the other way out is two commands, one
    per class (https://github.com/panlabs-tech/overpower/issues/97).
    """

    def __init__(self) -> None:
        """Name both ways out: naming the runtimes, or splitting the line."""
        super().__init__(
            "a skill and an MCP server on one line need --runtime named explicitly, "
            "or two separate commands — one per class"
        )


class UnsupportedRemoteListUnitError(BadInvocationError):
    """`--from` on a `list` line that also names an AI Framework.

    The same unit `UnsupportedRemoteUnitError` refuses on `install`, and for the
    same reason. Without this guard, `list --ai-framework x --from <url>` would
    print the *embedded* framework named `x` while the line claims to have
    consulted the URL — a silent narrowing, which is the defect both classes
    exist to refuse.

    Two classes and not one, because the verb differs: this one says *shows*
    where `install`'s says *installs*, and a message that names the wrong verb
    is a message the reader has to translate.
    """

    def __init__(self) -> None:
        """Name what `--from` shows, and why the one flag left out is left out."""
        super().__init__(
            f"`--from` on `list` shows skills, MCP servers and bundles — {REMOTELY_ABSENT}"
        )


class McpNameBelongsToAnotherFlagError(BadInvocationError):
    """A `--mcp` name the catalog has, filed under a different unit entirely.

    The closed-list miss `UnknownNameError` already answers is *"nothing has
    this name"*; this is a narrower, more useful miss — *something* has it, on
    a flag that was not typed. Naming the right one is a smaller correction than
    the closed list `UnknownNameError` would have printed instead.
    """

    def __init__(self, name: str, flag: str) -> None:
        """Name the value, and the flag its catalog entry actually answers to."""
        self.name = name
        self.flag = flag
        super().__init__(f"`{name}` is not an MCP server in this catalog; it is named under {flag}")


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
    from_: Annotated[
        str | None,
        typer.Option(
            FROM_FLAG,
            metavar="URL",
            help="Show what any GitHub repository offers, instead of the embedded catalog. "
            "Bare, it lists that repository's `skills/`, `.overpower/mcp/` and the bundles "
            "of `.overpower/catalog.yaml`; with --skill or --mcp, the URL is a search root. "
            "`tree/<ref>/<path>` pins a branch, a tag or a SHA.",
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
    _refuse_a_list_line_from_cannot_answer(from_, ai_framework)

    if from_ is None:
        catalog = load_catalog(content_root(), catalog_file())
        # Resolved before the banner: a name outside the catalog exits 2, and a
        # banner already on screen would be the product answering before it knew.
        screen = _listed(catalog, ai_framework=ai_framework, skill=skill, bundle=bundle, mcp=mcp)
        _print_banner()
        _out.print(screen)
        return
    # None of the three is an AI Framework here: the guard above already refused
    # that one. All three being `None` is not an empty line but a question —
    # *what does this repository offer?* — which `catalog_from` answers with the
    # showcase (#135).
    with catalog_from(
        from_,
        skills=(skill,) if skill else (),
        mcps=(mcp,) if mcp else (),
        bundles=(bundle,) if bundle else (),
    ) as catalog:
        screen = _listed(
            catalog, ai_framework=None, skill=skill, bundle=bundle, mcp=mcp, origin=from_
        )
        _print_banner()
        _out.print(screen)


def _refuse_a_list_line_from_cannot_answer(from_: str | None, ai_framework: str | None) -> None:
    """The way a `--from` line on `list` has no answer, refused before anything is fetched.

    Mirrors `_refuse_a_line_from_cannot_answer` on `install`, and the two refuse
    the *same* set — one unit since #137, which is what took `--bundle` out of
    the signature rather than out of the body.

    There is no second half here the way there is on `install`. A `list --from`
    line with no selector had nothing to look for and now has the showcase to
    print, so the refusal it used to earn — `NothingToListForError` — is gone
    rather than moved: `list` opens no wizard, so there is no terminal-shaped
    condition left for it to hold under.
    """
    if from_ is not None and ai_framework is not None:
        raise UnsupportedRemoteListUnitError


def _listed(  # noqa: PLR0913 — one keyword per selector, plus the catalog and where it came from
    catalog: Catalog,
    *,
    ai_framework: str | None,
    skill: str | None,
    bundle: str | None,
    mcp: str | None,
    origin: str | None = None,
) -> RenderableType:
    """The screen the flags asked for: the whole catalog, or one item of it.

    `origin` is the `--from` search root the catalog was obtained from, and the
    three screens `--from` can reach take it: the showcase, one skill and one
    recipe. Those are exactly the items that can be read from outside the
    catalog, so they are the lines whose printed command needs to say where it
    came from to work pasted back. A framework and a bundle screen never see one
    because `--from` never reaches them.
    """
    if ai_framework is not None:
        return framework_screen(catalog.framework(ai_framework))
    if skill is not None:
        return artifact_screen(catalog.artifact(skill), origin)
    if bundle is not None:
        return bundle_screen(catalog.bundle(bundle), origin)
    if mcp is not None:
        # The one screen that is not read off the item alone: which targets a
        # recipe serves is derived from the table (rule 4), so it is computed
        # here — where the product's own table is — and handed to the screen.
        recipe = catalog.mcp(mcp)
        return mcp_screen(recipe, targets_of(recipe), origin)
    return catalog_screen(catalog, origin)


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
            help="Runtimes to equip. Comma-separated, repeated, or both. No default. "
            "Skill and MCP support are separate tables, and not every runtime is in both.",
        ),
    ] = None,
    from_: Annotated[
        # No short flag, and no default: absent means the embedded catalog, which
        # is the only other thing it could mean.
        str | None,
        typer.Option(
            FROM_FLAG,
            metavar="URL",
            # ASCII only, and not a style point: this text is read back through a
            # subprocess whose stdout the Windows console encodes in cp1252, so a
            # single em dash here fails `test_the_install_help_still_fits_eighty_columns`
            # on three of the nine cells with a `UnicodeDecodeError` — the three
            # Windows ones of the 3 OS x 3 Python matrix in `.github/workflows/ci.yml`.
            help="Install from any GitHub repository instead of the embedded catalog. "
            "Bare, it opens the wizard on what that repository offers; with --skill or "
            "--mcp, the URL is a search root: the repository, a subfolder or the "
            "artifact's own folder. --bundle reads `.overpower/catalog.yaml` at the "
            "repository root. `tree/<ref>/<path>` pins a branch, a tag or a SHA.",
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
        bool,
        typer.Option(
            "--yes",
            "-y",
            # It skips the confirmation and nothing else, and that "nothing else"
            # is load-bearing: `_asking` is also the predicate that decides whether
            # an occupied destination is a question or a refusal, so `--yes` turns
            # a prompt that could have written into exit 3. The flag that lifts the
            # refusal is `--force`, and the help has to say which is which.
            help="Skip the confirmation. It does not accept an overwrite: an occupied "
            "global destination is refused instead of asked, and --force is what "
            "lifts that.",
        ),
    ] = False,
    dry_run: Annotated[
        # No short form, on purpose: an audit flag typed out in full is part of
        # the gesture. It resolves everything and leaves nothing in the target.
        bool,
        typer.Option("--dry-run", help="Print the plan and write nothing."),
    ] = False,
) -> None:
    """Install curated equipment into the current repository, or onto the machine.

    In a terminal, what the line leaves open (no selection, no runtime, or both)
    opens a wizard on exactly those steps; off a terminal it is refused instead.
    """
    frameworks = _accumulated(ai_framework)
    bundles = _accumulated(bundle)
    skills = _accumulated(skill)
    mcps = _accumulated(mcp)
    # Before the scope, before the catalog and before any obtention: a line that
    # `--from` cannot answer is a defect of the *line*, and answering it must not
    # depend on there being a git repository, a readable tree or a network.
    _refuse_a_line_from_cannot_answer(from_, frameworks)

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
    # The line decides this on its own — no catalog, no scope, no terminal — so
    # it is refused before any of the three, on the wizard path and the flag
    # path alike: since ADR 0018 the runtime step has two distinct shapes, one
    # per class, and a line naming both has no single shape to open. Naming
    # `--runtime` explicitly settles which runtimes each class reaches;
    # splitting into two commands is the other way out
    # (https://github.com/panlabs-tech/overpower/issues/97).
    if mcps and (frameworks or bundles or skills) and not asked.runtimes:
        raise MixedClassesWithoutRuntimeError

    already_read: Catalog | None = None
    if mcps and from_ is None:
        # Guarded by `from_ is None` for the same reason the artifacts step
        # below is: with `--from`, only the remote is consulted, and a slug
        # that only exists in the pointed repository must not be checked
        # against the embedded catalog first. The remote's own search —
        # `_mcp_called` — is what answers "not found" for that line, at
        # exit 3, once the block below obtains the repository.
        #
        # Loaded here and reused below rather than deferred to `_perform`: on a
        # terminal line missing --runtime that call happens only after the
        # whole wizard has already asked its questions, and a slug the catalog
        # does not have should cost none of them.
        already_read = load_catalog(content_root(), catalog_file())
        _refuse_an_mcp_name_from_the_wrong_class(already_read, mcps)

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
    # A search root and nothing to look for, on a line that cannot open a
    # wizard. Before #135 that was every such line; now the showcase is what a
    # bare `--from` means, and the showcase is a *step* — so off a pipe the old
    # shape is back, and so is the old reason for refusing it here rather than
    # later: reaching `plan_for`'s refusal would cost a repository download
    # first, for a line that could never have installed anything.
    if from_ is not None and not selected and not wizarding:
        raise NothingToSearchForError

    # One stack for both obtentions, because the showcase and the install are
    # the same one: a bare `--from` line obtains before the artifacts step and
    # then writes out of that very tree. Obtaining twice would put two
    # repositories on one line — the second could have moved, and the scratch
    # of the first is already gone.
    with ExitStack() as obtained:
        if wizarding:
            # Resolved ahead of the banner and of every question: a line with
            # nowhere legal to write is refused with no screen at all, the same
            # way the flag path refuses from behind `plan_for`.
            scoped = (
                None if asking_scope else _scope_and_root(global_=global_, environment=environment)
            )
            # The banner next: a human about to answer questions reads it as
            # context, unlike the flag path below, where a screen ahead of a
            # refusal would be the product answering before it knew.
            _print_banner()
            _open_session()
            # The artifacts step is the only one that consults a catalog, and a
            # line that already names something never opens it. Which catalog it
            # opens on is what `--from` decides — *"only the remote is
            # consulted"* speaks about exactly this step — and the embedded one
            # is never read on that path.
            if not selected:
                already_read = _what_the_artifacts_step_reads(from_, obtained)
            outcome = run_wizard(asked, already_read, environment, Path.cwd(), scoped, console=_out)
            if outcome is None:
                _stopped("nothing was written")
                raise typer.Exit(ExitCode.CANNOT_RUN)
            request, root = outcome
        else:
            scope, root = _scope_and_root(global_=global_, environment=environment)
            request = replace(asked, scope=scope)

        if from_ is None:
            # Read here only when the wizard did not already need it: the tree
            # is walked and every `SKILL.md` is read, so twice on one invocation
            # is a real cost and not a tidiness point.
            if already_read is None:
                already_read = load_catalog(content_root(), catalog_file())
            # The scratch lives exactly as long as the block, which has to cover
            # the write as well as the plan: `execute()` needs a `[source]`
            # recipe's clone still on disk at the point it copies it to its
            # destination.
            sources = obtained.enter_context(sources_for(already_read, request.mcps, request.scope))
            _perform(request, already_read, root, environment, sources, banner=not wizarding)
            return
        catalog = _what_the_remote_install_writes_from(from_, request, already_read, obtained)
        sources = obtained.enter_context(sources_for(catalog, request.mcps, request.scope))
        _perform(request, catalog, root, environment, sources, banner=not wizarding)


def _what_the_artifacts_step_reads(from_: str | None, obtained: ExitStack) -> Catalog:
    """The catalog the wizard's one catalog-reading step opens on.

    The artifacts step is the only step that consults a catalog, which is what
    makes *"with `--from`, only the remote is consulted"* a statement about this
    one line: the embedded catalog is not read on that path, and the showcase
    takes its place (#135).

    The obtention is entered on the caller's stack rather than in a `with` of its
    own, because the scratch it lands has to outlive the wizard by the whole
    length of the install: the tree the person just chose from is the tree the
    writer copies out of.
    """
    if from_ is None:
        return load_catalog(content_root(), catalog_file())
    return obtained.enter_context(catalog_from(from_))


def _what_the_remote_install_writes_from(
    from_: str, request: Request, already_read: Catalog | None, obtained: ExitStack
) -> Catalog:
    """The showcase the wizard already read, or the reach the line named.

    `already_read` on a `--from` line can only be the showcase: the embedded
    catalog is never loaded on that path, so a catalog in hand here is the one
    `_what_the_artifacts_step_reads` obtained a few lines up. Reusing it is not
    an optimisation — obtaining a second time would put *two* repositories on
    one line, since the remote could have moved between the two calls and the
    person chose from the first.

    With no showcase, the line named what to reach for and the reach is the
    obtention. Either way the scratch lives as long as the caller's stack, which
    covers the write as well as the plan: the sources of a remote install are
    inside it.
    """
    if already_read is not None:
        return already_read
    return obtained.enter_context(
        catalog_from(from_, request.skills, request.mcps, request.bundles)
    )


def _refuse_a_line_from_cannot_answer(from_: str | None, frameworks: Sequence[str]) -> None:
    """The way a `--from` line has no answer, refused before anything is fetched.

    The sequence is one of `Request`'s selectors and would rather travel as a
    whole `Request`, which is what it does everywhere else in this module. It
    cannot here, and the reason is the *order*: this refusal has to land before
    `_scope_and_root` — a line `--from` cannot answer must not need a git
    repository to be told so — and a `Request` built before the scope is resolved
    would carry a scope that is not the one it will run under.

    Since #135 the *other* refusal this used to make — a search root with
    nothing to look for — is no longer decidable here, and #137 took `--bundle`
    off the refused list, which is what leaves one selector in the signature. A
    bare `--from` line means the showcase where a wizard can open and means
    nothing where one cannot, so it is answered where the terminal is known, a
    few lines further down, and still before any obtention.
    """
    if from_ is not None and frameworks:
        raise UnsupportedRemoteUnitError


def _refuse_an_mcp_name_from_the_wrong_class(catalog: Catalog, mcps: Sequence[str]) -> None:
    """Refuse a `--mcp` name the recipe table misses, before the wizard opens.

    `plan_for` already raises `UnknownNameError` for the plain miss through
    `catalog.mcp(name)` — this does not replace that lookup, it calls it early
    and sharpens the answer when the name turns out to be real, just filed
    under a different flag (https://github.com/panlabs-tech/overpower/issues/97).
    """
    for name in mcps:
        try:
            catalog.mcp(name)
        except UnknownNameError:
            other = _flag_already_claiming(catalog, name)
            if other is not None:
                raise McpNameBelongsToAnotherFlagError(name, other) from None
            raise


def _flag_already_claiming(catalog: Catalog, name: str) -> str | None:
    """Which other selector's lookup already answers `name`, or `None`.

    Through the catalog's own closed-list lookups — the same ones
    `UnknownNameError` already backs — rather than a hand-rolled scan of each
    sequence, so this cannot drift from what `--ai-framework`/`--skill`/`--bundle`
    themselves accept.
    """
    for flag, lookup in (
        (AI_FRAMEWORK_FLAG, catalog.framework),
        (SKILL_FLAG, catalog.artifact),
        (BUNDLE_FLAG, catalog.bundle),
    ):
        try:
            lookup(name)
        except UnknownNameError:
            continue
        return flag
    return None


def _perform(  # noqa: PLR0913 — one argument per thing `plan_for` itself takes, plus `banner`
    request: Request,
    catalog: Catalog,
    root: Path,
    environment: Environment,
    sources: Mapping[str, Path] = MappingProxyType({}),
    *,
    banner: bool = True,
) -> None:
    """Plan against `catalog`, show the plan, and — unless asked not to — write it.

    One body for all three sources, and that is the whole shape of `--from`: it
    decides **where the catalog comes from** and changes nothing about what
    happens to one. A dry run therefore resolves the remote exactly as the real
    run does, which is what keeps it a report about *this* installation.

    `sources` is every `[source]` recipe's clone, already obtained by the
    caller's `remote.sources_for` block — passed through to `plan_for` and
    otherwise untouched here, the same way `catalog` is.

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
    plan = plan_for(request, catalog, root, environment, sources)
    # Read before anything is drawn and before the first byte, and on **both**
    # paths: a `--dry-run` that answered 0 to a line the real run refuses with 3
    # would be a report about a different installation
    # (https://github.com/panlabs-tech/overpower/issues/76).
    refuse_broken_documents(plan, request.scope)
    # Same reasoning, a fact of the machine rather than of a document: a
    # `--dry-run` that skipped this would report on a different machine than
    # the one that runs `install` for real (https://github.com/panlabs-tech/overpower/issues/82).
    refuse_unmet_preconditions(plan, environment.variables)
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
        _print_instructions(plan)
        # Before the closing line and not after it: `--dry-run` resolves
        # everything, so what it knows about the environment it knows *now*, and
        # a report ends with what it did rather than with an aside.
        _warn_about_skipped_classes(plan)
        _warn_about_unset_slots(plan, environment, request.scope)
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
    _print_instructions(plan)

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
                (counted(report.writes, report.files), "op.dim"),
            )
        )
    else:
        _print_railed()
        _out.print(installed_screen(plan, report.writes, report.files))
    if report.degraded:
        listed = ", ".join(str(path) for path in report.degraded)
        _out.print(Text.assemble(("degraded to copy", "op.warn"), " ", (listed, "op.dim")))
    _warn_about_skipped_classes(plan)
    _warn_about_unset_slots(plan, environment, request.scope)
    _warn_about_activation(plan, request.scope, root)
    _finished()


def _print_instructions(plan: Plan) -> None:
    """Print an MCP recipe's prose instructions beside the plan, once per recipe.

    A precondition is what the overpower checks; instructions are what it
    cannot — asking a credential, naming who on the team holds it. The plan is
    the last screen before the write, so this is where a human reads them,
    not folded into a warning after the fact.
    """
    for selection in plan.selections:
        for carried in selection.artifacts:
            if isinstance(carried, Recipe) and carried.instructions is not None:
                _out.print(Text.assemble((f"{carried.name} instructions", "op.section")))
                _out.print(Text(carried.instructions, style="op.dim"))


def _warn_about_unset_slots(plan: Plan, environment: Environment, scope: Scope) -> None:
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

    `scope` is here because *"the runtime reads it from the environment"* is not
    true of every target: a VS Code slot is filled from a prompt into the OS
    keychain, so the variable this shell lacks is one nothing will ever look for.
    Which document the plan lands in is a fact of (runtime, scope), so the scope
    has to travel — the same argument that put it on `_warn_about_activation`.
    """
    missing = unset_slots(plan, environment.variables, scope)
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


def _warn_about_skipped_classes(plan: Plan) -> None:
    """Name every runtime a mixed line carried both classes for that received only one.

    Issue #100: a mixed line no longer dies whole for a runtime with a row on
    just one of the two tables it carries — it writes what it has a row for,
    and this names what it does not. Exit 0, same reasoning
    `_warn_about_unset_slots` already uses — the write that happened is
    correct, and this says what did not happen instead of going silent about
    it. Grouped by which class is missing, since the fix reads differently for
    each: no MCP document names a target with no row to take one; no skills
    destination is `NoSkillsDestinationError`'s fix, one runtime early.
    """
    labels = (
        (MissingClass.MCP, "no MCP destination", "took the skills, skipped the server"),
        (MissingClass.SKILLS, "no skills destination", "took the server, skipped the skills"),
    )
    for missing, label, phrase in labels:
        listed = sorted(entry.runtime for entry in plan.skipped if entry.missing is missing)
        if listed:
            _warn(label, f"{', '.join(listed)} — {phrase}")


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
