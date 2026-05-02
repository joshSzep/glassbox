"""Record retained pre-commit and eval evidence against changesets."""

import hashlib
import json
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core import ChangesetId
from glassbox.core import ChangesetReadinessDecided
from glassbox.core import ChangesetReadinessKind
from glassbox.core import ChangesetReadinessState
from glassbox.core import ChangesetVerificationPostureUpdated
from glassbox.core import ChangesetVerificationState
from glassbox.core import EventEnvelope
from glassbox.core import SessionId
from glassbox.runtime.changesets import ChangesetQueryService
from glassbox.runtime.changesets import ChangesetRepository
from glassbox.runtime.commit_readiness import ChangesetCommitReadinessService
from glassbox.runtime.commit_readiness import CommitReadinessAssessment
from glassbox.services import ArtifactRepository
from glassbox.services import StoredArtifact

PRECOMMIT_EVIDENCE_ARTIFACT_KIND = "changeset_precommit_evidence"
PRECOMMIT_EVIDENCE_SCHEMA_VERSION = 1

PreCommitEvidenceKind = Literal["pre-commit", "eval-report"]
PreCommitEvidenceState = Literal["passed", "failed", "stale", "missing"]


class PreCommitEvidenceArtifact(BaseModel):
    """Summary-only retained evidence from a local pre-commit/eval run."""

    model_config = ConfigDict(extra="forbid")

    artifact_kind: Literal["changeset_precommit_evidence"] = (
        PRECOMMIT_EVIDENCE_ARTIFACT_KIND
    )
    schema_version: Literal[1] = PRECOMMIT_EVIDENCE_SCHEMA_VERSION
    changeset_id: ChangesetId
    session_id: SessionId
    evidence_kind: PreCommitEvidenceKind
    state: PreCommitEvidenceState
    summary: str = Field(min_length=1, max_length=4000)
    source_path: str | None = None
    source_sha256: str | None = Field(default=None, max_length=64)
    parsed_fields: dict[str, Any] = Field(default_factory=dict)
    recorded_at: datetime
    recorded_by: str = Field(min_length=1, max_length=200)
    redaction: str = "summary-only-no-raw-output"
    raw_command_output_included: Literal[False] = False
    raw_file_contents_included: Literal[False] = False
    local_only: bool = True
    non_claims: list[str] = Field(default_factory=list)


class PreCommitEvidenceRecordResult(BaseModel):
    """Result of recording one local pre-commit/eval evidence summary."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    changeset_id: ChangesetId
    session_id: SessionId
    evidence: PreCommitEvidenceArtifact
    artifact: StoredArtifact
    verification_event: EventEnvelope
    readiness_event: EventEnvelope
    commit_readiness: CommitReadinessAssessment


class ChangesetPreCommitEvidenceService:
    """Retain pre-commit/eval summary evidence and update readiness."""

    def __init__(
        self,
        repository: ChangesetRepository,
        artifact_repository: ArtifactRepository,
    ) -> None:
        self._repository = repository
        self._artifact_repository = artifact_repository

    async def record_summary(
        self,
        changeset_id: ChangesetId,
        summary_path: Path,
        workspace_root: Path,
        *,
        evidence_kind: PreCommitEvidenceKind = "pre-commit",
        state: PreCommitEvidenceState | None = None,
        recorded_by: str = "operator",
    ) -> PreCommitEvidenceRecordResult:
        """Record a summary-only pre-commit or eval artifact for a changeset."""

        changeset = (
            ChangesetQueryService(self._repository)
            .get_detail(
                changeset_id,
                workspace_root=workspace_root,
            )
            .changeset
        )
        source_path = _resolve_source_path(summary_path, workspace_root)
        source_bytes = source_path.read_bytes()
        parsed = _parsed_summary(source_bytes)
        resolved_state = state or _infer_state(parsed)
        summary = _summary(resolved_state, evidence_kind, parsed)
        evidence = PreCommitEvidenceArtifact(
            changeset_id=changeset.changeset_id,
            session_id=changeset.session_id,
            evidence_kind=evidence_kind,
            state=resolved_state,
            summary=summary,
            source_path=_display_path(source_path, workspace_root),
            source_sha256=hashlib.sha256(source_bytes).hexdigest(),
            parsed_fields=parsed,
            recorded_at=datetime.now(UTC),
            recorded_by=recorded_by,
            non_claims=[
                "raw pre-commit or eval output is not retained in this artifact",
                "recording evidence does not run hooks or evals",
                "recording evidence does not stage files or commit",
                "freshness is local to the supplied summary and current changeset",
            ],
        )
        artifact = self._artifact_repository.write_text_artifact(
            changeset.session_id,
            json.dumps(evidence.model_dump(mode="json"), indent=2, sort_keys=True)
            + "\n",
            suffix=".changeset-precommit-evidence.json",
        )
        verification_state = _verification_state(resolved_state)
        readiness_state = _readiness_state(resolved_state)
        blockers = [] if readiness_state == ChangesetReadinessState.READY else [summary]
        stored = self._repository.append_events(
            [
                EventEnvelope(
                    session_id=changeset.session_id,
                    sequence=0,
                    payload=ChangesetVerificationPostureUpdated(
                        changeset_id=changeset.changeset_id,
                        state=verification_state,
                        summary=summary,
                        artifact_id=artifact.artifact_id,
                        task_id=changeset.task_id,
                        failed_count=1 if resolved_state == "failed" else 0,
                        stale_count=1 if resolved_state == "stale" else 0,
                        missing_count=1 if resolved_state == "missing" else 0,
                    ),
                ),
                EventEnvelope(
                    session_id=changeset.session_id,
                    sequence=0,
                    payload=ChangesetReadinessDecided(
                        changeset_id=changeset.changeset_id,
                        readiness_kind=ChangesetReadinessKind.COMMIT,
                        state=readiness_state,
                        reason=summary,
                        blockers=blockers,
                        safe_next_actions=_safe_next_actions(resolved_state),
                        inventory_artifact_id=changeset.latest_inventory_artifact_id,
                        review_brief_artifact_id=(
                            changeset.latest_review_brief_artifact_id
                        ),
                        task_id=changeset.task_id,
                        accepted_risk_count=changeset.accepted_risk_count,
                        decided_by=recorded_by,
                    ),
                ),
            ]
        )
        commit_readiness = await ChangesetCommitReadinessService(
            self._repository,
            self._artifact_repository,
        ).preview(changeset.changeset_id, workspace_root)
        return PreCommitEvidenceRecordResult(
            changeset_id=changeset.changeset_id,
            session_id=changeset.session_id,
            evidence=evidence,
            artifact=artifact,
            verification_event=stored[0],
            readiness_event=stored[1],
            commit_readiness=commit_readiness,
        )


def precommit_evidence_readiness_state(
    state: PreCommitEvidenceState,
) -> ChangesetReadinessState:
    """Map retained evidence state to advisory commit-readiness state."""

    return _readiness_state(state)


def _resolve_source_path(summary_path: Path, workspace_root: Path) -> Path:
    path = summary_path if summary_path.is_absolute() else workspace_root / summary_path
    resolved = path.resolve(strict=True)
    if not resolved.is_file():
        raise ValueError(f"pre-commit evidence summary is not a file: {summary_path}")
    return resolved


def _parsed_summary(source_bytes: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(source_bytes.decode("utf-8"))
    except UnicodeDecodeError, json.JSONDecodeError:
        return {"format": "text", "byte_count": len(source_bytes)}
    if not isinstance(payload, dict):
        return {"format": "json", "summary": str(type(payload).__name__)}
    allowed_keys = {
        "status",
        "state",
        "profile_id",
        "profile_ids",
        "passed",
        "failed",
        "failures",
        "errors",
        "total",
        "summary",
        "verification_stage",
    }
    return {
        key: value
        for key, value in payload.items()
        if key in allowed_keys and isinstance(value, str | int | float | bool | list)
    }


def _infer_state(parsed: dict[str, Any]) -> PreCommitEvidenceState:
    raw_state = str(parsed.get("state") or parsed.get("status") or "").lower()
    if raw_state in {"passed", "pass", "success", "succeeded"}:
        return "passed"
    if raw_state in {"failed", "fail", "failure", "error", "errored"}:
        return "failed"
    if raw_state in {"stale", "outdated"}:
        return "stale"
    if raw_state in {"missing", "skipped"}:
        return "missing"
    failed = _int_field(parsed, "failed") or _int_field(parsed, "failures")
    errors = _int_field(parsed, "errors")
    if failed or errors:
        return "failed"
    return "passed"


def _summary(
    state: PreCommitEvidenceState,
    evidence_kind: PreCommitEvidenceKind,
    parsed: dict[str, Any],
) -> str:
    subject = parsed.get("summary")
    if isinstance(subject, str) and subject.strip():
        return subject.strip()[:4000]
    profile = parsed.get("profile_id")
    profile_text = f" for {profile}" if isinstance(profile, str) else ""
    counts = _counts_summary(parsed)
    suffix = f": {counts}" if counts else ""
    return f"{evidence_kind} evidence {state}{profile_text}{suffix}"


def _counts_summary(parsed: dict[str, Any]) -> str | None:
    parts: list[str] = []
    for key in ("passed", "failed", "errors", "total"):
        value = parsed.get(key)
        if isinstance(value, int | float):
            parts.append(f"{key}={int(value)}")
    return ", ".join(parts) if parts else None


def _int_field(parsed: dict[str, Any], key: str) -> int:
    value = parsed.get(key)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int | float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def _verification_state(
    state: PreCommitEvidenceState,
) -> ChangesetVerificationState:
    return {
        "passed": ChangesetVerificationState.PASSED,
        "failed": ChangesetVerificationState.FAILED,
        "stale": ChangesetVerificationState.STALE,
        "missing": ChangesetVerificationState.MISSING,
    }[state]


def _readiness_state(state: PreCommitEvidenceState) -> ChangesetReadinessState:
    return {
        "passed": ChangesetReadinessState.READY,
        "failed": ChangesetReadinessState.FAILED_CHECKS,
        "stale": ChangesetReadinessState.STALE_INVENTORY,
        "missing": ChangesetReadinessState.NEEDS_VERIFICATION,
    }[state]


def _safe_next_actions(state: PreCommitEvidenceState) -> list[str]:
    if state == "passed":
        return ["git status --short"]
    if state == "failed":
        return ["rerun the failed pre-commit or eval command after fixes"]
    if state == "stale":
        return ["rerun pre-commit or eval evidence for the current changeset"]
    return ["record fresh pre-commit or eval evidence for this changeset"]


def _display_path(path: Path, workspace_root: Path) -> str:
    try:
        return path.relative_to(workspace_root).as_posix()
    except ValueError:
        return str(path)


__all__ = [
    "PRECOMMIT_EVIDENCE_ARTIFACT_KIND",
    "PRECOMMIT_EVIDENCE_SCHEMA_VERSION",
    "ChangesetPreCommitEvidenceService",
    "PreCommitEvidenceArtifact",
    "PreCommitEvidenceKind",
    "PreCommitEvidenceRecordResult",
    "PreCommitEvidenceState",
    "precommit_evidence_readiness_state",
]
