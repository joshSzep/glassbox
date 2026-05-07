"""Unit tests for manual evidence artifact and redaction contracts."""

import pytest

from glassbox.core import ManualEvidenceFreshness
from glassbox.core import ManualEvidenceKind
from glassbox.core import ManualEvidenceRedactionStatus
from glassbox.core import ManualEvidenceTargetKind
from glassbox.core import new_changeset_id
from glassbox.core import new_manual_evidence_id
from glassbox.runtime.manual_evidence import MANUAL_EVIDENCE_ARTIFACT_KIND
from glassbox.runtime.manual_evidence import ManualEvidenceLimits
from glassbox.runtime.manual_evidence import ManualEvidenceLocalReference
from glassbox.runtime.manual_evidence import ManualEvidenceTargetRef
from glassbox.runtime.manual_evidence import manual_evidence_artifact
from glassbox.runtime.manual_evidence import manual_evidence_artifact_json
from glassbox.runtime.manual_evidence import validate_manual_evidence_text


def test_manual_evidence_artifact_is_summary_first_and_local_only() -> None:
    changeset_id = new_changeset_id()
    evidence_id = new_manual_evidence_id()

    artifact = manual_evidence_artifact(
        evidence_id=evidence_id,
        evidence_kind=ManualEvidenceKind.SCREENSHOT,
        summary="operator says the dashboard rendered the review feedback row",
        source_label="local-browser",
        targets=[
            ManualEvidenceTargetRef(
                target_kind=ManualEvidenceTargetKind.CHANGESET,
                target_id=str(changeset_id),
                changeset_id=changeset_id,
            )
        ],
        candidate_text="dashboard screenshot metadata reviewed locally",
        local_references=[
            ManualEvidenceLocalReference(
                label="dashboard screenshot",
                path_hint="screenshots/dashboard-review.png",
                media_type="image/png",
                width=1440,
                height=900,
            )
        ],
        freshness=ManualEvidenceFreshness.CURRENT,
    )
    payload = manual_evidence_artifact_json(artifact)

    assert artifact.artifact_kind == MANUAL_EVIDENCE_ARTIFACT_KIND
    assert artifact.local_only is True
    assert artifact.raw_log_included is False
    assert artifact.raw_provider_output_included is False
    assert artifact.raw_file_contents_included is False
    assert artifact.redaction_status == ManualEvidenceRedactionStatus.PASSED
    assert "not retained command evidence" in artifact.non_claims
    assert str(evidence_id) in payload


def test_manual_evidence_artifact_can_retain_skipped_advisory_non_claims() -> None:
    artifact = manual_evidence_artifact(
        evidence_id=new_manual_evidence_id(),
        evidence_kind=ManualEvidenceKind.BROWSER_OBSERVATION,
        summary="operator intentionally skipped dashboard walkthrough",
        source_label="dashboard-local",
        targets=[
            ManualEvidenceTargetRef(
                target_kind=ManualEvidenceTargetKind.CHANGESET,
                target_id=str(new_changeset_id()),
            )
        ],
        candidate_text=(
            "capture_state: not_run\n"
            "viewport: unknown\n"
            "skip_reason: local server was not started"
        ),
        freshness=ManualEvidenceFreshness.UNKNOWN,
        extra_limitations=[
            "skipped browser/dashboard evidence is not a pass",
            "viewport is unknown because no live pass was run",
        ],
        extra_non_claims=["skipped evidence is not passed evidence"],
    )

    assert artifact.freshness == ManualEvidenceFreshness.UNKNOWN
    assert "skipped browser/dashboard evidence is not a pass" in artifact.limitations
    assert "skipped evidence is not passed evidence" in artifact.non_claims


@pytest.mark.parametrize(
    ("text", "code"),
    [
        ("OPENAI_API_KEY=sk-secret", "secret-looking-value"),
        ("/Users/example/project/.glassbox/state.sqlite3", "glassbox-state"),
        ("/private/tmp/raw-output.log", "absolute-path"),
        ("-----BEGIN PRIVATE KEY-----\nabc", "private-key"),
        ('{"choices": [{"message": "raw"}]}', "provider-output"),
    ],
)
def test_manual_evidence_redaction_rejects_unsafe_text(
    text: str,
    code: str,
) -> None:
    result = validate_manual_evidence_text(text)

    assert result.accepted is False
    assert result.status == ManualEvidenceRedactionStatus.REJECTED
    assert code in {finding.code for finding in result.findings}
    assert result.sanitized_text is None


def test_manual_evidence_redaction_rejects_oversized_logs() -> None:
    result = validate_manual_evidence_text(
        "\n".join(f"line {index}" for index in range(6)),
        limits=ManualEvidenceLimits(max_text_chars=500, max_lines=5),
    )

    assert result.accepted is False
    assert "oversized-log" in {finding.code for finding in result.findings}


def test_manual_evidence_artifact_refuses_rejected_source_text() -> None:
    with pytest.raises(ValueError, match="failed redaction"):
        manual_evidence_artifact(
            evidence_id=new_manual_evidence_id(),
            evidence_kind=ManualEvidenceKind.SANITIZED_LOG,
            summary="operator attempted to attach raw log",
            source_label="local-shell",
            targets=[
                ManualEvidenceTargetRef(
                    target_kind=ManualEvidenceTargetKind.UNKNOWN,
                    target_id="unknown",
                )
            ],
            candidate_text="password=super-secret",
        )
