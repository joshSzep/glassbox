"""Unit coverage for deterministic repository intelligence indexing."""

from pathlib import Path

from glassbox.core import RepositoryIndexFreshness
from glassbox.core import RepositoryIndexSourceType
from glassbox.runtime.repository_index import build_and_write_repository_index
from glassbox.runtime.repository_index import get_repository_index_entry
from glassbox.runtime.repository_index import load_repository_index
from glassbox.runtime.repository_index import repository_index_path
from glassbox.runtime.repository_index import search_repository_index


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
    assert loaded.status == RepositoryIndexFreshness.FRESH
    assert any(entry.name == "pyproject.toml" for entry in loaded.entries)
    assert any(entry.name == "docs/architecture.md" for entry in loaded.entries)
    assert any(entry.name == "tests/test_example.py" for entry in loaded.entries)
    assert any(entry.name == "frontend:test" for entry in loaded.entries)
    assert any(entry.name == "python dependencies" for entry in loaded.entries)
    assert all("node_modules" not in entry.entry_id for entry in loaded.entries)
    assert fetched.entry_id == symbol_entry.entry_id
    assert (
        fetched.provenance[0].source_type == RepositoryIndexSourceType.STATIC_ANALYSIS
    )
    assert fetched.provenance[0].line_start == 1


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


def _seed_repository(root: Path) -> None:
    (root / "src").mkdir()
    (root / "docs").mkdir()
    (root / "evals" / "cases").mkdir(parents=True)
    (root / "frontend").mkdir()
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
    (root / "node_modules" / "ignored.py").write_text(
        "class Ignored:\n    pass\n",
        encoding="utf-8",
    )
