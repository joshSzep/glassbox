"""Source-specific cue derivation for workspace knowledge posture."""

from glassbox.runtime.knowledge_posture_guidance import checkpoint_inspection_commands
from glassbox.runtime.knowledge_posture_guidance import compaction_inspection_commands
from glassbox.runtime.knowledge_posture_guidance import memory_inspection_commands
from glassbox.runtime.knowledge_posture_guidance import (
    provider_evidence_inspection_commands,
)
from glassbox.runtime.knowledge_posture_guidance import (
    repository_index_inspection_commands,
)
from glassbox.runtime.knowledge_posture_guidance import verification_inspection_commands
from glassbox.runtime.knowledge_posture_models import KnowledgeCueProvenance
from glassbox.runtime.knowledge_posture_models import KnowledgePostureCue
from glassbox.runtime.knowledge_posture_models import KnowledgePostureStatus
from glassbox.runtime.knowledge_posture_provenance import checkpoint_provenance
from glassbox.runtime.knowledge_posture_provenance import compaction_provenance
from glassbox.runtime.knowledge_posture_provenance import memory_provenance
from glassbox.runtime.knowledge_posture_provenance import (
    session_without_checkpoint_provenance,
)
from glassbox.runtime.knowledge_posture_provenance import sort_latest
from glassbox.runtime.knowledge_posture_sources import KnowledgePostureSources


def build_knowledge_cues_from_sources(
    sources: KnowledgePostureSources,
) -> list[KnowledgePostureCue]:
    return [
        _memory_cue(sources),
        _repository_index_cue(sources),
        _checkpoint_cue(sources),
        _compaction_cue(sources),
        _verification_cue(sources),
        _provider_cue(sources),
    ]


def _memory_cue(sources: KnowledgePostureSources) -> KnowledgePostureCue:
    memory = sources.memory
    if memory.stale_count:
        status: KnowledgePostureStatus = "stale"
        summary = f"{memory.stale_count} stale memory entrie(s) need review."
    elif memory.invalidated_count and not memory.active_count:
        status = "invalidated"
        summary = "Only invalidated or inactive workspace memory is available."
    elif memory.active_count:
        status = "fresh"
        summary = f"{memory.active_count} active workspace memory entrie(s)."
    elif memory.imported_count:
        status = "historical-only"
        summary = f"{memory.imported_count} imported memory entrie(s)."
    else:
        status = "missing"
        summary = "No workspace memory has been confirmed."
    return KnowledgePostureCue(
        key="workspace-memory",
        title="Workspace Memory",
        status=status,
        summary=summary,
        authoritative_source="workspace_memory projection from canonical events",
        inspect_commands=memory_inspection_commands(memory),
        source_count=memory.active_count
        + memory.stale_count
        + memory.imported_count
        + memory.invalidated_count,
        provenance=[
            memory_provenance(entry)
            for entry in sort_latest(sources.memory_entries, "updated_at")[:3]
        ],
    )


def _repository_index_cue(
    sources: KnowledgePostureSources,
) -> KnowledgePostureCue:
    repository_index = sources.repository_index
    status_map: dict[str, KnowledgePostureStatus] = {
        "fresh": "fresh",
        "stale": "stale",
        "missing": "missing",
        "failed": "degraded",
    }
    status = status_map.get(repository_index.status, "degraded")
    return KnowledgePostureCue(
        key="repository-index",
        title="Repository Index",
        status=status,
        summary=(
            f"Repository index is {repository_index.status} with "
            f"{repository_index.entry_count} entrie(s)."
        ),
        authoritative_source="repository-index.json rebuildable artifact",
        inspect_commands=repository_index_inspection_commands(repository_index),
        source_count=repository_index.entry_count,
        provenance=[
            KnowledgeCueProvenance(
                label="Repository index snapshot",
                source_kind="repository-index",
                source_id="repository-index",
                path=repository_index.path,
                timestamp=repository_index.built_at,
                freshness=repository_index.status,
                detail=repository_index.stale_reason
                or repository_index.failure_reason
                or repository_index.detail,
            )
        ],
    )


def _checkpoint_cue(sources: KnowledgePostureSources) -> KnowledgePostureCue:
    if sources.active_session_without_checkpoint_count:
        status: KnowledgePostureStatus = "degraded"
        summary = (
            f"{sources.active_session_without_checkpoint_count} active session(s) "
            "lack checkpoint evidence."
        )
    elif sources.checkpoint_count:
        status = "fresh"
        summary = f"{sources.checkpoint_count} checkpoint record(s) are projected."
    else:
        status = "historical-only"
        summary = "No checkpoints are projected; this may be historical-only state."
    return KnowledgePostureCue(
        key="checkpoints",
        title="Checkpoints",
        status=status,
        summary=summary,
        authoritative_source=(
            "TaskCheckpointCreated events and task_checkpoints projection"
        ),
        inspect_commands=checkpoint_inspection_commands(),
        source_count=sources.checkpoint_count,
        provenance=[
            *[
                checkpoint_provenance(checkpoint)
                for checkpoint in sort_latest(
                    sources.checkpoint_records,
                    "last_sequence",
                )[:3]
            ],
            *[
                session_without_checkpoint_provenance(session)
                for session in sort_latest(
                    sources.active_sessions_without_checkpoints,
                    "updated_at",
                )[:3]
            ],
        ][:5],
    )


def _compaction_cue(sources: KnowledgePostureSources) -> KnowledgePostureCue:
    if sources.stale_compaction_count:
        status: KnowledgePostureStatus = "stale"
        summary = (
            f"{sources.stale_compaction_count} stale compaction artifact(s) "
            "need review."
        )
    elif sources.compaction_count:
        status = "fresh"
        summary = (
            f"{sources.compaction_count} fresh compaction artifact(s) are retained."
        )
    else:
        status = "missing"
        summary = "No context compaction artifacts are retained."
    return KnowledgePostureCue(
        key="compactions",
        title="Context Compactions",
        status=status,
        summary=summary,
        authoritative_source=(
            "ContextCompactionCreated events, projection, and artifacts"
        ),
        inspect_commands=compaction_inspection_commands(),
        source_count=sources.compaction_count,
        provenance=[
            compaction_provenance(compaction)
            for compaction in sort_latest(sources.compaction_records, "last_sequence")[
                :3
            ]
        ],
    )


def _verification_cue(sources: KnowledgePostureSources) -> KnowledgePostureCue:
    verification = sources.verification
    if not verification.summary_count:
        status: KnowledgePostureStatus = "missing"
        summary = "No retained eval or verification summary was found."
    elif verification.latest_suite_status == "passed":
        status = "fresh"
        summary = (
            f"Latest retained verification passed "
            f"({verification.latest_profile_id or 'unknown profile'})."
        )
    else:
        status = "degraded"
        summary = (
            f"Latest retained verification is "
            f"{verification.latest_suite_status or 'unknown'}."
        )
    return KnowledgePostureCue(
        key="verification",
        title="Verification Evidence",
        status=status,
        summary=summary,
        authoritative_source=".glassbox/evals retained summary artifacts",
        inspect_commands=verification_inspection_commands(verification),
        source_count=verification.summary_count,
        provenance=[
            KnowledgeCueProvenance(
                label="Latest retained verification summary",
                source_kind="verification-summary",
                source_id=verification.latest_profile_id,
                path=verification.latest_summary_path,
                freshness=verification.latest_suite_status,
                detail=(
                    f"exit_code={verification.latest_exit_code}; "
                    f"failed_cases={verification.latest_failed_case_count}"
                ),
            )
        ]
        if verification.latest_summary_path is not None
        else [],
    )


def _provider_cue(sources: KnowledgePostureSources) -> KnowledgePostureCue:
    provider_canary = sources.provider_canary
    if provider_canary.freshness_status in {"fresh", "warning"}:
        status: KnowledgePostureStatus = "advisory"
    elif provider_canary.freshness_status in {"stale", "incompatible"}:
        status = "stale"
    elif provider_canary.freshness_status in {"failed"}:
        status = "degraded"
    else:
        status = "missing"
    return KnowledgePostureCue(
        key="provider-evidence",
        title="Provider Evidence",
        status=status,
        summary=(
            "Provider canary evidence is advisory: "
            f"{provider_canary.latest_status}; freshness "
            f"{provider_canary.freshness_status}."
        ),
        authoritative_source="retained provider-canary summary artifacts",
        inspect_commands=provider_evidence_inspection_commands(provider_canary),
        source_count=provider_canary.summary_count,
        provenance=[
            KnowledgeCueProvenance(
                label="Latest provider canary evidence",
                source_kind="provider-evidence",
                path=provider_canary.latest_summary_path,
                timestamp=provider_canary.latest_generated_at,
                freshness=provider_canary.freshness_status,
                detail=(
                    f"status={provider_canary.latest_status}; "
                    f"provider={provider_canary.provider or 'unknown'}; "
                    f"model={provider_canary.model_name or 'unknown'}"
                ),
            )
        ]
        if provider_canary.latest_summary_path is not None
        else [],
    )


__all__ = ["build_knowledge_cues_from_sources"]
