"""Runtime orchestration package for Glassbox."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from glassbox.runtime.bus import EventBus, EventBusStats, EventBusSubscription
from glassbox.runtime.context import (
    RuntimeContext,
    RuntimeInfrastructure,
    RuntimeRepositories,
    RuntimeServices,
)
from glassbox.runtime.context_builder import (
    PYTEST_FAILURE_DIGEST_ARTIFACT_KIND,
    ArtifactBackedContextSnapshot,
    ArtifactBackedContextSummarySnapshot,
    PolicyContext,
    PytestFailureDigestArtifact,
    RepositoryContextSnapshot,
    RuntimeContextNoteSnapshot,
    RuntimeContextSnapshot,
    ToolSchema,
    TurnContext,
    TurnContextBuilder,
    WorkingSetItemSnapshot,
    WorkingSetSnapshot,
    build_artifact_backed_context_snapshot,
    build_pytest_failure_digest_artifact,
    build_repository_context_snapshot,
    build_runtime_context_snapshot,
    build_working_set_snapshot,
    format_repository_context_for_prompt,
    format_tool_schemas_for_prompt,
    format_transcript_for_prompt,
    normalize_tool_schemas,
)
from glassbox.runtime.provider_config import (
    ProviderSecretConfig,
    RuntimeProviderConfig,
    load_runtime_provider_config,
)

if TYPE_CHECKING:
    from glassbox.runtime.eval_runner import EvalCaseResult, EvalRunner, EvalSuiteResult
    from glassbox.runtime.evals import (
        EvalCase,
        EvalCaseExpectation,
        EvalCaseManifest,
        discover_eval_case_files,
        load_eval_case,
        load_eval_suite,
    )
    from glassbox.runtime.replay import ReplayBundle, ReplayResult, ReplayRunner
    from glassbox.runtime.supervisor import SessionSupervisor
    from glassbox.runtime.turn_engine import TurnEngine


def __getattr__(name: str) -> Any:
    if name in {"default_database_path", "open_runtime_context"}:
        from glassbox.runtime import bootstrap as _bootstrap

        return getattr(_bootstrap, name)
    if name == "SessionSupervisor":
        from glassbox.runtime.supervisor import SessionSupervisor as _SessionSupervisor

        return _SessionSupervisor
    if name in {
        "EvalCaseResult",
        "EvalRunner",
        "EvalSuiteResult",
        "EvalCase",
        "EvalCaseExpectation",
        "EvalCaseManifest",
        "discover_eval_case_files",
        "load_eval_case",
        "load_eval_suite",
    }:
        if name in {"EvalCaseResult", "EvalRunner", "EvalSuiteResult"}:
            from glassbox.runtime import eval_runner as _eval_runner

            return getattr(_eval_runner, name)
        from glassbox.runtime import evals as _evals

        return getattr(_evals, name)
    if name in {"ReplayBundle", "ReplayResult", "ReplayRunner"}:
        from glassbox.runtime import replay as _replay

        return getattr(_replay, name)
    if name == "TurnEngine":
        from glassbox.runtime.turn_engine import TurnEngine as _TurnEngine

        return _TurnEngine
    raise AttributeError(f"module 'glassbox.runtime' has no attribute {name!r}")


__all__ = [
    "default_database_path",
    "ArtifactBackedContextSnapshot",
    "ArtifactBackedContextSummarySnapshot",
    "build_artifact_backed_context_snapshot",
    "build_pytest_failure_digest_artifact",
    "build_repository_context_snapshot",
    "build_runtime_context_snapshot",
    "build_working_set_snapshot",
    "discover_eval_case_files",
    "EvalCase",
    "EvalCaseExpectation",
    "EvalCaseManifest",
    "EvalCaseResult",
    "EvalRunner",
    "EvalSuiteResult",
    "EventBus",
    "EventBusStats",
    "EventBusSubscription",
    "load_eval_case",
    "load_eval_suite",
    "open_runtime_context",
    "PolicyContext",
    "PYTEST_FAILURE_DIGEST_ARTIFACT_KIND",
    "PytestFailureDigestArtifact",
    "RepositoryContextSnapshot",
    "ProviderSecretConfig",
    "ReplayBundle",
    "ReplayResult",
    "ReplayRunner",
    "RuntimeContext",
    "RuntimeContextNoteSnapshot",
    "RuntimeContextSnapshot",
    "RuntimeInfrastructure",
    "RuntimeProviderConfig",
    "RuntimeRepositories",
    "RuntimeServices",
    "SessionSupervisor",
    "ToolSchema",
    "TurnEngine",
    "TurnContext",
    "TurnContextBuilder",
    "WorkingSetItemSnapshot",
    "WorkingSetSnapshot",
    "format_repository_context_for_prompt",
    "format_tool_schemas_for_prompt",
    "format_transcript_for_prompt",
    "load_runtime_provider_config",
    "normalize_tool_schemas",
]
