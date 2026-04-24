"""Offline deterministic replay runner for persisted Glassbox sessions."""

from pathlib import Path

from glassbox.core.ids import SessionId
from glassbox.runtime.replay_bundle_io import ReplayBundleStore
from glassbox.runtime.replay_compare import collect_mismatches
from glassbox.runtime.replay_compare import hydrate_lineage_aware_bundle
from glassbox.runtime.replay_execution import execute_replay_bundle
from glassbox.runtime.replay_failures import ReplayFailure
from glassbox.runtime.replay_failures import ReplayManifestDrift
from glassbox.runtime.replay_failures import ReplayUnsupportedSession
from glassbox.runtime.replay_models import REPLAY_BUNDLE_KIND
from glassbox.runtime.replay_models import REPLAY_BUNDLE_VERSION
from glassbox.runtime.replay_models import ReplayAction
from glassbox.runtime.replay_models import ReplayApprovalSnapshot
from glassbox.runtime.replay_models import ReplayBundle
from glassbox.runtime.replay_models import ReplayFinalStateSnapshot
from glassbox.runtime.replay_models import ReplayLineageSnapshot
from glassbox.runtime.replay_models import ReplayNormalizedSession
from glassbox.runtime.replay_models import ReplayOutcome
from glassbox.runtime.replay_models import ReplayQuestionSnapshot
from glassbox.runtime.replay_models import ReplayRecordedModelCall
from glassbox.runtime.replay_models import ReplayRecordedToolCall
from glassbox.runtime.replay_models import ReplayResult
from glassbox.runtime.replay_models import ReplayToolCallSnapshot
from glassbox.runtime.replay_models import ReplayTranscriptMessage
from glassbox.runtime.replay_models import ReplayTranscriptPart
from glassbox.runtime.replay_models import ReplayTriage
from glassbox.runtime.replay_models import ReplayTriageClassification
from glassbox.runtime.replay_models import ReplayTriageSeverity
from glassbox.runtime.replay_triage import build_replay_result
from glassbox.runtime.replay_triage import build_replay_triage
from glassbox.services import ArtifactRepository
from glassbox.services import SessionRepository


class ReplayRunner:
    """Load and replay persisted sessions through an isolated runtime."""

    def __init__(
        self,
        session_repository: SessionRepository | None = None,
        artifact_repository: ArtifactRepository | None = None,
    ) -> None:
        self._bundle_store = ReplayBundleStore(
            session_repository=session_repository,
            artifact_repository=artifact_repository,
        )

    def load_session_bundle(self, session_id: SessionId) -> ReplayBundle:
        return self._bundle_store.load_session_bundle(session_id)

    def export_session_bundle(
        self,
        session_id: SessionId,
        output_path: Path,
    ) -> Path:
        return self._bundle_store.export_session_bundle(session_id, output_path)

    def load_bundle_file(self, bundle_path: Path) -> ReplayBundle:
        return self._bundle_store.load_bundle_file(bundle_path)

    async def replay_session(self, session_id: SessionId) -> ReplayResult:
        try:
            bundle = self.load_session_bundle(session_id)
            return await self.replay_bundle(bundle)
        except ReplayManifestDrift as exc:
            return build_replay_result(
                outcome="manifest_drift",
                source_session_id=session_id,
                message=str(exc),
            )
        except ReplayUnsupportedSession as exc:
            return build_replay_result(
                outcome="unsupported_session",
                source_session_id=session_id,
                message=str(exc),
            )
        except ReplayFailure as exc:
            return build_replay_result(
                outcome="replay_failure",
                source_session_id=session_id,
                message=str(exc),
            )

    async def replay_bundle_file(
        self,
        bundle_path: Path,
        *,
        workspace_root: Path | None = None,
    ) -> ReplayResult:
        try:
            bundle = self.load_bundle_file(bundle_path)
        except ReplayUnsupportedSession as exc:
            return build_replay_result(
                outcome="unsupported_session",
                source_session_id=None,
                message=str(exc),
            )
        except ReplayFailure as exc:
            return build_replay_result(
                outcome="replay_failure",
                source_session_id=None,
                message=str(exc),
            )

        return await self.replay_bundle(bundle, workspace_root=workspace_root)

    async def replay_bundle(
        self,
        bundle: ReplayBundle,
        *,
        workspace_root: Path | None = None,
    ) -> ReplayResult:
        bundle = hydrate_lineage_aware_bundle(bundle)
        try:
            replay_session = await execute_replay_bundle(
                bundle,
                workspace_root=workspace_root,
            )
        except ReplayManifestDrift as exc:
            return build_replay_result(
                outcome="manifest_drift",
                source_session_id=bundle.source_session_id,
                message=str(exc),
                baseline=bundle.baseline,
            )
        except ReplayUnsupportedSession as exc:
            return build_replay_result(
                outcome="unsupported_session",
                source_session_id=bundle.source_session_id,
                message=str(exc),
                baseline=bundle.baseline,
            )
        except ReplayFailure as exc:
            return build_replay_result(
                outcome="replay_failure",
                source_session_id=bundle.source_session_id,
                message=str(exc),
                baseline=bundle.baseline,
            )

        mismatches = collect_mismatches(bundle.baseline, replay_session)
        return build_replay_result(
            outcome="exact_match" if not mismatches else "behavioral_drift",
            source_session_id=bundle.source_session_id,
            message=None if not mismatches else "normalized replay drift detected",
            mismatches=mismatches,
            baseline=bundle.baseline,
            replay=replay_session,
        )


__all__ = [
    "REPLAY_BUNDLE_KIND",
    "REPLAY_BUNDLE_VERSION",
    "ReplayAction",
    "ReplayApprovalSnapshot",
    "ReplayBundle",
    "ReplayFinalStateSnapshot",
    "ReplayLineageSnapshot",
    "ReplayNormalizedSession",
    "ReplayOutcome",
    "ReplayQuestionSnapshot",
    "ReplayRecordedModelCall",
    "ReplayRecordedToolCall",
    "ReplayResult",
    "ReplayRunner",
    "ReplayToolCallSnapshot",
    "ReplayTranscriptMessage",
    "ReplayTranscriptPart",
    "ReplayTriage",
    "ReplayTriageClassification",
    "ReplayTriageSeverity",
    "build_replay_triage",
]
