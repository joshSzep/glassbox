"""Manual evidence action service."""

from collections.abc import Sequence
from datetime import datetime

from glassbox.core import ChangesetId
from glassbox.core import ChangesetRecord
from glassbox.core import EventEnvelope
from glassbox.core import ManualEvidenceAttached
from glassbox.core import ManualEvidenceFreshness
from glassbox.core import ManualEvidenceId
from glassbox.core import ManualEvidenceKind
from glassbox.core import ManualEvidenceRedactionStatus
from glassbox.core import ManualEvidenceRejected
from glassbox.core import ManualEvidenceTargetKind
from glassbox.core import ReviewFeedbackId
from glassbox.core import new_manual_evidence_id
from glassbox.runtime.changeset_models import ManualEvidenceRecordResult
from glassbox.runtime.changeset_repository_contracts import ChangesetRepository
from glassbox.runtime.changeset_safe_commands import changeset_brief_command
from glassbox.runtime.manual_evidence import MANUAL_EVIDENCE_ARTIFACT_SCHEMA_VERSION
from glassbox.runtime.manual_evidence import ManualEvidenceLocalReference
from glassbox.runtime.manual_evidence import ManualEvidenceTargetRef
from glassbox.runtime.manual_evidence import manual_evidence_artifact
from glassbox.runtime.manual_evidence import manual_evidence_artifact_json
from glassbox.runtime.manual_evidence import validate_manual_evidence_text
from glassbox.services import ArtifactRepository
from glassbox.services import StoredArtifact


class ManualEvidenceActionService:
    """Attach summary-first manual evidence without claiming Glassbox ran it."""

    def __init__(
        self,
        repository: ChangesetRepository,
        artifact_repository: ArtifactRepository | None = None,
    ) -> None:
        self._repository = repository
        self._artifact_repository = artifact_repository

    def attach(
        self,
        changeset_id: ChangesetId,
        *,
        evidence_kind: ManualEvidenceKind,
        summary: str,
        source_label: str,
        actor: str = "operator",
        target_kind: ManualEvidenceTargetKind = ManualEvidenceTargetKind.CHANGESET,
        target_id: str | None = None,
        feedback_id: ReviewFeedbackId | None = None,
        note: str | None = None,
        command_text: str | None = None,
        external_url_label: str | None = None,
        local_file_label: str | None = None,
        local_file_path_hint: str | None = None,
        local_file_media_type: str | None = None,
        local_file_size_bytes: int | None = None,
        local_file_width: int | None = None,
        local_file_height: int | None = None,
        freshness: ManualEvidenceFreshness = ManualEvidenceFreshness.UNKNOWN,
        observed_at: datetime | None = None,
        extra_limitations: Sequence[str] = (),
        extra_non_claims: Sequence[str] = (),
    ) -> ManualEvidenceRecordResult:
        if self._artifact_repository is None:
            raise ValueError("artifact repository is required for manual evidence")
        changeset = self._require_changeset(changeset_id)
        resolved_target_kind, resolved_target_id, resolved_feedback_id = (
            self._resolve_target(
                changeset,
                target_kind=target_kind,
                target_id=target_id,
                feedback_id=feedback_id,
            )
        )
        evidence_id = new_manual_evidence_id()
        candidate_text = note or summary
        redaction = validate_manual_evidence_text(candidate_text)
        if not redaction.accepted:
            event = self._repository.append_events(
                [
                    EventEnvelope(
                        session_id=changeset.session_id,
                        sequence=0,
                        payload=ManualEvidenceRejected(
                            evidence_id=evidence_id,
                            evidence_kind=evidence_kind,
                            target_kind=resolved_target_kind,
                            target_id=resolved_target_id,
                            changeset_id=changeset.changeset_id,
                            feedback_id=resolved_feedback_id,
                            summary=summary,
                            source_label=source_label,
                            reason="; ".join(
                                finding.code for finding in redaction.findings
                            )
                            or "manual evidence rejected by redaction checks",
                            rejected_by=actor,
                            redaction_findings=[
                                finding.code for finding in redaction.findings
                            ],
                            task_id=changeset.task_id,
                        ),
                    )
                ]
            )[0]
            return self._result(changeset, evidence_id, event, artifact=None)

        local_references = (
            [
                ManualEvidenceLocalReference(
                    label=local_file_label or "local evidence reference",
                    path_hint=local_file_path_hint,
                    media_type=local_file_media_type,
                    size_bytes=local_file_size_bytes,
                    width=local_file_width,
                    height=local_file_height,
                )
            ]
            if local_file_path_hint is not None
            else []
        )
        artifact_payload = manual_evidence_artifact(
            evidence_id=evidence_id,
            evidence_kind=evidence_kind,
            summary=summary,
            source_label=source_label,
            targets=[
                ManualEvidenceTargetRef(
                    target_kind=resolved_target_kind,
                    target_id=resolved_target_id,
                    changeset_id=changeset.changeset_id,
                )
            ],
            created_by=actor,
            observed_at=observed_at,
            candidate_text=candidate_text,
            command_text=command_text,
            external_url_label=external_url_label,
            local_references=local_references,
            freshness=freshness,
            extra_limitations=extra_limitations,
            extra_non_claims=extra_non_claims,
        )
        artifact = self._artifact_repository.write_text_artifact(
            changeset.session_id,
            manual_evidence_artifact_json(artifact_payload),
            suffix=".manual-evidence.json",
        )
        event = self._repository.append_events(
            [
                EventEnvelope(
                    session_id=changeset.session_id,
                    sequence=0,
                    payload=ManualEvidenceAttached(
                        evidence_id=evidence_id,
                        evidence_kind=evidence_kind,
                        target_kind=resolved_target_kind,
                        target_id=resolved_target_id,
                        changeset_id=changeset.changeset_id,
                        feedback_id=resolved_feedback_id,
                        artifact_id=artifact.artifact_id,
                        artifact_schema_version=(
                            MANUAL_EVIDENCE_ARTIFACT_SCHEMA_VERSION
                        ),
                        summary=summary,
                        source_label=source_label,
                        created_by=actor,
                        observed_at=observed_at,
                        redaction_status=ManualEvidenceRedactionStatus.PASSED,
                        freshness=freshness,
                        limitations=artifact_payload.limitations,
                        non_claims=artifact_payload.non_claims,
                        task_id=changeset.task_id,
                    ),
                )
            ]
        )[0]
        return self._result(changeset, evidence_id, event, artifact=artifact)

    def _resolve_target(
        self,
        changeset: ChangesetRecord,
        *,
        target_kind: ManualEvidenceTargetKind,
        target_id: str | None,
        feedback_id: ReviewFeedbackId | None,
    ) -> tuple[ManualEvidenceTargetKind, str, ReviewFeedbackId | None]:
        if feedback_id is not None:
            feedback = self._repository.get_review_feedback(feedback_id)
            if feedback is None:
                raise ValueError(f"unknown review feedback: {feedback_id}")
            if feedback.changeset_id != changeset.changeset_id:
                raise ValueError("feedback does not belong to this changeset")
            return ManualEvidenceTargetKind.FEEDBACK, str(feedback_id), feedback_id
        if target_kind == ManualEvidenceTargetKind.CHANGESET:
            return target_kind, str(changeset.changeset_id), None
        return target_kind, target_id or "unknown", None

    def _require_changeset(self, changeset_id: ChangesetId) -> ChangesetRecord:
        changeset = self._repository.get_changeset(changeset_id)
        if changeset is None:
            raise ValueError(f"unknown changeset: {changeset_id}")
        return changeset

    def _result(
        self,
        changeset: ChangesetRecord,
        evidence_id: ManualEvidenceId,
        event: EventEnvelope,
        *,
        artifact: StoredArtifact | None,
    ) -> ManualEvidenceRecordResult:
        evidence = self._repository.get_manual_evidence(evidence_id)
        if evidence is None:
            raise ValueError(f"manual evidence projection missing: {evidence_id}")
        return ManualEvidenceRecordResult(
            evidence=evidence,
            artifact=artifact,
            event=event,
            safe_next_actions=[
                "glassbox changeset evidence list --changeset "
                f"{changeset.changeset_id} --cwd .",
                "glassbox changeset verification-plan "
                f"{changeset.changeset_id} --cwd .",
                changeset_brief_command(changeset.changeset_id),
            ],
            non_claims=[
                "manual evidence is not retained command evidence",
                "manual evidence is not deterministic verification proof",
                "Glassbox did not stage, commit, push, open a PR, or merge",
            ],
        )


__all__ = ["ManualEvidenceActionService"]
