"""The one write boundary: it executes the plan and reads nothing else.

Every byte the overpower puts in a target passes through here, and the input is
a `Plan` — not a request, not a catalog, not a runtime table. A writer that
recomputed a path could diverge from the screen by construction, and the
three-way identity would have nothing left to assert.

**The write is unconditional.** Reinstalling overwrites: no byte comparison, no
provenance heuristic, no backup, no *"generated"* marker in the target. Running
twice writes again and exits 0 without asking anything, and in a project the
overpower does not even call `git status` — in CI the tree is dirty all the
time, and a warning nobody can act on is noise. The accepted, explicit price: in
a project, an uncommitted edit over an artifact dies in silence.

**There is no rollback.** Rolling back writes, and the failure that triggers it
is the same one that would make it fail; measured, `os.replace` over a non-empty
directory gives `ENOTEMPTY`, so atomic staging does not exist for a directory.
Half an installation is a diagnosis instead: *"wrote 14 of 22, stopped here,
disk full"* is actionable, and that sentence is `WriteFailedError`.

Three mechanical traps are mandatory, not optional, and every write path
exercises them (https://github.com/panlabs-tech/overpower/issues/9 and
https://github.com/panlabs-tech/overpower/issues/19):

1. `rmtree(ignore_errors=True)` over a symlink **removes nothing and says
   nothing**, and the `copytree` that follows writes *through* the link,
   corrupting the target. So the link is detached first, and no removal here is
   allowed to fail quietly;
2. `os.path.islink()` answers **`False`** for a junction and `shutil.rmtree()`
   refuses it anyway — the idiomatic `if islink: unlink else: rmtree` breaks on
   Windows. `points_elsewhere` is the predicate that recognises **either**
   before detaching;
3. `dirs_exist_ok=True` overlays without syncing, so yesterday's file survives
   and reads as installed. The destination has to end up **equal** to the
   source, not overlaid on it, which is what binds this module to the identity.

Plus `symlinks=True` on the `copytree`, or a link inside the skill arrives
dereferenced as a second copy.
"""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

from overpower.errors import OverpowerError
from overpower.planning import DirectoryTree, DocumentKey, WriteMode

if TYPE_CHECKING:
    from pathlib import Path

    from overpower.planning import Destination, Plan, Write


@dataclass(frozen=True)
class Report:
    """What the run actually put on disk."""

    writes: int
    files: int


class WriteFailedError(OverpowerError):
    """The write stopped in the middle, and the message is the report.

    It names how far it got, where it stopped and what the operating system
    said, because those three together are what makes half an installation
    something a person can act on.
    """

    def __init__(self, done: int, total: int, where: Path, cause: OSError) -> None:
        """Name what was written, where it stopped and why."""
        self.done = done
        self.total = total
        self.where = where
        super().__init__(f"wrote {done} of {total}, stopped at {where}: {cause}")


class UnsupportedWriteError(OverpowerError):
    """The plan asks for an operation this version does not have.

    Two axes reach here, and both are open by design rather than by oversight: a
    destination that is a **document and a key** — the graft class, which joins
    in v0.2 — and a mode that is **link or junction**, which is how the global
    scope lands. Refusing by name is the trigger; answering with a copy would be
    the silent wrong answer this product exists to avoid.
    """

    def __init__(self, destination: Destination, mode: WriteMode) -> None:
        """Name both halves of the operation that has no implementation."""
        self.destination = destination
        self.mode = mode
        form = "a document key" if isinstance(destination, DocumentKey) else "a directory tree"
        super().__init__(f"no operation for {mode} into {form}: {destination.path}")


def execute(plan: Plan) -> Report:
    """Perform every write of `plan`, in order, and say what landed.

    A failure leaves what was already written and reports where it stopped —
    there is no rollback, and the reasoning is in the module docstring.
    """
    writes = plan.writes
    done = 0
    files = 0
    for write in writes:
        try:
            _perform(write)
        except OSError as failure:
            # `.path` on either form of destination: both of them occupy one,
            # and which one it is does not change what the report has to name.
            raise WriteFailedError(done, len(writes), write.destination.path, failure) from failure
        done += 1
        files += write.files
    return Report(writes=done, files=files)


def points_elsewhere(path: Path) -> bool:
    """Whether `path` is a link or a junction — the predicate trap 2 is about.

    `os.path.islink()` alone is not it: it answers `False` for a Windows
    junction, and `shutil.rmtree()` refuses the junction anyway, so the
    idiomatic pair breaks exactly where nobody develops.
    """
    return path.is_symlink() or os.path.isjunction(path)


def _perform(write: Write) -> None:
    """One write, dispatched on the *form of the destination* before the mode.

    The form comes first because that is the axis the graft lock is about: a
    flow that read the mode first would have already assumed the destination is
    a folder.
    """
    match write.destination, write.mode:
        case DirectoryTree(path), WriteMode.COPY:
            _land_tree(write.source, path)
        case destination, mode:
            raise UnsupportedWriteError(destination, mode)


def _land_tree(source: Path, destination: Path) -> None:
    """Make `destination` **equal** to `source`, never overlaid on it."""
    _clear(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # `symlinks=True`, or a link inside the skill arrives dereferenced as a
    # second copy. No `dirs_exist_ok`: the destination was just cleared, and
    # overlaying is trap 3.
    shutil.copytree(source, destination, symlinks=True)


def _clear(path: Path) -> None:
    """Take whatever is at `path` out of the way, without ever following a link.

    Nothing here ignores an error. `rmtree(ignore_errors=True)` is what makes
    trap 1 silent, and a removal that failed has to become the failure report
    rather than a corrupted target.
    """
    if points_elsewhere(path):
        _detach(path)
        return
    if path.is_dir():
        shutil.rmtree(path)
        return
    if path.exists():
        path.unlink()


def _detach(path: Path) -> None:
    """Remove the link itself, never what it points at.

    On POSIX `unlink` is the only call that removes the link instead of
    following it. On Windows a junction — and a symlink to a directory — is a
    *directory* carrying a reparse point: `unlink` refuses it and `rmdir`
    detaches it without recursing into the target, while a *file* symlink is the
    other way round and `NotADirectoryError` is how it says so.
    """
    if sys.platform != "win32":
        path.unlink()
        return
    try:
        path.rmdir()
    except NotADirectoryError:
        path.unlink()
