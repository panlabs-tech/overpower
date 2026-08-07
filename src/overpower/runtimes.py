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
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import TYPE_CHECKING, assert_never

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

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
    """The user's home directory."""


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


Anchor = HomeAnchor | EnvironmentAnchor | FirstPresentAnchor
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
    """One row of the table: a runtime and its two skill destinations.

    `global_dir` is `None` for the two runtimes upstream declares
    `globalSkillsDir: undefined` — they are project-only, and a global install
    has nowhere to put their skills.
    """

    key: str
    display_name: str
    project_dir: ProjectSkillsDir
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

    @classmethod
    def from_process(cls) -> Environment:
        """Read the environment of the running process.

        The one place in the package that touches `os.environ`.
        """
        return cls(
            home=Path.home(),
            variables=os.environ,
            directory_exists=Path.is_dir,
        )


def resolve_project_dir(runtime: Runtime, root: Path) -> Path:
    """Absolute path a project-scope install writes to, under `root`."""
    return _join(root, runtime.project_dir.relative)


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
        case HomeAnchor():
            return environment.home
        case EnvironmentAnchor(variable, fallback):
            override = _override(environment.variables.get(variable))
            return override if override is not None else environment.home / fallback
        case FirstPresentAnchor(candidates, fallback):
            for candidate in candidates:
                path = environment.home / candidate
                if environment.directory_exists(path):
                    return path
            return environment.home / fallback
        case _ as unreachable:
            assert_never(unreachable)


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
    _runtime(
        "universal",
        "Universal",
        ".agents/skills",
        _config("agents/skills"),
        in_universal_list=False,
    ),
)
"""The 76 rows, in upstream declaration order."""

RUNTIMES_BY_KEY: Mapping[str, Runtime] = MappingProxyType(
    {runtime.key: runtime for runtime in RUNTIMES}
)
"""The table indexed by key, for `--runtime <key>` lookup."""


def runtimes_in(scope: Scope) -> tuple[Runtime, ...]:
    """The runtimes `--runtime` accepts in `scope`, in upstream declaration order.

    The set is a function of the scope, and that is not a formality: `eve` and
    `promptscript` declare no global destination, so a global install has 74
    rows to offer and refuses the other two instead of inventing a path for
    them — ADR 0009. In project scope every row has a destination, so the
    answer is the whole table and the rule is inert.

    One implementation, so that the screen and the validator cannot disagree.
    A wizard that offers what the next step refuses is exactly the failure ADR
    0008 was written against, one layer earlier.
    """
    match scope:
        case Scope.PROJECT:
            return RUNTIMES
        case Scope.GLOBAL:
            return tuple(runtime for runtime in RUNTIMES if runtime.global_dir is not None)
        case _ as unreachable:
            assert_never(unreachable)
