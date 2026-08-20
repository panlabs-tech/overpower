"""A real `git` remote, built on disk, so the fetch path runs without a network.

The doctrine cuts the `--from` path in one place and one only: **the subprocess
runs; the network does not**
(https://github.com/ThiagoPanini/overpower/issues/30). Everything the primary
obtention path is worth asserting survives that cut, measured against a local
repository standing in for the remote:

| requested ref  | rc  | result                                          |
| -------------- | --- | ----------------------------------------------- |
| branch (`main`)| 0   | found                                           |
| tag (`v1.0.0`) | 0   | found                                           |
| full SHA       | 0   | found                                           |
| missing ref    | 128 | `fatal: couldn't find remote ref nope`          |
| missing remote | 128 | `fatal: … does not appear to be a git repository` |

The branch/tag/SHA row is the discriminator that made `init` + `fetch` win over
`clone --branch`, which cannot take a SHA — and it is exercisable with no
network at all. The `couldn't find remote ref` string comes out identical here
and against the real GitHub.

**The honest limit**, because a local remote does not cover it: fetching an
arbitrary SHA depends on the *server* allowing it. `allow_any_sha` below turns
that on so the local remote behaves like GitHub, but that GitHub does behave
this way was measured in https://github.com/ThiagoPanini/overpower/issues/25,
not here.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

from overpower import remote

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence
    from pathlib import Path

# `git` is invoked by name and without a shell. `S603`/`S607` want an absolute
# path; resolving one would pin the test to the machine that wrote it, and the
# product has the same argv shape, so the exemption is stated once, here.
_GIT = "git"

_DETERMINISTIC = {
    "GIT_AUTHOR_NAME": "overpower tests",
    "GIT_AUTHOR_EMAIL": "tests@overpower.invalid",
    "GIT_COMMITTER_NAME": "overpower tests",
    "GIT_COMMITTER_EMAIL": "tests@overpower.invalid",
    # The stderr of a failed fetch is asserted by content, so the locale that
    # produces it cannot be the one the developer happens to have.
    "LC_ALL": "C",
}


@dataclass(frozen=True)
class LocalRemote:
    """A git repository on disk, usable as the `origin` of a fetch."""

    path: Path
    branch: str
    head: str
    tag: str | None

    @property
    def url(self) -> str:
        """What goes into `git remote add origin <url>`."""
        return str(self.path)


def git(
    *args: str,
    cwd: Path,
    env: Mapping[str, str] | None = None,
    stdin: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run `git` under a deterministic identity, the C locale and no user config.

    The process environment is inherited and then overridden, never replaced: a
    child with no `PATH` cannot find `git` at all on Windows, and on POSIX it
    falls back to `os.defpath` — so a replaced environment is a helper that
    works on some cells of the matrix and not others.

    What is scrubbed instead is git's own configuration. `GIT_CONFIG_GLOBAL`
    points at a path that will not exist and `GIT_CONFIG_NOSYSTEM` turns the
    system file off, so the developer's `~/.gitconfig` cannot decide what a
    fixture ends up looking like. That is not hygiene in the abstract:
    `core.symlinks=false` set there produces a *differently* broken checkout,
    measured, and it is exactly the value one test builds on purpose — a caller
    that wants it passes it back through `env`.

    `stdin` is what a plumbing call needs: `git hash-object --stdin` takes the
    blob's bytes from the pipe and writes no trailing newline of its own.
    """
    scrubbed = {
        "GIT_CONFIG_GLOBAL": str(cwd / ".absent-gitconfig"),
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    return subprocess.run(  # noqa: S603 - fixed argv, no shell; see _GIT above
        [_GIT, *args],
        cwd=cwd,
        env={**os.environ, **_DETERMINISTIC, **scrubbed, **(env or {})},
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )


def build(
    root: Path,
    files: Mapping[str, str],
    *,
    branch: str = "main",
    tag: str | None = None,
    allow_any_sha: bool = True,
) -> LocalRemote:
    """Create a repository under `root` containing `files`, and return its refs.

    `files` maps a repository-relative path to its content, so a caller writes
    `{"skills/wayfinder/SKILL.md": "..."}` and gets a tree the discovery walk can
    be pointed at.
    """
    root.mkdir(parents=True, exist_ok=True)
    _must(git("init", "-b", branch, cwd=root))
    if allow_any_sha:
        _must(git("config", "uploadpack.allowAnySHA1InWant", "true", cwd=root))

    for relative, content in files.items():
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8", newline="\n")

    _must(git("add", "-A", cwd=root))
    _must(git("commit", "-m", "seed", cwd=root))
    if tag is not None:
        _must(git("tag", tag, cwd=root))

    head = _must(git("rev-parse", "HEAD", cwd=root)).stdout.strip()
    return LocalRemote(path=root, branch=branch, head=head, tag=tag)


def _must(result: subprocess.CompletedProcess[str]) -> subprocess.CompletedProcess[str]:
    """Fail the test where the remote is built, not where it is used."""
    if result.returncode != 0:
        message = f"building the local remote failed ({result.returncode}): {result.stderr}"
        raise RuntimeError(message)
    return result


def skill_files(*names: str, under: str = "skills") -> dict[str, str]:
    """A repository tree carrying one `SKILL.md` per name, at `<under>/<name>/`.

    The same mapping `build` takes, so a tree can be committed into a local
    remote or planted directly by `planting` without either side knowing which
    one the test chose.
    """
    return {
        f"{under}/{name}/SKILL.md": (
            f"---\nname: {name}\ndescription: The {name} skill.\n---\n\n# {name}\n"
        )
        for name in names
    }


def installed_skill_files(*names: str, runtime: str = ".claude/skills") -> dict[str, str]:
    """The *copy* an install leaves behind, at a runtime's own project destination.

    The same shape `skill_files` writes, named apart because the difference is
    not in the bytes: `skills/<name>/` is what a repository **offers**, and
    `<runtime destination>/<name>/` is where an install **put** one. A
    repository equipped with the overpower has both, and telling them apart is
    what keeps the showcase from counting one skill as two and the reach from
    refusing it as ambiguous.

    `runtime` defaults to Claude Code's `project_dir` because that is the row
    the defect was measured on; any other value from `overpower.runtimes`
    behaves the same way.
    """
    return skill_files(*names, under=runtime)


def mcp_recipe_files(*names: str, under: str = ".overpower/mcp") -> dict[str, str]:
    """A repository tree carrying one minimal recipe per name, at `<under>/<name>.toml`.

    The same mapping `build` and `planting` take, and the same convention path
    `overpower.remote._mcp_called` searches — `.overpower/mcp/<slug>.toml`
    (`docs/agents/domain.md` § Vocabulário).
    """
    return {
        f"{under}/{name}.toml": (
            f'description = "The {name} MCP server."\n'
            'transport = "stdio"\n\n'
            "[server]\n"
            f'command = "{name}"\n'
        )
        for name in names
    }


def bundle_catalog_file(
    bundles: Mapping[str, Sequence[str]], *, at: str = ".overpower/catalog.yaml"
) -> dict[str, str]:
    """A repository tree carrying `.overpower/catalog.yaml`, one entry per bundle.

    Sibling of `mcp_recipe_files`, one directory up and in the other format:
    `.overpower/` is a namespace rather than a format (ADR 0020), and the two
    functions are what makes a test say so without prose. The same mapping
    `build` and `planting` take, so it composes —
    `{**skill_files("alpha"), **bundle_catalog_file({"api": ["alpha"]})}` is a
    repository that offers a skill and declares a bundle naming it.

    `at` is a parameter for one reason: the manifest is read from the repository
    **root** and nowhere else, and a test of that anchor has to be able to plant
    one somewhere else and watch it be ignored.
    """
    lines = ["bundles:"]
    for name, items in bundles.items():
        lines.append(f"  {name}:")
        lines.append(f'    description: "The {name} bundle."')
        lines.append("    items:")
        lines.extend(f"      - {item}" for item in items)
    return {at: "\n".join(lines) + "\n"}


def offering(*skills: str, bundles: Mapping[str, Sequence[str]] | None = None) -> dict[str, str]:
    """A repository that offers `skills` under `skills/` and composes them in `bundles`.

    The two halves a federated bundle needs, in the one shape `build` and
    `planting` take. It exists because `items` resolve against the **enumerated**
    skills of the same repository, so a manifest and the skills it names are not
    two independent fixtures — a test that planted only one of them would be
    describing a repository the product refuses.
    """
    planted = dict(skill_files(*skills))
    if bundles is not None:
        planted.update(bundle_catalog_file(bundles))
    return planted


def instead_of_github(local: LocalRemote) -> Callable[[str, str, Path], Path]:
    """The product's own primary obtention, aimed at `local` instead of GitHub.

    Not a double of the fetch: it **is** `overpower.remote.fetch_with_git`, with
    the one argument that cannot be a local path — the URL — replaced. That is
    what keeps the subprocess, the argv, the `LC_ALL=C` guard and the `exit 128`
    classification real while the network stays out of the gate
    (`docs/agents/testing.md`, §3).
    """

    # Bound now, not at call time: the caller's next move is to monkeypatch this
    # very name, and a late lookup would find the replacement and recurse.
    real = remote.fetch_with_git

    def fetch(_url: str, ref: str, into: Path) -> Path:
        return real(local.url, ref, into)

    return fetch


def planting(files: Mapping[str, str]) -> Callable[[str, str, Path], Path]:
    """An obtainer that succeeds, landing `files` where the search will look.

    This is the one double the doctrine's table sanctions on this path — *"decidir
    cair no fallback: **stub** do obtentor, devolvendo o desfecho"*. It stands in
    for the outcome of an obtention, never for its mechanism, which is what
    `instead_of_github` keeps real.
    """

    def fetch(_url: str, _ref: str, into: Path) -> Path:
        for relative, content in files.items():
            destination = into / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8", newline="\n")
        return into

    return fetch


def refusing(reason: str) -> Callable[..., Path]:
    """An obtainer that fails the way a transport fails, carrying `reason`."""

    def fetch(*_args: object, **_kwargs: object) -> Path:
        raise remote.ObtentionError(reason)

    return fetch
