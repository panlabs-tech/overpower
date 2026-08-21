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
  https://github.com/ThiagoPanini/overpower/issues/10 is a loose file in the type
  folder becoming an artifact, and it closes by ignoring what is not a directory.

**A skill's description comes from its own `SKILL.md`, whole.** Deriving a short
line was measured and is not possible — median 179 characters, maximum 517, and
cutting at the first sentence leaves 13 of 22 above one line. The cost in screen
height was rendered and accepted; what it buys is that the embedded and the
remote path describe an artifact identically, because both read the artifact.

**The frontmatter is read by a real YAML reader**, `overpower.yamlio`, and the
hand-rolled parser that used to stand here is gone
(https://github.com/ThiagoPanini/overpower/issues/136). Keeping one by hand next
to a real one is the weak form of the two-readers defect, and the hand-rolled
one was wrong: `description: >` and `description: |` arrived with the block
marker as the first word of the text. It was invisible while the product only
read its own content — 0 of the 26 embedded `SKILL.md` use a block — and it
turns into a visible defect the day somebody else's frontmatter renders.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import TYPE_CHECKING, cast

from overpower.errors import BadInvocationError, OverpowerError
from overpower.written import read_written_catalog
from overpower.yamlio import loads_yaml

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from pathlib import Path

    from overpower.recipes import Recipe

POOL_DIR = "pool"
FRAMEWORKS_DIR = "frameworks"
SKILL_FILE = "SKILL.md"


class ArtifactType(StrEnum):
    """What an artifact is, which is also what decides where it lands.

    The set is closed: destination is a function of (type, runtime, scope) —
    rule 8, ADR 0006 — so a type nobody wrote a destination for cannot be
    installed, and discovering one silently would ship that hole.

    It is the closed set of **type folders under a content root**, which is why
    the MCP server is not on it even though the operation that lands one now
    exists: a recipe does not land, so it is not content — and it is not
    discovered at all, it is *written*, under the `mcp:` key of the one written
    file (`overpower.written`, ADR 0021). The hook is still to come, and it
    *will* join this set — it is contract **and** tree, so part of it is content.
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
    mcps: tuple[Recipe, ...] = ()
    """The MCP recipes, which are a fourth thing to know and not a fourth unit.

    A server is an artifact of the pool in the model — it is chosen alone and it
    is not composed — and it sits in its own field for one mechanical reason: it
    is not an `Artifact`, because an `Artifact` is a directory that gets copied
    and a recipe is a declaration that gets rendered.
    """

    def framework(self, name: str) -> Framework:
        """The AI Framework by that name, or the error carrying the closed list."""
        return _named("AI Framework", name, {item.name: item for item in self.frameworks})

    def artifact(self, name: str) -> Artifact:
        """The pool artifact by that name, or the error carrying the closed list."""
        return _named("pool artifact", name, {item.name: item for item in self.pool})

    def bundle(self, name: str) -> Bundle:
        """The bundle by that name, or the error carrying the closed list."""
        return _named("bundle", name, {item.name: item for item in self.bundles})

    def mcp(self, name: str) -> Recipe:
        """The MCP recipe by that name, or the error carrying the closed list."""
        return _named("MCP server", name, {item.name: item for item in self.mcps})


class UnknownArtifactTypeError(OverpowerError):
    """A directory sitting where a type name belongs, and it is not one."""

    def __init__(self, path: Path) -> None:
        """Name the directory that is not a type, so the fix is one `mv`."""
        self.path = path
        known = ", ".join(sorted(TYPE_DIRS))
        super().__init__(f"unknown artifact type directory: {path} (the set is {known})")


class UnreadableFrontmatterError(OverpowerError):
    """A `SKILL.md` whose frontmatter is not YAML — nothing was read out of it.

    Sibling of `MissingDescriptionError` and deliberately not the same class:
    *there is no description* and *the block it would be in does not parse* are
    two defects with two different fixes. The reader's own complaint is carried
    through because it names the line and the column, which is the difference
    between one edit and bisecting the file.

    The hand-rolled parser this replaced never refused anything — it guessed,
    and a guess over frontmatter written by somebody else is how a block marker
    ends up rendered as the first word of a description.
    """

    def __init__(self, path: Path, detail: str) -> None:
        """Name the file and repeat what the reader said about it."""
        self.path = path
        self.detail = detail
        super().__init__(f"unreadable frontmatter in {path} ({detail})")


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
    """The whole catalog: the tree, plus the one line per thing the tree cannot know.

    **There is no third discovery root.** A recipe never lands, so it has no tree
    to be discovered by walking; it is written, under the `mcp:` key of the very
    file this function already reads (ADR 0021). One address locates everything
    the tree cannot know, and there is no second root to keep pointed at the
    first.
    """
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
        mcps=written.mcps,
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


def artifact_at(directory: Path, artifact_type: ArtifactType) -> Artifact:
    """One artifact, read off its own directory: its name, its description, its weight.

    The embedded walk and the remote search of `--from` both land here, and that
    is what makes the module docstring's promise true rather than hopeful: the
    two paths describe an artifact identically **because both of them read the
    artifact**. The type is a parameter because the tree is what knows it — the
    walk reads it off the folder above, and a remote search of `SKILL.md` names
    it at the call site.
    """
    files, size = _weigh(directory)
    return Artifact(
        type=artifact_type,
        name=directory.name,
        path=directory,
        description=_description_of(directory),
        files=files,
        size=size,
    )


def _artifacts_in(type_dir: Path, artifact_type: ArtifactType) -> Iterable[Artifact]:
    for directory in _directories(type_dir):
        yield artifact_at(directory, artifact_type)


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
    description = _frontmatter_description(skill_md)
    if not description:
        raise MissingDescriptionError(skill_md)
    return description


def _frontmatter_description(path: Path) -> str:
    """`description:` out of the frontmatter, read as the YAML it always was.

    Quoting, folding and block scalars are the reader's job now, not this
    module's — which is the whole point of taking the dependency. What arrives
    is what YAML says the value is, stripped of the whitespace the format itself
    leaves at the edges: `>` folds its lines into one, `|` keeps its newlines,
    and neither carries its marker into the text.

    A `description` that is not a string is no description, and so is a file
    with no frontmatter block at all — both answer `""`, and the caller turns
    that into a refusal that names the file. A block that is *not YAML* is a
    different answer and gets its own.
    """
    block = _frontmatter(path.read_text(encoding="utf-8"))
    if block is None:
        return ""
    try:
        document = loads_yaml(block)
    except ValueError as error:
        raise UnreadableFrontmatterError(path, str(error)) from error
    if not isinstance(document, dict):
        return ""
    description = cast("dict[object, object]", document).get("description")
    return description.strip() if isinstance(description, str) else ""


def _frontmatter(text: str) -> str | None:
    """The lines between the opening `---` and the next one, or `None`.

    Splitting the block off before decoding is what keeps the markdown below it
    out of the reader: a `SKILL.md` body is prose, and prose is rarely YAML. The
    closing delimiter is required, because a block that never closes is a file
    with no frontmatter rather than a file whose frontmatter runs to the end.

    The cost of splitting is that a line number in the reader's complaint counts
    from the start of the block and not of the file — one line off, on a block
    that is a handful of lines long and whose offending line the reader quotes
    back verbatim.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "\n".join(lines[1:index])
    return None
