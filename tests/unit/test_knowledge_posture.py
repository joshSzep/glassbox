"""Unit coverage for unified workspace knowledge posture."""

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
            latest_suite_status="passed",
            latest_profile_id="commit-smoke",
        ),
        provider_canary=ProviderCanaryEvidenceSummary(
            summary_count=1,
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
    assert "glassbox provider canary evidence --cwd ." in posture.next_actions


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


def _cue_status(posture, key: str) -> str:
    cue = next(cue for cue in posture.cues if cue.key == key)
    return cue.status
