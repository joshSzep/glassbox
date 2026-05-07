"""Boundary checks for concrete store repository adapters."""

from collections.abc import Mapping
from importlib import import_module
from types import ModuleType

from glassbox.services import ArtifactRepository
from glassbox.services import SessionRepository
from glassbox.store.repositories import FilesystemArtifactRepository
from glassbox.store.repositories import SQLiteSessionRepository

DOMAIN_EXPORTS: Mapping[str, set[str]] = {
    "glassbox.store.repository_sessions": {"_SQLiteSessionMethods"},
    "glassbox.store.repository_events": {"_SQLiteEventMethods"},
    "glassbox.store.repository_projection_reads": {"_SQLiteProjectionReadMethods"},
    "glassbox.store.repository_background_jobs": {"_SQLiteBackgroundJobMethods"},
    "glassbox.store.repository_workspace_memory": {"_SQLiteWorkspaceMemoryMethods"},
    "glassbox.store.repository_tasks": {"_SQLiteTaskMethods"},
    "glassbox.store.repository_branch_search": {"_SQLiteBranchSearchMethods"},
    "glassbox.store.repository_changeset_detail": {"_SQLiteChangesetDetailMethods"},
    "glassbox.store.repository_changeset_readiness": {
        "_SQLiteChangesetReviewReadinessMethods"
    },
    "glassbox.store.repository_changesets": {
        "_SQLiteChangesetDetailMethods",
        "_SQLiteChangesetMethods",
        "_SQLiteChangesetReviewReadinessMethods",
    },
    "glassbox.store.repository_manual_evidence": {"_SQLiteManualEvidenceMethods"},
    "glassbox.store.repository_review_feedback": {"_SQLiteReviewFeedbackMethods"},
    "glassbox.store.repository_review_loop": {
        "_SQLiteManualEvidenceMethods",
        "_SQLiteReviewFeedbackMethods",
        "_SQLiteReviewLoopMethods",
    },
    "glassbox.store.repository_artifacts": {"FilesystemArtifactRepository"},
}


def test_repository_facade_exports_stable_public_adapters() -> None:
    import glassbox.store.repositories as facade

    assert facade.__all__ == [
        "FilesystemArtifactRepository",
        "SQLiteSessionRepository",
    ]
    assert facade.SQLiteSessionRepository is SQLiteSessionRepository
    assert facade.FilesystemArtifactRepository is FilesystemArtifactRepository


def test_repository_domain_modules_export_one_adapter_family() -> None:
    for module_name, exported_names in DOMAIN_EXPORTS.items():
        module = import_module(module_name)

        assert set(module.__all__) == exported_names


def test_sqlite_session_repository_inherits_domain_method_families() -> None:
    loaded_modules: dict[str, ModuleType] = {
        module_name: import_module(module_name) for module_name in DOMAIN_EXPORTS
    }

    assert issubclass(
        SQLiteSessionRepository,
        loaded_modules["glassbox.store.repository_sessions"]._SQLiteSessionMethods,
    )
    assert issubclass(
        SQLiteSessionRepository,
        loaded_modules["glassbox.store.repository_events"]._SQLiteEventMethods,
    )
    assert issubclass(
        SQLiteSessionRepository,
        loaded_modules[
            "glassbox.store.repository_projection_reads"
        ]._SQLiteProjectionReadMethods,
    )
    assert issubclass(
        SQLiteSessionRepository,
        loaded_modules[
            "glassbox.store.repository_background_jobs"
        ]._SQLiteBackgroundJobMethods,
    )
    assert issubclass(
        SQLiteSessionRepository,
        loaded_modules[
            "glassbox.store.repository_workspace_memory"
        ]._SQLiteWorkspaceMemoryMethods,
    )
    assert issubclass(
        SQLiteSessionRepository,
        loaded_modules["glassbox.store.repository_tasks"]._SQLiteTaskMethods,
    )
    assert issubclass(
        SQLiteSessionRepository,
        loaded_modules[
            "glassbox.store.repository_branch_search"
        ]._SQLiteBranchSearchMethods,
    )
    assert issubclass(
        SQLiteSessionRepository,
        loaded_modules["glassbox.store.repository_changesets"]._SQLiteChangesetMethods,
    )
    assert issubclass(
        loaded_modules["glassbox.store.repository_changesets"]._SQLiteChangesetMethods,
        loaded_modules[
            "glassbox.store.repository_changeset_detail"
        ]._SQLiteChangesetDetailMethods,
    )
    assert issubclass(
        loaded_modules["glassbox.store.repository_changesets"]._SQLiteChangesetMethods,
        loaded_modules[
            "glassbox.store.repository_changesets"
        ]._SQLiteChangesetReviewReadinessMethods,
    )
    assert issubclass(
        SQLiteSessionRepository,
        loaded_modules[
            "glassbox.store.repository_review_loop"
        ]._SQLiteReviewLoopMethods,
    )
    assert issubclass(
        loaded_modules[
            "glassbox.store.repository_review_loop"
        ]._SQLiteReviewLoopMethods,
        loaded_modules[
            "glassbox.store.repository_review_feedback"
        ]._SQLiteReviewFeedbackMethods,
    )
    assert issubclass(
        loaded_modules[
            "glassbox.store.repository_review_loop"
        ]._SQLiteReviewLoopMethods,
        loaded_modules[
            "glassbox.store.repository_manual_evidence"
        ]._SQLiteManualEvidenceMethods,
    )


def test_repository_adapters_remain_protocol_compatible() -> None:
    assert issubclass(SQLiteSessionRepository, SessionRepository)
    assert issubclass(FilesystemArtifactRepository, ArtifactRepository)
