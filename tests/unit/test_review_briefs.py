"""Tests for the changeset review brief artifact contract."""

from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from glassbox.core import ChangesetInventoryFreshness
from glassbox.core import ChangesetReadinessDecided
from glassbox.core import ChangesetReadinessState
from glassbox.core import ChangesetRecord
from glassbox.core import ChangesetReviewBriefCreated
from glassbox.core import ChangesetRiskLevel
from glassbox.core import ChangesetSourceKind
from glassbox.core import ChangesetSourceRecord
from glassbox.core import EventEnvelope
from glassbox.core import ManualEvidenceFreshness
from glassbox.core import ManualEvidenceKind
from glassbox.core import ManualEvidenceRecord
from glassbox.core import ManualEvidenceRedactionStatus
from glassbox.core import ManualEvidenceState
from glassbox.core import ManualEvidenceTargetKind
from glassbox.core import ReviewFeedbackDisposition
from glassbox.core import ReviewFeedbackFixupInventoryRecord
from glassbox.core import ReviewFeedbackKind
from glassbox.core import ReviewFeedbackProvenance
from glassbox.core import ReviewFeedbackRecord
from glassbox.core import ReviewFixupSourceKind
from glassbox.core import SessionId
from glassbox.core import new_artifact_id
from glassbox.core import new_changeset_id
from glassbox.core import new_manual_evidence_id
from glassbox.core import new_review_feedback_id
from glassbox.core import new_session_id
from glassbox.core import new_task_verification_id
from glassbox.runtime.changesets import ChangesetRepository
from glassbox.runtime.changesets import ChangesetReviewBriefService
from glassbox.runtime.review_briefs import REVIEW_BRIEF_ARTIFACT_KIND
from glassbox.runtime.review_briefs import REVIEW_BRIEF_REDACTION
from glassbox.runtime.review_briefs import ReviewBriefArtifact
from glassbox.runtime.review_briefs import ReviewBriefEvidenceRef
from glassbox.runtime.review_briefs import ReviewBriefSection
from glassbox.runtime.review_briefs import redact_review_brief_text
from glassbox.runtime.review_briefs import review_brief_artifact_json
from glassbox.runtime.review_briefs import review_brief_markdown
from glassbox.services import ArtifactRepository
from glassbox.services import StoredArtifact


def test_review_brief_artifact_contract_and_render_targets() -> None:
    artifact = _brief()
    payload = artifact.model_dump(mode="json")
    markdown = review_brief_markdown(artifact)
    raw_json = review_brief_artifact_json(artifact)

    assert artifact.artifact_kind == REVIEW_BRIEF_ARTIFACT_KIND
    assert artifact.redaction == REVIEW_BRIEF_REDACTION
    assert artifact.render_targets == ["markdown", "json"]
    assert artifact.redacted is True
    assert artifact.raw_command_output_included is False
    assert artifact.raw_provider_transcript_included is False
    assert artifact.raw_diff_included is False
    assert artifact.raw_file_contents_included is False
    assert payload["schema_version"] == 2
    assert "Change Summary" in markdown
    assert "Changed-File Inventory" in markdown
    assert "Affected Subsystems" in markdown
    assert "runtime package" in markdown
    assert "Verification" in markdown
    assert "Command Evidence" in markdown
    assert "Reviewer Checklist" in markdown
    assert "Safe Inspection Commands" in markdown
    assert '"artifact_kind": "changeset_review_brief"' in raw_json


def test_review_lifecycle_brief_contract_sections_and_evidence_refs() -> None:
    artifact = _brief(
        lifecycle_summary=ReviewBriefSection(
            title="Lifecycle Summary",
            body=(
                "Feedback exists, one response is stale, and handoff is not claimed."
            ),
            evidence_refs=[
                ReviewBriefEvidenceRef(
                    kind="readiness",
                    identifier="handoff-preview",
                    summary="handoff posture remains advisory",
                )
            ],
        ),
        review_feedback=ReviewBriefSection(
            title="Review Feedback",
            body="One requested change remains open and visible.",
            evidence_refs=[
                ReviewBriefEvidenceRef(
                    kind="feedback",
                    identifier="rfb_1",
                    summary="requested change is unresolved",
                )
            ],
        ),
        review_responses=ReviewBriefSection(
            title="Review Responses",
            body="One fixup response cites inventory but needs fresh checks.",
            evidence_refs=[
                ReviewBriefEvidenceRef(
                    kind="response",
                    identifier="rrsp_1",
                    summary="response linked to changed files",
                )
            ],
        ),
        manual_evidence=ReviewBriefSection(
            title="Manual Evidence",
            body="External check is summary-only and local-only.",
            evidence_refs=[
                ReviewBriefEvidenceRef(
                    kind="manual_evidence",
                    identifier="mev_1",
                    summary="operator-attached command summary",
                    local_only=True,
                )
            ],
        ),
        live_review_evidence=ReviewBriefSection(
            title="Live Review Evidence",
            body="Browser and accessibility notes are advisory.",
            evidence_refs=[
                ReviewBriefEvidenceRef(
                    kind="browser_evidence",
                    identifier="browser-1",
                    summary="dashboard route inspected in local browser",
                    local_only=True,
                ),
                ReviewBriefEvidenceRef(
                    kind="accessibility_evidence",
                    identifier="a11y-1",
                    summary="keyboard pass noted unresolved focus risk",
                    local_only=True,
                ),
            ],
        ),
        stale_verification=ReviewBriefSection(
            title="Stale Verification",
            body="A retained pass predates response-linked fixup inventory.",
            evidence_refs=[
                ReviewBriefEvidenceRef(
                    kind="verification",
                    identifier="pytest-stale",
                    summary="rerun focused tests before handoff",
                )
            ],
        ),
        publication_boundary=ReviewBriefSection(
            title="Publication Boundary",
            body="Handoff readiness is advisory; publication did not occur.",
            evidence_refs=[
                ReviewBriefEvidenceRef(
                    kind="publication_boundary",
                    identifier="publication-boundary",
                    summary="no stage, commit, push, PR, or merge action",
                )
            ],
        ),
    )

    payload = artifact.model_dump(mode="json")
    markdown = review_brief_markdown(artifact)

    assert payload["schema_version"] == 2
    assert payload["review_feedback"]["evidence_refs"][0]["kind"] == "feedback"
    assert payload["manual_evidence"]["evidence_refs"][0]["local_only"] is True
    for section_title in (
        "Lifecycle Summary",
        "Review Feedback",
        "Review Responses",
        "Manual Evidence",
        "Live Review Evidence",
        "Stale Verification",
        "Publication Boundary",
    ):
        assert section_title in markdown
    assert "publication did not occur" in markdown
    assert "no stage, commit, push, PR, or merge action" in markdown


def test_review_brief_redacts_local_paths_glassbox_paths_and_secrets() -> None:
    artifact = _brief(
        objective=(
            "Review /Users/alice/src/private and "
            ".glassbox/sessions/session-1/artifacts/raw.log with token=secret123"
        )
    )
    markdown = review_brief_markdown(artifact)
    raw_json = review_brief_artifact_json(artifact)

    assert "/Users/alice" not in markdown
    assert ".glassbox/sessions" not in markdown
    assert "secret123" not in markdown
    assert "[local-path]" in raw_json
    assert "[glassbox-artifact-ref]" in raw_json
    assert "[secret-redacted]" in raw_json


def test_review_brief_text_redaction_handles_provider_keys() -> None:
    redacted = redact_review_brief_text(
        "provider skipped with api_key=abc123 and sk-abcdefghijklmnopqrstuvwxyz"
    )

    assert "abc123" not in redacted
    assert "sk-abcdefghijklmnopqrstuvwxyz" not in redacted
    assert redacted.count("[secret-redacted]") == 2


def test_review_brief_generation_degrades_without_inventory(tmp_path: Path) -> None:
    repository = _FakeReviewBriefRepository(tmp_path)
    artifacts = _FakeArtifactRepository(tmp_path)

    result = ChangesetReviewBriefService(
        cast(ChangesetRepository, repository),
        cast(ArtifactRepository, artifacts),
    ).generate(
        repository.changeset.changeset_id,
        tmp_path,
        created_by="qa",
    )

    assert result.brief.changed_file_inventory.body.startswith(
        "No structured change inventory"
    )
    assert "verification readiness is missing" in result.limitations
    assert result.event.payload.event_type == "ChangesetReviewBriefCreated"
    assert result.readiness_event.payload.event_type == "ChangesetReadinessDecided"
    assert result.artifact.absolute_path.exists()
    assert "changeset_review_brief" in result.artifact.absolute_path.read_text(
        encoding="utf-8"
    )
    assert isinstance(repository.events[0].payload, ChangesetReviewBriefCreated)
    assert isinstance(repository.events[1].payload, ChangesetReadinessDecided)
    assert repository.events[1].payload.review_brief_artifact_id == (
        result.artifact.artifact_id
    )


def test_review_brief_generation_includes_review_loop_evidence(
    tmp_path: Path,
) -> None:
    repository = _FakeReviewBriefRepository(tmp_path)
    artifacts = _FakeArtifactRepository(tmp_path)
    feedback_id = new_review_feedback_id()
    manual_evidence_id = new_manual_evidence_id()
    manual_artifact_id = new_artifact_id()
    fixup_artifact_id = new_artifact_id()
    now = datetime.now(UTC)
    repository.feedback = [
        ReviewFeedbackRecord(
            session_id=repository.session_id,
            feedback_id=feedback_id,
            changeset_id=repository.changeset.changeset_id,
            feedback_kind=ReviewFeedbackKind.REQUESTED_CHANGE,
            provenance=ReviewFeedbackProvenance.REVIEWER,
            disposition=ReviewFeedbackDisposition.RESPONDED,
            summary="Clarify lifecycle brief feedback handling",
            body=None,
            source_label="local-review",
            reviewer_label="reviewer",
            created_by="operator",
            updated_by="operator",
            resolved_by=None,
            archived_by=None,
            accepted_by=None,
            resolution_summary=None,
            residual_risk=None,
            risk_summary=None,
            acceptance_reason=None,
            archived_reason=None,
            replacement_feedback_id=None,
            reopened_count=0,
            created_at=now,
            updated_at=now,
            last_sequence=3,
        )
    ]
    repository.fixup_inventories[feedback_id] = [
        ReviewFeedbackFixupInventoryRecord(
            session_id=repository.session_id,
            feedback_id=feedback_id,
            changeset_id=repository.changeset.changeset_id,
            artifact_id=fixup_artifact_id,
            artifact_schema_version=1,
            source_kind=ReviewFixupSourceKind.MANUAL_WORKSPACE_EDIT,
            source_summary="Updated review brief contract tests",
            source_digest="before",
            inventory_freshness=ChangesetInventoryFreshness.STALE,
            changed_path_count=2,
            matched_scope_path_count=1,
            stale=True,
            stale_reason="workspace changed after response fixup inventory",
            recorded_by="operator",
            created_at=now,
            last_sequence=4,
        )
    ]
    repository.manual_evidence = [
        ManualEvidenceRecord(
            session_id=repository.session_id,
            evidence_id=manual_evidence_id,
            evidence_kind=ManualEvidenceKind.ACCESSIBILITY_NOTE,
            state=ManualEvidenceState.ATTACHED,
            target_kind=ManualEvidenceTargetKind.FEEDBACK,
            target_id=str(feedback_id),
            changeset_id=repository.changeset.changeset_id,
            feedback_id=feedback_id,
            artifact_id=manual_artifact_id,
            artifact_schema_version=1,
            summary="Keyboard review noted one unresolved focus risk",
            source_label="manual-a11y",
            observed_at=now,
            created_by="operator",
            local_only=True,
            redaction_status=ManualEvidenceRedactionStatus.PASSED,
            freshness=ManualEvidenceFreshness.CURRENT,
            limitations=["manual accessibility note is advisory"],
            non_claims=["not accessibility certification"],
            created_at=now,
            updated_at=now,
            last_sequence=5,
        )
    ]

    result = ChangesetReviewBriefService(
        cast(ChangesetRepository, repository),
        cast(ArtifactRepository, artifacts),
    ).generate(
        repository.changeset.changeset_id,
        Path(__file__).resolve().parents[2],
        created_by="qa",
    )

    assert result.brief.lifecycle_summary is not None
    assert result.brief.review_feedback is not None
    assert result.brief.review_responses is not None
    assert result.brief.manual_evidence is not None
    assert result.brief.live_review_evidence is not None
    assert result.brief.stale_verification is not None
    assert result.brief.publication_boundary is not None
    assert result.brief.review_feedback.evidence_refs[0].kind == "feedback"
    assert result.brief.review_responses.evidence_refs[0].kind == "response"
    assert (
        result.brief.manual_evidence.evidence_refs[0].kind == "accessibility_evidence"
    )
    assert result.brief.local_only is True
    assert "Review Feedback" in result.markdown
    assert "Live Review Evidence" in result.markdown
    assert "Publication Boundary" in result.markdown
    assert isinstance(repository.events[1].payload, ChangesetReadinessDecided)
    assert repository.events[1].payload.state == (
        ChangesetReadinessState.NEEDS_VERIFICATION
    )
    assert any(
        "need fresh verification" in blocker
        for blocker in repository.events[1].payload.blockers
    )


def test_review_brief_generation_currently_fails_when_limitations_overflow(
    tmp_path: Path,
) -> None:
    repository = _FakeReviewBriefRepository(tmp_path)
    artifacts = _FakeArtifactRepository(tmp_path)
    now = datetime.now(UTC)
    repository.manual_evidence = [
        ManualEvidenceRecord(
            session_id=repository.session_id,
            evidence_id=new_manual_evidence_id(),
            evidence_kind=ManualEvidenceKind.OPERATOR_ASSERTION,
            state=ManualEvidenceState.ATTACHED,
            target_kind=ManualEvidenceTargetKind.CHANGESET,
            target_id=str(repository.changeset.changeset_id),
            changeset_id=repository.changeset.changeset_id,
            feedback_id=None,
            artifact_id=new_artifact_id(),
            artifact_schema_version=1,
            summary=f"Retained rich evidence item {index}",
            source_label="gbx-1410-characterization",
            observed_at=now,
            created_by="operator",
            local_only=True,
            redaction_status=ManualEvidenceRedactionStatus.PASSED,
            freshness=ManualEvidenceFreshness.NEEDS_INSPECTION,
            limitations=[f"retained limitation {index:02d}"],
            non_claims=["manual evidence is not deterministic proof"],
            created_at=now,
            updated_at=now,
            last_sequence=10 + index,
        )
        for index in range(25)
    ]

    with pytest.raises(ValidationError) as exc_info:
        ChangesetReviewBriefService(
            cast(ChangesetRepository, repository),
            cast(ArtifactRepository, artifacts),
        ).generate(
            repository.changeset.changeset_id,
            tmp_path,
            created_by="qa",
        )

    assert "limitations" in str(exc_info.value)
    assert "at most 20 items" in str(exc_info.value)
    assert repository.events == []


def _brief(
    objective: str = "Review deterministic changeset evidence",
    lifecycle_summary: ReviewBriefSection | None = None,
    review_feedback: ReviewBriefSection | None = None,
    review_responses: ReviewBriefSection | None = None,
    manual_evidence: ReviewBriefSection | None = None,
    live_review_evidence: ReviewBriefSection | None = None,
    stale_verification: ReviewBriefSection | None = None,
    publication_boundary: ReviewBriefSection | None = None,
) -> ReviewBriefArtifact:
    verification_id = new_task_verification_id()
    inventory_artifact_id = new_artifact_id()
    return ReviewBriefArtifact(
        changeset_id=new_changeset_id(),
        session_id=new_session_id(),
        objective=objective,
        change_summary=ReviewBriefSection(
            title="Change Summary",
            body="Updates changeset review posture without raw diffs.",
            evidence_refs=[
                ReviewBriefEvidenceRef(
                    kind="changeset",
                    identifier="changeset-summary",
                    summary="Changeset projection names the objective.",
                )
            ],
        ),
        changed_file_inventory=ReviewBriefSection(
            title="Changed-File Inventory",
            body="Inventory artifact summarizes 3 changed paths.",
            evidence_refs=[
                ReviewBriefEvidenceRef(
                    kind="inventory",
                    identifier=str(inventory_artifact_id),
                    artifact_id=inventory_artifact_id,
                    summary="Summary-only inventory artifact.",
                )
            ],
        ),
        affected_subsystems=ReviewBriefSection(
            title="Affected Subsystems",
            body="runtime package has fresh topology and tests/unit coverage.",
        ),
        provenance=ReviewBriefSection(
            title="Provenance",
            body="Path provenance is direct for runtime changes and inferred for docs.",
        ),
        lifecycle_summary=lifecycle_summary,
        review_feedback=review_feedback,
        review_responses=review_responses,
        manual_evidence=manual_evidence,
        live_review_evidence=live_review_evidence,
        verification=ReviewBriefSection(
            title="Verification",
            body="One retained verification check is missing.",
            evidence_refs=[
                ReviewBriefEvidenceRef(
                    kind="verification",
                    identifier=str(verification_id),
                    verification_id=verification_id,
                    summary="Verification readiness is missing.",
                )
            ],
        ),
        stale_verification=stale_verification,
        command_evidence=ReviewBriefSection(
            title="Command Evidence",
            body="One retained command supports verification.",
            evidence_refs=[
                ReviewBriefEvidenceRef(
                    kind="command",
                    identifier="attempt-1",
                    artifact_id=new_artifact_id(),
                    summary="test/failed: retained command evidence.",
                    local_only=True,
                )
            ],
        ),
        publication_boundary=publication_boundary,
        risks=ReviewBriefSection(
            title="Risks",
            body="Medium advisory risk remains until verification is fresh.",
        ),
        non_claims=[
            "review brief is a summary, not proof",
            "raw command output is not included",
        ],
        reviewer_checklist=[
            "Inspect the changed-file inventory",
            "Run or review the recommended verification command",
        ],
        safe_inspection_commands=[
            "glassbox changeset show CHANGESET --cwd .",
            "glassbox changeset verification-plan CHANGESET --cwd .",
        ],
    )


class _FakeReviewBriefRepository:
    def __init__(self, tmp_path: Path) -> None:
        self.session_id = new_session_id()
        self.changeset = ChangesetRecord(
            session_id=self.session_id,
            changeset_id=new_changeset_id(),
            objective="Review local evidence",
            summary=None,
            status="active",
            created_by="operator",
            risk_level=ChangesetRiskLevel.UNKNOWN,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            last_sequence=1,
        )
        self.sources = [
            ChangesetSourceRecord(
                session_id=self.session_id,
                changeset_id=self.changeset.changeset_id,
                source_kind=ChangesetSourceKind.WORKSPACE_DIFF,
                source_session_id=self.session_id,
                reason="created from workspace diff request with no local diff",
                limitation="workspace diff has not been refreshed",
                created_at=datetime.now(UTC),
                last_sequence=2,
            )
        ]
        self.feedback: list[ReviewFeedbackRecord] = []
        self.fixup_inventories: dict[
            object,
            list[ReviewFeedbackFixupInventoryRecord],
        ] = {}
        self.manual_evidence: list[ManualEvidenceRecord] = []
        self.events: list[EventEnvelope] = []
        self.tmp_path = tmp_path

    def get_changeset(self, changeset_id):
        return self.changeset if changeset_id == self.changeset.changeset_id else None

    def list_changeset_sources(self, session_id, changeset_id):
        del session_id, changeset_id
        return list(self.sources)

    def get_changeset_inventory(self, session_id, changeset_id):
        del session_id, changeset_id
        return None

    def get_changeset_verification_posture(self, session_id, changeset_id):
        del session_id, changeset_id
        return None

    def list_changeset_review_briefs(self, session_id, changeset_id):
        del session_id, changeset_id
        return []

    def list_changeset_readiness(self, session_id, changeset_id):
        del session_id, changeset_id
        return []

    def list_review_feedback(self, **kwargs):
        del kwargs
        return list(self.feedback)

    def list_review_feedback_fixup_inventories(self, session_id, feedback_id):
        del session_id
        return list(self.fixup_inventories.get(feedback_id, []))

    def list_review_feedback_fixup_paths(self, session_id, feedback_id, artifact_id):
        del session_id, feedback_id, artifact_id
        return []

    def list_manual_evidence(self, **kwargs):
        del kwargs
        return list(self.manual_evidence)

    def list_task_verification_ledger(self, session_id, task_id):
        del session_id, task_id
        return []

    def list_tool_attempts(self, session_id, *, limit=None, offset=0):
        del session_id, limit, offset
        return []

    def read_session_events(self, session_id):
        del session_id
        return []

    def append_events(self, events):
        stored = [
            event.model_copy(update={"sequence": len(self.events) + index})
            for index, event in enumerate(events, start=1)
        ]
        self.events.extend(stored)
        return stored


class _FakeArtifactRepository:
    def __init__(self, tmp_path: Path) -> None:
        self.tmp_path = tmp_path

    def write_text_artifact(
        self,
        session_id: SessionId,
        content: str,
        *,
        suffix: str,
    ) -> StoredArtifact:
        artifact_id = new_artifact_id()
        relative_path = (
            Path(".glassbox")
            / "sessions"
            / str(session_id)
            / "artifacts"
            / f"{artifact_id}{suffix}"
        )
        absolute_path = self.tmp_path / relative_path
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        absolute_path.write_text(content, encoding="utf-8")
        return StoredArtifact(
            artifact_id=artifact_id,
            session_id=session_id,
            relative_path=relative_path,
            absolute_path=absolute_path,
        )

    def read_text_artifact(
        self,
        relative_path: Path,
        *,
        encoding: str = "utf-8",
    ) -> str:
        return (self.tmp_path / relative_path).read_text(encoding=encoding)
