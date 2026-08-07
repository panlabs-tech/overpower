"""The only file the overpower writes about its own content.

Sibling of the content root, with the opposite invariant: `content/` **100%
lands** in the user's repository, this root **0% lands**. The rule that decides
what may appear here holds forever, and it is ADR 0006:

    what the overpower writes only carries what the tree cannot know.
    A path, never.

Two things qualify in v0.1.0 — **bundles**, which by definition have no tree,
and **one description line per AI Framework**, because a framework is a folder
of artifacts with no frontmatter of its own. There is no skill entry, no command
entry, no agent entry and no path: those are discovered by walking the tree
(`overpower.discovery`).

**The decoder returns `object`, and that is a tripwire rather than a style.**
Measured in https://github.com/panlabs-tech/overpower/issues/2: pyright strict
has a blind spot on `Any`, so `return data["name"]` inside a `-> str` function
type-checks and blows up at runtime. `tomllib.load` hands back `dict[str, Any]`,
so the decode is confined to `_loads` below — which declares `object` — and every
field is narrowed in the open, where all three checkers can see it. It is the
same discipline `pyproject.toml` bans `json.load` to enforce.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from overpower.errors import OverpowerError

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


@dataclass(frozen=True)
class WrittenBundle:
    """A bundle as written down: a name, a description and the names it points at.

    It carries no content of its own — a bundle is a manifest over pool
    artifacts — so weighing one means resolving the names, which is
    `overpower.discovery`'s job and not this module's.
    """

    name: str
    description: str
    items: tuple[str, ...]


@dataclass(frozen=True)
class WrittenCatalog:
    """Everything the tree cannot know, and nothing else."""

    bundles: tuple[WrittenBundle, ...]
    frameworks: Mapping[str, str]
    """Framework name to its one description line."""


class MalformedWrittenCatalogError(OverpowerError):
    """The written file parsed as TOML but is not shaped like a catalog."""

    def __init__(self, path: Path, key: str, expected: str) -> None:
        """Name the file and the key, so the fix is one edit away."""
        self.path = path
        self.key = key
        super().__init__(f"{path}: `{key}` should be {expected}")


def read_written_catalog(path: Path) -> WrittenCatalog:
    """Read the one written file, narrowing every field as it goes."""
    document = _table(path, "the file", _loads(path.read_text(encoding="utf-8")), "a table")
    return WrittenCatalog(
        bundles=_bundles(path, document.get("bundles", {})),
        frameworks=_frameworks(path, document.get("frameworks", {})),
    )


def _bundles(path: Path, value: object) -> tuple[WrittenBundle, ...]:
    bundles: list[WrittenBundle] = []
    for name, value_of in sorted(_table(path, "bundles", value, "a table of bundles").items()):
        entry = _table(path, f"bundles.{name}", value_of, "a table")
        bundles.append(
            WrittenBundle(
                name=name,
                description=_description(path, f"bundles.{name}", entry.get("description")),
                items=_items(path, name, entry.get("items", [])),
            )
        )
    return tuple(bundles)


def _frameworks(path: Path, value: object) -> Mapping[str, str]:
    frameworks: dict[str, str] = {}
    for name, value_of in sorted(
        _table(path, "frameworks", value, "a table of frameworks").items()
    ):
        entry = _table(path, f"frameworks.{name}", value_of, "a table")
        frameworks[name] = _description(path, f"frameworks.{name}", entry.get("description"))
    return frameworks


def _items(path: Path, bundle: str, value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise MalformedWrittenCatalogError(path, f"bundles.{bundle}.items", "a list of names")
    items = cast("list[object]", value)
    if not all(isinstance(item, str) for item in items):
        raise MalformedWrittenCatalogError(path, f"bundles.{bundle}.items", "a list of names")
    return tuple(str(item) for item in items)


def _description(path: Path, key: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MalformedWrittenCatalogError(path, f"{key}.description", "a non-empty string")
    return value


def _table(path: Path, key: str, value: object, expected: str) -> dict[str, object]:
    """A TOML table, typed.

    The cast is not a shrug: TOML has **no** key type but string, so `dict[str,
    object]` is what the format guarantees and `isinstance` cannot express. The
    values stay `object` — that is the point of the whole module.
    """
    if not isinstance(value, dict):
        raise MalformedWrittenCatalogError(path, key, expected)
    return cast("dict[str, object]", value)


def _loads(text: str) -> object:
    """The whole decode surface, and it declares `object` on purpose."""
    return tomllib.loads(text)
