"""Replay outcome triage and operator-facing reporting helpers."""

from typing import Any

from glassbox.runtime.replay_models import ReplayResult
from glassbox.runtime.replay_models import ReplayTriage


def build_replay_result(**kwargs: Any) -> ReplayResult:
    result = ReplayResult(**kwargs)
    return result.model_copy(update={"triage": build_replay_triage(result)})


def build_replay_triage(result: ReplayResult) -> ReplayTriage:
    if result.outcome == "exact_match":
        if result.baseline is not None and result.baseline.cancellations:
            return ReplayTriage(
                severity="info",
                classification="exact_match",
                headline=(
                    "replay preserved the recorded cancellation outcome and final "
                    "state without treating operator cancellation as failure"
                ),
                impacted_dimensions=["cancellations", "final_state"],
                recommended_inspection_path=(
                    "Inspect cancellation events, cancelled tool output, and the "
                    "replay turn-output artifact for the recorded turn."
                ),
            )
        return ReplayTriage(
            severity="info",
            classification="exact_match",
            headline=(
                "replay matched the recorded transcript, tool flow, and final state"
            ),
        )

    if result.outcome == "behavioral_drift":
        impacted_dimensions = [
            dimension
            for mismatch in result.mismatches
            if (dimension := mismatch_dimension(mismatch)) is not None
        ]
        first_dimension = impacted_dimensions[0] if impacted_dimensions else None
        return ReplayTriage(
            severity="warning",
            classification="behavioral_drift",
            headline=behavioral_drift_headline(first_dimension),
            first_relevant_change=result.mismatches[0] if result.mismatches else None,
            impacted_dimensions=impacted_dimensions,
            recommended_inspection_path=behavioral_inspection_path(first_dimension),
        )

    if result.outcome == "manifest_drift":
        return manifest_drift_triage(result.message)

    if result.outcome == "unsupported_session":
        return ReplayTriage(
            severity="error",
            classification="unsupported_session",
            headline=result.message or "replay bundle is not supported by this runtime",
            first_relevant_change=result.message,
            recommended_inspection_path=(
                "Inspect the replay bundle version and runtime compatibility for the "
                "recorded session."
            ),
        )

    return ReplayTriage(
        severity="error",
        classification="replay_failure",
        headline=result.message or "replay failed before comparison completed",
        first_relevant_change=result.message,
        recommended_inspection_path=(
            "Inspect the replay bundle, retained replay artifacts, and runtime error "
            "surface for missing or invalid inputs."
        ),
    )


def manifest_drift_triage(message: str | None) -> ReplayTriage:
    clauses = drift_message_clauses(message)
    first_change = clauses[0] if clauses else message
    drift_sources = [
        source_name
        for clause in clauses
        if (source_name := context_source_name_from_clause(clause)) is not None
    ]
    if drift_sources or any("enriched context" in clause for clause in clauses):
        primary_source = drift_sources[0] if drift_sources else None
        return ReplayTriage(
            severity="error",
            classification="context_source_drift",
            headline=context_source_headline(primary_source, first_change),
            first_relevant_change=first_change,
            drift_sources=drift_sources,
            recommended_inspection_path=context_source_inspection_path(primary_source),
        )

    return ReplayTriage(
        severity="error",
        classification="manifest_drift",
        headline=manifest_drift_headline(first_change),
        first_relevant_change=first_change,
        drift_sources=manifest_drift_sources(first_change),
        recommended_inspection_path=manifest_drift_inspection_path(first_change),
    )


def drift_message_clauses(message: str | None) -> list[str]:
    if message is None:
        return []
    return [clause.strip() for clause in message.split(";") if clause.strip()]


def context_source_name_from_clause(clause: str) -> str | None:
    markers = (
        "source drifted: ",
        "source added: ",
        "source missing: ",
        "provenance changed: ",
        "schema version changed: ",
        "inheritance changed: ",
        "item count changed: ",
        "overflow count changed: ",
    )
    for marker in markers:
        if marker in clause:
            source_name = clause.partition(marker)[2].strip()
            return source_name or None
    return None


def manifest_drift_headline(first_change: str | None) -> str:
    if first_change is None:
        return "replay manifest drifted before behavior comparison"
    if first_change.startswith("prepared turn"):
        return "prepared turn drifted before model execution"
    if first_change.startswith("tool request no longer matches"):
        return "tool request drifted from the recorded replay manifest"
    if first_change.startswith("current runtime no longer exposes"):
        return "recorded replay tools are no longer available in the runtime"
    if first_change.startswith("live replay turn did not include enriched context"):
        return "live replay turn omitted recorded enriched context"
    return first_change


def manifest_drift_sources(first_change: str | None) -> list[str]:
    if first_change is None:
        return []
    if first_change.startswith("prepared turn"):
        return ["prepared_turn"]
    if first_change.startswith("tool request no longer matches"):
        return ["tool_request"]
    if first_change.startswith("current runtime no longer exposes"):
        return ["tool_registry"]
    if first_change.startswith("live replay turn did not include enriched context"):
        return ["enriched_context"]
    return []


def manifest_drift_inspection_path(first_change: str | None) -> str:
    if first_change is None:
        return "Inspect the recorded replay manifest and live replay inputs."
    if first_change.startswith("prepared turn"):
        return (
            "Inspect the recorded prepared turn manifest and the current prompt and "
            "turn-context inputs."
        )
    if first_change.startswith("tool request no longer matches"):
        return (
            "Inspect the recorded tool request manifest and the live tool-call "
            "arguments for the replayed step."
        )
    if first_change.startswith("current runtime no longer exposes"):
        return (
            "Inspect the current tool registry and the recorded replay bundle tool "
            "names."
        )
    if first_change.startswith("live replay turn did not include enriched context"):
        return (
            "Inspect the turn-context builder and the recorded enriched-context "
            "sources for this replay step."
        )
    return (
        "Inspect the recorded replay manifest and the first replay step that drifted."
    )


def context_source_headline(
    source_name: str | None,
    first_change: str | None,
) -> str:
    if source_name is not None:
        return f"recorded enriched context drifted for {source_name}"
    return first_change or "recorded enriched context drifted"


def context_source_inspection_path(source_name: str | None) -> str:
    if source_name == "workspace_memory":
        return (
            "Inspect workspace memory entries, provenance, confirmation state, and "
            "the context section that consumed them."
        )
    if source_name == "repository_index":
        return (
            "Inspect the repository intelligence index snapshot, freshness state, "
            "and source paths used for turn context."
        )
    if source_name == "policy":
        return (
            "Inspect policy decision traces, repository-owned safe autonomy rules, "
            "and approval-mode calibration for the drifting action."
        )
    if source_name == "budget":
        return (
            "Inspect autonomy budget decisions and the budget posture projection for "
            "the first exhausted or changed counter."
        )
    if source_name == "verification":
        return (
            "Inspect verification plan events, retained failure artifacts, and the "
            "verify-repair attempt that first diverged."
        )
    if source_name == "provider_advisory":
        return (
            "Inspect provider advisory evidence, canary profile selection, and "
            "whether live-provider checks were intentionally included."
        )
    if source_name == "runtime_notes":
        return (
            "Inspect runtime note inputs and replay enriched-context capture for "
            "runtime_notes."
        )
    if source_name == "repository_context":
        return (
            "Inspect repository-context summarization and the recorded repo_context "
            "payload."
        )
    if source_name == "working_set":
        return (
            "Inspect working-set selection, normalization, and the recorded "
            "working-set summary."
        )
    if source_name == "pytest_failure_digest":
        return (
            "Inspect artifact-backed context summaries and the underlying pytest "
            "failure digest artifact."
        )
    if source_name == "artifact_context":
        return (
            "Inspect artifact-backed context summaries and the source artifacts used "
            "to build them."
        )
    return (
        "Inspect the recorded enriched-context sources and the live context builder "
        "output for the drifting source."
    )


def behavioral_drift_headline(dimension: str | None) -> str:
    if dimension is None:
        return "behavioral drift detected during normalized replay comparison"
    if dimension == "budget_posture":
        return "autonomy budget posture drifted during replay"
    if dimension == "verification":
        return "verification evidence drifted during replay"
    if dimension == "workspace_memory":
        return "workspace memory evidence drifted during replay"
    if dimension == "repository_index":
        return "repository intelligence evidence drifted during replay"
    if dimension == "policy":
        return "policy decision evidence drifted during replay"
    if dimension == "provider_advisory":
        return "provider advisory evidence drifted during replay"
    return f"behavioral drift detected in {dimension}"


def behavioral_inspection_path(dimension: str | None) -> str:
    if dimension == "transcript":
        return (
            "Inspect transcript messages and the last recorded model response in the "
            "retained replay artifact."
        )
    if dimension == "tool_calls":
        return (
            "Inspect tool request and tool result manifests plus the replayed "
            "tool-call summaries."
        )
    if dimension == "approvals":
        return "Inspect approval request and resolution events in the replayed session."
    if dimension == "questions":
        return "Inspect ask_user question and answer events in the replayed session."
    if dimension == "cancellations":
        return (
            "Inspect cancellation requested, acknowledged, tool-cancelled, and "
            "turn-cancelled events plus retained partial output artifacts."
        )
    if dimension == "task_plans":
        return (
            "Inspect task-plan events, captured plan proposal details, and the "
            "normalized task projection in the replay bundle."
        )
    if dimension == "budget_posture":
        return (
            "Inspect autonomy budget decision events, exhausted counters, and the "
            "budget posture projection for the first divergent task or session."
        )
    if dimension == "verification":
        return (
            "Inspect verification planned/started/failed/completed events, retained "
            "failure artifacts, and the verify-repair attempt sequence."
        )
    if dimension == "workspace_memory":
        return (
            "Inspect workspace memory create/update/use events, source provenance, "
            "and context inclusion evidence."
        )
    if dimension == "repository_index":
        return (
            "Inspect repository-index snapshots, freshness status, changed source "
            "paths, and repository context injected into the turn."
        )
    if dimension == "policy":
        return (
            "Inspect policy decision traces, approval-mode calibration, and any "
            "repository-owned safe autonomy rules that matched the action."
        )
    if dimension == "provider_advisory":
        return (
            "Inspect eval recommendation output, provider canary profile selection, "
            "and advisory live-provider evidence."
        )
    if dimension == "event_families":
        return (
            "Inspect the replay session event stream for added or missing event "
            "families and tool-flow branches."
        )
    if dimension == "final_state":
        return (
            "Inspect terminal session state plus pending approval and question flags."
        )
    if dimension == "lineage":
        return (
            "Inspect session lineage and fork metadata captured in the replay bundle."
        )
    if dimension == "inherited_transcript":
        return "Inspect inherited transcript imports and replay bundle fork boundaries."
    if dimension == "post_fork_transcript":
        return "Inspect post-fork transcript messages and replayed branch execution."
    return "Inspect the retained replay artifact for the first normalized mismatch."


def mismatch_dimension(mismatch: str) -> str | None:
    dimension, separator, _suffix = mismatch.partition(" drift")
    if separator:
        return dimension
    return None
