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
exercises them (https://github.com/ThiagoPanini/overpower/issues/9 and
https://github.com/ThiagoPanini/overpower/issues/19):

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

**Global scope climbs a ladder** (https://github.com/ThiagoPanini/overpower/issues/40):
a `WriteMode.LINK` or `WriteMode.JUNCTION` write points at the canonical
landing's *destination*, which by plan order has already been written as a real
copy by the time a link write runs. Either rung can fail — a filesystem with no
reparse points, a network share a junction cannot cross, a Windows audit hook
blocking `_winapi.CreateJunction` — and the fallback is the same one #9 already
decided for a collision it could not resolve: land a real copy instead, and say
so. Falling back is a warning at exit 0, never a failure: the content is on
disk either way, and what changed is only which of the three modes carries it.
"""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, cast

from overpower.errors import OverpowerError
from overpower.grafting import EMPTY_DOCUMENT, grafted, read_document, write_document
from overpower.planning import DirectoryTree, DocumentKey, WriteMode
from overpower.rendering import Fragment, Inputs

if TYPE_CHECKING:
    from collections.abc import Callable

    from overpower.planning import Destination, Plan, Write
    from overpower.rendering import Graft


@dataclass(frozen=True)
class Report:
    """What the run actually put on disk."""

    writes: int
    files: int
    degraded: tuple[Path, ...] = ()
    """Destinations planned as a link or a junction that landed as a copy instead.

    Empty on the happy path. Non-empty is not a failure — the content is intact
    at every one of these paths — it is what earns the warning `overpower.cli`
    prints after a successful install.
    """


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
    """The plan asks for an operation this dispatch has no branch for.

    Both operations exist now — a tree that is copied and a key that is grafted
    — so what reaches here is a **pair that does not go together**: a document
    key asked for by copy, a folder asked for by graft, or a graft whose origin
    is a path instead of a rendered fragment. Refusing by name is the trigger;
    answering with a copy would be the silent wrong answer this product exists
    to avoid.
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

    **`done` and what the report says are two different counts**, and the split
    is the point rather than an accident. `done` counts operations performed, so
    the partial-failure message means *"this many of the operations I was going
    to do"* and its denominator is the same list. The report counts what the
    reader can see afterwards, and for a graft those disagree: a server and the
    prompt it refers to are two operations and — by #75, *because they land in
    the same place* — **one write**, and however many servers reach one document
    it is **one file**.

    The file count deduplicates across the whole plan and not inside a landing,
    because a landing is built per selection and cannot see the others: three
    servers asked for in one line are three landings on one `.vscode/mcp.json`,
    and the second and third are exactly the *"second graft into the same one"*
    the count promises to answer zero for.
    """
    total = len(plan.writes)
    done = 0
    written = 0
    files = 0
    grafted: set[Path] = set()
    degraded: list[Path] = []
    for landing in plan.landings:
        for index, write in enumerate(landing.writes):
            try:
                landed = _perform(write)
            except OSError as failure:
                # `.path` on either form of destination: both of them occupy one,
                # and which one it is does not change what the report has to name.
                raise WriteFailedError(done, total, write.destination.path, failure) from failure
            if landed is not write.mode:
                degraded.append(write.destination.path)
            done += 1
            if write.mode is not WriteMode.GRAFT:
                written += 1
                files += write.files
                continue
            written += 1 if index == 0 else 0
            path = write.destination.path
            files += 1 if path not in grafted else 0
            grafted.add(path)
    return Report(writes=written, files=files, degraded=tuple(degraded))


def points_elsewhere(path: Path) -> bool:
    """Whether `path` is a link or a junction — the predicate trap 2 is about.

    `os.path.islink()` alone is not it: it answers `False` for a Windows
    junction, and `shutil.rmtree()` refuses the junction anyway, so the
    idiomatic pair breaks exactly where nobody develops.
    """
    return path.is_symlink() or os.path.isjunction(path)


def _perform(write: Write) -> WriteMode:
    """One write, dispatched on the *form of the destination* before the mode.

    The form comes first because that is the axis the graft lock is about: a
    flow that read the mode first would have already assumed the destination is
    a folder.

    Returns the mode that actually landed, which is `write.mode` on the happy
    path and `WriteMode.COPY` wherever a link or a junction degraded.
    """
    match write.destination, write.mode, write.source:
        case DirectoryTree(path), WriteMode.COPY, Path() as origin:
            _land_tree(origin, path)
            return write.mode
        case DirectoryTree(path), WriteMode.LINK, Path() as origin:
            return _land_link(origin, path)
        case DirectoryTree(path), WriteMode.JUNCTION, Path() as origin:
            return _land_junction(origin, path)
        case DocumentKey(path), WriteMode.GRAFT, (Fragment() | Inputs()) as graft:
            _land_graft(graft, path)
            return WriteMode.GRAFT
        case destination, mode, _:
            raise UnsupportedWriteError(destination, mode)


def _land_tree(source: Path, destination: Path) -> None:
    """Make `destination` **equal** to `source`, never overlaid on it."""
    _clear(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # `symlinks=True`, or a link inside the skill arrives dereferenced as a
    # second copy. No `dirs_exist_ok`: the destination was just cleared, and
    # overlaying is trap 3.
    shutil.copytree(source, destination, symlinks=True)


def _land_graft(graft: Graft, destination: Path) -> None:
    """Put one key into a document, and leave every other byte of it alone.

    Read, splice, write — never serialise. The whole argument is ADR 0016 and
    the mechanics are `overpower.grafting`; what belongs here is that the graft
    is a **branch of the one write boundary** and not a second writer, so the
    plan is still the only thing that decides what lands.

    One graft and not one recipe, which is what lets a recipe be two of them: a
    VS Code slot lands the server and the prompt it points at under two root keys
    of the same document, so the file is read and written twice and the second
    pass reads what the first one wrote — the same path two servers on one line
    already take.

    A document that is not there yet is created; a document that is there and
    does not parse was already refused before the first byte
    (`overpower.planning.broken_documents`), and refused again here if it ever
    reached this far.
    """
    text = read_document(destination) if destination.is_file() else EMPTY_DOCUMENT
    write_document(destination, grafted(destination, text, graft))


def _land_link(source: Path, destination: Path) -> WriteMode:
    """Point `destination` at `source` with a relative symlink, or copy if it fails.

    Relative, not absolute: `os.path.relpath` is what lets the link survive
    `$HOME` moving and the machine cloning to another one. The failure this
    catches is real but not reproducible on demand — a FAT32 or exFAT target, a
    network share, PyPy without `os.symlink` parity — so it is a plain `OSError`
    around one call, exercised in the suite with a narrow stub rather than a
    fabricated filesystem (ADR 0010 rules out the latter).
    """
    _clear(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    target = os.path.relpath(source, destination.parent)
    try:
        destination.symlink_to(target, target_is_directory=True)
    except OSError:
        _land_tree(source, destination)
        return WriteMode.COPY
    return WriteMode.LINK


def _land_junction(source: Path, destination: Path) -> WriteMode:
    """Point `destination` at `source` with a junction, or copy if it fails.

    No privilege probe first: measured in
    https://github.com/ThiagoPanini/overpower/issues/19, a junction works with
    or without `SeCreateSymbolicLinkPrivilege` — there is no rung to choose, only
    one to attempt. The catch is broad on purpose: an audit hook on
    `_winapi.CreateJunction` can raise from outside the `OSError` hierarchy, and
    the correct response to *that* is the same fallback as to `FileNotFoundError`
    on a missing volume — land a real copy and say so, never crash an install
    over the one write that could not take the fast path.
    """
    _clear(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        _create_junction(source, destination)
    except Exception:  # noqa: BLE001 — see the docstring: an audit hook is not an OSError
        _land_tree(source, destination)
        return WriteMode.COPY
    return WriteMode.JUNCTION


def _create_junction(source: Path, destination: Path) -> None:
    """`_winapi.CreateJunction(str, str)` — Windows only, imported only when run there.

    Two guards this API does not carry itself, measured in #19: it accepts
    `Path` nowhere (`str` or `TypeError`), and it accepts a *file* as `source`
    and creates an unusable junction in silence. Both are this function's job,
    not the caller's.
    """
    if not source.is_dir():
        message = f"junction source is not a directory: {source}"
        raise NotADirectoryError(message)
    import _winapi  # noqa: PLC0415 — Windows-only builtin, reached only on that platform

    create_junction = cast(
        "Callable[[str, str], None]",
        _winapi.CreateJunction,  # pyright: ignore[reportAttributeAccessIssue,reportUnknownMemberType]
    )
    create_junction(str(source), str(destination))


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
