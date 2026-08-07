"""Options the suite adds to pytest.

`pytest_addoption` is only honoured in an initial conftest, which this one is
because `testpaths = ["tests"]` puts it on the collection root.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Declare `--snapshot-update`.

    Rewriting a recorded screen is a deliberate act, never a side effect of a
    green run: the flag is the whole update path decided in
    https://github.com/panlabs-tech/overpower/issues/30, and it exists instead of
    a snapshot plugin.
    """
    parser.addoption(
        "--snapshot-update",
        action="store_true",
        default=False,
        help="rewrite the recorded screens under tests/snapshots/ instead of asserting them",
    )
