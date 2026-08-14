"""The runtime path table: where each AI runtime reads skills from.

Destination is a function of (artifact type, runtime, scope), never a catalog
field — rule 8 of the model, ADR 0006. For the copy class that v0.1.0 ships,
the (runtime, scope) half of that function is this table.

**The table is transcribed, not measured.** It mirrors `src/agents.ts` of
`vercel-labs/skills` at the pinned commit below, decided in
https://github.com/panlabs-tech/overpower/issues/18 and bounded by ADR 0008:
the table, the branches and the screen are inherited; the *writing* is not.
Attribution rides in the repository `NOTICE`, which travels into the wheel via
PEP 639 `license-files`.

Only a handful of rows have been verified against the runtime's own primary
source; every other row is an unverified copy, and `Evidence` says which is
which on each row rather than leaving it to a comment nobody reads.

Two behaviours deliberately diverge from upstream, both in `_override`, both
fail-safe and both named at their site: a blank override is treated as unset,
and a relative one is ignored.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import TYPE_CHECKING, assert_never

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

UPSTREAM_REPOSITORY = "https://github.com/vercel-labs/skills"
"""Origin of the table. MIT, `LICENSE` at the root of the repository."""

UPSTREAM_RELEASE = "v1.5.22"
"""Upstream release the table was transcribed from."""

UPSTREAM_COMMIT = "a4d243c3d4f86cdf9385dd1b6a0733f6937e70b5"
"""Commit the table was read at.

Read from `src/agents.ts` in git, never from the `dist/cli.mjs` of the npm
tarball: the published file is a rolldown bundle, minified and reordered.
"""

UNIVERSAL_PROJECT_DIR = ".agents/skills"
"""The project path shared by the runtimes upstream calls universal.

Shared by 19 of the 76 rows, which makes it the largest single destination and
not, despite the name, a path that covers everyone: measured 2026-08-06, Claude
Code 2.1.223 does not discover skills here, and Codex does not read
`.claude/skills`. Full coverage costs two writes, always.

The same folder name serves both scopes — see `universal_place` — but the set
of runtimes that read it does not: 19 in project, 6 in global (ADR 0011).
"""


class Dialect(StrEnum):
    """Which spelling of MCP configuration a document is written in.

    It is a property of the **document** and never of the runtime, and the
    difference is measured: `.mcp.json` is read by Claude Code, VS Code and the
    Copilot CLI, so three runtimes share one spelling, while the same VS Code
    reads `.vscode/mcp.json` in a different one — `servers` instead of
    `mcpServers`, `${input:}` instead of `${VAR}`. A dialect per runtime would
    have to answer twice for VS Code and could only be wrong once.

    Three members, and each one arrived exactly as designed: the set is closed
    and matched with `assert_never` in `overpower.rendering`, so
    https://github.com/panlabs-tech/overpower/issues/79 and
    https://github.com/panlabs-tech/overpower/issues/80 each landed as a
    compiler-visible hole in every `match` rather than as a silent default.

    **Three members that share one root key twice and agree on nothing else** is
    the shape the class predicted: `mcpServers` in Claude and Devin, `servers` in
    VS Code; the transport discriminated by `type` in two of three and by
    `transport` — HTTP only — in the third; and three distinct spellings of a
    secret between them. A dialect per runtime could not have said that.
    """

    CLAUDE = "claude"
    """`mcpServers`, an explicit `type`, and `${VAR}` interpolation."""

    VSCODE = "vscode"
    """`servers`, and a slot spelled `${input:<id>}` against an `inputs[]` entry.

    The one dialect whose slot is **two grafts and not one**: the reference and
    the prompt it points at live under different root keys of the same document.
    That is not decoration — measured, the `password: true` on the prompt is what
    encrypts the value under a key in the OS keychain, and it is the only spelling
    in the whole measured space where the secret is *stored* protected rather
    than merely referenced (`docs/research/mcp-config-formats.md`, trap 10).
    """

    DEVIN = "devin"
    """`mcpServers`, `transport` on HTTP only, and `${env:VAR}` interpolation.

    Stdio carries **no** discriminator: the vendor documents `"http"` and `"sse"`
    as the values of that field and infers stdio from `command`, so there is no
    value to write. Evidence is the vendor's documentation and not a measurement
    — the binary is not on the machine this was written on
    (`docs/research/mcp-config-formats.md` § Adendo 2026-08-13).
    """


@dataclass(frozen=True)
class McpDocument:
    """Where a runtime reads MCP servers in one scope, and how that file is written.

    Destination is a function of (type, runtime, scope) — rule 8, ADR 0006 — and
    this is the graft half of it: a copy lands in a folder, a graft lands in a
    **file plus a key inside it**, so this row carries the root key as well as
    the path.

    There is deliberately **no field for the file type**. JSON and JSONC differ
    for a reader that uses the standard library, and this product does not: the
    graft reads both through the same parser
    (docs/adr/0016-o-diff-aditivo-e-requisito.md). A field with no reader would
    be a field that goes stale unnoticed.
    """

    relative: str
    """The document, `/`-separated, hanging off whatever this row's base is."""

    root_key: str
    """The key the servers live under — `mcpServers` here, `servers` in VS Code."""

    dialect: Dialect

    born_pending: bool = False
    """Whether a server written here is inert until the user approves it.

    Measured in https://github.com/panlabs-tech/overpower/issues/17: a server
    coming from `.mcp.json` is born `⏸ Pending approval` in Claude Code and
    **does not connect** — no message, no exit code, no sign in a normal
    session. It is a column of this table and not a fact of the CLI because it
    is a fact of the pair (runtime, scope), and ADR 0014 makes the warning a
    requirement rather than a courtesy.
    """

    anchor: Anchor | None = None
    """What `relative` hangs off, or `None` for the target repository.

    A machine document is not the project one under a different root: it is a
    different directory on each operating system, and on two of the three rows
    an environment variable can move it. So the base travels **on the row**
    rather than being derived from the `scope` argument at the call site — the
    same authority rule 8 gives the table everywhere else. A row that says
    nothing hangs off the repository, which is what every project row does
    (https://github.com/panlabs-tech/overpower/issues/81).
    """


class Evidence(StrEnum):
    """Whether a path was verified against the runtime that reads it.

    `MEASURED` means this map has primary-source evidence — the runtime's own
    documentation, or an execution against the runtime — that the runtime reads
    skills at this location under its default configuration. `UNVERIFIED` means
    the path was copied from upstream and never checked here.
    """

    MEASURED = "measured"
    UNVERIFIED = "unverified"


class Scope(StrEnum):
    """Where an install writes: inside the target repository, or on the machine.

    Scope is not only the root a path hangs off — it also decides *which
    runtimes exist at all*, because two rows have no global destination. See
    `runtimes_in` and ADR 0009.
    """

    PROJECT = "project"
    GLOBAL = "global"


@dataclass(frozen=True)
class HomeAnchor:
    """The user's home directory, or a fixed `/`-separated directory under it.

    `relative` is empty for every row of the skills table, which hangs its own
    relative off this. It carries a value for the one machine document whose
    directory is spelled by the operating system and not by the product —
    macOS's `~/Library/Application Support`, which no variable names.
    """

    relative: str = ""


@dataclass(frozen=True)
class EnvironmentAnchor:
    """`$variable` when it names an absolute path, else `~/<fallback>`."""

    variable: str
    fallback: str


@dataclass(frozen=True)
class FirstPresentAnchor:
    """The first of `candidates` present under the home, else `~/<fallback>`.

    One row uses this — OpenClaw, which was renamed twice and still reads from
    whichever of its old directories the user has. Resolving it is the only
    reason global resolution touches the filesystem at all.
    """

    candidates: tuple[str, ...]
    fallback: str


@dataclass(frozen=True)
class PlatformAnchor:
    r"""A different anchor per operating system, because one row is three paths.

    The VS Code user profile is the case that forced it: `%APPDATA%\Code\User`
    on Windows, `~/Library/Application Support/Code/User` on macOS,
    `$XDG_CONFIG_HOME/Code/User` on Linux — one document, three anchors, and the
    same file name under all of them
    (`docs/research/mcp-config-formats.md`, the runtime-by-field table, note 1).

    Anything that is not Windows and not macOS resolves through `linux`: the
    values of `sys.platform` are an open set — `freebsd14`, `cygwin`, `aix` —
    and the XDG layout is what the rest of them follow. Guessing per unknown
    name would be inventing a path, which this table refuses to do.
    """

    windows: Anchor
    macos: Anchor
    linux: Anchor


Anchor = HomeAnchor | EnvironmentAnchor | FirstPresentAnchor | PlatformAnchor
"""What a global path hangs off. Project paths hang off the target repository."""


@dataclass(frozen=True)
class ProjectSkillsDir:
    """Where a runtime reads skills inside a repository.

    `relative` is stored exactly as upstream spells it, with `/` separators, so
    that a re-diff against `src/agents.ts` stays a string comparison. It becomes
    a platform path only in `resolve_project_dir`.
    """

    relative: str
    evidence: Evidence


@dataclass(frozen=True)
class GlobalSkillsDir:
    """Where a runtime reads skills on the machine."""

    anchor: Anchor
    relative: str
    evidence: Evidence


@dataclass(frozen=True)
class Runtime:
    """One row of the table: a runtime and, where it has one, its skill destinations.

    `global_dir` is `None` for the two runtimes upstream declares
    `globalSkillsDir: undefined` — they are project-only, and a global install
    has nowhere to put their skills.

    `project_dir` is `None` for exactly one row — `vscode` — and for a
    different reason (ADR 0018): it is not a transcribed runtime at all, it is
    the graft axis's own target given a display name so the wizard's MCP step
    can name it. Membership in this table stopped proving a skill destination
    the day that row was added; `runtimes_in` is what still answers *that*
    question, by filtering on the field rather than on presence in the tuple.
    """

    key: str
    display_name: str
    project_dir: ProjectSkillsDir | None
    global_dir: GlobalSkillsDir | None
    in_universal_list: bool = True
    in_universal_prompt: bool = True


@dataclass(frozen=True)
class Environment:
    """The machine facts that global path resolution consumes.

    Every one of them is an input to the decision of *where to write*, so each
    arrives as a value instead of being read at the point of use. That is what
    makes the whole table testable without a sandboxed `HOME`, and it keeps the
    process environment behind a single call site — `from_process`.
    """

    home: Path
    variables: Mapping[str, str]
    directory_exists: Callable[[Path], bool]
    platform: str
    """`sys.platform` of the machine being written to.

    A value like the other three, and for the same reason: a machine document
    is in a different directory on each of the three systems, so the whole 3x3
    matrix is assertable on whichever runner happens to be running. The suite
    still keys what it *cannot* run on `sys.platform` directly — this moves
    where a path resolves, never whether a test can execute.
    """

    file_exists: Callable[[Path], bool] = Path.is_file
    """Whether an MCP document already sits at a resolved path — `detected_mcp_runtimes`'s probe.

    `directory_exists` cannot answer this: an MCP document is a *file*, and
    `Path.is_dir()` is false of every one of them by construction. Defaulted
    rather than threaded through every existing call site — the graft class is
    the only reader, and every other construction of this type is unaffected.
    """

    @classmethod
    def from_process(cls) -> Environment:
        """Read the environment of the running process.

        The one place in the package that touches `os.environ` — and the one
        place that reads `sys.platform`.
        """
        return cls(
            home=Path.home(),
            variables=os.environ,
            directory_exists=Path.is_dir,
            platform=sys.platform,
            file_exists=Path.is_file,
        )


def resolve_project_dir(runtime: Runtime, root: Path) -> Path:
    """Absolute path a project-scope install writes to, under `root`.

    `None` is a real answer for `vscode` (ADR 0018), so a caller reaches here
    only after filtering through `runtimes_in` — same contract
    `resolve_global_dir` already has, mirrored rather than returning `None`
    itself, because every other row really does have one.
    """
    project_dir = runtime.project_dir
    if project_dir is None:  # pragma: no cover — every caller filters by `runtimes_in` first
        message = f"`{runtime.key}` has no project destination, despite `runtimes_in`"
        raise AssertionError(message)
    return _join(root, project_dir.relative)


def resolve_global_dir(runtime: Runtime, environment: Environment) -> Path | None:
    """Absolute path a global-scope install writes to.

    `None` when the runtime declares no global destination, which is a real
    answer and not a failure: the caller has to refuse the runtime in global
    scope rather than invent a path for it.
    """
    global_dir = runtime.global_dir
    if global_dir is None:
        return None
    return _join(_resolve_anchor(global_dir.anchor, environment), global_dir.relative)


def places_of(
    runtimes: Sequence[Runtime], scope: Scope, root: Path, environment: Environment
) -> Mapping[Path, tuple[str, ...]]:
    """Each distinct place `runtimes` read in `scope`, mapped to all of its readers.

    Two runtimes collapse into one place far more often than not — 19 of the 76
    rows read `.agents/skills` — and collapsing them is what makes both callers
    honest. `overpower.planning` passes the runtimes a line *selected*, so the
    plan says what a selection costs instead of naming a runtime that shares its
    directory with eighteen others (ADR 0008); `overpower.inspection` passes the
    whole scope, because the `doctor` has no manifest to read (axiom 2) and the
    closed table is the only thing that knows where equipment can be.

    Insertion order is the order of the runtime table, and both callers inherit
    it: it is the only order the screen and the writer share — and, in global
    scope, the order that decides which place is canonical.
    """
    grouped: dict[Path, list[str]] = {}
    for runtime in runtimes:
        grouped.setdefault(_place_of(runtime, scope, environment, root), []).append(runtime.key)
    return {place: tuple(readers) for place, readers in grouped.items()}


def _place_of(runtime: Runtime, scope: Scope, environment: Environment, root: Path) -> Path:
    """Where `runtime` reads skills, in `scope`."""
    match scope:
        case Scope.PROJECT:
            return resolve_project_dir(runtime, root)
        case Scope.GLOBAL:
            place = resolve_global_dir(runtime, environment)
            if place is None:  # pragma: no cover — every caller filters by `runtimes_in` first
                message = f"`{runtime.key}` has no global destination, despite `runtimes_in`"
                raise AssertionError(message)
            return place
        case _ as unreachable:
            assert_never(unreachable)


def _join(base: Path, relative: str) -> Path:
    r"""Append an upstream `/`-separated path to `base` as a platform path.

    The separator matters on Windows, where the transcribed `.factory/skills`
    has to become `.factory\\skills` before it reaches an API that only accepts
    a string — measured in
    https://github.com/panlabs-tech/overpower/issues/19.
    """
    return base.joinpath(*PurePosixPath(relative).parts)


def _resolve_anchor(anchor: Anchor, environment: Environment) -> Path:
    """Find the directory a global path hangs off."""
    match anchor:
        case HomeAnchor(relative):
            return _join(environment.home, relative)
        case EnvironmentAnchor(variable, fallback):
            override = _override(environment.variables.get(variable))
            return override if override is not None else _join(environment.home, fallback)
        case FirstPresentAnchor(candidates, fallback):
            for candidate in candidates:
                path = environment.home / candidate
                if environment.directory_exists(path):
                    return path
            return environment.home / fallback
        case PlatformAnchor():
            return _resolve_anchor(_for_platform(anchor, environment.platform), environment)
        case _ as unreachable:
            assert_never(unreachable)


def _for_platform(anchor: PlatformAnchor, platform: str) -> Anchor:
    """The branch `platform` reads, with every other Unix reading the Linux one."""
    if platform == "win32":
        return anchor.windows
    if platform == "darwin":
        return anchor.macos
    return anchor.linux


def _override(value: str | None) -> Path | None:
    """A directory named by the environment, or `None` to fall back.

    Two divergences from upstream live here, and both trade fidelity for a
    failure the map already refuses to ship.

    Upstream reads `XDG_CONFIG_HOME` through `xdg-basedir@5.1.0`, which does not
    trim, so a whitespace-only value becomes a *path made of spaces*. Here blank
    means unset, which is also what upstream itself does for the six
    tool-specific overrides.

    Upstream also honours a relative override, resolving it against the process
    working directory. The XDG spec says the opposite — *"if an implementation
    encounters a relative path in any of these variables it should consider the
    path invalid and ignore it"* — and the failure it prevents is the exact one
    ADR 0008 refuses to inherit: a global install that announces a path under
    the home and writes inside the user's repository, with exit 0.
    """
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    path = Path(stripped)
    return path if path.is_absolute() else None


_MEASURED_PROJECT_DIRS = frozenset(
    {
        # `.claude/skills`, measured against Claude Code 2.1.223 on 2026-08-06
        # in https://github.com/panlabs-tech/overpower/issues/18.
        "claude-code",
        # `.agents/skills` is a documented read path of each of these three,
        # read in each vendor's own documentation in
        # https://github.com/panlabs-tech/overpower/issues/5.
        "cursor",
        "codex",
        "github-copilot",
    }
)
"""Rows whose *project* path this map verified in primary source.

VS Code was verified alongside these and does not appear, because upstream has
no row for it: the table has no `vscode` key at all.
"""

_MEASURED_GLOBAL_DIRS = frozenset(
    {
        # `~/.claude/skills`, the "personal" tier of the precedence Claude Code
        # documents — enterprise over personal over project — read in
        # https://github.com/panlabs-tech/overpower/issues/5.
        "claude-code",
    }
)
"""Rows whose *global* path this map verified in primary source.

One of 74. The asymmetry against the four verified project paths is not an
oversight: the research this map ran read project layouts, and a global path is
only observable by installing into a real home.
"""


def _home(relative: str) -> GlobalSkillsDir:
    """`~/<relative>`."""
    return GlobalSkillsDir(HomeAnchor(), relative, Evidence.UNVERIFIED)


def _config(relative: str) -> GlobalSkillsDir:
    """`$XDG_CONFIG_HOME/<relative>`, else `~/.config/<relative>`."""
    return GlobalSkillsDir(
        EnvironmentAnchor("XDG_CONFIG_HOME", ".config"), relative, Evidence.UNVERIFIED
    )


def _env(variable: str, fallback: str) -> GlobalSkillsDir:
    """`$<variable>/skills`, else `~/<fallback>/skills`."""
    return GlobalSkillsDir(EnvironmentAnchor(variable, fallback), "skills", Evidence.UNVERIFIED)


def _first_present(candidates: tuple[str, ...], fallback: str) -> GlobalSkillsDir:
    """`~/<first present candidate>/skills`, else `~/<fallback>/skills`."""
    return GlobalSkillsDir(FirstPresentAnchor(candidates, fallback), "skills", Evidence.UNVERIFIED)


def _xdg() -> Anchor:
    """`$XDG_CONFIG_HOME`, else `~/.config` — the POSIX configuration directory."""
    return EnvironmentAnchor("XDG_CONFIG_HOME", ".config")


def _roaming() -> Anchor:
    """`%APPDATA%`, else `~/AppData/Roaming` — the Windows per-user application directory."""
    return EnvironmentAnchor("APPDATA", "AppData/Roaming")


def _runtime(  # noqa: PLR0913 — six parameters because a table row has six columns
    key: str,
    display_name: str,
    project_relative: str,
    global_dir: GlobalSkillsDir | None,
    *,
    in_universal_list: bool = True,
    in_universal_prompt: bool = True,
) -> Runtime:
    """Build a row, attaching the evidence recorded for its key.

    Evidence is applied here rather than spelled on every row so that the claim
    is readable in one place and the 76 rows stay a mechanical mirror of
    upstream.
    """
    project_evidence = Evidence.MEASURED if key in _MEASURED_PROJECT_DIRS else Evidence.UNVERIFIED
    if global_dir is not None and key in _MEASURED_GLOBAL_DIRS:
        global_dir = replace(global_dir, evidence=Evidence.MEASURED)
    return Runtime(
        key=key,
        display_name=display_name,
        project_dir=ProjectSkillsDir(project_relative, project_evidence),
        global_dir=global_dir,
        in_universal_list=in_universal_list,
        in_universal_prompt=in_universal_prompt,
    )


def _graft_only(key: str, display_name: str) -> Runtime:
    """A row with no skill destination in either scope — `vscode`, and alone (ADR 0018).

    A named constructor and not a seventh, defaultable column on `_runtime`:
    that builder's `project_relative` is a required upstream fact for all 76
    transcribed rows, and letting it take `None` would let a future
    transcription mistake an omission for this one deliberate exception.
    """
    return Runtime(
        key=key,
        display_name=display_name,
        project_dir=None,
        global_dir=None,
        in_universal_list=False,
        in_universal_prompt=False,
    )


RUNTIMES: tuple[Runtime, ...] = (
    # Upstream declaration order, which is the order the selection screen shows.
    _runtime("aider-desk", "AiderDesk", ".aider-desk/skills", _home(".aider-desk/skills")),
    _runtime("amp", "Amp", ".agents/skills", _config("agents/skills")),
    _runtime(
        "antigravity",
        "Antigravity",
        ".agents/skills",
        _home(".gemini/antigravity/skills"),
    ),
    _runtime(
        "antigravity-cli",
        "Antigravity CLI",
        ".agents/skills",
        _home(".gemini/antigravity-cli/skills"),
    ),
    _runtime("astrbot", "AstrBot", "data/skills", _home(".astrbot/data/skills")),
    _runtime(
        "autohand-code",
        "Autohand Code CLI",
        ".autohand/skills",
        _env("AUTOHAND_HOME", ".autohand"),
    ),
    _runtime("augment", "Augment", ".augment/skills", _home(".augment/skills")),
    _runtime("bob", "IBM Bob", ".bob/skills", _home(".bob/skills")),
    _runtime(
        "claude-code",
        "Claude Code",
        ".claude/skills",
        _env("CLAUDE_CONFIG_DIR", ".claude"),
    ),
    _runtime(
        "openclaw",
        "OpenClaw",
        "skills",
        _first_present((".openclaw", ".clawdbot", ".moltbot"), ".openclaw"),
    ),
    _runtime("cline", "Cline", ".agents/skills", _home(".agents/skills")),
    _runtime(
        "codearts-agent",
        "CodeArts Agent",
        ".codeartsdoer/skills",
        _home(".codeartsdoer/skills"),
    ),
    _runtime("codebuddy", "CodeBuddy", ".codebuddy/skills", _home(".codebuddy/skills")),
    _runtime("codemaker", "Codemaker", ".codemaker/skills", _home(".codemaker/skills")),
    _runtime("codestudio", "Code Studio", ".codestudio/skills", _home(".codestudio/skills")),
    _runtime("codex", "Codex", ".agents/skills", _env("CODEX_HOME", ".codex")),
    _runtime(
        "command-code",
        "Command Code",
        ".commandcode/skills",
        _home(".commandcode/skills"),
    ),
    _runtime("continue", "Continue", ".continue/skills", _home(".continue/skills")),
    _runtime("cortex", "Cortex Code", ".cortex/skills", _home(".snowflake/cortex/skills")),
    # Upstream hardcodes `~/.config` here and for `kimchi`, bypassing the
    # `xdg-basedir` it uses for the six `_config` rows. Transcribed as written.
    _runtime("crush", "Crush", ".crush/skills", _home(".config/crush/skills")),
    _runtime("cursor", "Cursor", ".agents/skills", _home(".cursor/skills")),
    _runtime("deepagents", "Deep Agents", ".agents/skills", _home(".deepagents/agent/skills")),
    _runtime("devin", "Devin for Terminal", ".devin/skills", _config("devin/skills")),
    _runtime(
        "dexto",
        "Dexto",
        ".agents/skills",
        _home(".agents/skills"),
        in_universal_prompt=False,
    ),
    _runtime("droid", "Droid", ".factory/skills", _home(".factory/skills")),
    _runtime("eve", "Eve", "agent/skills", None),
    _runtime(
        "firebender",
        "Firebender",
        ".agents/skills",
        _home(".firebender/skills"),
        in_universal_prompt=False,
    ),
    _runtime("forgecode", "ForgeCode", ".forge/skills", _home(".forge/skills")),
    _runtime("gemini-cli", "Gemini CLI", ".agents/skills", _home(".gemini/skills")),
    _runtime("github-copilot", "GitHub Copilot", ".agents/skills", _home(".copilot/skills")),
    _runtime("goose", "Goose", ".goose/skills", _config("goose/skills")),
    _runtime("grok", "Grok Build", ".grok/skills", _env("GROK_HOME", ".grok")),
    _runtime("hermes-agent", "Hermes Agent", ".hermes/skills", _env("HERMES_HOME", ".hermes")),
    _runtime(
        "inference-sh",
        "inference.sh",
        ".inferencesh/skills",
        _home(".inferencesh/skills"),
    ),
    _runtime("jazz", "Jazz", ".jazz/skills", _home(".jazz/skills")),
    _runtime("junie", "Junie", ".junie/skills", _home(".junie/skills")),
    _runtime("iflow-cli", "iFlow CLI", ".iflow/skills", _home(".iflow/skills")),
    _runtime("kilo", "Kilo Code", ".kilocode/skills", _home(".kilocode/skills")),
    _runtime("kimchi", "Kimchi", ".kimchi/skills", _home(".config/kimchi/harness/skills")),
    _runtime("kimi-code-cli", "Kimi Code CLI", ".agents/skills", _home(".agents/skills")),
    _runtime("kiro-cli", "Kiro CLI", ".kiro/skills", _home(".kiro/skills")),
    _runtime("kode", "Kode", ".kode/skills", _home(".kode/skills")),
    _runtime("lingma", "Lingma", ".lingma/skills", _home(".lingma/skills")),
    _runtime(
        "loaf",
        "Loaf",
        ".agents/skills",
        _home(".agents/skills"),
        in_universal_prompt=False,
    ),
    _runtime("mcpjam", "MCPJam", ".mcpjam/skills", _home(".mcpjam/skills")),
    _runtime("minimax-code", "MiniMax Code", ".minimax/skills", _home(".minimax/skills")),
    _runtime("mistral-vibe", "Mistral Vibe", ".vibe/skills", _env("VIBE_HOME", ".vibe")),
    _runtime("moxby", "Moxby", ".moxby/skills", _home(".moxby/skills")),
    _runtime("mux", "Mux", ".mux/skills", _home(".mux/skills")),
    _runtime("opencode", "OpenCode", ".agents/skills", _config("opencode/skills")),
    _runtime("openhands", "OpenHands", ".openhands/skills", _home(".openhands/skills")),
    _runtime("ona", "Ona", ".ona/skills", _home(".ona/skills")),
    _runtime("pi", "Pi", ".pi/skills", _home(".pi/agent/skills")),
    _runtime("qoder", "Qoder", ".qoder/skills", _home(".qoder/skills")),
    _runtime("qoder-cn", "Qoder CN", ".qoder/skills", _home(".qoder-cn/skills")),
    _runtime("qwen-code", "Qwen Code", ".qwen/skills", _home(".qwen/skills")),
    _runtime(
        "replit",
        "Replit",
        ".agents/skills",
        _config("agents/skills"),
        in_universal_list=False,
    ),
    _runtime("reasonix", "Reasonix", ".reasonix/skills", _home(".reasonix/skills")),
    _runtime("rovodev", "Rovo Dev", ".rovodev/skills", _home(".rovodev/skills")),
    _runtime("roo", "Roo Code", ".roo/skills", _home(".roo/skills")),
    _runtime(
        "tabnine-cli",
        "Tabnine CLI",
        ".tabnine/agent/skills",
        _home(".tabnine/agent/skills"),
    ),
    _runtime("terramind", "Terramind", ".terramind/skills", _home(".terramind/skills")),
    _runtime("tinycloud", "Tinycloud", ".tinycloud/skills", _home(".tinycloud/skills")),
    _runtime("trae", "Trae", ".trae/skills", _home(".trae/skills")),
    _runtime("trae-cn", "Trae CN", ".trae/skills", _home(".trae-cn/skills")),
    _runtime("warp", "Warp", ".agents/skills", _home(".agents/skills")),
    _runtime("windsurf", "Windsurf", ".windsurf/skills", _home(".codeium/windsurf/skills")),
    _runtime("zed", "Zed", ".agents/skills", _home(".agents/skills")),
    _runtime("zcode", "ZCode", ".zcode/skills", _home(".zcode/skills")),
    _runtime("zencoder", "Zencoder", ".zencoder/skills", _home(".zencoder/skills")),
    _runtime("zenflow", "Zenflow", ".zencoder/skills", _home(".zencoder/skills")),
    _runtime("neovate", "Neovate", ".neovate/skills", _home(".neovate/skills")),
    _runtime("pochi", "Pochi", ".pochi/skills", _home(".pochi/skills")),
    _runtime(
        "promptscript",
        "PromptScript",
        ".agents/skills",
        None,
        in_universal_prompt=False,
    ),
    _runtime("adal", "AdaL", ".adal/skills", _home(".adal/skills")),
    # Not upstream's, and not a skill destination — the graft axis's own target,
    # given a row so the wizard's MCP step can name it (ADR 0018). It sits after
    # every transcribed row and before the synthetic `universal` one, which is
    # this table's other non-transcribed member.
    _graft_only("vscode", "VS Code"),
    _runtime(
        "universal",
        "Universal",
        ".agents/skills",
        _config("agents/skills"),
        in_universal_list=False,
    ),
)
"""The 76 transcribed rows, plus `vscode` — 77 total (ADR 0018)."""

RUNTIMES_BY_KEY: Mapping[str, Runtime] = MappingProxyType(
    {runtime.key: runtime for runtime in RUNTIMES}
)
"""The table indexed by key, for `--runtime <key>` lookup."""

MCP_DOCUMENTS: Mapping[tuple[str, Scope], McpDocument] = MappingProxyType(
    {
        # Measured against Claude Code 2.1.220 in
        # https://github.com/panlabs-tech/overpower/issues/17: `.mcp.json` at the
        # root of the project, strict JSON, `mcpServers`, and the server born
        # pending approval.
        ("claude-code", Scope.PROJECT): McpDocument(
            relative=".mcp.json",
            root_key="mcpServers",
            dialect=Dialect.CLAUDE,
            born_pending=True,
        ),
        # Measured in https://github.com/panlabs-tech/overpower/issues/17:
        # `.vscode/mcp.json`, JSONC, `servers`, and the secret held by the OS
        # keychain through `inputs[]`. Nothing is born pending here — what VS
        # Code gates is Workspace Trust, which is a fact of the folder and not of
        # the server, so it is not a per-graft warning (ADR 0014).
        ("vscode", Scope.PROJECT): McpDocument(
            relative=".vscode/mcp.json",
            root_key="servers",
            dialect=Dialect.VSCODE,
        ),
        # Vendor documentation and **not** a measurement, in
        # https://github.com/panlabs-tech/overpower/issues/80: `.devin/mcp_config.json`
        # at the root of the project, `mcpServers`, and no approval gate
        # documented anywhere — so `born_pending` stays false, because inventing
        # one would be asserting a fact nobody here could observe.
        ("devin", Scope.PROJECT): McpDocument(
            relative=".devin/mcp_config.json",
            root_key="mcpServers",
            dialect=Dialect.DEVIN,
        ),
        # --- machine scope, https://github.com/panlabs-tech/overpower/issues/81
        #
        # `~/.claude.json`, `mcpServers` at the **root** of the file — the same
        # key the project document uses, in a file that is not the project's
        # (`docs/research/mcp-config-formats.md`, the runtime-by-field table).
        # The home anchors it on all three systems, and no variable in the
        # research moves it.
        #
        # `born_pending` is **false here and true one row up**, which is the
        # whole reason it is a column: the approval gate the research measured is
        # what a *project* file has to pass, and the personal file is the user's
        # own. So the warning ADR 0014 requires goes quiet in machine scope
        # without the CLI learning a second rule.
        #
        # This file carries `userID`, `machineID` and onboarding state. Nothing
        # protects them here — the additive diff of ADR 0016 does, and it does it
        # for every graft, which is why this row is a path and not a special case.
        ("claude-code", Scope.GLOBAL): McpDocument(
            relative=".claude.json",
            root_key="mcpServers",
            dialect=Dialect.CLAUDE,
            anchor=HomeAnchor(),
        ),
        # The VS Code user profile: one file name under three directories. The
        # macOS one is spelled by the operating system and named by no variable,
        # so it is the only anchor in the package that hangs a fixed directory
        # off the home.
        #
        # **The default profile only.** A non-default profile puts the document
        # under `<userDataDir>/User/profiles/<id>/mcp.json`, and the id is not
        # derivable from anything the product can read — inventing one would
        # write a file nothing reads, at exit 0. Same for the second copy a
        # Remote-WSL or Remote-SSH session keeps on the remote: the research
        # records that it exists and that writing to the wrong one is a silent
        # no-op, and records no path for it
        # (`docs/research/mcp-config-formats.md`, risk item 18). A path nobody
        # read in primary source does not go on this table.
        #
        # **Which leaves the silent no-op reachable, and says so here rather
        # than pretending otherwise**: a `--global` graft from inside a WSL
        # session writes the Linux profile, exits 0, and a VS Code running on
        # the Windows side never reads it. Warning about it would mean
        # detecting the session and naming the file it *should* have been —
        # the second half is the part no source supplies, and half a warning
        # points nowhere.
        ("vscode", Scope.GLOBAL): McpDocument(
            relative="Code/User/mcp.json",
            root_key="servers",
            dialect=Dialect.VSCODE,
            anchor=PlatformAnchor(
                windows=_roaming(),
                macos=HomeAnchor("Library/Application Support"),
                linux=_xdg(),
            ),
        ),
        # Vendor documentation, read directly: `~/.config/devin/mcp_config.json`,
        # and `%APPDATA%\devin\mcp_config.json` on Windows.
        #
        # **The POSIX branch reads a variable the vendor's sentence does not
        # name.** `~/.config` is not a literal here — it is what
        # `XDG_CONFIG_HOME` defaults to, so the anchor spells the directory the
        # vendor named rather than the syntax it named it with. The row is
        # wrong for a machine that moves the variable only if the vendor
        # hard-codes the literal, which its own page gives no sign of.
        #
        # **It does not have to agree with the skills row for this runtime**,
        # and on Windows it does not: `_config("devin/skills")` reads XDG on
        # every platform, this reads `APPDATA`. That is two tables with two
        # sources, not a contradiction — the skills row is a transcription of
        # `vercel-labs/skills` and the vendor's own page is what decides here.
        # Where the two sources speak, the source of the class wins.
        #
        # The `AppData/Roaming` fallback is **derived and not transcribed** —
        # it is the documented default of `%APPDATA%`, and a real Windows never
        # reaches it, because the variable is always set there.
        ("devin", Scope.GLOBAL): McpDocument(
            relative="devin/mcp_config.json",
            root_key="mcpServers",
            dialect=Dialect.DEVIN,
            anchor=PlatformAnchor(windows=_roaming(), macos=_xdg(), linux=_xdg()),
        ),
    }
)
"""Where each (runtime, scope) pair reads MCP servers — **and the function is partial**.

Skills have a destination for all 76 rows in project scope; MCP has two, and
that asymmetry is the shape of the whole class rather than a gap in the
transcription. There is **no canonical format** — measured, the same server has
three root keys, three file names and three secret spellings across three
targets, and the MCP spec itself documents the absence (SEP-2633). So a row here
is a target somebody rendered and read the primary source for, never a path
copied from a list.

**That sentence used to say "rendered and measured", and the second row is what
moved it.** Said plainly rather than edited quietly: `.mcp.json` was executed
against Claude Code 2.1.220, and the Devin row was read off the vendor's
documentation with the binary absent from the machine
(https://github.com/panlabs-tech/overpower/issues/80). The bar that survives is
*primary source, read directly* — which the research already treats as a grade it
carries, and lists among its own weaknesses. What the bar still refuses is the
thing it was written against: a path transcribed from somebody's list.

**The difference between the two grades is not a column here.** It lives in the
dialect's docstring and in `docs/research/mcp-config-formats.md`, because no code
reads it — a field with no reader is a field that goes stale unnoticed. The day
something branches on it, it becomes a column.

**This table is the closed set of MCP runtimes, and `RUNTIMES` no longer proves
the other direction.** Since ADR 0018 every key here also has a row in
`RUNTIMES` — `vscode` joined `claude-code` and `devin` there, given a display
name and no skill destination — so the key sets nest one way now. They do not
nest the other way: `cursor` has a skills row and no MCP document anywhere, which
is what keeps this a pair of tables rather than a hierarchy. The key stays a
`str` and not a `Runtime` regardless: presence in `RUNTIMES` answers "does this
key have a display name", never "which classes can it receive" — that is still
per-class, this table for the graft half and `runtimes_in` for the copy half
(https://github.com/panlabs-tech/overpower/issues/79, ADR 0018).

Where the pair has no row the pair **does not exist**: `overpower.planning`
refuses the whole line with exit 3 rather than inventing a file, which is ADR
0009's reading applied to the second axis. All three targets now have both
scopes, so the partiality that remains is per *runtime*: `cursor` reads skills
and has no MCP document anywhere.

**A machine row is not the project row under another root.** It carries its own
`anchor`, because the three targets disagree about where the personal file is
and two of them disagree with themselves across operating systems
(https://github.com/panlabs-tech/overpower/issues/81).
"""


@dataclass(frozen=True)
class McpPlace:
    """One document a graft lands in, and every selected runtime that reads it.

    The graft twin of what `places_of` answers for the copy class, and it
    collapses runtimes onto a place for the same reason (ADR 0008): three
    runtimes read `.mcp.json`, so announcing a runtime would promise one target
    and equip several.
    """

    path: Path
    document: McpDocument
    readers: tuple[str, ...]


def mcp_document_of(key: str, scope: Scope) -> McpDocument | None:
    """Where `key` reads MCP servers in `scope`, or `None` when the pair has none.

    `None` is a real answer and not a failure — the caller has to refuse the
    runtime rather than invent a file for it, the same contract
    `resolve_global_dir` already has.

    A **key** and not a `Runtime`, because a row in `RUNTIMES` no longer implies
    anything about this table (ADR 0018): `vscode` has one and no skills
    destination, `cursor` has one and no MCP document anywhere. Taking a
    `Runtime` would read as a promise that the argument's other fields mean
    something here, which since ADR 0018 is not even true of the row's own
    `project_dir` (https://github.com/panlabs-tech/overpower/issues/79).
    """
    return MCP_DOCUMENTS.get((key, scope))


def mcp_runtimes_in(scope: Scope) -> tuple[str, ...]:
    """The runtime keys that can receive an MCP server in `scope`, in table order.

    Read straight off `MCP_DOCUMENTS` rather than filtered out of `runtimes_in`,
    which is the same change of authority `mcp_document_of` describes: the set of
    MCP runtimes is what the MCP table says it is, and filtering the skills table
    would silently drop every target that has no skills row.

    One implementation, so the refusal and every screen that lists the
    alternatives cannot disagree about who is on it — the same reason
    `runtimes_in` is single.
    """
    return tuple(key for (key, at), _ in MCP_DOCUMENTS.items() if at is scope)


def known_runtimes() -> tuple[str, ...]:
    """Every key `--runtime` accepts anywhere, in table order — **both** axes of it.

    What a `--runtime` value is checked against is the **union** of `RUNTIMES`
    and the MCP table's keys. Since ADR 0018 every graft target has a row in
    `RUNTIMES` — `vscode` was the one exception, and it joined the table with no
    skill destination rather than staying outside it — so the union costs one
    walk of `RUNTIMES_BY_KEY` for the ordinary case and only reaches into the
    graft table for a key that table declares and this one never will: none
    exist today, and the shape stays ready for the day one does.

    Here and not in `overpower.planning` for the reason `runtimes_in` is here:
    the tables live in this module, and a caller that walked them itself would be
    a second place that has to learn about a third one.

    `RUNTIMES`' own order first, then any graft-only key it does not carry: the
    order the plan lists places in is the order the writer performs them.
    """
    grafts = dict.fromkeys(key for key, _ in MCP_DOCUMENTS)
    return (*RUNTIMES_BY_KEY, *(key for key in grafts if key not in RUNTIMES_BY_KEY))


def mcp_places_of(
    keys: Sequence[str], scope: Scope, root: Path, environment: Environment
) -> tuple[McpPlace, ...]:
    """Each distinct document `keys` read in `scope`, with all of its readers.

    `root` is the target repository, and it is what a row with no anchor hangs
    off. A machine row carries its own anchor and ignores `root` entirely —
    which is not the shape the copy class has, because a skills row is the same
    directory name under two different bases and a machine document is a
    different directory on each operating system.

    `environment` is therefore load-bearing here and not merely passed through:
    it carries the home, the variables that move two of the three rows, and the
    platform that chooses between them.

    A runtime with no document in `scope` is **skipped**, not guessed at: the
    caller refuses the line before this runs, and refusing twice in two places
    would be two chances to word it differently.
    """
    grouped: dict[Path, tuple[McpDocument, list[str]]] = {}
    for key in keys:
        document = mcp_document_of(key, scope)
        if document is None:
            continue
        path = _join(_mcp_base(document, root, environment), document.relative)
        grouped.setdefault(path, (document, []))[1].append(key)
    return tuple(
        McpPlace(path=path, document=document, readers=tuple(readers))
        for path, (document, readers) in grouped.items()
    )


def _mcp_base(document: McpDocument, root: Path, environment: Environment) -> Path:
    """What this document's relative path hangs off — the table decides, not the scope."""
    anchor = document.anchor
    return root if anchor is None else _resolve_anchor(anchor, environment)


def runtimes_in(scope: Scope) -> tuple[Runtime, ...]:
    """The runtimes `--runtime` accepts for a **skill** in `scope`, in table order.

    The set is a function of the scope, and that is not a formality: `eve` and
    `promptscript` declare no global destination, so a global install has 74 of
    the 76 skill-capable rows to offer and refuses the other two instead of
    inventing a path for them — ADR 0009.

    **Filtered by *has a skill destination in this scope*, not by membership in
    `RUNTIMES`** (ADR 0018). Before `vscode` joined the table the two questions
    had the same answer in project scope, so the row was returned whole; they no
    longer do, and returning it whole would offer a graft-only target the next
    step refuses — exactly the failure ADR 0008 was written against, arriving
    through this function instead of through the screen.

    One implementation, so that the screen and the validator cannot disagree.
    """
    match scope:
        case Scope.PROJECT:
            return tuple(runtime for runtime in RUNTIMES if runtime.project_dir is not None)
        case Scope.GLOBAL:
            return tuple(runtime for runtime in RUNTIMES if runtime.global_dir is not None)
        case _ as unreachable:
            assert_never(unreachable)


def universal_place(scope: Scope) -> str:
    """How the shared place is spelled in `scope` — what the group's heading names.

    Two spellings of one folder name, because the two roots are not the same
    word: a project path hangs off the repository and reads `.agents/skills`, a
    global one hangs off the home and reads `~/.agents/skills`. A heading that
    could only say one of them would be a heading that lies in the other scope.
    """
    match scope:
        case Scope.PROJECT:
            return UNIVERSAL_PROJECT_DIR
        case Scope.GLOBAL:
            return f"~/{UNIVERSAL_PROJECT_DIR}"
        case _ as unreachable:
            assert_never(unreachable)


def universal_runtimes(scope: Scope) -> tuple[Runtime, ...]:
    """The runtimes that read the universal place **in `scope`** — 19 in project, 6 in global.

    The group is what the wizard shows as *always included* (ADR 0011), so its
    membership is not a taxonomy: the heading names a place, and a member is
    whoever reads **that** place in **that** scope. Measured, the 18 members the
    project group has in global scope land in 11 distinct directories, and only
    six of them in `~/.agents/skills` — `codex` goes to `~/.codex/skills`,
    `cursor` to `~/.cursor/skills`, `amp` to `~/.config/agents/skills`. Naming
    them under one heading is the *"the screen says one thing and the result is
    another"* class ADR 0008 exists to refuse, arriving through the screen
    instead of through the write.

    Same shape as `runtimes_in`, and for the same reason: **one implementation**,
    consumed both by the screen that locks the group and by the `Request` the
    wizard builds out of it, so the two cannot disagree about who is in it.
    """
    return tuple(runtime for runtime in runtimes_in(scope) if _reads_universally(runtime, scope))


def _reads_universally(runtime: Runtime, scope: Scope) -> bool:
    """Whether `runtime` reads the universal place in `scope`.

    Read off the table rather than off a resolved path, and that is deliberate:
    the anchor is what decides it — `~/.agents/skills` is a `HomeAnchor`, while
    `amp`'s `~/.config/agents/skills` is an `EnvironmentAnchor` that the machine
    can move — so membership stays a fact of the transcription, answerable
    without a filesystem or a home directory.
    """
    match scope:
        case Scope.PROJECT:
            project_dir = runtime.project_dir
            return project_dir is not None and project_dir.relative == UNIVERSAL_PROJECT_DIR
        case Scope.GLOBAL:
            global_dir = runtime.global_dir
            return (
                global_dir is not None
                and isinstance(global_dir.anchor, HomeAnchor)
                and global_dir.relative == UNIVERSAL_PROJECT_DIR
            )
        case _ as unreachable:
            assert_never(unreachable)


def detected_runtimes(scope: Scope, root: Path, environment: Environment) -> frozenset[str]:
    """Runtime keys whose destination already exists on disk — the wizard's pre-mark.

    No state file survives an install (ADR 0008, https://github.com/panlabs-tech/overpower/issues/41):
    versioning a schema, migrating it and handling its corruption do not pay for
    themselves to save two taps of space. What stands in for memory is disk
    itself.

    Project scope probes `root`, the target repository — what is decided there
    is what the *repository* carries, which is team property, and neither `~`
    nor a memory of a past selection can see the team (ADR 0008). Global scope
    probes `~` directly. When the project carries no runtime directory at
    all — the common case, a repository that has never run the overpower — that
    is zero signal from the repository, and the probe falls back to `~` rather
    than pre-checking nothing.
    """
    candidates = runtimes_in(scope)
    match scope:
        case Scope.PROJECT:
            found = _present_at(candidates, environment, lambda r: resolve_project_dir(r, root))
            if found:
                return found
            return _present_at(
                candidates, environment, lambda r: resolve_global_dir(r, environment)
            )
        case Scope.GLOBAL:
            return _present_at(
                candidates, environment, lambda r: resolve_global_dir(r, environment)
            )
        case _ as unreachable:
            assert_never(unreachable)


def _present_at(
    candidates: Sequence[Runtime],
    environment: Environment,
    resolve: Callable[[Runtime], Path | None],
) -> frozenset[str]:
    """The keys among `candidates` whose resolved destination already exists.

    Through `environment.directory_exists` and never a bare `Path.is_dir()` —
    the same single injection point `_resolve_anchor` already reads the
    filesystem through, so this table stays testable without a sandboxed
    `HOME` the way every other function here already is.
    """
    return frozenset(
        runtime.key
        for runtime in candidates
        if (place := resolve(runtime)) is not None and environment.directory_exists(place)
    )


def detected_mcp_runtimes(scope: Scope, root: Path, environment: Environment) -> frozenset[str]:
    """Runtime keys whose MCP document already exists on disk — the graft class's pre-mark.

    `detected_runtimes`' twin, and simpler: a skills directory is the same name
    under two different bases, so a repository with no signal falls back to `~`
    to avoid pre-checking nothing. An MCP document does not need the fallback —
    every row already carries its own base (`McpDocument.anchor`), project and
    machine are genuinely different files rather than the same folder under two
    roots, so probing the one `scope` names is the whole answer.
    """
    found: set[str] = set()
    for key in mcp_runtimes_in(scope):
        document = mcp_document_of(key, scope)
        if document is None:  # pragma: no cover — `mcp_runtimes_in` reads the same table
            continue
        path = _join(_mcp_base(document, root, environment), document.relative)
        if environment.file_exists(path):
            found.add(key)
    return frozenset(found)
