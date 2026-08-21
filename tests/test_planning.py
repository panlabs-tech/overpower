"""What a request costs: the plan that comes out, and every line that is refused.

Mirror of `src/overpower/planning.py`. The refusals go through the CLI, because
what they promise is an **exit code** and that is only observable there; the
shape of the plan is asserted over values, the way the runtime table already is,
because the plan is the vocabulary the screen and the writer share and its
*shape* is what the graft lock is about.

Nothing here reaches the disk except to build a real content tree for the
product to walk — the writing side is next door, in `test_writing.py`.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING

from overpower.discovery import load_catalog
from overpower.planning import (
    DirectoryTree,
    DocumentKey,
    Plan,
    Request,
    Write,
    WriteMode,
    askable_slots,
    plan_for,
    unset_slots,
)
from overpower.rendering import Fragment, Inputs
from overpower.runtimes import MCP_DOCUMENTS, Environment, Scope, known_runtimes
from tests.support.project import (
    AGENTS,
    CLAUDE,
    SLOT_VARIABLE,
    SLOTTED,
    catalog_of,
    custom_recipe,
    joined,
    run,
    target,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    import pytest


def test_the_copy_class_lands_in_a_folder_and_the_planner_says_which(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The implemented half of the two-form destination, straight from the planner.

    The other half — a destination that is a document and a key — is refused by
    name in `test_writing.py`, which is where the operation would live.
    """
    # given
    content = catalog_of(tmp_path, monkeypatch, "alpha")
    root = target(tmp_path, monkeypatch)
    catalog = load_catalog(content, tmp_path / "packaged" / "catalog.yaml")

    plan = plan_for(
        Request(skills=("alpha",), runtimes=("claude-code",), scope=Scope.PROJECT),
        catalog,
        root,
        Environment.from_process(),
    )

    assert [write.destination for write in plan.writes] == [
        DirectoryTree(path=root / CLAUDE / "alpha")
    ]
    assert [write.mode for write in plan.writes] == [WriteMode.COPY]


def test_the_graft_class_lands_in_a_document_and_the_planner_says_which_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The other half of the two-form destination, and the one the model reserved.

    The plan carries the **rendered fragment** as the write's origin, not a path
    and not the recipe: a writer that re-rendered could disagree with the screen
    by construction, and no test written afterwards would close that.
    """
    # given
    content = catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": "https://mcp.example.com/mcp"})
    root = target(tmp_path, monkeypatch)
    catalog = load_catalog(content, tmp_path / "packaged" / "catalog.yaml")

    plan = plan_for(
        Request(mcps=("cloudflare",), runtimes=("claude-code",), scope=Scope.PROJECT),
        catalog,
        root,
        Environment.from_process(),
    )

    assert [write.destination for write in plan.writes] == [
        DocumentKey(path=root / ".mcp.json", key="mcpServers.cloudflare")
    ]
    assert [write.mode for write in plan.writes] == [WriteMode.GRAFT]
    assert [write.source for write in plan.writes] == [
        Fragment(
            root_key="mcpServers",
            name="cloudflare",
            value={"type": "http", "url": "https://mcp.example.com/mcp"},
        )
    ]


def test_one_recipe_is_two_writes_of_one_landing_where_the_dialect_asks_for_two(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two keys, one place — the shape the VS Code dialect imposes on the plan.

    A landing is a *place*, and both keys fall in the same file, so announcing
    two landings would say the run touches two documents. The writes are in
    render order because that is the order the writer performs them, and the
    second one counts **zero files**: the report at the end counts what landed on
    disk, and one file did.
    """
    # given
    content = catalog_of(tmp_path, monkeypatch, mcps={"panel": SLOTTED})
    root = target(tmp_path, monkeypatch)
    catalog = load_catalog(content, tmp_path / "packaged" / "catalog.yaml")

    plan = plan_for(
        Request(mcps=("panel",), runtimes=("vscode",), scope=Scope.PROJECT),
        catalog,
        root,
        Environment.from_process(),
    )

    (landing,) = plan.selections[0].landings
    assert landing.place == root / ".vscode" / "mcp.json"
    assert landing.keys == ("servers.panel", "inputs")
    assert landing.files == 1
    assert [write.source for write in landing.writes] == [
        Fragment(
            root_key="servers",
            name="panel",
            value={
                "type": "stdio",
                "command": "uvx",
                "args": ["panel-server", "--repository", "."],
                "env": {
                    "PANEL_URL": "https://panel.example.com",
                    SLOT_VARIABLE: "${input:panel-token}",
                },
            },
        ),
        Inputs(
            root_key="inputs",
            entries=(
                {
                    "type": "promptString",
                    "id": "panel-token",
                    "description": SLOT_VARIABLE,
                    "password": True,
                },
            ),
            identity="id",
        ),
    ]


def test_every_runtime_the_mcp_table_names_is_one_the_flag_accepts() -> None:
    """A target nobody can select is a target that does not exist.

    The two tables stopped being nested when `vscode` arrived — it owns
    `.vscode/mcp.json` and has no row in the skills transcription — so what
    `--runtime` validates against is the union of both, and this is the assertion
    that the union has not fallen behind either half.
    """
    named = {key for key, _ in MCP_DOCUMENTS}

    assert named <= set(known_runtimes())
    assert "vscode" in named


def test_a_graft_only_runtime_is_refused_in_the_scope_that_has_no_document(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """It is nameable and it still has nowhere to land on the machine — ADR 0009.

    `eve` reads skills in a repository and declares no global directory at all,
    so in machine scope both halves of the union say no. Exit 3: the value is
    real and the destination is not.

    This used to be `vscode --global`, which the machine documents of
    https://github.com/ThiagoPanini/overpower/issues/81 turned into a *landing*.
    The refusal it guards did not move — the pair it is asserted on did.
    """
    # given
    catalog_of(tmp_path, monkeypatch, "alpha", mcps={"panel": SLOTTED})
    target(tmp_path, monkeypatch)

    code, output = run(capsys, *("install", "--skill", "alpha", "--runtime", "eve", "--global"))

    assert code == 3
    assert "eve" in joined(output)
    assert "no destination in global scope" in joined(output)


def test_a_runtime_with_no_mcp_document_still_receives_the_skill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Issue #100: the refusal narrows to the runtime with a row on neither table.

    `cursor` has a skills destination and no MCP document; `claude-code` has
    both. `cursor` still has a real row on one of the two tables the line
    carries, so the line is not refused for its sake — it receives the skill,
    the server is skipped for it, and the screen names what it did not get.
    """
    # given
    catalog_of(tmp_path, monkeypatch, "alpha", mcps={"cloudflare": "https://mcp.example.com/mcp"})
    root = target(tmp_path, monkeypatch)

    code, output = run(
        capsys,
        *("install", "--skill", "alpha", "--mcp", "cloudflare"),
        *("--runtime", "claude-code,cursor"),
    )

    assert code == 0
    assert (root / CLAUDE / "alpha").exists()
    assert (root / AGENTS / "alpha").exists()
    assert (root / ".mcp.json").exists()
    assert "cursor" in joined(output)
    assert "no MCP destination" in joined(output)


def test_the_machine_scope_lands_in_the_personal_file_and_not_in_the_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The table is a function of (runtime, **scope**), and the scope moves the file.

    `--global` is not the project document under another root: it is
    `~/.claude.json`, a different file with the same root key
    (https://github.com/ThiagoPanini/overpower/issues/81). The repository is
    asserted **empty** in the same breath, because a machine install that also
    touched the tree would be the failure ADR 0008 refuses to inherit.
    """
    # given
    catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": "https://mcp.example.com/mcp"})
    root = target(tmp_path, monkeypatch)

    code, output = run(
        capsys, *("install", "--mcp", "cloudflare", "--runtime", "claude-code", "--global")
    )

    assert code == 0
    assert ".claude.json" in joined(output)
    assert (tmp_path / ".claude.json").is_file()
    assert not (root / ".mcp.json").exists()
    assert list(root.iterdir()) == []


def test_comma_and_repetition_both_accumulate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """What `ruff --select E,F,W` and `gh pr create --reviewer a,b --reviewer c` taught."""
    # given
    catalog_of(tmp_path, monkeypatch, "alpha", "beta", "gamma")
    root = target(tmp_path, monkeypatch)

    code, _ = run(
        capsys,
        *("install", "--skill", "alpha", "--skill", "beta,gamma"),
        *("--runtime", "claude-code", "--yes"),
    )

    assert code == 0
    assert {entry.name for entry in (root / CLAUDE).iterdir()} == {"alpha", "beta", "gamma"}


def test_a_runtime_with_no_directory_in_the_target_is_created_and_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A named runtime is an equipped runtime — the silent skip is not inherited.

    Upstream returns `success: true, skipped: true` for a non-universal runtime
    whose root directory does not exist, and writes nothing (ADR 0008).
    """
    # given
    catalog_of(tmp_path, monkeypatch, "alpha")
    root = target(tmp_path, monkeypatch)
    assert not (root / ".devin").exists()

    code, _ = run(capsys, "install", "--skill", "alpha", "--runtime", "devin", "--yes")

    assert code == 0
    assert (root / ".devin" / "skills" / "alpha" / "SKILL.md").is_file()


def test_a_missing_runtime_without_a_terminal_exits_two(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Guessing a destination is the class of error this product exists not to commit."""
    # given
    catalog_of(tmp_path, monkeypatch, "alpha")
    root = target(tmp_path, monkeypatch)

    code, _ = run(capsys, "install", "--skill", "alpha")

    assert code == 2
    assert list(root.iterdir()) == []


def test_a_runtime_outside_the_table_exits_two_naming_the_closed_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The table is closed, and there is no `--dir` hatch in v0.1.0."""
    # given
    catalog_of(tmp_path, monkeypatch, "alpha")
    target(tmp_path, monkeypatch)

    code, output = run(capsys, "install", "--skill", "alpha", "--runtime", "cursr")

    assert code == 2
    assert "cursr" in joined(output)
    assert "claude-code" in joined(output)


def test_a_runtime_with_no_global_destination_exits_three_and_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """ADR 0009: the value exists, the flag exists — what is missing is the destination.

    Paired with `claude-code`, which *does* have one, to prove the whole
    command is refused rather than the writable half going through silently.
    """
    # given
    catalog_of(tmp_path, monkeypatch, "alpha")
    target(tmp_path, monkeypatch)

    code, output = run(
        capsys,
        "install",
        "--skill",
        "alpha",
        "--runtime",
        "eve,claude-code",
        "--global",
        "--yes",
    )

    assert code == 3
    assert "eve" in joined(output)
    assert "global" in joined(output)
    assert not (tmp_path / CLAUDE).exists()


def test_a_skill_outside_the_catalog_exits_two(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # given
    catalog_of(tmp_path, monkeypatch, "alpha")
    target(tmp_path, monkeypatch)

    code, output = run(capsys, "install", "--skill", "alfa", "--runtime", "claude-code")

    assert code == 2
    assert "alfa" in joined(output)


def test_naming_nothing_exits_two_instead_of_writing_nothing_and_saying_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """An empty manifest is a typo, and an empty plan at exit 0 is the lie to avoid."""
    # given
    catalog_of(tmp_path, monkeypatch, "alpha")
    root = target(tmp_path, monkeypatch)

    code, output = run(capsys, "install", "--runtime", "claude-code")

    assert code == 2
    assert list(root.iterdir()) == []
    assert "--ai-framework" in joined(output)
    assert "--bundle" in joined(output)


# --------------------------------------------------------------------------- #
# #40: global scope's one --force trigger — an existing destination
# --------------------------------------------------------------------------- #


def test_an_existing_global_destination_without_force_exits_three(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Global scope has no git to reveal or undo an overwrite, unlike project scope."""
    # given
    catalog_of(tmp_path, monkeypatch, "alpha")
    target(tmp_path, monkeypatch)
    existing = tmp_path / CLAUDE / "alpha"
    existing.mkdir(parents=True)
    (existing / "stale.md").write_text("from before\n", encoding="utf-8")

    code, output = run(
        capsys, "install", "--skill", "alpha", "--runtime", "claude-code", "--global", "--yes"
    )

    assert code == 3
    assert "--force" in joined(output)
    assert (existing / "stale.md").is_file()


def test_the_dry_run_mirrors_exit_three_the_same_way_it_mirrors_exit_two(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """#8: a dry run that answered 0 where the real run answers 3 would lie to a pipeline."""
    # given
    catalog_of(tmp_path, monkeypatch, "alpha")
    target(tmp_path, monkeypatch)
    existing = tmp_path / CLAUDE / "alpha"
    existing.mkdir(parents=True)
    selectors = ("install", "--skill", "alpha", "--runtime", "claude-code", "--global")

    dry_code, _ = run(capsys, *selectors, "--dry-run")
    real_code, _ = run(capsys, *selectors, "--yes")

    assert dry_code == real_code == 3


def test_force_overwrites_an_existing_global_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # given
    catalog_of(tmp_path, monkeypatch, "alpha")
    target(tmp_path, monkeypatch)
    existing = tmp_path / CLAUDE / "alpha"
    existing.mkdir(parents=True)
    (existing / "stale.md").write_text("from before\n", encoding="utf-8")

    code, _ = run(
        capsys,
        "install",
        "--skill",
        "alpha",
        "--runtime",
        "claude-code",
        "--global",
        "--force",
        "--yes",
    )

    assert code == 0
    assert not (existing / "stale.md").exists()
    assert (existing / "SKILL.md").is_file()


def test_project_scope_never_needs_force(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The `--force` trigger is global-scope-only: project scope writes unconditionally."""
    # given
    catalog_of(tmp_path, monkeypatch, "alpha")
    root = target(tmp_path, monkeypatch)
    existing = root / CLAUDE / "alpha"
    existing.mkdir(parents=True)
    (existing / "stale.md").write_text("from before\n", encoding="utf-8")

    code, _ = run(capsys, "install", "--skill", "alpha", "--runtime", "claude-code", "--yes")

    assert code == 0
    assert not (existing / "stale.md").exists()
    assert (existing / "SKILL.md").is_file()


# --------------------------------------------------------------------------- #
# #39: framework and bundle join --skill as sibling selectors
# --------------------------------------------------------------------------- #


def test_an_ai_framework_writes_every_artifact_it_carries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rule 1: a framework installs whole — one write per artifact it carries."""
    # given
    content = catalog_of(tmp_path, monkeypatch, frameworks={"matt-pocock": ("grilling", "tdd")})
    root = target(tmp_path, monkeypatch)
    catalog = load_catalog(content, tmp_path / "packaged" / "catalog.yaml")

    plan = plan_for(
        Request(ai_frameworks=("matt-pocock",), runtimes=("claude-code",)),
        catalog,
        root,
        Environment.from_process(),
    )

    assert [selection.name for selection in plan.selections] == ["matt-pocock"]
    assert {write.destination for write in plan.writes} == {
        DirectoryTree(path=root / CLAUDE / "grilling"),
        DirectoryTree(path=root / CLAUDE / "tdd"),
    }


def test_a_bundle_writes_exactly_what_it_names_and_no_framework(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ADR 0002: a bundle is a manifest over the pool, never a framework."""
    # given
    content = catalog_of(
        tmp_path,
        monkeypatch,
        "alpha",
        "beta",
        frameworks={"matt-pocock": ("gamma",)},
        bundles={"api-python": ("alpha",)},
    )
    root = target(tmp_path, monkeypatch)
    catalog = load_catalog(content, tmp_path / "packaged" / "catalog.yaml")

    plan = plan_for(
        Request(bundles=("api-python",), runtimes=("claude-code",)),
        catalog,
        root,
        Environment.from_process(),
    )

    assert [selection.name for selection in plan.selections] == ["api-python"]
    assert [write.destination for write in plan.writes] == [
        DirectoryTree(path=root / CLAUDE / "alpha")
    ]


def test_framework_bundle_and_skill_on_one_line_produce_one_plan_in_fixed_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """#39: the order is fixed and documented — framework, bundle, individual artifact."""
    # given
    content = catalog_of(
        tmp_path,
        monkeypatch,
        "alpha",
        frameworks={"matt-pocock": ("gamma",)},
        bundles={"api-python": ("alpha",)},
    )
    root = target(tmp_path, monkeypatch)
    catalog = load_catalog(content, tmp_path / "packaged" / "catalog.yaml")

    plan = plan_for(
        Request(
            ai_frameworks=("matt-pocock",),
            bundles=("api-python",),
            skills=("alpha",),
            runtimes=("claude-code",),
        ),
        catalog,
        root,
        Environment.from_process(),
    )

    assert [selection.name for selection in plan.selections] == [
        "matt-pocock",
        "api-python",
        "alpha",
    ]


def test_requesting_a_frameworks_inner_artifact_by_skill_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Rule 1: no partial framework install — a framework's artifact is not in the pool."""
    # given
    catalog_of(tmp_path, monkeypatch, frameworks={"matt-pocock": ("grilling",)})
    root = target(tmp_path, monkeypatch)

    code, output = run(capsys, "install", "--skill", "grilling", "--runtime", "claude-code")

    assert code == 2
    assert "grilling" in joined(output)
    assert list(root.iterdir()) == []


def test_an_ai_framework_and_a_bundle_accept_comma_and_repetition_too(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """What `--skill` already taught, extended to the two selectors #39 adds."""
    # given
    catalog_of(
        tmp_path,
        monkeypatch,
        "p1",
        "p2",
        frameworks={"fw-one": ("f1",), "fw-two": ("f2",)},
        bundles={"bun-one": ("p1",), "bun-two": ("p2",)},
    )
    root = target(tmp_path, monkeypatch)

    code, _ = run(
        capsys,
        "install",
        "--ai-framework",
        "fw-one",
        "--ai-framework",
        "fw-two",
        "--bundle",
        "bun-one,bun-two",
        "--runtime",
        "claude-code",
        "--yes",
    )

    assert code == 0
    assert {entry.name for entry in (root / CLAUDE).iterdir()} == {"f1", "f2", "p1", "p2"}


def test_a_skill_naming_other_skills_in_its_text_writes_only_itself(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rule 7: the command is the contract, even when the text names siblings."""
    # given
    content = catalog_of(tmp_path, monkeypatch, "wayfinder", "to-spec")
    (content / "pool" / "skills" / "wayfinder" / "SKILL.md").write_text(
        "---\nname: wayfinder\ndescription: Names to-spec in its own body.\n---\n\n"
        "Invoke to-spec.\n",
        encoding="utf-8",
    )
    root = target(tmp_path, monkeypatch)
    catalog = load_catalog(content, tmp_path / "packaged" / "catalog.yaml")

    plan = plan_for(
        Request(skills=("wayfinder",), runtimes=("claude-code",)),
        catalog,
        root,
        Environment.from_process(),
    )

    assert [selection.name for selection in plan.selections] == ["wayfinder"]


# --------------------------------------------------------------------------- #
# `source:`: the clone is a second write of the same selection (#84)
# --------------------------------------------------------------------------- #

SOURCED = """\
description: "A server with code of its own."
transport: "stdio"

source:
  url: "https://github.com/example/homegrown-mcp"

server:
  command: "uv"
  args:
    - "run"
    - "--project"
    - "{source}"
    - "server.py"
"""


def test_a_sourced_recipe_costs_a_clone_landing_alongside_its_graft(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Issue #84: the clone is a second write of the selection, never a side effect."""
    # given
    content = catalog_of(tmp_path, monkeypatch)
    custom_recipe(tmp_path, "homegrown", SOURCED)
    root = target(tmp_path, monkeypatch)
    cloned = tmp_path / "scratch" / "homegrown"
    (cloned / "pkg").mkdir(parents=True)
    (cloned / "pkg" / "server.py").write_text("x", encoding="utf-8")
    (cloned / "readme.md").write_text("x", encoding="utf-8")
    catalog = load_catalog(content, tmp_path / "packaged" / "catalog.yaml")

    plan = plan_for(
        Request(mcps=("homegrown",), runtimes=("claude-code",), scope=Scope.GLOBAL),
        catalog,
        root,
        Environment.from_process(),
        sources={"homegrown": cloned},
    )

    (selection,) = plan.selections
    clone_landing, graft_landing = selection.landings
    destination = root / ".overpower" / "mcp" / "homegrown"
    assert clone_landing.place == destination
    assert clone_landing.readers == graft_landing.readers
    assert clone_landing.files == 2
    assert clone_landing.writes == (
        Write(source=cloned, destination=DirectoryTree(destination), mode=WriteMode.CLONE, files=2),
    )
    (write,) = graft_landing.writes
    assert isinstance(write.source, Fragment)
    assert write.source.value["args"] == ["run", "--project", str(destination), "server.py"]


def test_a_recipe_with_no_source_costs_no_clone_landing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The ordinary case, unaffected: no `source:`, one landing, exactly as before."""
    # given
    content = catalog_of(tmp_path, monkeypatch, mcps={"cloudflare": "https://mcp.example.com/mcp"})
    root = target(tmp_path, monkeypatch)
    catalog = load_catalog(content, tmp_path / "packaged" / "catalog.yaml")

    plan = plan_for(
        Request(mcps=("cloudflare",), runtimes=("claude-code",), scope=Scope.PROJECT),
        catalog,
        root,
        Environment.from_process(),
    )

    (selection,) = plan.selections
    assert len(selection.landings) == 1
    assert all(write.mode is not WriteMode.CLONE for write in selection.landings[0].writes)


# --------------------------------------------------------------------------- #
# the secret the plan carries, and the scope that decides whether it may (#167)
# --------------------------------------------------------------------------- #


def _planned(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scope: Scope,
    runtime: str = "claude-code",
    secrets: Mapping[str, str] = MappingProxyType({}),
) -> Plan:
    """One slotted server, planned for one runtime, with whatever was answered."""
    content = catalog_of(tmp_path, monkeypatch, mcps={"paneled": SLOTTED})
    root = target(tmp_path, monkeypatch)
    catalog = load_catalog(content, tmp_path / "packaged" / "catalog.yaml")
    return plan_for(
        Request(mcps=("paneled",), runtimes=(runtime,), scope=scope),
        catalog,
        root,
        Environment.from_process(),
        secrets=secrets,
    )


def _environment_of(plan: Plan) -> object:
    """The `env` table of the one server graft this plan carries."""
    (selection,) = plan.selections
    (landing,) = selection.landings
    write, *_ = landing.writes
    assert isinstance(write.source, Fragment)
    return write.source.value["env"]


def test_the_machine_scope_carries_the_answered_value_into_the_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ADR 0024, at the layer that decides it: the plan is what the writer reads.

    The value is put in the plan and not handed to the writer beside it, because
    the plan is the whole of what `execute` consumes — a second channel is a
    second thing the screen and the disk could disagree about.
    """
    plan = _planned(tmp_path, monkeypatch, Scope.GLOBAL, secrets={SLOT_VARIABLE: "pt_live_x"})

    assert _environment_of(plan) == {
        "PANEL_URL": "https://panel.example.com",
        SLOT_VARIABLE: "pt_live_x",
    }


def test_the_project_scope_refuses_the_value_however_it_was_answered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The other half of the rule, and it is enforced **here** rather than upstream.

    A caller that gathered a value and then asked for a project-scope plan gets
    the reference back regardless — the file goes to the git, and no argument
    reaches this function that can change that.
    """
    plan = _planned(tmp_path, monkeypatch, Scope.PROJECT, secrets={SLOT_VARIABLE: "pt_live_x"})

    assert _environment_of(plan) == {
        "PANEL_URL": "https://panel.example.com",
        SLOT_VARIABLE: f"${{{SLOT_VARIABLE}}}",
    }


def test_the_vault_target_keeps_its_prompt_even_in_the_machine_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scope opens the door; the dialect still decides who walks through it."""
    plan = _planned(
        tmp_path, monkeypatch, Scope.GLOBAL, "vscode", secrets={SLOT_VARIABLE: "pt_live_x"}
    )

    assert _environment_of(plan) == {
        "PANEL_URL": "https://panel.example.com",
        SLOT_VARIABLE: "${input:panel-token}",
    }


def test_the_plan_names_the_secrets_it_would_ask_about(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """What `--dry-run` announces and what the prompt loop walks — one answer, two readers."""
    plan = _planned(tmp_path, monkeypatch, Scope.GLOBAL)

    assert askable_slots(plan, Scope.GLOBAL) == (SLOT_VARIABLE,)


def test_a_project_scope_plan_would_ask_about_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The prompt is a machine-scope act, so in a repository there is nothing to count."""
    plan = _planned(tmp_path, monkeypatch, Scope.PROJECT)

    assert askable_slots(plan, Scope.PROJECT) == ()


def test_the_vault_target_alone_would_ask_about_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """VS Code asks for itself, so the overpower asking too would be one prompt too many."""
    plan = _planned(tmp_path, monkeypatch, Scope.GLOBAL, "vscode")

    assert askable_slots(plan, Scope.GLOBAL) == ()


def test_a_variable_written_into_the_document_is_no_longer_unset_here(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The warning is about a reference nothing will expand, and a value is not one.

    Left alone it would tell somebody to export a variable that is already in
    the file — the same defect as the approval line appearing everywhere, which
    is a warning nobody can act on.
    """
    plan = _planned(tmp_path, monkeypatch, Scope.GLOBAL, secrets={SLOT_VARIABLE: "pt_live_x"})

    assert unset_slots(plan, {}, Scope.GLOBAL) == (SLOT_VARIABLE,)
    assert unset_slots(plan, {}, Scope.GLOBAL, written=(SLOT_VARIABLE,)) == ()
