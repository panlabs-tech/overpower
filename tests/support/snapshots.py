"""The snapshot comparator: one file per screen, updated only when asked.

No plugin, and that is a decision rather than an omission
(https://github.com/panlabs-tech/overpower/issues/30): one dev dependency fewer,
and the update path stays an explicit command instead of a reflex.

    uv run pytest --snapshot-update tests/test_screens.py

**One file per screen, never one per session.** Measured against the real
captures of the prototype: the four aesthetic tweaks of round 2 moved 49% of the
lines of a whole-session snapshot at 80 columns and 52% at 60, while a single
redrawn screen moved 17%. Half a changed snapshot is a diff nobody reads, and an
unintended regression travelling inside those 49% is invisible. At one file per
screen the same rework would have touched four files and left the rest at 0%,
and the reviewer sees exactly which screens the change had licence to move.
"""

from __future__ import annotations

from pathlib import Path

import pytest

SNAPSHOT_DIR = Path(__file__).parent.parent / "snapshots"
"""`tests/snapshots/`. Created on first write; an empty directory says nothing."""


def assert_matches_snapshot(request: pytest.FixtureRequest, name: str, rendered: str) -> None:
    """Compare `rendered` against `tests/snapshots/<name>.txt`.

    With `--snapshot-update` the file is written instead of read, and the test
    still fails when it had to be created — a snapshot that is born green is a
    snapshot nobody looked at.
    """
    path = SNAPSHOT_DIR / f"{name}.txt"
    updating = bool(request.config.getoption("--snapshot-update"))

    if updating:
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        previous = path.read_text(encoding="utf-8") if path.exists() else None
        path.write_text(rendered, encoding="utf-8", newline="\n")
        if previous != rendered:
            pytest.fail(f"snapshot {name} rewritten; re-run without --snapshot-update to assert")
        return

    if not path.exists():
        pytest.fail(f"no snapshot for {name}: run `uv run pytest --snapshot-update` and read it")

    expected = path.read_text(encoding="utf-8")
    assert rendered == expected, f"screen {name} changed; read the diff, then --snapshot-update"
