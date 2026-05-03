"""Manual evidence artifact and redaction contracts."""

import json
import re
from collections.abc import Sequence
from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core.ids import ChangesetId
from glassbox.core.ids import ManualEvidenceId
from glassbox.core.types import ManualEvidenceFreshness
from glassbox.core.types import ManualEvidenceKind
from glassbox.core.types import ManualEvidenceRedactionStatus
from glassbox.core.types import ManualEvidenceTargetKind

MANUAL_EVIDENCE_ARTIFACT_KIND = "manual_evidence"
MANUAL_EVIDENCE_ARTIFACT_SCHEMA_VERSION = 1
MANUAL_EVIDENCE_DEFAULT_MAX_TEXT_CHARS = 12_000
MANUAL_EVIDENCE_DEFAULT_MAX_LINES = 200
MANUAL_EVIDENCE_REDACTION = "summary-first-manual-evidence-v1"

_SECRET_PATTERN = re.compile(
    r"(?i)\b[\w.-]*(api[_-]?key|token|secret|password|authorization|cookie)"
    r"[\w.-]*\b\s*[:=]\s*\S+"
)
_PRIVATE_KEY_PATTERN = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
_GLASSBOX_PATH_PATTERN = re.compile(r"(^|[\s\"'`])(?:\.glassbox/|[^ \n\t]*\.glassbox/)")
_ABSOLUTE_PATH_PATTERN = re.compile(
    r"(?<![\w:/.-])/(?:Users|home|private|tmp|var)/[^\s\"'`]+"
)
_RAW_PROVIDER_PATTERN = re.compile(
    r"(?i)(raw provider transcript|provider_output|hidden provider output|"
    r'"choices"\s*:|\"messages\"\s*:|\"tool_calls\"\s*:)'
)


class ManualEvidenceLimits(BaseModel):
    """Bounded limits for summary-first manual evidence artifacts."""

    model_config = ConfigDict(extra="forbid")

    max_text_chars: int = Field(
        default=MANUAL_EVIDENCE_DEFAULT_MAX_TEXT_CHARS,
        ge=100,
        le=100_000,
    )
    max_lines: int = Field(default=MANUAL_EVIDENCE_DEFAULT_MAX_LINES, ge=1, le=2000)


class ManualEvidenceRedactionFinding(BaseModel):
    """A redaction finding that names the class without retaining raw secret text."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=100)
    severity: Literal["info", "warning", "reject"] = "warning"
    message: str = Field(min_length=1, max_length=500)


class ManualEvidenceRedactionResult(BaseModel):
    """Redaction decision for candidate manual evidence text."""

    model_config = ConfigDict(extra="forbid")

    status: ManualEvidenceRedactionStatus
    accepted: bool
    local_only: bool = True
    findings: list[ManualEvidenceRedactionFinding] = Field(default_factory=list)
    sanitized_text: str | None = Field(default=None, max_length=20_000)
    limitations: list[str] = Field(default_factory=list, max_length=20)


class ManualEvidenceTargetRef(BaseModel):
    """Stable local target reference for one manual evidence artifact."""

    model_config = ConfigDict(extra="forbid")

    target_kind: ManualEvidenceTargetKind
    target_id: str = Field(min_length=1, max_length=200)
    changeset_id: ChangesetId | None = None


class ManualEvidenceLocalReference(BaseModel):
    """Metadata-only local file or screenshot reference."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=200)
    path_hint: str | None = Field(default=None, max_length=500)
    media_type: str | None = Field(default=None, max_length=100)
    size_bytes: int | None = Field(default=None, ge=0)
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)
    local_only: Literal[True] = True


class ManualEvidenceArtifact(BaseModel):
    """Reviewer-bounded manual evidence artifact without raw local dumps."""

    model_config = ConfigDict(extra="forbid")

    artifact_kind: Literal["manual_evidence"] = MANUAL_EVIDENCE_ARTIFACT_KIND
    schema_version: Literal[1] = MANUAL_EVIDENCE_ARTIFACT_SCHEMA_VERSION
    evidence_id: ManualEvidenceId
    evidence_kind: ManualEvidenceKind
    redaction: Literal["summary-first-manual-evidence-v1"] = MANUAL_EVIDENCE_REDACTION
    raw_log_included: Literal[False] = False
    raw_provider_output_included: Literal[False] = False
    raw_file_contents_included: Literal[False] = False
    summary: str = Field(min_length=1, max_length=1000)
    source_label: str = Field(min_length=1, max_length=200)
    observed_at: datetime | None = None
    created_by: str = Field(default="operator", min_length=1, max_length=200)
    targets: list[ManualEvidenceTargetRef] = Field(min_length=1, max_length=20)
    local_only: bool = True
    redaction_status: ManualEvidenceRedactionStatus
    freshness: ManualEvidenceFreshness = ManualEvidenceFreshness.UNKNOWN
    sanitized_note: str | None = Field(default=None, max_length=4000)
    command_text: str | None = Field(default=None, max_length=500)
    external_url_label: str | None = Field(default=None, max_length=300)
    local_references: list[ManualEvidenceLocalReference] = Field(
        default_factory=list,
        max_length=20,
    )
    redaction_findings: list[ManualEvidenceRedactionFinding] = Field(
        default_factory=list,
        max_length=20,
    )
    limitations: list[str] = Field(default_factory=list, max_length=20)
    non_claims: list[str] = Field(default_factory=list, max_length=20)


def validate_manual_evidence_text(
    text: str,
    *,
    limits: ManualEvidenceLimits | None = None,
) -> ManualEvidenceRedactionResult:
    """Validate bounded manual evidence text without retaining unsafe snippets."""

    resolved_limits = limits or ManualEvidenceLimits()
    findings: list[ManualEvidenceRedactionFinding] = []
    _append_pattern_finding(findings, text, _SECRET_PATTERN, "secret-looking-value")
    _append_pattern_finding(findings, text, _PRIVATE_KEY_PATTERN, "private-key")
    _append_pattern_finding(findings, text, _GLASSBOX_PATH_PATTERN, "glassbox-state")
    _append_pattern_finding(findings, text, _ABSOLUTE_PATH_PATTERN, "absolute-path")
    _append_pattern_finding(findings, text, _RAW_PROVIDER_PATTERN, "provider-output")
    if len(text) > resolved_limits.max_text_chars:
        findings.append(
            ManualEvidenceRedactionFinding(
                code="oversized-text",
                severity="reject",
                message="manual evidence text exceeds the configured size boundary",
            )
        )
    if text.count("\n") + 1 > resolved_limits.max_lines:
        findings.append(
            ManualEvidenceRedactionFinding(
                code="oversized-log",
                severity="reject",
                message="manual evidence text has too many lines for summary capture",
            )
        )
    if findings:
        return ManualEvidenceRedactionResult(
            status=ManualEvidenceRedactionStatus.REJECTED,
            accepted=False,
            findings=findings,
            limitations=[
                "manual evidence rejected before artifact capture",
                "unsafe source text was not retained",
            ],
        )
    return ManualEvidenceRedactionResult(
        status=ManualEvidenceRedactionStatus.PASSED,
        accepted=True,
        sanitized_text=text,
        limitations=["manual evidence is summary-first and local provenance only"],
    )


def manual_evidence_artifact(
    *,
    evidence_id: ManualEvidenceId,
    evidence_kind: ManualEvidenceKind,
    summary: str,
    source_label: str,
    targets: Sequence[ManualEvidenceTargetRef],
    created_by: str = "operator",
    observed_at: datetime | None = None,
    candidate_text: str | None = None,
    command_text: str | None = None,
    external_url_label: str | None = None,
    local_references: Sequence[ManualEvidenceLocalReference] = (),
    freshness: ManualEvidenceFreshness = ManualEvidenceFreshness.UNKNOWN,
    limits: ManualEvidenceLimits | None = None,
) -> ManualEvidenceArtifact:
    """Build a retained manual evidence artifact after redaction validation."""

    redaction = validate_manual_evidence_text(candidate_text or summary, limits=limits)
    if not redaction.accepted:
        raise ValueError("manual evidence failed redaction checks")
    limitations = [
        *redaction.limitations,
        "manual evidence does not mean Glassbox ran the cited command or check",
    ]
    return ManualEvidenceArtifact(
        evidence_id=evidence_id,
        evidence_kind=evidence_kind,
        summary=summary,
        source_label=source_label,
        observed_at=observed_at,
        created_by=created_by,
        targets=list(targets),
        redaction_status=redaction.status,
        freshness=freshness,
        sanitized_note=redaction.sanitized_text,
        command_text=command_text,
        external_url_label=external_url_label,
        local_references=list(local_references),
        redaction_findings=redaction.findings,
        limitations=limitations,
        non_claims=[
            "not retained command evidence",
            "not deterministic verification proof",
            "not review approval",
            "not publication authority",
        ],
    )


def manual_evidence_artifact_json(artifact: ManualEvidenceArtifact) -> str:
    """Serialize a manual evidence artifact with deterministic key ordering."""

    return json.dumps(
        artifact.model_dump(mode="json"),
        indent=2,
        sort_keys=True,
    )


def _append_pattern_finding(
    findings: list[ManualEvidenceRedactionFinding],
    text: str,
    pattern: re.Pattern[str],
    code: str,
) -> None:
    if pattern.search(text):
        findings.append(
            ManualEvidenceRedactionFinding(
                code=code,
                severity="reject",
                message=f"manual evidence appears to contain {code}",
            )
        )


__all__ = [
    "MANUAL_EVIDENCE_ARTIFACT_KIND",
    "MANUAL_EVIDENCE_ARTIFACT_SCHEMA_VERSION",
    "MANUAL_EVIDENCE_REDACTION",
    "ManualEvidenceArtifact",
    "ManualEvidenceLimits",
    "ManualEvidenceLocalReference",
    "ManualEvidenceRedactionFinding",
    "ManualEvidenceRedactionResult",
    "ManualEvidenceTargetRef",
    "manual_evidence_artifact",
    "manual_evidence_artifact_json",
    "validate_manual_evidence_text",
]
