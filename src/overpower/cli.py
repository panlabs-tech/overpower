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

_PAYLOAD = ("_payload", "probe.bin")


def _version() -> str:
    try:
        return metadata.version("overpower")
    except metadata.PackageNotFoundError:
        return "desinstalado (rodando do fonte)"


def _payload() -> str:
    # `importlib.resources`, never a filesystem path: it is the only access that
    # behaves the same way installed on disk and installed inside a zip.
    node = resources.files("overpower")
    for part in _PAYLOAD:
        node = node / part
    if not node.is_file():
        return "ausente (build sem probe)"
    data = node.read_bytes()
    return f"{len(data)} bytes · sha256 {hashlib.sha256(data).hexdigest()[:16]}"


def main() -> int:
    impl = platform.python_implementation()
    print(f"overpower {_version()}")
    print(f"python    {impl} {platform.python_version()} · {sys.platform}")
    print(f"exe       {sys.executable}")
    print(f"payload   {_payload()}")
    return 0
