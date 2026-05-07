"""Boundary checks for SQLite projection query modules."""

from collections.abc import Mapping
from importlib import import_module
from types import ModuleType

import glassbox.store.sqlite_queries as facade

DOMAIN_EXPORTS: Mapping[str, set[str]] = {
    "glassbox.store.sqlite_query_transcript": {"list_transcript_messages"},
    "glassbox.store.sqlite_query_runtime_notes": {"list_runtime_notes"},
    "glassbox.store.sqlite_query_tools": {"list_approvals", "list_tool_calls"},
    "glassbox.store.sqlite_query_tool_attempts": {
        "get_tool_attempt",
        "list_tool_attempts",
    },
    "glassbox.store.sqlite_query_provider_recovery": {
        "get_latest_provider_recovery",
        "list_provider_recovery",
    },
    "glassbox.store.sqlite_query_metrics": {"list_turn_metrics"},
    "glassbox.store.sqlite_query_budgets": {"get_budget_posture"},
    "glassbox.store.sqlite_query_checkpoints": {
        "get_latest_task_checkpoint",
        "list_task_checkpoints",
    },
    "glassbox.store.sqlite_query_compactions": {
        "get_context_compaction",
        "list_context_compactions",
    },
    "glassbox.store.sqlite_query_tasks": {
        "get_task",
        "list_open_blocked_tasks",
        "list_task_steps",
        "list_task_verifications",
        "list_tasks",
    },
    "glassbox.store.sqlite_query_branch_search": {
        "get_branch_search",
        "list_branch_candidates",
        "list_branch_searches",
    },
    "glassbox.store.sqlite_query_changeset_detail": {
        "get_changeset",
        "get_changeset_inventory",
        "get_changeset_verification_posture",
        "list_changeset_readiness",
        "list_changeset_review_briefs",
        "list_changeset_sources",
        "list_changesets",
    },
    "glassbox.store.sqlite_query_changesets": {
        "get_changeset",
        "get_changeset_inventory",
        "get_changeset_verification_posture",
        "list_changeset_readiness",
        "list_changeset_review_briefs",
        "list_changeset_sources",
        "list_changesets",
    },
    "glassbox.store.sqlite_query_manual_evidence": {
        "get_manual_evidence",
        "list_manual_evidence",
    },
    "glassbox.store.sqlite_query_review_feedback": {
        "get_review_feedback",
        "list_review_feedback_fixup_inventories",
        "list_review_feedback_fixup_paths",
        "list_review_feedback",
        "list_review_feedback_scopes",
    },
    "glassbox.store.sqlite_query_review_loop": {
        "get_manual_evidence",
        "get_review_feedback",
        "list_manual_evidence",
        "list_review_feedback_fixup_inventories",
        "list_review_feedback_fixup_paths",
        "list_review_feedback",
        "list_review_feedback_scopes",
    },
}


def test_sqlite_query_facade_forwards_to_domain_modules() -> None:
    for module_name, exported_names in DOMAIN_EXPORTS.items():
        module = import_module(module_name)

        assert set(module.__all__) == exported_names
        for name in exported_names:
            assert getattr(facade, name) is getattr(module, name)


def test_sqlite_query_facade_exports_every_domain_helper() -> None:
    expected_exports = set().union(*DOMAIN_EXPORTS.values())

    assert set(facade.__all__) == expected_exports


def test_sqlite_query_domains_are_split_by_projection_family() -> None:
    loaded_modules: dict[str, ModuleType] = {
        module_name: import_module(module_name) for module_name in DOMAIN_EXPORTS
    }

    assert loaded_modules["glassbox.store.sqlite_query_transcript"].__doc__
    assert loaded_modules["glassbox.store.sqlite_query_runtime_notes"].__doc__
    assert loaded_modules["glassbox.store.sqlite_query_tools"].__doc__
    assert loaded_modules["glassbox.store.sqlite_query_tool_attempts"].__doc__
    assert loaded_modules["glassbox.store.sqlite_query_provider_recovery"].__doc__
    assert loaded_modules["glassbox.store.sqlite_query_metrics"].__doc__
    assert loaded_modules["glassbox.store.sqlite_query_budgets"].__doc__
    assert loaded_modules["glassbox.store.sqlite_query_checkpoints"].__doc__
    assert loaded_modules["glassbox.store.sqlite_query_compactions"].__doc__
    assert loaded_modules["glassbox.store.sqlite_query_tasks"].__doc__
    assert loaded_modules["glassbox.store.sqlite_query_branch_search"].__doc__
    assert loaded_modules["glassbox.store.sqlite_query_changeset_detail"].__doc__
    assert loaded_modules["glassbox.store.sqlite_query_changesets"].__doc__
    assert loaded_modules["glassbox.store.sqlite_query_manual_evidence"].__doc__
    assert loaded_modules["glassbox.store.sqlite_query_review_feedback"].__doc__
    assert loaded_modules["glassbox.store.sqlite_query_review_loop"].__doc__
