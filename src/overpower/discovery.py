"""The tree is the catalog: `list` and `install` discover by looking.

`content/pool/<type>/<name>/` and `content/frameworks/<name>/<type>/<name>/`, and
**no path is registered anywhere** (rule 8 of the model, ADR 0006). Adding a file
inside a skill touches nothing; adding a whole skill touches nothing. Registering
paths would be duplication — the filesystem already knows — and it produces
silent drift: measured, a new skill on disk with no catalog entry is *invisible*,
with no warning.

Two properties follow, and both are asserted rather than promised:

- **the set of type names is closed.** A directory outside it is a named error on
  the first call, with the offending path in the message — never a silent
  omission;
- **only a directory is an artifact.** The one blind spot measured in
  https://github.com/panlabs-tech/overpower/issues/10 is a loose file in the type
  folder becoming an artifact, and it closes by ignoring what is not a directory.

**A skill's description comes from its own `SKILL.md`, whole.** Deriving a short
line was measured and is not possible — median 179 characters, maximum 517, and
cutting at the first sentence leaves 13 of 22 above one line. The cost in screen
height was rendered and accepted; what it buys is that the embedded and the
remote path describe an artifact identically, because both read the artifact.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import TYPE_CHECKING

from overpower.errors import BadInvocationError, OverpowerError
from overpower.written import read_written_catalog

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from pathlib import Path

POOL_DIR = "pool"
FRAMEWORKS_DIR = "frameworks"
SKILL_FILE = "SKILL.md"


class ArtifactType(StrEnum):
    """What an artifact is, which is also what decides where it lands.

    The set is closed: destination is a function of (type, runtime, scope) —
    rule 8, ADR 0006 — so a type nobody wrote a destination for cannot be
    installed, and discovering one silently would ship that hole. v0.1.0 copies
    files only; the graft classes (MCP server, hook) join the set when the
    operation that lands them exists, which is the trigger this error is for.
    """

    SKILL = "skill"
    COMMAND = "command"
    AGENT = "agent"


TYPE_DIRS: Mapping[str, ArtifactType] = MappingProxyType(
    {
        "skills": ArtifactType.SKILL,
        "commands": ArtifactType.COMMAND,
        "agents": ArtifactType.AGENT,
    }
)
"""The closed set, spelled as it appears on disk: the plural is the directory."""


@dataclass(frozen=True)
class Artifact:
    """An atom of equipment: a directory, its description and what it weighs."""

    type: ArtifactType
    name: str
    path: Path
    description: str
    files: int
    size: int


@dataclass(frozen=True)
class Framework:
    """A self-contained body of equipment, installed whole.

    Its weight is the sum of its artifacts rather than a walk of its own root:
    what `install --ai-framework` writes is the artifacts, so the number on the
    screen is the number that lands.
    """

    name: str
    path: Path
    description: str
    artifacts: tuple[Artifact, ...]

    @property
    def files(self) -> int:
        """How many files installing it whole writes."""
        return sum(artifact.files for artifact in self.artifacts)

    @property
    def size(self) -> int:
        """How many bytes installing it whole writes."""
        return sum(artifact.size for artifact in self.artifacts)


@dataclass(frozen=True)
class Bundle:
    """A named composition of pool artifacts for one context of work.

    It is a manifest: it points at names and carries no content, so it weighs
    what the artifacts it names weigh.
    """

    name: str
    description: str
    artifacts: tuple[Artifact, ...]

    @property
    def files(self) -> int:
        """How many files the artifacts it names write."""
        return sum(artifact.files for artifact in self.artifacts)

    @property
    def size(self) -> int:
        """How many bytes the artifacts it names write."""
        return sum(artifact.size for artifact in self.artifacts)


@dataclass(frozen=True)
class Catalog:
    """Everything the overpower knows how to install, in the three units.

    They are not levels of one hierarchy: an AI Framework, a pool artifact and a
    bundle are chosen independently.

    The three lookups return the item or raise, and never `None`. A closed list
    has no third answer: either the name is on it, or the invocation is wrong —
    and a `None` here would let a caller carry the miss forwards silently, which
    is the class of defect this product exists not to commit.
    """

    frameworks: tuple[Framework, ...]
    pool: tuple[Artifact, ...]
    bundles: tuple[Bundle, ...]

    def framework(self, name: str) -> Framework:
        """The AI Framework by that name, or the error carrying the closed list."""
        return _named("AI Framework", name, {item.name: item for item in self.frameworks})

    def artifact(self, name: str) -> Artifact:
        """The pool artifact by that name, or the error carrying the closed list."""
        return _named("pool artifact", name, {item.name: item for item in self.pool})

    def bundle(self, name: str) -> Bundle:
        """The bundle by that name, or the error carrying the closed list."""
        return _named("bundle", name, {item.name: item for item in self.bundles})


class UnknownArtifactTypeError(OverpowerError):
    """A directory sitting where a type name belongs, and it is not one."""

    def __init__(self, path: Path) -> None:
        """Name the directory that is not a type, so the fix is one `mv`."""
        self.path = path
        known = ", ".join(sorted(TYPE_DIRS))
        super().__init__(f"unknown artifact type directory: {path} (the set is {known})")


class MissingDescriptionError(OverpowerError):
    """An artifact with nothing to say about itself on the catalog screen."""

    def __init__(self, path: Path) -> None:
        """Name the file that was read and had nothing to say."""
        self.path = path
        super().__init__(f"no description in the frontmatter of {path}")


class MissingFrameworkDescriptionError(OverpowerError):
    """A framework the written file does not describe.

    A framework has no `SKILL.md`, so this one line has nowhere else to come
    from — and a framework on the catalog screen with no description is the
    silent half-state the written file exists to prevent.
    """

    def __init__(self, name: str) -> None:
        """Name the framework the written file skipped."""
        self.name = name
        super().__init__(f"the written catalog has no description for the framework `{name}`")


class UnknownBundleItemError(OverpowerError):
    """A bundle naming an artifact the pool does not have."""

    def __init__(self, bundle: str, item: str) -> None:
        """Name both sides: the manifest and the name it points at."""
        self.bundle = bundle
        self.item = item
        super().__init__(f"the bundle `{bundle}` names `{item}`, which is not in the pool")


class UnknownNameError(BadInvocationError):
    """A name asked of the catalog that the catalog does not have.

    Exit **2**, and the whole closed list travels in the message. There is no
    `--dir` escape hatch in v0.1.0, so the answer to *"what may I type here"* is
    finite and can simply be shown — which is what turns a typo into one
    correction instead of a trip to the catalog screen.
    """

    def __init__(self, unit: str, name: str, known: Iterable[str]) -> None:
        """Name the unit, the name that missed, and everything that would hit."""
        self.unit = unit
        self.name = name
        self.known = tuple(known)
        listed = ", ".join(self.known)
        has = f"the catalog has: {listed}" if self.known else f"the catalog has no {unit} at all"
        super().__init__(f"no {unit} named `{name}` ({has})")


def load_catalog(content_root: Path, catalog_file: Path) -> Catalog:
    """The whole catalog: the tree, plus the one line per thing the tree cannot know."""
    written = read_written_catalog(catalog_file)
    pool = discover_pool(content_root / POOL_DIR)
    by_name = {artifact.name: artifact for artifact in pool}

    bundles = tuple(
        Bundle(
            name=bundle.name,
            description=bundle.description,
            artifacts=tuple(_from_pool(bundle.name, item, by_name) for item in bundle.items),
        )
        for bundle in written.bundles
    )
    return Catalog(
        frameworks=discover_frameworks(content_root / FRAMEWORKS_DIR, written.frameworks),
        pool=pool,
        bundles=bundles,
    )


def discover_pool(pool_root: Path) -> tuple[Artifact, ...]:
    """Every artifact under `<pool>/<type>/<name>/`, sorted by name."""
    return _artifacts_under(pool_root)


def discover_frameworks(
    frameworks_root: Path, descriptions: Mapping[str, str]
) -> tuple[Framework, ...]:
    """Every framework under `<frameworks>/<name>/`, with its written description.

    The description is the one thing a framework cannot say for itself — it has
    no `SKILL.md` — so it is the one thing written down. Everything else about
    it, including the *type* of each artifact inside it, comes from the tree:
    a framework may mix skill, command and agent, and the written file has no
    artifact entry at all.
    """
    frameworks: list[Framework] = []
    for directory in _directories(frameworks_root):
        name = directory.name
        if name not in descriptions:
            raise MissingFrameworkDescriptionError(name)
        frameworks.append(
            Framework(
                name=name,
                path=directory,
                description=descriptions[name],
                artifacts=_artifacts_under(directory),
            )
        )
    return tuple(sorted(frameworks, key=lambda framework: framework.name))


def _named[NamedT](unit: str, name: str, by_name: Mapping[str, NamedT]) -> NamedT:
    """One item of a closed list, by name, or the error that shows the list."""
    if name not in by_name:
        raise UnknownNameError(unit, name, by_name)
    return by_name[name]


def _from_pool(bundle: str, item: str, pool: Mapping[str, Artifact]) -> Artifact:
    """The artifact a bundle points at, or the error that names both."""
    if item not in pool:
        raise UnknownBundleItemError(bundle, item)
    return pool[item]


def _artifacts_under(root: Path) -> tuple[Artifact, ...]:
    """Every artifact of every type below `root`, sorted by name.

    The pool and a framework are walked by the same function because the level
    below them is the same level — `<type>/<name>/` — and that is rule 8 rather
    than a coincidence: the type folder repeats inside a framework, with the
    same closed set of names.

    Sorted because `iterdir` returns the filesystem's order, and a screen — plus
    a plan, and a snapshot of both — needs one of ours, identical on the nine
    cells of the matrix.
    """
    artifacts = [
        artifact
        for type_dir, artifact_type in _type_dirs(root)
        for artifact in _artifacts_in(type_dir, artifact_type)
    ]
    return tuple(sorted(artifacts, key=lambda artifact: artifact.name))


def _type_dirs(root: Path) -> Iterable[tuple[Path, ArtifactType]]:
    for directory in _directories(root):
        artifact_type = TYPE_DIRS.get(directory.name)
        if artifact_type is None:
            raise UnknownArtifactTypeError(directory)
        yield directory, artifact_type


def _artifacts_in(type_dir: Path, artifact_type: ArtifactType) -> Iterable[Artifact]:
    for directory in _directories(type_dir):
        files, size = _weigh(directory)
        yield Artifact(
            type=artifact_type,
            name=directory.name,
            path=directory,
            description=_description_of(directory),
            files=files,
            size=size,
        )


def _directories(root: Path) -> list[Path]:
    """The directories directly under `root`, sorted, and nothing else.

    Nothing else is where the measured blind spot closes: a loose file in a type
    folder is not an artifact. A root that does not exist yields nothing — a
    content tree may legitimately carry only a pool, or only frameworks.
    """
    if not root.is_dir():
        return []
    return sorted((child for child in root.iterdir() if child.is_dir()), key=lambda p: p.name)


def _weigh(artifact: Path) -> tuple[int, int]:
    """How many files the artifact has, and how many bytes they are."""
    files = [path for path in artifact.rglob("*") if path.is_file()]
    return len(files), sum(path.stat().st_size for path in files)


def _description_of(artifact: Path) -> str:
    """The artifact's own description, whole, from its `SKILL.md` frontmatter.

    When the first command or agent lands in the tree, this is the line that
    decides where *its* description comes from; until then the error names the
    file it looked for rather than inventing a convention for content that does
    not exist yet.
    """
    skill_md = artifact / SKILL_FILE
    if not skill_md.is_file():
        raise MissingDescriptionError(skill_md)
    description = _frontmatter_description(skill_md.read_text(encoding="utf-8"))
    if not description:
        raise MissingDescriptionError(skill_md)
    return description


def _frontmatter_description(text: str) -> str:
    """`description:` out of the YAML frontmatter, folded, unquoted, untruncated.

    Hand-parsed, and that is a decision: a YAML dependency would be the first
    one the product does not already need, for one key of one block that every
    measured artifact writes on a single line. Continuation lines are folded
    with a space, the way YAML folds a plain scalar, so an artifact that wraps
    its description in the file still arrives whole.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""

    collected: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if collected:
            if line.startswith((" ", "\t")):
                collected.append(line.strip())
                continue
            break
        key, separator, value = line.partition(":")
        if separator and key.strip() == "description":
            collected.append(value.strip())

    return _unquote(" ".join(part for part in collected if part))


def _unquote(value: str) -> str:
    quoted = len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}  # noqa: PLR2004
    return value[1:-1] if quoted else value
