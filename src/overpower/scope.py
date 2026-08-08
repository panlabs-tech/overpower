"""Whether `cwd` is inside a git repository — the one fact the default scope needs.

Axiom 2 — *"the git is the manifest"* — only holds where there is git. Inside a
repository, a wrong scope costs a `git checkout` and `git status` says so; outside
one, nothing on the machine audits what `install` wrote. That is the whole reason
the default scope is conditional rather than always-project: `overpower.cli`
reads `git_root` and, finding none, refuses instead of guessing
(https://github.com/panlabs-tech/overpower/issues/40).

**A walk-up, not a subprocess.** `git rev-parse --show-toplevel` would answer the
same question, but at the cost the transport-versus-installer line of axiom 1
exists to police: a question asked of a third-party binary is still a dependency
on it being installed, and the plain filesystem check has none. Presence of
`.git` is all the decision needs — not its contents — so a directory (an ordinary
repository) and a file (`gitdir: ...`, a worktree or a submodule) both count.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def git_root(cwd: Path) -> Path | None:
    """The nearest ancestor of `cwd` carrying a `.git`, or `None` outside any repository."""
    for candidate in (cwd, *cwd.parents):
        if (candidate / ".git").exists():
            return candidate
    return None
