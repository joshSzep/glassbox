"""Unit coverage for unified workspace knowledge posture."""

from datetime import UTC
from datetime import datetime
from uuid import uuid4

from glassbox.core.models import ContextCompactionRecord
from glassbox.core.models import TaskCheckpointRecord
from glassbox.core.models import WorkspaceMemoryEntry
from glassbox.core.models import WorkspaceMemoryProvenance
from glassbox.core.types import ContextCompactionFreshness
from glassbox.core.types import ContextCompactionScope
from glassbox.core.types import LongRunPhase
from glassbox.core.types import WorkspaceMemoryKind
from glassbox.core.types import WorkspaceMemorySourceType
from glassbox.core.types import WorkspaceMemoryState
from glassbox.runtime.knowledge_posture import build_knowledge_posture_from_sources
from glassbox.runtime.observability_models import RepositoryIndexObservability
from glassbox.runtime.observability_models import VerificationObservability
from glassbox.runtime.observability_models import WorkspaceMemoryObservability
from glassbox.runtime.provider_canary_models import ProviderCanaryEvidenceSummary


def test_knowledge_posture_reports_fresh_local_sources_with_advisory_provider() -> None:
    posture = build_knowledge_posture_from_sources(
        memory=WorkspaceMemoryObservability(
            active_count=2,
            stale_count=0,
            imported_count=0,
            invalidated_count=0,
            pruned_count=0,
            redacted_count=0,
        ),
        repository_index=RepositoryIndexObservability(
            status="fresh",
            path=".glassbox/repository-index.json",
            entry_count=12,
        ),
        checkpoint_count=1,
        active_session_without_checkpoint_count=0,
        compaction_count=1,
        stale_compaction_count=0,
        verification=VerificationObservability(
            summary_count=1,
            latest_summary_path=".glassbox/evals/summary.json",
            latest_suite_status="passed",
            latest_profile_id="commit-smoke",
        ),
        provider_canary=ProviderCanaryEvidenceSummary(
            summary_count=1,
            latest_summary_path=".glassbox/provider-canary/summary.json",
            latest_generated_at="2026-04-30T12:00:00Z",
            latest_status="passed",
            freshness_status="fresh",
        ),
    )

    assert posture.overall_status == "advisory"
    assert _cue_status(posture, "workspace-memory") == "fresh"
    assert _cue_status(posture, "repository-index") == "fresh"
    assert _cue_status(posture, "checkpoints") == "fresh"
    assert _cue_status(posture, "compactions") == "fresh"
    assert _cue_status(posture, "verification") == "fresh"
    assert _cue_status(posture, "provider-evidence") == "advisory"
    assert _cue(posture, "repository-index").provenance[0].path == (
        ".glassbox/repository-index.json"
    )
    assert _cue(posture, "verification").provenance[0].source_id == "commit-smoke"
    assert _cue(posture, "provider-evidence").provenance[0].freshness == "fresh"
    assert "glassbox provider canary evidence --cwd ." in posture.next_actions


def test_knowledge_posture_includes_bounded_source_provenance() -> None:
    session_id = uuid4()
    task_id = uuid4()
    artifact_id = uuid4()
    now = datetime(2026, 4, 30, 12, tzinfo=UTC)

    posture = build_knowledge_posture_from_sources(
        memory=WorkspaceMemoryObservability(
            active_count=1,
            stale_count=0,
            imported_count=0,
            invalidated_count=0,
            pruned_count=0,
            redacted_count=0,
        ),
        memory_entries=[
            WorkspaceMemoryEntry(
                memory_id=uuid4(),
                session_id=session_id,
                kind=WorkspaceMemoryKind.FACT,
                state=WorkspaceMemoryState.ACTIVE,
                content="Use the retained local index.",
                provenance=WorkspaceMemoryProvenance(
                    source_type=WorkspaceMemorySourceType.SESSION_EVENT,
                    source_label="operator note",
                    session_id=session_id,
                    source_sequence=7,
                ),
                created_at=now,
                updated_at=now,
                last_sequence=8,
            )
        ],
        repository_index=RepositoryIndexObservability(
            status="fresh",
            path=".glassbox/repository-index.json",
            entry_count=12,
            built_at="2026-04-30T12:00:00Z",
        ),
        checkpoint_count=1,
        checkpoint_records=[
            TaskCheckpointRecord(
                checkpoint_id=uuid4(),
                session_id=session_id,
                task_id=task_id,
                artifact_id=artifact_id,
                objective="Ship provenance",
                current_phase=LongRunPhase.TOOL_EXECUTION,
                next_action="Verify provenance",
                recovery_guidance="Continue after review",
                source_start_sequence=4,
                source_end_sequence=9,
                created_at=now,
                last_sequence=10,
            )
        ],
        compaction_count=1,
        stale_compaction_count=1,
        compaction_records=[
            ContextCompactionRecord(
                compaction_id=uuid4(),
                session_id=session_id,
                scope=ContextCompactionScope.TASK,
                source_start_sequence=2,
                source_end_sequence=12,
                summary="Compacted session context",
                artifact_id=artifact_id,
                artifact_schema_version=1,
                freshness=ContextCompactionFreshness.STALE,
                freshness_reason="superseded",
                created_at=now,
                last_sequence=13,
            )
        ],
        verification=VerificationObservability(summary_count=0),
        provider_canary=ProviderCanaryEvidenceSummary(
            summary_count=0,
            latest_status="missing",
            freshness_status="missing",
        ),
    )

    assert _cue(posture, "workspace-memory").provenance[0].source_start_sequence == 7
    assert _cue(posture, "checkpoints").provenance[0].artifact_id == str(artifact_id)
    assert _cue(posture, "checkpoints").provenance[0].source_end_sequence == 9
    assert _cue(posture, "compactions").provenance[0].freshness == "stale"


def test_knowledge_posture_ranks_degraded_above_stale_and_missing() -> None:
    posture = build_knowledge_posture_from_sources(
        memory=WorkspaceMemoryObservability(
            active_count=0,
            stale_count=1,
            imported_count=0,
            invalidated_count=0,
            pruned_count=0,
            redacted_count=0,
        ),
        repository_index=RepositoryIndexObservability(
            status="stale",
            path=".glassbox/repository-index.json",
            entry_count=3,
        ),
        checkpoint_count=0,
        active_session_without_checkpoint_count=1,
        compaction_count=2,
        stale_compaction_count=1,
        verification=VerificationObservability(
            summary_count=1,
            latest_suite_status="failed",
            latest_profile_id="release-candidate",
        ),
        provider_canary=ProviderCanaryEvidenceSummary(
            summary_count=0,
            latest_status="missing",
            freshness_status="missing",
        ),
    )

    assert posture.overall_status == "degraded"
    assert _cue_status(posture, "workspace-memory") == "stale"
    assert _cue_status(posture, "repository-index") == "stale"
    assert _cue_status(posture, "checkpoints") == "degraded"
    assert _cue_status(posture, "compactions") == "stale"
    assert _cue_status(posture, "verification") == "degraded"
    assert _cue_status(posture, "provider-evidence") == "missing"
    assert "glassbox session status SESSION_ID --cwd ." in posture.next_actions
    assert "glassbox eval audit --cwd ." in posture.next_actions


def test_knowledge_posture_surfaces_memory_conflict_cues() -> None:
    posture = build_knowledge_posture_from_sources(
        memory=WorkspaceMemoryObservability(
            active_count=1,
            stale_count=0,
            imported_count=0,
            invalidated_count=0,
            pruned_count=0,
            redacted_count=0,
            conflict_count=1,
            conflicted_memory_ids=["memory-1"],
            next_actions=["glassbox memory show memory-1 --cwd ."],
        ),
        repository_index=RepositoryIndexObservability(
            status="fresh",
            path=".glassbox/repository-index.json",
            entry_count=12,
        ),
        checkpoint_count=0,
        compaction_count=0,
        stale_compaction_count=0,
        verification=VerificationObservability(summary_count=0),
        provider_canary=ProviderCanaryEvidenceSummary(
            summary_count=0,
            latest_status="missing",
            freshness_status="missing",
        ),
    )

    cue = _cue(posture, "workspace-memory")
    assert cue.status == "stale"
    assert "conflict" in cue.summary
    assert "glassbox memory show memory-1 --cwd ." in posture.next_actions


def _cue_status(posture, key: str) -> str:
    return _cue(posture, key).status


def _cue(posture, key: str):
    cue = next(cue for cue in posture.cues if cue.key == key)
    return cue
