"""A real content tree, a real target and the CLI between them.

Machinery with no subject of its own, and it belongs here for the reason the
ruler draws the line at: **`support/` talks to real infrastructure**, which is
exactly what building a content tree on disk and pointing the product at it is.
There is no filesystem double anywhere below the CLI (ADR 0010).

`content_root` and `catalog_file` are redirected, and that is not a double
either: they are aimed at a **real tree built in `tmp_path`**. Two properties
need it — the shipped catalog carries a single pool skill while the criteria ask
for two names on one line, and the internal-link property needs a source tree
that *contains* a link. The tree the product walks is real either way; only its
address moves.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, assert_never, cast

from json5 import loads
from rich.console import Console

from overpower import cli
from overpower.inspection import GIT_CONFIG_GLOBAL
from overpower.runtimes import (
    MCP_DOCUMENTS,
    RUNTIMES,
    EnvironmentAnchor,
    FirstPresentAnchor,
    HomeAnchor,
    PlatformAnchor,
)
from overpower.screens import THEME

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping, Sequence
    from pathlib import Path

    import pytest

    from overpower.runtimes import Anchor

CLAUDE = ".claude/skills"
"""Where Claude Code reads skills in a repository — measured, not transcribed."""

AGENTS = ".agents/skills"
"""The path Cursor reads, shared with 18 other rows of the table."""

PATH = re.compile(r"(?:[\w.@+-]+/)+")
"""Every `/`-terminated path token on a screen.

The plan screen is the only screen that prints paths, and it prints them
relative to the target with a trailing separator — so this finds the announced
set and nothing else. A runtime key carries no separator.
"""

KEY = re.compile(r"[›>]\s+([\w.@+-]+)")
"""The key half of a graft line: `.mcp.json › mcpServers.cloudflare`.

The plan is the only screen that spells a document key, and it spells it after
the separator — so this finds the announced set and nothing else. A path carries
no separator of this kind and a runtime key carries no dot.
"""

ANSI = re.compile(r"\x1b\[[0-9;]*m")
"""The SGR sequences a console in a terminal writes around styled text.

Colour only — cursor control never reaches these captures, because nothing in
the product animates. `tests/support/screens.py` takes styles off through
`export_text(styles=False)`; this is the same subtraction for the path that
captures a stream instead of recording a screen.
"""


def _variables_of(anchor: Anchor) -> Iterator[str]:
    """Every environment variable this anchor can read, following platform branches.

    Recursive because `PlatformAnchor` holds anchors: the Windows branch of the
    VS Code profile reads `APPDATA` and the Linux one reads `XDG_CONFIG_HOME`,
    and a walk that stopped at the top level would scrub one runner's leak and
    not the other's.

    Matched exhaustively with `assert_never` rather than written as an
    `isinstance` cascade: a fifth anchor variant that reads a variable would
    otherwise fall through in silence and reopen the very leak this closes.
    """
    match anchor:
        case EnvironmentAnchor(variable, _):
            yield variable
        case PlatformAnchor(windows, macos, linux):
            for branch in (windows, macos, linux):
                yield from _variables_of(branch)
        case HomeAnchor() | FirstPresentAnchor():
            return
        case _ as unreachable:
            assert_never(unreachable)


ANCHORS = (
    GIT_CONFIG_GLOBAL,
    *sorted(
        {
            variable
            for anchor in (
                *(
                    runtime.global_dir.anchor
                    for runtime in RUNTIMES
                    if runtime.global_dir is not None
                ),
                *(
                    document.anchor
                    for document in MCP_DOCUMENTS.values()
                    if document.anchor is not None
                ),
            )
            for variable in _variables_of(anchor)
        }
    ),
)
"""Every variable that can move a path the product reads, out of the sandbox.

Scrubbed alongside `HOME`, and for the same reason: a developer with
`CLAUDE_CONFIG_DIR` exported would send a global install *out* of the sandbox,
and a test that asserted against `tmp_path` would fail on their machine and
nowhere else. `doctor` makes it sharper — it walks **every** global destination
of the table, so an unscrubbed anchor is the suite reading the developer's own
equipment — and `GIT_CONFIG_GLOBAL` joins them because `overpower.inspection`
honours it when it looks for `core.symlinks`.

**Both tables, not just the skills one.** The machine documents of
https://github.com/panlabs-tech/overpower/issues/81 brought `APPDATA` in, which
is *always* set on the Windows cell of the matrix — an unscrubbed one there is a
suite that writes into the runner's real roaming profile and asserts nothing.

**Derived from the tables, never listed by hand.** They grow and never shrink,
so a hand-written list would go quietly stale on the next transcription and
restore exactly the leak this exists to close.
"""


def catalog_of(  # noqa: PLR0913 — one keyword per unit of the catalog, plus the two roots
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *names: str,
    extra: Sequence[str] = (),
    frameworks: Mapping[str, Sequence[str]] | None = None,
    bundles: Mapping[str, Sequence[str]] | None = None,
    mcps: Mapping[str, str] | None = None,
) -> Path:
    """Build a real content tree of `names`, aim the product at it, answer its root.

    Each pool skill gets the `SKILL.md` whose frontmatter discovery reads, plus
    whatever `extra` names — which is how a skill is given more than one file
    when the test is about what survives a second install.

    `frameworks` maps a framework name to the skill names inside it, each built
    the same way as a pool skill and written into the catalog with a description
    (#39: a framework needs one, discovery reads it and not a tree). `bundles`
    maps a bundle name to the pool skill names its manifest points at. `mcps`
    maps a server slug to its URL — or to one of `STDIO`, `SLOTTED` and `BEARER`
    — written as a recipe in the third discovery root, beside the written file,
    because a recipe never lands. All three are optional and additive, so a call
    that only names pool skills is unaffected.
    """
    content = tmp_path / "packaged" / "content"
    content.mkdir(parents=True, exist_ok=True)
    for name in names:
        _skill(content / "pool" / "skills" / name, name, extra)
    for framework, artifacts in (frameworks or {}).items():
        for artifact_name in artifacts:
            _skill(content / "frameworks" / framework / "skills" / artifact_name, artifact_name, ())
    for slug, url in (mcps or {}).items():
        _recipe(tmp_path / "packaged" / "mcps" / f"{slug}.toml", slug, url)

    written = tmp_path / "packaged" / "catalog.yaml"
    written.write_text(_written(frameworks or {}, bundles or {}), encoding="utf-8")
    monkeypatch.setattr(cli, "content_root", lambda: content)
    monkeypatch.setattr(cli, "catalog_file", lambda: written)
    return content


def _skill(skill: Path, name: str, extra: Sequence[str]) -> None:
    """One skill directory, with the `SKILL.md` frontmatter discovery reads."""
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: The {name} skill.\n---\n\n# {name}\n", encoding="utf-8"
    )
    for relative in extra:
        path = skill / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{name}: {relative}\n", encoding="utf-8")


STDIO = "stdio"
"""What a value in the `mcps` mapping says instead of a URL to get a stdio recipe.

The two transports render differently — stdio is the one that carries an array
and a nested table — so a suite that could only build an HTTP recipe could never
assert on disk what those two look like once written.
"""

SLOTTED = "stdio+slot"
"""A stdio recipe carrying **both** halves of the distinction, like the real one.

`PANEL_URL` is configuration and lands written; `PANEL_TOKEN` is a secret and
lands as a reference. A fixture with only one of the two could not show that a
document holds them side by side.
"""

BEARER = "http+bearer"
"""An HTTP recipe whose secret travels in the header the renderer assembles."""

SLOT_VARIABLE = "PANEL_TOKEN"
"""The variable the slotted fixtures name, so a test can set it or leave it unset."""

OTHER_SLOTTED = "stdio+other-slot"
"""A slotted stdio recipe naming a **different** variable from every other fixture.

`SLOTTED` and `BEARER` share `PANEL_TOKEN`, which is what lets a test assert that
two servers wanting one secret get one prompt. The opposite claim — that a second
secret is *added* beside the first instead of replacing it — cannot be asserted
with fixtures that share a name, so this one exists to carry the other name.
"""

OTHER_SLOT_VARIABLE = "OTHER_TOKEN"
"""The second variable, and the id derived from it differs from the first."""

_BODIES = {
    STDIO: '{stdio}\n[server.env]\nPANEL_URL = "https://panel.example.com"\n',
    SLOTTED: (
        '{stdio}\n[server.env]\nPANEL_URL = "https://panel.example.com"\n\n'
        f'[[slots]]\nname = "{SLOT_VARIABLE}"\nrole = "env"\n'
    ),
    OTHER_SLOTTED: (f'{{stdio}}\n\n[[slots]]\nname = "{OTHER_SLOT_VARIABLE}"\nrole = "env"\n'),
    BEARER: (
        'url = "https://mcp.example.com/mcp"\n\n'
        f'[[slots]]\nname = "{SLOT_VARIABLE}"\nrole = "bearer"\n'
    ),
}
"""One body per kind a value of the `mcps` mapping can name, keyed by that value."""


def _recipe(path: Path, slug: str, kind: str) -> None:
    """One MCP recipe on disk: a kind out of `_BODIES`, or a URL to reach.

    The mapping's value doubles as the selector because a recipe is small enough
    that a second parameter would be a second thing every call site has to say.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    stdio = f'command = "uvx"\nargs = ["{slug}-server", "--repository", "."]\n'
    body = _BODIES.get(kind, f'url = "{kind}"\n').format(stdio=stdio)
    transport = STDIO if kind in {STDIO, SLOTTED, OTHER_SLOTTED} else "http"
    path.write_text(
        f'description = "The {slug} server."\ntransport = "{transport}"\n\n[server]\n{body}',
        encoding="utf-8",
        newline="\n",
    )


def custom_recipe(tmp_path: Path, slug: str, body: str) -> Path:
    """One MCP recipe written verbatim, for a shape `catalog_of`'s canned kinds do not carry.

    `catalog_of` must have run first — this only writes at the path `_recipe`
    already uses, `packaged/mcps/<slug>.toml`, which is how preconditions and
    instructions (issue #82) get tested without a fixture kind per combination
    of check and value.
    """
    path = tmp_path / "packaged" / "mcps" / f"{slug}.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8", newline="\n")
    return path


def _written(frameworks: Mapping[str, Sequence[str]], bundles: Mapping[str, Sequence[str]]) -> str:
    """The written catalog: one description per framework, one manifest per bundle.

    Every string is quoted, which is not decoration: a plain YAML scalar may not
    carry `: `, and a test is free to name a bundle whatever it needs to.
    """
    lines: list[str] = []
    if bundles:
        lines.append("bundles:")
        lines.extend(_bundle_entry(name, items) for name, items in bundles.items())
    if frameworks:
        lines.append("frameworks:")
        lines.extend(f'  {name}:\n    description: "The {name} framework."' for name in frameworks)
    return "\n".join(lines) + "\n" if lines else ""


def _bundle_entry(name: str, items: Sequence[str]) -> str:
    listed = ", ".join(f'"{item}"' for item in items)
    return f'  {name}:\n    description: "The {name} bundle."\n    items: [{listed}]'


def source(content: Path, name: str) -> Path:
    """The directory a pool skill occupies inside the content tree."""
    return content / "pool" / "skills" / name


def target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str = "project") -> Path:
    """An empty directory, made the working directory, the home and a pipe.

    `tmp_path` itself carries a `.git` marker, and `root` is a subdirectory of
    it — a repository with the command run from inside it, the ordinary case
    (https://github.com/panlabs-tech/overpower/issues/40). The marker sits
    *above* `root`, never inside it, so every existing `root.iterdir()`
    assertion keeps seeing exactly what `install` wrote and nothing else. A
    test of the *outside-a-repository* refusal builds its own bare directory
    instead of calling this.
    """
    (tmp_path / ".git").mkdir(exist_ok=True)
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(root)
    _sandboxed(monkeypatch, tmp_path)
    monkeypatch.setattr(cli, "_out", pinned(tty=False))
    return root


def at_home(monkeypatch: pytest.MonkeyPatch, home: Path) -> None:
    """Aim the machine at `home`, with every anchor that could move a path scrubbed.

    The half of `target` a **global-scope** test needs on its own: a run that
    compares two homes moves the home between the two runs and never touches a
    working directory, so it cannot take the whole fixture. Here rather than
    written out at the call site because a hand-rolled copy scrubs whatever
    `ANCHORS` held the day it was written, and `ANCHORS` grows.
    """
    _sandboxed(monkeypatch, home)


def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """A repository and a home that are **different directories**, and the CLI in it.

    `target` puts the two on top of each other — the `.git` marker sits on
    `tmp_path`, which is also `HOME` — and for `install` that costs nothing,
    because one command writes in one scope. `doctor` reads **both scopes in one
    output**, so a home that is also the repository would make every project
    place and its global twin the same directory on disk: the counts double and
    a divergence between them can never exist. Pulling them apart is what makes
    the two halves of the screen separately assertable.

    Answers `(repository, home)`, with the working directory inside the
    repository — the ordinary case, and the one where `install` and `doctor`
    disagree about the root on purpose: `install` writes where you stand,
    `doctor` reads the repository, so that running it from a subdirectory cannot
    answer *"nothing installed"* about a repository that is fully equipped.
    """
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    root = tmp_path / "repo"
    root.mkdir(parents=True, exist_ok=True)
    (root / ".git").mkdir(exist_ok=True)
    monkeypatch.chdir(root)
    _sandboxed(monkeypatch, home)
    monkeypatch.setattr(cli, "_out", pinned(tty=False))
    return root, home


def _sandboxed(monkeypatch: pytest.MonkeyPatch, home: Path) -> None:
    """Point every machine variable the product can read at the sandbox."""
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    for anchor in ANCHORS:
        monkeypatch.delenv(anchor, raising=False)
    # Rich reads `COLUMNS` off the environment mapping it captured at
    # construction, so this pins the width of the error panel, which is the one
    # screen that does not go through the console pinned in `pinned`.
    monkeypatch.setenv("COLUMNS", "100")


def pinned(*, tty: bool) -> Console:
    """The product's stdout console with the `isatty()` answer pinned.

    Not a convenience. Measured in #12 and recorded in `test_cli.py`: rich and
    typer read `FORCE_COLOR`, `PY_COLORS` and `GITHUB_ACTIONS` and force a
    terminal when any of them is set, and both this machine and the CI runner
    set one. An in-process test that left it alone would assert the developer's
    environment instead of the product — and it would put the ASCII banner,
    which is made of `/` and `_`, into the very output the path assertions read.
    The other half of the gate, a real pipe on a real child, lives in
    `test_cli.py`.
    """
    return Console(theme=THEME, width=100, force_terminal=tty, highlight=False)


def terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    """Move the product into a terminal, which is where the confirmation lives."""
    monkeypatch.setattr(cli, "_out", pinned(tty=True))


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str]:
    """The command, in process, with its two streams joined the way a user reads them."""
    code = cli.main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out + captured.err


def joined(output: str) -> str:
    """The output with its frame, its re-wrapping and its styling undone.

    A message is allowed to wrap; the assertion is about what it says, and that
    is only visible after joining the lines back up.

    The styles come off for the same reason and only matter on one path: a test
    that has to run **in a terminal** — the confirmation, the wizard — gets a
    console that emits them, and `skill  fa` arrives there as `ESC[2mskill`,
    `ESC[36mfa`, which is the same text with the answer hidden inside it. On the
    piped console this is a no-op, and the *presence* of ANSI is asserted where
    it belongs, against a real child in `test_cli.py`.
    """
    plain = ANSI.sub("", output)
    lines = [line.strip().strip("│").strip() for line in plain.splitlines()]
    return " ".join(" ".join(line.split()) for line in lines if line)


def paths_in(output: str) -> set[str]:
    """Every path the screen announced."""
    return {match.group(0) for match in PATH.finditer(output)}


def keys_in(output: str) -> set[str]:
    """Every document key the screen named, **and each of its parents**.

    Naming `mcpServers.cloudflare` names `mcpServers` as well: the plan cannot
    write the leaf without the branch, so a document that gained both gained
    nothing the plan did not say. Without that reading the identity would fail on
    the first install into a file that had no `mcpServers` yet — which is the
    ordinary case, not an edge one.

    Both spellings of the separator are accepted for the reason the product has
    two: `›` cannot be encoded in cp1252, which is what a pipe on Windows takes.
    """
    named = {match.group(1) for match in KEY.finditer(output)}
    return {prefix for key in named for prefix in _prefixes(key)}


def parsed(path: Path) -> dict[str, object]:
    """The document as values, for assertions that are about what it *says*.

    Read with the tolerant loader because that is what the file is — `.mcp.json`
    is strict JSON and `.vscode/mcp.json` is JSONC — and a helper that reached
    for `json.loads` would pass on the file this product writes and fail on the
    file a user hands it. It is the same loader `document_keys` uses, and beside
    it for that reason.
    """
    return cast("dict[str, object]", loads(path.read_text(encoding="utf-8")))


def document_keys(path: Path) -> set[str]:
    """Every key of a JSON document, dotted, to the two levels a graft occupies.

    Parsed with the library's own loader rather than with the product's writer:
    a helper built out of `overpower.grafting` could only ever prove the graft
    agrees with itself.
    """
    parsed: object = loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        return set()
    document = cast("dict[str, object]", parsed)
    found = set(document)
    for name, value in document.items():
        if isinstance(value, dict):
            found |= {f"{name}.{key}" for key in cast("dict[str, object]", value)}
    return found


def _prefixes(key: str) -> set[str]:
    parts = key.split(".")
    return {".".join(parts[: index + 1]) for index in range(len(parts))}


def files_under(root: Path) -> set[str]:
    """Every file below `root`, relative and separator-normalised.

    `Path.walk(follow_symlinks=True)`, not `rglob` — a global-scope landing may
    be a symlink, and the whole point of the central identity
    (https://github.com/panlabs-tech/overpower/issues/40) is that content
    reachable *through* one still counts. `rglob`'s own `recurse_symlinks` is
    3.13+ only; `Path.walk` carries the same option since 3.12, which is the
    floor here. A junction needs no opt-in: it is not a symlink
    (`os.path.islink()` is `False` for one), so the walk always descends into
    it regardless of `follow_symlinks`.
    """
    return {
        (base / name).relative_to(root).as_posix()
        for base, _dirs, names in root.walk(follow_symlinks=True)
        for name in names
    }


def landings_of(files: set[str], announced: set[str]) -> set[str]:
    """Each walked file mapped to the announced path it landed under, or to itself.

    This is what makes the disk half of the identity a **walk** rather than a
    lookup. Nothing here knows what was asked for: a file that landed under no
    announced path maps to *itself* and therefore cannot disappear into the
    comparison, and an announced path that received nothing is simply absent
    from the result. Comparing this against the announced set closes both
    directions of the measured `npx skills` defect at once — a path announced
    and never written, and a path written and never announced.
    """
    return {next((named for named in announced if path.startswith(named)), path) for path in files}
