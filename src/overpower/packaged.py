"""Where the two sibling roots live inside the package.

They are siblings with **opposite invariants**, and that is the whole reason
they are two (https://github.com/ThiagoPanini/overpower/issues/11):

- `content/` **100% lands** in the user's repository — the frameworks and the
  pool. P1 and P2 guard it, because content lost is lost *silently*: half a
  skill lands and nobody notices;
- `catalog/` **0% lands** — one written file, the bundles and one description
  line per AI Framework. It has no gate on purpose, because losing it fails
  loudly: the bundle disappears from `list` and `install` answers that it does
  not know the name.

Nothing here decides *what* is inside either root. The tree is the catalog
(ADR 0006), so the answer to that question is a walk, in `overpower.discovery`.
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path

from overpower.errors import OverpowerError

CONTENT_DIR = "content"
"""The root that lands whole."""

CATALOG_DIR = "catalog"
"""The root that never lands."""

CATALOG_FILE = "catalog.yaml"
"""The one file in it, and the format is the reader's rather than this module's.

It was `catalog.toml` until https://github.com/ThiagoPanini/overpower/issues/136
moved it, so that the manifest a homemade repository federates goes through the
same reader as this one. The recipe of an MCP server, which lives in the sibling
directory, stayed TOML.
"""


def content_root() -> Path:
    """The vendored content tree that ships inside the package."""
    return _packaged(CONTENT_DIR)


def catalog_file() -> Path:
    """The one written file that ships inside the package."""
    return _packaged(CATALOG_DIR) / CATALOG_FILE


def _packaged(name: str) -> Path:
    """A directory that ships inside the package, as a real path on disk.

    `importlib.resources` is the access that behaves the same installed on disk
    and installed inside a zip — but the product *copies trees* out of this one,
    so a zip import could not serve it anyway. The check is here so that case
    names itself instead of failing later against a path that does not exist.
    """
    node = resources.files("overpower") / name
    if not isinstance(node, Path):  # pragma: no cover — a wheel on disk is a Path
        message = f"the overpower package has to be unpacked on disk; got {node!r}"
        raise OverpowerError(message)
    return node
