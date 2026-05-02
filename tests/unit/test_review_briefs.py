"""Tests for the changeset review brief artifact contract."""

from glassbox.core import new_artifact_id
from glassbox.core import new_changeset_id
from glassbox.core import new_session_id
from glassbox.core import new_task_verification_id
from glassbox.runtime.review_briefs import REVIEW_BRIEF_ARTIFACT_KIND
from glassbox.runtime.review_briefs import REVIEW_BRIEF_REDACTION
from glassbox.runtime.review_briefs import ReviewBriefArtifact
from glassbox.runtime.review_briefs import ReviewBriefEvidenceRef
from glassbox.runtime.review_briefs import ReviewBriefSection
from glassbox.runtime.review_briefs import redact_review_brief_text
from glassbox.runtime.review_briefs import review_brief_artifact_json
from glassbox.runtime.review_briefs import review_brief_markdown


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
