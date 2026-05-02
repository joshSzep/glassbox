"""Tests for the changeset review brief artifact contract."""

from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import cast

from glassbox.core import ChangesetReadinessDecided
from glassbox.core import ChangesetRecord
from glassbox.core import ChangesetReviewBriefCreated
from glassbox.core import ChangesetRiskLevel
from glassbox.core import ChangesetSourceKind
from glassbox.core import ChangesetSourceRecord
from glassbox.core import EventEnvelope
from glassbox.core import SessionId
from glassbox.core import new_artifact_id
from glassbox.core import new_changeset_id
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
    assert payload["schema_version"] == 1
    assert "Change Summary" in markdown
    assert "Changed-File Inventory" in markdown
    assert "Verification" in markdown
    assert "Reviewer Checklist" in markdown
    assert "Safe Inspection Commands" in markdown
    assert '"artifact_kind": "changeset_review_brief"' in raw_json


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


def _brief(
    objective: str = "Review deterministic changeset evidence",
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
        provenance=ReviewBriefSection(
            title="Provenance",
            body="Path provenance is direct for runtime changes and inferred for docs.",
        ),
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

    def list_task_verification_ledger(self, session_id, task_id):
        del session_id, task_id
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
