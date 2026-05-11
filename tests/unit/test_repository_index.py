"""Unit coverage for deterministic repository intelligence indexing."""

import json
from datetime import UTC
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from glassbox.core import CommandPurpose
from glassbox.core import CommandReviewRelevance
from glassbox.core import RepositoryIndexFreshness
from glassbox.core import RepositoryIndexProvenance
from glassbox.core import RepositoryIndexSnapshot
from glassbox.core import RepositoryIndexSourceType
from glassbox.core import RepositoryIntelligenceCommandRecipe
from glassbox.core import RepositoryIntelligenceCommandRisk
from glassbox.core import RepositoryIntelligenceConfidence
from glassbox.core import RepositoryIntelligenceMemoryReference
from glassbox.core import RepositoryIntelligenceOwnershipHint
from glassbox.core import RepositoryIntelligencePackageBoundary
from glassbox.core import RepositoryIntelligencePackageKind
from glassbox.core import RepositoryIntelligencePathHint
from glassbox.core import RepositoryIntelligencePathKind
from glassbox.core import RepositoryIntelligenceReleaseSurface
from glassbox.core import RepositoryIntelligenceReleaseSurfaceKind
from glassbox.core import RepositoryIntelligenceSourceManifest
from glassbox.core import WorkspaceMemoryEntry
from glassbox.core import WorkspaceMemoryKind
from glassbox.core import WorkspaceMemoryProvenance
from glassbox.core import WorkspaceMemorySourceType
from glassbox.core import WorkspaceMemoryState
from glassbox.core import new_session_id
from glassbox.core import new_workspace_memory_id
from glassbox.runtime.repository_index import build_and_write_repository_index
from glassbox.runtime.repository_index import get_repository_index_entry
from glassbox.runtime.repository_index import load_repository_index
from glassbox.runtime.repository_index import repository_index_path
from glassbox.runtime.repository_index import search_repository_index
from glassbox.runtime.repository_index import write_repository_index
from glassbox.runtime.repository_index_discovery import INDEX_SCAN_LIMITATION
from glassbox.runtime.repository_index_discovery import MAX_INDEXED_FILES
from glassbox.runtime.repository_index_discovery import classify_repository_path
from glassbox.runtime.repository_index_persistence import RepositoryIndexLoadError
from glassbox.runtime.repository_index_status import (
    build_repository_index_status_summary,
)
from glassbox.runtime.repository_intelligence_layout_common import _dedupe_by_id
from glassbox.runtime.repository_intelligence_layout_common import _existing_paths
from glassbox.runtime.repository_intelligence_layout_common import _file_digest
from glassbox.runtime.repository_intelligence_layout_common import _provenance
from glassbox.runtime.repository_intelligence_layout_common import _read_json
from glassbox.runtime.repository_intelligence_layout_common import _read_toml
from glassbox.runtime.repository_intelligence_layout_common import _slug
from glassbox.runtime.repository_intelligence_layout_docs import (
    discover_docs_command_recipes,
)
from glassbox.runtime.repository_intelligence_layout_evals import (
    discover_eval_command_recipes,
)
from glassbox.runtime.repository_intelligence_layout_ownership import (
    discover_codeowners_ownership_hints,
)
from glassbox.runtime.repository_intelligence_layout_ownership import (
    discover_subsystem_owner_hints,
)
from glassbox.runtime.repository_intelligence_layout_packages import (
    discover_repository_intelligence_packages,
)
from glassbox.runtime.repository_intelligence_layout_paths import (
    discover_repository_intelligence_paths,
)
from glassbox.runtime.repository_intelligence_layout_recipes import (
    dedupe_command_recipes,
)
from glassbox.runtime.repository_intelligence_layout_recipes import (
    discover_package_command_recipes,
)
from glassbox.runtime.repository_intelligence_layout_recipes import (
    discover_release_script_command_recipes,
)
from glassbox.runtime.repository_intelligence_layout_release import (
    discover_release_surface_hints,
)
from glassbox.runtime.repository_intelligence_layout_subsystems import (
    discover_repository_intelligence_subsystems,
)
from glassbox.runtime.repository_intelligence_queries import (
    inspect_repository_intelligence_path,
)
from glassbox.runtime.repository_intelligence_queries import (
    workspace_relative_repository_path,
)
from glassbox.runtime.repository_intelligence_refresh import (
    refresh_repository_intelligence,
)
from glassbox.runtime.workspace_topology import load_workspace_topology
from glassbox.runtime.workspace_topology import workspace_topology_path

_BUILT_AT = datetime(2026, 4, 29, 12, tzinfo=UTC)


def test_repository_index_builds_searchable_local_snapshot(tmp_path: Path) -> None:
    _seed_repository(tmp_path)

    snapshot = build_and_write_repository_index(tmp_path)
    loaded = load_repository_index(tmp_path)
    search_results = search_repository_index(tmp_path, "useful")
    symbol_entry = next(
        entry for entry in search_results if entry.symbol == "UsefulThing"
    )
    fetched = get_repository_index_entry(tmp_path, symbol_entry.entry_id)

    assert repository_index_path(tmp_path).exists()
    assert snapshot.status == RepositoryIndexFreshness.FRESH
    assert snapshot.schema_version == 2
    assert snapshot.builder_version == "v2-schema"
    assert loaded.status == RepositoryIndexFreshness.FRESH
    assert any(entry.name == "pyproject.toml" for entry in loaded.entries)
    assert any(entry.name == "docs/architecture.md" for entry in loaded.entries)
    assert any(entry.name == "tests/test_example.py" for entry in loaded.entries)
    assert any(entry.name == "frontend:test" for entry in loaded.entries)
    assert any(entry.name == "python dependencies" for entry in loaded.entries)
    assert all("node_modules" not in entry.entry_id for entry in loaded.entries)
    assert {root.path.as_posix() for root in loaded.source_roots} >= {"src"}
    assert {root.path.as_posix() for root in loaded.test_roots} == {"tests"}
    assert {root.path.as_posix() for root in loaded.doc_roots} == {"docs"}
    assert {package.package_id for package in loaded.package_boundaries} >= {
        "package:fixture",
        "app:frontend",
        "docs:docs",
    }
    assert any(
        hint.path == Path("frontend/generated")
        and hint.kind == RepositoryIntelligencePathKind.GENERATED_PATH
        for hint in loaded.generated_paths
    )
    commands = {recipe.command: recipe for recipe in loaded.command_recipes}
    assert commands["pnpm --dir frontend test"].purpose == CommandPurpose.TEST
    assert (
        commands["pnpm --dir frontend test"].risk
        == RepositoryIntelligenceCommandRisk.READ_ONLY
    )
    assert (
        commands[
            "uv run pytest tests/unit/test_release_candidate_docs.py -q"
        ].confidence
        == RepositoryIntelligenceConfidence.HIGH
    )
    assert (
        commands["uv run glassbox eval run --profile release-candidate --cwd ."].purpose
        == CommandPurpose.EVAL
    )
    assert {subsystem.subsystem_id for subsystem in loaded.subsystems} >= {
        "subsystem:docs",
        "subsystem:evals",
        "subsystem:frontend",
        "subsystem:packaging",
        "subsystem:release",
    }
    assert any(
        hint.owner_label == "@docs-team" and hint.scope_paths == [Path("docs")]
        for hint in loaded.ownership_hints
    )
    assert {surface.kind for surface in loaded.release_sensitive_surfaces} == {
        RepositoryIntelligenceReleaseSurfaceKind.COMMIT_TIME,
        RepositoryIntelligenceReleaseSurfaceKind.PUSH_TIME,
        RepositoryIntelligenceReleaseSurfaceKind.RELEASE_CANDIDATE,
        RepositoryIntelligenceReleaseSurfaceKind.ADVISORY,
    }
    assert fetched.entry_id == symbol_entry.entry_id
    assert (
        fetched.provenance[0].source_type == RepositoryIndexSourceType.STATIC_ANALYSIS
    )
    assert fetched.provenance[0].line_start == 1


def test_repository_path_classifier_identifies_generated_and_sensitive_paths() -> None:
    generated = classify_repository_path("frontend/generated/api-types.ts")
    cache = classify_repository_path("frontend/node_modules/react/index.js")
    build = classify_repository_path("frontend/out/index.html")
    policy = classify_repository_path("docs/tasks-v15.md")

    assert generated.generated
    assert generated.excluded is False
    assert cache.generated
    assert cache.cache
    assert cache.excluded
    assert build.build_output
    assert build.excluded
    assert policy.policy_sensitive


def test_repository_package_path_discovery_preserves_generated_policy_hints(
    tmp_path: Path,
) -> None:
    _seed_repository(tmp_path)
    (tmp_path / "docs" / "tasks-v15.md").write_text("# Tasks\n", encoding="utf-8")

    packages = discover_repository_intelligence_packages(tmp_path)
    paths = discover_repository_intelligence_paths(
        tmp_path, packages.package_boundaries
    )

    assert {manifest.manifest_id for manifest in packages.source_manifests} >= {
        "manifest:pyproject.toml",
        "manifest:frontend:package.json",
    }
    assert {package.package_id for package in packages.package_boundaries} >= {
        "package:fixture",
        "app:frontend",
        "docs:docs",
        "evals:evals",
    }
    assert {hint.path for hint in paths.source_roots} >= {
        Path("src"),
        Path("frontend"),
    }
    assert any(
        hint.path == Path("frontend/generated")
        and hint.kind == RepositoryIntelligencePathKind.GENERATED_PATH
        for hint in paths.generated_paths
    )
    assert any(
        hint.path == Path("docs/tasks-v15.md")
        and hint.kind == RepositoryIntelligencePathKind.POLICY_SENSITIVE_PATH
        for hint in paths.policy_sensitive_paths
    )


def test_repository_intelligence_layout_common_helpers_are_stable(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "pyproject.toml"
    manifest.write_text("[project]\nname = 'fixture'\n", encoding="utf-8")
    payload = tmp_path / "payload.json"
    payload.write_text('{"ok": true}', encoding="utf-8")

    assert _slug(Path(".")) == "root"
    assert _slug(Path("frontend/package.json")) == "frontend:package.json"
    assert _existing_paths(
        tmp_path,
        [
            "pyproject.toml",
            "../outside.toml",
            tmp_path / "pyproject.toml",
            "missing.toml",
        ],
    ) == [Path("pyproject.toml")]
    assert _read_toml(manifest)["project"]["name"] == "fixture"
    assert _read_toml(tmp_path / "missing.toml") == {}
    assert _read_json(payload) == {"ok": True}
    assert _read_json(manifest) == {}
    assert _file_digest(manifest) == (
        "874ce04b7320d550993d21feb306fd772ba7238b58020423133bf68c6feb4ef7"
    )
    assert _file_digest(tmp_path / "missing.toml") is None
    provenance = _provenance(
        RepositoryIndexSourceType.MANIFEST,
        Path("pyproject.toml"),
    )
    assert provenance.source_type == RepositoryIndexSourceType.MANIFEST
    assert provenance.path == Path("pyproject.toml")
    assert [
        item.item_id
        for item in _dedupe_by_id(
            [
                SimpleNamespace(item_id="one"),
                SimpleNamespace(item_id="one"),
                SimpleNamespace(item_id="two"),
            ],
            "item_id",
        )
    ] == ["one", "two"]


def test_repository_path_inspection_matches_runtime_query_families(
    tmp_path: Path,
) -> None:
    _seed_repository(tmp_path)
    (tmp_path / "docs" / "tasks-v15.md").write_text("# Tasks\n", encoding="utf-8")
    snapshot = build_and_write_repository_index(tmp_path)

    docs_path = workspace_relative_repository_path(
        tmp_path,
        str(tmp_path / "docs" / "tasks-v15.md"),
    )
    inspection = inspect_repository_intelligence_path(snapshot, docs_path)

    assert inspection.path == Path("docs/tasks-v15.md")
    assert inspection.snapshot_status == "fresh"
    assert "docs:docs" in [package.package_id for package in inspection.packages]
    assert {hint.kind for hint in inspection.path_hints} >= {
        RepositoryIntelligencePathKind.DOC_ROOT,
        RepositoryIntelligencePathKind.POLICY_SENSITIVE_PATH,
    }
    assert "subsystem:docs" in [
        subsystem.subsystem_id for subsystem in inspection.subsystems
    ]
    assert "@docs-team" in [owner.owner_label for owner in inspection.ownership_hints]
    assert any(
        recipe.command == "uv run pytest tests/unit/test_release_candidate_docs.py -q"
        for recipe in inspection.command_recipes
    )
    assert any(
        surface.kind == RepositoryIntelligenceReleaseSurfaceKind.RELEASE_CANDIDATE
        for surface in inspection.release_surfaces
    )
    assert inspection.next_actions == [
        "glassbox repo recommend docs/tasks-v15.md",
        "glassbox eval recommend docs/tasks-v15.md",
    ]

    with pytest.raises(ValueError, match="inside the workspace"):
        workspace_relative_repository_path(tmp_path, "../outside.py")


def test_repository_index_layout_respects_builder_limit_and_generated_paths(
    tmp_path: Path,
) -> None:
    _seed_repository(tmp_path)
    bulk = tmp_path / "src" / "bulk"
    bulk.mkdir()
    for index in range(MAX_INDEXED_FILES + 20):
        (bulk / f"module_{index}.py").write_text("VALUE = 1\n", encoding="utf-8")

    snapshot = build_and_write_repository_index(tmp_path)

    assert len(snapshot.source_inputs) == MAX_INDEXED_FILES
    assert snapshot.limitations == [INDEX_SCAN_LIMITATION]
    assert all("node_modules" not in source for source in snapshot.source_inputs)
    assert any(
        hint.path == Path("frontend/out")
        and hint.kind == RepositoryIntelligencePathKind.BUILD_OUTPUT
        for hint in snapshot.generated_paths
    )
    assert any(
        "Excluded from file crawling" in " ".join(hint.limitations)
        for hint in snapshot.generated_paths
        if hint.path == Path("frontend/out")
    )


def test_repository_command_recipes_dedupe_and_explain_sources(
    tmp_path: Path,
) -> None:
    _seed_repository(tmp_path)
    (tmp_path / "README.md").write_text(
        "# Fixture\n\n$ uv run pytest tests/unit/test_release_candidate_docs.py -q\n",
        encoding="utf-8",
    )

    snapshot = build_and_write_repository_index(tmp_path)
    docs_recipe = next(
        recipe
        for recipe in snapshot.command_recipes
        if recipe.command
        == "uv run pytest tests/unit/test_release_candidate_docs.py -q"
    )
    release_recipe = next(
        recipe
        for recipe in snapshot.command_recipes
        if recipe.command
        == "uv run python scripts/validate_v1_release_gate.py --dry-run"
    )

    assert (
        len(
            [
                recipe
                for recipe in snapshot.command_recipes
                if recipe.command
                == "uv run pytest tests/unit/test_release_candidate_docs.py -q"
            ]
        )
        == 1
    )
    assert {source.path for source in docs_recipe.provenance} == {
        Path("evals/recipes.json"),
        Path("README.md"),
    }
    assert docs_recipe.review_relevance == CommandReviewRelevance.VERIFICATION
    assert release_recipe.purpose == CommandPurpose.RELEASE_GATE
    assert release_recipe.timeout_seconds == 600


def test_repository_command_recipe_source_helpers_preserve_metadata(
    tmp_path: Path,
) -> None:
    _seed_repository(tmp_path)
    (tmp_path / "docs" / "recipe.md").write_text(
        "$ uv run pytest tests/unit/test_release_candidate_docs.py -q\n",
        encoding="utf-8",
    )

    packages = discover_repository_intelligence_packages(tmp_path)
    package_recipes = discover_package_command_recipes(
        tmp_path, packages.package_boundaries
    )
    eval_recipes = discover_eval_command_recipes(tmp_path)
    docs_recipes = discover_docs_command_recipes(tmp_path)
    release_recipes = discover_release_script_command_recipes(tmp_path)
    recipes = {
        recipe.recipe_id: recipe
        for recipe in [
            *package_recipes,
            *eval_recipes,
            *docs_recipes,
            *release_recipes,
        ]
    }

    assert recipes["recipe:pyproject:glassbox-fixture"].confidence == (
        RepositoryIntelligenceConfidence.LOW
    )
    assert recipes["recipe:node:frontend:test"].command == "pnpm --dir frontend test"
    assert recipes["recipe:eval-recipe:docs-only:0"].scope_paths == [Path("docs")]
    assert recipes["recipe:eval-profile:release-candidate"].timeout_seconds == 600
    release_script_recipe = recipes[
        "recipe:release-script:scripts:validate_v1_release_gate.py"
    ]
    assert release_script_recipe.risk == RepositoryIntelligenceCommandRisk.READ_ONLY
    assert recipes["recipe:docs:docs:recipe.md:0"].provenance[0].source_type == (
        RepositoryIndexSourceType.DOCUMENTATION
    )

    deduped_recipe = next(
        recipe
        for recipe in dedupe_command_recipes([*eval_recipes, *docs_recipes])
        if recipe.command
        == "uv run pytest tests/unit/test_release_candidate_docs.py -q"
    )
    assert {source.path for source in deduped_recipe.provenance} == {
        Path("evals/recipes.json"),
        Path("docs/recipe.md"),
    }


def test_repository_owner_subsystem_release_helpers_preserve_advisory_metadata(
    tmp_path: Path,
) -> None:
    _seed_repository(tmp_path)

    packages = discover_repository_intelligence_packages(tmp_path)
    package_recipes = discover_package_command_recipes(
        tmp_path, packages.package_boundaries
    )
    command_recipes = dedupe_command_recipes(
        [
            *package_recipes,
            *discover_eval_command_recipes(tmp_path),
            *discover_release_script_command_recipes(tmp_path),
        ]
    )
    codeowners = discover_codeowners_ownership_hints(tmp_path)
    subsystems = discover_repository_intelligence_subsystems(
        tmp_path, packages.package_boundaries
    )
    subsystem_owners = discover_subsystem_owner_hints(tmp_path, subsystems)
    release_surfaces = discover_release_surface_hints(tmp_path, command_recipes)

    assert any(
        hint.owner_label == "@docs-team"
        and hint.scope_paths == [Path("docs")]
        and hint.provenance[0].line_start == 1
        for hint in codeowners
    )
    frontend_subsystem = next(
        subsystem
        for subsystem in subsystems
        if subsystem.subsystem_id == "subsystem:frontend"
    )
    assert frontend_subsystem.package_ids == ["app:frontend"]
    frontend_owner = next(
        owner for owner in subsystem_owners if owner.subsystem == "subsystem:frontend"
    )
    assert "not a person" in frontend_owner.limitations[0]
    release_candidate = next(
        surface
        for surface in release_surfaces
        if surface.kind == RepositoryIntelligenceReleaseSurfaceKind.RELEASE_CANDIDATE
    )
    assert release_candidate.surface_id == "release-surface:release-candidate"
    assert {
        "recipe:eval-profile:release-candidate",
        "recipe:release-script:scripts:validate_v1_release_gate.py",
    } <= set(release_candidate.command_recipe_ids)


def test_repository_intelligence_snapshot_v2_round_trips_rich_schema(
    tmp_path: Path,
) -> None:
    _seed_repository(tmp_path)
    snapshot = build_and_write_repository_index(tmp_path)
    provenance = RepositoryIndexProvenance(
        source_type=RepositoryIndexSourceType.MANIFEST,
        path=Path("pyproject.toml"),
    )
    enriched = snapshot.model_copy(
        update={
            "source_manifests": [
                RepositoryIntelligenceSourceManifest(
                    manifest_id="manifest:pyproject",
                    path=Path("pyproject.toml"),
                    source_type=RepositoryIndexSourceType.MANIFEST,
                    role="python project manifest",
                    digest="b" * 64,
                    provenance=[provenance],
                )
            ],
            "source_roots": [
                RepositoryIntelligencePathHint(
                    hint_id="source-root:src",
                    kind=RepositoryIntelligencePathKind.SOURCE_ROOT,
                    path=Path("src"),
                    language="python",
                    confidence=RepositoryIntelligenceConfidence.HIGH,
                    provenance=[provenance],
                )
            ],
            "test_roots": [
                RepositoryIntelligencePathHint(
                    hint_id="test-root:tests",
                    kind=RepositoryIntelligencePathKind.TEST_ROOT,
                    path=Path("tests"),
                    language="python",
                    confidence=RepositoryIntelligenceConfidence.HIGH,
                    provenance=[provenance],
                )
            ],
            "package_boundaries": [
                RepositoryIntelligencePackageBoundary(
                    package_id="package:fixture",
                    name="fixture",
                    kind=RepositoryIntelligencePackageKind.PYTHON,
                    root=Path("."),
                    manifest_paths=[Path("pyproject.toml")],
                    source_roots=[Path("src")],
                    test_roots=[Path("tests")],
                    confidence=RepositoryIntelligenceConfidence.HIGH,
                    provenance=[provenance],
                )
            ],
            "command_recipes": [
                RepositoryIntelligenceCommandRecipe(
                    recipe_id="recipe:pytest",
                    name="backend tests",
                    command="uv run pytest tests",
                    purpose=CommandPurpose.TEST,
                    review_relevance=CommandReviewRelevance.VERIFICATION,
                    risk=RepositoryIntelligenceCommandRisk.READ_ONLY,
                    scope_paths=[Path("src"), Path("tests")],
                    timeout_seconds=120,
                    confidence=RepositoryIntelligenceConfidence.MEDIUM,
                    provenance=[provenance],
                    limitations=["Derived recipe; execution is still operator-gated."],
                )
            ],
            "ownership_hints": [
                RepositoryIntelligenceOwnershipHint(
                    hint_id="owner:runtime",
                    owner_label="runtime maintainers",
                    scope_paths=[Path("src")],
                    subsystem="runtime",
                    confidence=RepositoryIntelligenceConfidence.LOW,
                    provenance=[provenance],
                )
            ],
            "release_sensitive_surfaces": [
                RepositoryIntelligenceReleaseSurface(
                    surface_id="release:unit",
                    name="unit verification",
                    kind=RepositoryIntelligenceReleaseSurfaceKind.COMMIT_TIME,
                    scope_paths=[Path("tests")],
                    command_recipe_ids=["recipe:pytest"],
                    confidence=RepositoryIntelligenceConfidence.MEDIUM,
                    provenance=[provenance],
                )
            ],
            "memory_references": [
                RepositoryIntelligenceMemoryReference(
                    reference_id="memory:pytest",
                    memory_id=new_workspace_memory_id(),
                    kind=WorkspaceMemoryKind.COMMAND,
                    summary="Prefer uv run pytest for backend tests.",
                    source_label="operator note",
                    confirmed_by="operator",
                    confirmed_at=snapshot.built_at,
                    confidence=RepositoryIntelligenceConfidence.MEDIUM,
                    provenance=WorkspaceMemoryProvenance(
                        source_type=WorkspaceMemorySourceType.OPERATOR,
                        source_label="operator note",
                    ),
                    limitations=["Memory-derived intelligence remains advisory."],
                )
            ],
            "limitations": [
                "Schema test data does not imply command approval or "
                "ownership authority."
            ],
        }
    )

    restored = RepositoryIndexSnapshot.model_validate_json(enriched.model_dump_json())

    assert restored.schema_version == 2
    assert restored.command_recipes[0].command == "uv run pytest tests"
    assert restored.package_boundaries[0].source_roots == [Path("src")]
    assert restored.release_sensitive_surfaces[0].command_recipe_ids == [
        "recipe:pytest"
    ]
    assert restored.memory_references[0].kind == WorkspaceMemoryKind.COMMAND


def test_repository_index_includes_confirmed_active_memory_references(
    tmp_path: Path,
) -> None:
    _seed_repository(tmp_path)
    memory = WorkspaceMemoryEntry(
        memory_id=new_workspace_memory_id(),
        session_id=new_session_id(),
        kind=WorkspaceMemoryKind.CONVENTION,
        state=WorkspaceMemoryState.ACTIVE,
        content="Generated frontend API types live in frontend/generated.",
        summary="Generated API type location",
        provenance=WorkspaceMemoryProvenance(
            source_type=WorkspaceMemorySourceType.OPERATOR,
            source_label="operator confirmation",
        ),
        created_at=_BUILT_AT,
        updated_at=_BUILT_AT,
        confirmed_by="operator",
        confirmed_at=_BUILT_AT,
        last_sequence=3,
        tags=["repository-intelligence", "generated-output"],
    )
    stale_memory = memory.model_copy(
        update={
            "memory_id": new_workspace_memory_id(),
            "state": WorkspaceMemoryState.STALE,
            "summary": "Stale memory should not enter repository intelligence",
        }
    )

    snapshot = build_and_write_repository_index(
        tmp_path,
        workspace_memory_entries=[memory, stale_memory],
    )
    summary = build_repository_index_status_summary(tmp_path)

    assert [reference.memory_id for reference in snapshot.memory_references] == [
        memory.memory_id
    ]
    assert snapshot.memory_references[0].summary == "Generated API type location"
    assert snapshot.memory_references[0].provenance.source_label == (
        "operator confirmation"
    )
    assert summary.memory_reference_count == 1


def test_repository_intelligence_snapshot_loads_legacy_v1_payload() -> None:
    payload = {
        "schema_version": 1,
        "workspace_root": "/tmp/glassbox",
        "status": "failed",
        "builder_version": "v1",
        "failure_reason": "legacy failure",
    }

    snapshot = RepositoryIndexSnapshot.model_validate(payload)

    assert snapshot.schema_version == 1
    assert snapshot.command_recipes == []
    assert snapshot.package_boundaries == []


def test_repository_intelligence_snapshot_rejects_malformed_v2_fields() -> None:
    provenance = RepositoryIndexProvenance(
        source_type=RepositoryIndexSourceType.MANIFEST,
        path=Path("pyproject.toml"),
    )

    with pytest.raises(ValidationError):
        RepositoryIntelligencePathHint(
            hint_id="source-root:absolute",
            kind=RepositoryIntelligencePathKind.SOURCE_ROOT,
            path=Path("/tmp/glassbox/src"),
            provenance=[provenance],
        )

    with pytest.raises(ValidationError):
        RepositoryIntelligenceCommandRecipe(
            recipe_id="recipe:logs",
            name="bad command",
            command="uv run pytest\nraw output follows",
            provenance=[provenance],
        )

    with pytest.raises(ValidationError):
        RepositoryIndexSnapshot(
            schema_version=1,
            workspace_root=Path("/tmp/glassbox"),
            status=RepositoryIndexFreshness.FAILED,
            failure_reason="legacy failure",
            limitations=["v2-only limitation"],
        )

    with pytest.raises(ValidationError):
        RepositoryIndexSnapshot(
            schema_version=2,
            workspace_root=Path("/tmp/glassbox"),
            status=RepositoryIndexFreshness.FAILED,
            failure_reason="duplicate recipe",
            command_recipes=[
                RepositoryIntelligenceCommandRecipe(
                    recipe_id="recipe:pytest",
                    name="backend tests",
                    command="uv run pytest",
                    provenance=[provenance],
                ),
                RepositoryIntelligenceCommandRecipe(
                    recipe_id="recipe:pytest",
                    name="unit tests",
                    command="uv run pytest tests/unit",
                    provenance=[provenance],
                ),
            ],
        )


def test_repository_index_marks_snapshot_stale_after_source_change(
    tmp_path: Path,
) -> None:
    _seed_repository(tmp_path)
    build_and_write_repository_index(tmp_path)

    (tmp_path / "src" / "sample.py").write_text(
        "class UsefulThing:\n    pass\n\ndef changed() -> None:\n    pass\n",
        encoding="utf-8",
    )

    loaded = load_repository_index(tmp_path)

    assert loaded.status == RepositoryIndexFreshness.STALE


def test_repository_index_status_explains_stale_source_inputs(
    tmp_path: Path,
) -> None:
    _seed_repository(tmp_path)
    build_and_write_repository_index(tmp_path)

    (tmp_path / "src" / "sample.py").write_text(
        "class UsefulThing:\n    pass\n\ndef changed() -> None:\n    pass\n",
        encoding="utf-8",
    )
    (tmp_path / "src" / "new_module.py").write_text(
        "VALUE = 1\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").unlink()

    summary = build_repository_index_status_summary(tmp_path)

    assert summary.status == "stale"
    assert summary.stale_reason is not None
    assert summary.freshness_cues[0].state == "stale"
    assert summary.freshness_cues[0].reason == "source_digest_changed"
    assert any(cue.source == "command-recipes" for cue in summary.freshness_cues)
    assert any(cue.source == "eval-metadata" for cue in summary.freshness_cues)
    assert summary.source_diff is not None
    assert summary.source_diff.added_count == 1
    assert summary.source_diff.removed_count == 1
    assert summary.source_diff.changed_count >= 1
    assert "src/new_module.py" in summary.source_diff.added_paths
    assert "README.md" in summary.source_diff.removed_paths
    assert "src/sample.py" in summary.source_diff.changed_paths
    assert summary.next_actions == [
        f"glassbox repo index status --cwd {tmp_path.resolve()} --json",
        f"glassbox repo index build --cwd {tmp_path.resolve()}",
    ]


def test_repository_index_status_reports_missing_guidance(tmp_path: Path) -> None:
    _seed_repository(tmp_path)

    summary = build_repository_index_status_summary(tmp_path)

    assert summary.status == "missing"
    assert summary.entry_count == 0
    assert summary.current_source_file_count > 0
    assert summary.freshness_cues[0].source == "repository-index"
    assert summary.freshness_cues[0].reason == "artifact_missing"
    assert summary.next_actions == [
        f"glassbox repo index build --cwd {tmp_path.resolve()}",
    ]


def test_repository_index_status_reports_failed_guidance(tmp_path: Path) -> None:
    _seed_repository(tmp_path)
    write_repository_index(
        tmp_path,
        RepositoryIndexSnapshot(
            workspace_root=tmp_path.resolve(),
            status=RepositoryIndexFreshness.FAILED,
            failure_reason="parser crashed",
        ),
    )

    summary = build_repository_index_status_summary(tmp_path)

    assert summary.status == "failed"
    assert summary.failure_reason == "parser crashed"
    assert summary.stale_reason == "parser crashed"
    assert summary.freshness_cues[0].state == "degraded"
    assert summary.freshness_cues[0].reason == "build_failed"
    assert summary.detail.startswith("The last repository index refresh failed")
    assert summary.next_actions == [
        f"glassbox repo index status --cwd {tmp_path.resolve()} --json",
        f"glassbox repo index build --cwd {tmp_path.resolve()}",
    ]


def test_repository_index_status_classifies_corrupted_snapshot(tmp_path: Path) -> None:
    _seed_repository(tmp_path)
    repository_index_path(tmp_path).parent.mkdir()
    repository_index_path(tmp_path).write_text("{not-json", encoding="utf-8")

    with pytest.raises(RepositoryIndexLoadError) as exc_info:
        load_repository_index(tmp_path)
    summary = build_repository_index_status_summary(tmp_path)

    assert exc_info.value.reason == "corrupted_snapshot"
    assert summary.status == "failed"
    assert summary.failure_reason is not None
    assert "not valid JSON" in summary.failure_reason
    assert summary.freshness_cues[0].state == "degraded"
    assert summary.freshness_cues[0].safe_next_actions == [
        f"glassbox repo index status --cwd {tmp_path.resolve()} --json",
        f"glassbox repo index build --cwd {tmp_path.resolve()}",
    ]


def test_repository_index_status_classifies_unsupported_schema(
    tmp_path: Path,
) -> None:
    _seed_repository(tmp_path)
    repository_index_path(tmp_path).parent.mkdir()
    repository_index_path(tmp_path).write_text(
        json.dumps(
            {
                "schema_version": 99,
                "workspace_root": str(tmp_path),
                "status": "fresh",
                "built_at": _BUILT_AT.isoformat(),
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RepositoryIndexLoadError) as exc_info:
        load_repository_index(tmp_path)
    summary = build_repository_index_status_summary(tmp_path)

    assert exc_info.value.reason == "unsupported_schema_version"
    assert summary.status == "failed"
    assert summary.failure_reason is not None
    assert "unsupported schema version 99" in summary.failure_reason


def test_repository_intelligence_refresh_writes_index_and_topology(
    tmp_path: Path,
) -> None:
    _seed_repository(tmp_path)

    result = refresh_repository_intelligence(tmp_path)
    loaded_index = load_repository_index(tmp_path)
    loaded_topology = load_workspace_topology(tmp_path)

    assert result.index_path == repository_index_path(tmp_path)
    assert result.topology_path == workspace_topology_path(tmp_path)
    assert result.index_entry_count == len(loaded_index.entries)
    assert result.topology_component_count == len(loaded_topology.components)
    assert result.command_recipe_count == len(loaded_index.command_recipes)
    assert result.memory_reference_count == 0
    assert {component.component_id for component in loaded_topology.components} >= {
        "package:fixture",
        "app:frontend",
    }


def _seed_repository(root: Path) -> None:
    (root / "src").mkdir()
    (root / "docs").mkdir()
    (root / "evals" / "cases").mkdir(parents=True)
    (root / "frontend").mkdir()
    (root / "frontend" / "generated").mkdir()
    (root / "frontend" / "out").mkdir()
    (root / ".github").mkdir()
    (root / "tests").mkdir()
    (root / "node_modules").mkdir()
    (root / "pyproject.toml").write_text(
        """
[project]
name = "fixture"
dependencies = ["pydantic>=2"]

[project.scripts]
glassbox-fixture = "fixture:main"
""".strip(),
        encoding="utf-8",
    )
    (root / "README.md").write_text("# Fixture\n", encoding="utf-8")
    (root / ".github" / "CODEOWNERS").write_text(
        "docs/* @docs-team\nfrontend/* @frontend-team\n",
        encoding="utf-8",
    )
    (root / "docs" / "architecture.md").write_text("# Architecture\n", encoding="utf-8")
    (root / "evals" / "cases" / "example.json").write_text("{}\n", encoding="utf-8")
    (root / "evals" / "recipes.json").write_text(
        json.dumps(
            {
                "manifest_version": 1,
                "recipes": [
                    {
                        "recipe_id": "docs-only",
                        "title": "Docs checks",
                        "path_globs": ["docs/*.md"],
                        "commands": [
                            "uv run pytest tests/unit/test_release_candidate_docs.py -q"
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (root / "evals" / "profiles.json").write_text(
        json.dumps(
            {
                "manifest_version": 1,
                "profiles": [
                    {
                        "profile_id": "release-candidate",
                        "title": "Release Candidate",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (root / "src" / "sample.py").write_text(
        "class UsefulThing:\n    pass\n\ndef helper() -> None:\n    pass\n",
        encoding="utf-8",
    )
    (root / "tests" / "test_example.py").write_text(
        "def test_example() -> None:\n    assert True\n",
        encoding="utf-8",
    )
    (root / "frontend" / "package.json").write_text(
        '{"scripts":{"test":"vitest"},"dependencies":{"react":"19.0.0"}}',
        encoding="utf-8",
    )
    (root / "frontend" / "pnpm-lock.yaml").write_text("", encoding="utf-8")
    (root / "frontend" / "generated" / "api-types.ts").write_text(
        "export type Api = {};\n",
        encoding="utf-8",
    )
    (root / "frontend" / "out" / "index.html").write_text(
        "<html></html>\n",
        encoding="utf-8",
    )
    (root / "node_modules" / "ignored.py").write_text(
        "class Ignored:\n    pass\n",
        encoding="utf-8",
    )
    (root / "scripts").mkdir()
    (root / "scripts" / "validate_v1_release_gate.py").write_text(
        "def main() -> None: pass\n",
        encoding="utf-8",
    )
