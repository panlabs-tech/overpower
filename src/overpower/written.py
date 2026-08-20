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
Measured in https://github.com/ThiagoPanini/overpower/issues/2: pyright strict
has a blind spot on `Any`, so `return data["name"]` inside a `-> str` function
type-checks and blows up at runtime. The YAML reader hands back `Any`, so the
decode is confined to `overpower.yamlio` — which declares `object` — and every
field is narrowed in the open, where all three checkers can see it. It is the
same discipline `pyproject.toml` bans `json.load` to enforce, and `yaml.load`
beside it.

**The format is YAML, and the format before it was TOML.** The move
(https://github.com/ThiagoPanini/overpower/issues/136) buys one thing: the
manifest a homemade repository federates reaches *this* reader, so there is
never a second validator to disagree with the first. It costs one guarantee.
TOML had no key type but string; YAML has, so `_table` below **checks** the key
where it used to cast it. The recipe of an MCP server did not move and will not:
that module is a closed allowlist under the promise that *a recipe that gets
past it is a recipe that renders*, and `.overpower/` is a namespace rather than
a format.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from overpower.errors import OverpowerError
from overpower.yamlio import loads_yaml

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


class UnreadableWrittenCatalogError(OverpowerError):
    """The written file is not YAML at all — the reader never got to look inside.

    Sibling of `MalformedWrittenCatalogError` and deliberately not the same
    class: *did not parse* and *parsed into the wrong shape* are two defects,
    and only the second one has a field to name. The parser's own complaint is
    carried through because it names the line and the column.
    """

    def __init__(self, path: Path, detail: str) -> None:
        """Name the file and repeat what the reader said about it."""
        self.path = path
        self.detail = detail
        super().__init__(f"{path}: not YAML the reader can parse ({detail})")


class MalformedWrittenCatalogError(OverpowerError):
    """The written file parsed as YAML but is not shaped like a catalog."""

    def __init__(self, path: Path, key: str, expected: str) -> None:
        """Name the file and the key, so the fix is one edit away."""
        self.path = path
        self.key = key
        super().__init__(f"{path}: `{key}` should be {expected}")


def read_written_catalog(path: Path) -> WrittenCatalog:
    """Read the one written file, narrowing every field as it goes."""
    decoded = _loads(path)
    document = _table(path, "the file", {} if decoded is None else decoded, "a table")
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
    """A mapping whose keys were **checked**, because the format stopped promising them.

    Under TOML the cast here was not a shrug: the format has no key type but
    string, so `dict[str, object]` was what it guaranteed and what `isinstance`
    could not express. YAML guarantees no such thing — `1:` decodes to an
    integer and `true:` to a boolean — so the same cast would now be a lie, and
    it would be living in the one module whose whole reason to exist is being
    the type tripwire. The cast that remains claims nothing about keys; the loop
    below is what makes the return type true. The values stay `object`, which is
    the point of the whole module.
    """
    if not isinstance(value, dict):
        raise MalformedWrittenCatalogError(path, key, expected)
    checked: dict[str, object] = {}
    for name, entry in cast("dict[object, object]", value).items():
        if not isinstance(name, str):
            raise MalformedWrittenCatalogError(path, f"{key}.{name!r}", "a name")
        checked[name] = entry
    return checked


def _loads(path: Path) -> object:
    """The whole decode surface, and it declares `object` on purpose.

    The reader is `overpower.yamlio`, which is the only place in the product
    allowed to touch a YAML loader. It answers `ValueError` when the text is not
    YAML, and that becomes a named refusal here — the next thing to arrive
    through this function is a manifest written by a stranger.
    """
    try:
        return loads_yaml(path.read_text(encoding="utf-8"))
    except ValueError as error:
        raise UnreadableWrittenCatalogError(path, str(error)) from error
