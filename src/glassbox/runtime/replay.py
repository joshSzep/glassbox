"""Offline deterministic replay runner for persisted Glassbox sessions."""

from pathlib import Path

from glassbox.core.ids import SessionId
from glassbox.runtime.replay_models import REPLAY_BUNDLE_KIND
from glassbox.runtime.replay_models import REPLAY_BUNDLE_VERSION
from glassbox.runtime.replay_models import ReplayAction
from glassbox.runtime.replay_models import ReplayApprovalSnapshot
from glassbox.runtime.replay_models import ReplayBundle
from glassbox.runtime.replay_models import ReplayCancellationSnapshot
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
from glassbox.runtime.replay_orchestrator import ReplayOrchestrator
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
        self._orchestrator = ReplayOrchestrator(
            session_repository=session_repository,
            artifact_repository=artifact_repository,
        )

    def load_session_bundle(self, session_id: SessionId) -> ReplayBundle:
        return self._orchestrator.load_session_bundle(session_id)

    def export_session_bundle(
        self,
        session_id: SessionId,
        output_path: Path,
    ) -> Path:
        return self._orchestrator.export_session_bundle(session_id, output_path)

    def load_bundle_file(self, bundle_path: Path) -> ReplayBundle:
        return self._orchestrator.load_bundle_file(bundle_path)

    async def replay_session(self, session_id: SessionId) -> ReplayResult:
        return await self._orchestrator.replay_session(session_id)

    async def replay_bundle_file(
        self,
        bundle_path: Path,
        *,
        workspace_root: Path | None = None,
    ) -> ReplayResult:
        return await self._orchestrator.replay_bundle_file(
            bundle_path,
            workspace_root=workspace_root,
        )

    async def replay_bundle(
        self,
        bundle: ReplayBundle,
        *,
        workspace_root: Path | None = None,
    ) -> ReplayResult:
        return await self._orchestrator.replay_bundle(
            bundle,
            workspace_root=workspace_root,
        )


__all__ = [
    "REPLAY_BUNDLE_KIND",
    "REPLAY_BUNDLE_VERSION",
    "ReplayAction",
    "ReplayApprovalSnapshot",
    "ReplayBundle",
    "ReplayCancellationSnapshot",
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
