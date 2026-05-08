"""Unit coverage for deterministic repository intelligence indexing."""

from pathlib import Path

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
from glassbox.core import RepositoryIntelligenceOwnershipHint
from glassbox.core import RepositoryIntelligencePackageBoundary
from glassbox.core import RepositoryIntelligencePackageKind
from glassbox.core import RepositoryIntelligencePathHint
from glassbox.core import RepositoryIntelligencePathKind
from glassbox.core import RepositoryIntelligenceReleaseSurface
from glassbox.core import RepositoryIntelligenceReleaseSurfaceKind
from glassbox.core import RepositoryIntelligenceSourceManifest
from glassbox.runtime.repository_index import build_and_write_repository_index
from glassbox.runtime.repository_index import get_repository_index_entry
from glassbox.runtime.repository_index import load_repository_index
from glassbox.runtime.repository_index import repository_index_path
from glassbox.runtime.repository_index import search_repository_index
from glassbox.runtime.repository_index import write_repository_index
from glassbox.runtime.repository_index_discovery import MAX_INDEXED_FILES
from glassbox.runtime.repository_index_discovery import classify_repository_path
from glassbox.runtime.repository_index_status import (
    build_repository_index_status_summary,
)


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
    assert summary.detail.startswith("The last repository index refresh failed")
    assert summary.next_actions == [
        f"glassbox repo index status --cwd {tmp_path.resolve()} --json",
        f"glassbox repo index build --cwd {tmp_path.resolve()}",
    ]


def _seed_repository(root: Path) -> None:
    (root / "src").mkdir()
    (root / "docs").mkdir()
    (root / "evals" / "cases").mkdir(parents=True)
    (root / "frontend").mkdir()
    (root / "frontend" / "generated").mkdir()
    (root / "frontend" / "out").mkdir()
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
    (root / "docs" / "architecture.md").write_text("# Architecture\n", encoding="utf-8")
    (root / "evals" / "cases" / "example.json").write_text("{}\n", encoding="utf-8")
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
