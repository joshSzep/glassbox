"""High-level replay orchestration over bundle I/O, execution, and triage."""

from dataclasses import dataclass
from pathlib import Path

from glassbox.core.ids import SessionId
from glassbox.runtime.replay_bundle_io import ReplayBundleStore
from glassbox.runtime.replay_compare import collect_mismatches
from glassbox.runtime.replay_compare import hydrate_lineage_aware_bundle
from glassbox.runtime.replay_execution import execute_replay_bundle
from glassbox.runtime.replay_failures import ReplayFailure
from glassbox.runtime.replay_failures import ReplayManifestDrift
from glassbox.runtime.replay_failures import ReplayUnsupportedSession
from glassbox.runtime.replay_models import ReplayBundle
from glassbox.runtime.replay_models import ReplayNormalizedSession
from glassbox.runtime.replay_models import ReplayResult
from glassbox.runtime.replay_triage import build_replay_result
from glassbox.services import ArtifactRepository
from glassbox.services import SessionRepository


@dataclass(frozen=True, slots=True)
class ReplayExecutionRequest:
    """Typed input boundary for one replay execution request."""

    bundle: ReplayBundle
    workspace_root: Path | None = None


@dataclass(frozen=True, slots=True)
class ReplayExecutionOutcome:
    """Typed execution boundary between replay runtime and comparison."""

    request: ReplayExecutionRequest
    replay: ReplayNormalizedSession


@dataclass(frozen=True, slots=True)
class ReplayComparisonOutcome:
    """Typed comparison boundary between normalized replay and result building."""

    source_session_id: SessionId | None
    baseline: ReplayNormalizedSession
    replay: ReplayNormalizedSession
    mismatches: list[str]


class ReplayOrchestrator:
    """Coordinate replay bundle loading, execution, comparison, and triage."""

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
        except ReplayManifestDrift as exc:
            return self._failure_result(
                outcome="manifest_drift",
                source_session_id=session_id,
                message=str(exc),
            )
        except ReplayUnsupportedSession as exc:
            return self._failure_result(
                outcome="unsupported_session",
                source_session_id=session_id,
                message=str(exc),
            )
        except ReplayFailure as exc:
            return self._failure_result(
                outcome="replay_failure",
                source_session_id=session_id,
                message=str(exc),
            )

        return await self.replay_bundle(bundle)

    async def replay_bundle_file(
        self,
        bundle_path: Path,
        *,
        workspace_root: Path | None = None,
    ) -> ReplayResult:
        try:
            bundle = self.load_bundle_file(bundle_path)
        except ReplayUnsupportedSession as exc:
            return self._failure_result(
                outcome="unsupported_session",
                source_session_id=None,
                message=str(exc),
            )
        except ReplayFailure as exc:
            return self._failure_result(
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
        request = ReplayExecutionRequest(
            bundle=hydrate_lineage_aware_bundle(bundle),
            workspace_root=workspace_root,
        )
        try:
            execution = await self._execute(request)
        except ReplayManifestDrift as exc:
            return self._failure_result(
                outcome="manifest_drift",
                source_session_id=request.bundle.source_session_id,
                message=str(exc),
                baseline=request.bundle.baseline,
            )
        except ReplayUnsupportedSession as exc:
            return self._failure_result(
                outcome="unsupported_session",
                source_session_id=request.bundle.source_session_id,
                message=str(exc),
                baseline=request.bundle.baseline,
            )
        except ReplayFailure as exc:
            return self._failure_result(
                outcome="replay_failure",
                source_session_id=request.bundle.source_session_id,
                message=str(exc),
                baseline=request.bundle.baseline,
            )

        comparison = self._compare(execution)
        return self._result_from_comparison(comparison)

    async def _execute(
        self,
        request: ReplayExecutionRequest,
    ) -> ReplayExecutionOutcome:
        replay = await execute_replay_bundle(
            request.bundle,
            workspace_root=request.workspace_root,
        )
        return ReplayExecutionOutcome(request=request, replay=replay)

    def _compare(
        self,
        execution: ReplayExecutionOutcome,
    ) -> ReplayComparisonOutcome:
        mismatches = collect_mismatches(
            execution.request.bundle.baseline,
            execution.replay,
        )
        return ReplayComparisonOutcome(
            source_session_id=execution.request.bundle.source_session_id,
            baseline=execution.request.bundle.baseline,
            replay=execution.replay,
            mismatches=mismatches,
        )

    def _result_from_comparison(
        self,
        comparison: ReplayComparisonOutcome,
    ) -> ReplayResult:
        return build_replay_result(
            outcome=(
                "exact_match" if not comparison.mismatches else "behavioral_drift"
            ),
            source_session_id=comparison.source_session_id,
            message=(
                None
                if not comparison.mismatches
                else "normalized replay drift detected"
            ),
            mismatches=comparison.mismatches,
            baseline=comparison.baseline,
            replay=comparison.replay,
        )

    def _failure_result(self, **kwargs) -> ReplayResult:
        return build_replay_result(**kwargs)
