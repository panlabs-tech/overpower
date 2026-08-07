"""The one gate in the suite, and it guards the network — nothing else.

The disk is never gated: it is not a service the dev brings up by hand, so
`tmp_path` runs everywhere, always (ADR 0010). GitHub *is* a third party, and
"a gate blocks what this repository controls; what depends on a third party is
an act of curation, not automation" is the rule this file implements.

The key is our own and named after the scenario, never the generic `CI` that
every runner sets: with the variable on, the skip condition can no longer be
satisfied, so a network test that gets renamed or lost turns red instead of
disappearing in silence.
"""

from __future__ import annotations

import os

import pytest

_REQUIRE = os.getenv("OVERPOWER_NETWORK_TESTS") == "1"

needs_network = pytest.mark.skipif(
    not _REQUIRE,
    reason="talks to GitHub: set OVERPOWER_NETWORK_TESTS=1 (curation step, never a gate)",
)
"""Marks a test that reaches the real GitHub. Runs in curation, in no CI job."""
