"""Provisional entry point for the 0.0.x series — pipeline proof, not product.

This module exists so that `uvx overpower` answers something *verifiable* after
an install. It reports four things that only a real execution can answer:

- the **version** that arrived, read from installed metadata rather than from a
  constant, which proves the `dist-info` travelled intact;
- the **interpreter** uv picked, with its path — the path is what reveals
  whether uv had to *download* a Python, which comes from `releases.astral.sh`
  and not from the package index, a second egress the packaging research never
  covered;
- the **platform**, because the corporate machine is Windows;
- the **payload**, when present: size and digest, which is the proof that heavy
  content crossed a proxy without truncation.

The real command surface is decided in
https://github.com/panlabs-tech/overpower/issues/8 and is born in v0.1.0. There
is deliberately no argument parsing here: every invocation prints the same
report and exits 0, so that `overpower`, `overpower --version` and
`uvx overpower@latest` are all usable as a smoke test.
"""

from __future__ import annotations

import hashlib
import platform
import sys
from importlib import metadata, resources

from rich.console import Console

_PAYLOAD = ("_payload", "probe.bin")

# Every byte the product writes leaves through a `rich.Console`, and never
# through `print` — `T201` is enabled precisely to keep that true. The reason is
# testability rather than looks: the snapshot doctrine records
# `Console(record=True).export_text()`, so an output path that bypasses the
# console is an output path no snapshot can see.
# https://github.com/panlabs-tech/overpower/issues/30
#
# `soft_wrap=True` is not cosmetic either. Measured at 60 columns without it,
# rich hard-wraps the interpreter path mid-word (`…/bin/py` + `thon3`), and that
# path is the whole point of the line: it is what reveals whether uv had to
# *download* a Python, from `releases.astral.sh` and not from the package index.
# A report is not a screen; it hands the terminal the exact string.
_console = Console(markup=False, highlight=False, soft_wrap=True)


def _version() -> str:
    try:
        return metadata.version("overpower")
    except metadata.PackageNotFoundError:
        return "uninstalled (running from source)"


def _payload() -> str:
    # `importlib.resources`, never a filesystem path: it is the only access that
    # behaves the same way installed on disk and installed inside a zip.
    node = resources.files("overpower")
    for part in _PAYLOAD:
        node = node / part
    if not node.is_file():
        return "absent (built without a probe)"
    data = node.read_bytes()
    return f"{len(data)} bytes · sha256 {hashlib.sha256(data).hexdigest()[:16]}"


def main() -> int:
    """Print the four facts only a real execution can answer, and exit 0."""
    impl = platform.python_implementation()
    _console.print(f"overpower {_version()}")
    _console.print(f"python    {impl} {platform.python_version()} · {sys.platform}")
    _console.print(f"exe       {sys.executable}")
    _console.print(f"payload   {_payload()}")
    return 0
