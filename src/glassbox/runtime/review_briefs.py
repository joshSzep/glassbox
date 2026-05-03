"""Reviewer-safe review brief artifact contract for local changesets."""

import json
import re
from collections.abc import Iterable
from typing import Annotated
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator

from glassbox.core.ids import ArtifactId
from glassbox.core.ids import BranchCandidateId
from glassbox.core.ids import BranchSearchId
from glassbox.core.ids import ChangesetId
from glassbox.core.ids import SessionId
from glassbox.core.ids import TaskId
from glassbox.core.ids import TaskVerificationId

REVIEW_BRIEF_ARTIFACT_KIND = "changeset_review_brief"
REVIEW_BRIEF_ARTIFACT_SCHEMA_VERSION = 2
REVIEW_BRIEF_REDACTION = "reviewer-safe-summary-no-raw-logs"

ReviewBriefRenderTarget = Literal["markdown", "json"]
ReviewBriefEvidenceKind = Literal[
    "changeset",
    "inventory",
    "provenance",
    "verification",
    "command",
    "feedback",
    "response",
    "manual_evidence",
    "browser_evidence",
    "dashboard_evidence",
    "accessibility_evidence",
    "readiness",
    "publication_boundary",
    "branch_candidate",
    "risk",
    "artifact",
    "operator_note",
]

_LOCAL_PATH_RE = re.compile(r"(?:(?:/Users|/private|/tmp|/var|/home)/[^\s`\"')\]]+)")
_GLASSBOX_PATH_RE = re.compile(r"(?:(?:^|\s)(?:\./)?\.glassbox/[^\s`\"')\]]+)")
_SECRET_RE = re.compile(
    r"(?i)\b(?:api[_-]?key|token|secret|password|authorization)\s*[:=]\s*[^\s,;]+|"
    r"\bsk-[A-Za-z0-9_-]{12,}\b"
)


class ReviewBriefEvidenceRef(BaseModel):
    """Reference to retained evidence without flattening raw logs."""

    model_config = ConfigDict(extra="forbid")

    kind: ReviewBriefEvidenceKind
    identifier: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=1000)
    artifact_id: ArtifactId | None = None
    verification_id: TaskVerificationId | None = None
    local_only: bool = False

    @field_validator("identifier", "summary", mode="before")
    @classmethod
    def redact_text_fields(cls, value: object) -> object:
        return redact_review_brief_text(value) if isinstance(value, str) else value


class ReviewBriefSection(BaseModel):
    """One named reviewer brief section."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1, max_length=4000)
    evidence_refs: list[ReviewBriefEvidenceRef] = Field(default_factory=list)

    @field_validator("title", "body", mode="before")
    @classmethod
    def redact_section_text(cls, value: object) -> object:
        return redact_review_brief_text(value) if isinstance(value, str) else value


class ReviewBriefArtifact(BaseModel):
    """Stable artifact shape for a reviewer-safe local changeset brief."""

    model_config = ConfigDict(extra="forbid")

    artifact_kind: Literal["changeset_review_brief"] = REVIEW_BRIEF_ARTIFACT_KIND
    schema_version: Literal[2] = REVIEW_BRIEF_ARTIFACT_SCHEMA_VERSION
    changeset_id: ChangesetId
    session_id: SessionId
    task_id: TaskId | None = None
    branch_search_id: BranchSearchId | None = None
    branch_candidate_id: BranchCandidateId | None = None
    render_targets: Annotated[
        list[ReviewBriefRenderTarget],
        Field(min_length=1, max_length=2),
    ] = ["markdown", "json"]
    redaction: Literal["reviewer-safe-summary-no-raw-logs"] = REVIEW_BRIEF_REDACTION
    redacted: Literal[True] = True
    local_only: bool = False
    raw_command_output_included: Literal[False] = False
    raw_provider_transcript_included: Literal[False] = False
    raw_diff_included: Literal[False] = False
    raw_file_contents_included: Literal[False] = False
    objective: str = Field(min_length=1, max_length=1000)
    change_summary: ReviewBriefSection
    changed_file_inventory: ReviewBriefSection
    affected_subsystems: ReviewBriefSection | None = None
    provenance: ReviewBriefSection
    lifecycle_summary: ReviewBriefSection | None = None
    review_feedback: ReviewBriefSection | None = None
    review_responses: ReviewBriefSection | None = None
    manual_evidence: ReviewBriefSection | None = None
    live_review_evidence: ReviewBriefSection | None = None
    verification: ReviewBriefSection
    stale_verification: ReviewBriefSection | None = None
    command_evidence: ReviewBriefSection
    branch_candidate_rationale: ReviewBriefSection | None = None
    publication_boundary: ReviewBriefSection | None = None
    risks: ReviewBriefSection
    non_claims: list[str] = Field(default_factory=list, min_length=1, max_length=20)
    reviewer_checklist: list[str] = Field(
        default_factory=list,
        min_length=1,
        max_length=20,
    )
    safe_inspection_commands: list[str] = Field(
        default_factory=list,
        min_length=1,
        max_length=20,
    )
    limitations: list[str] = Field(default_factory=list, max_length=20)

    @field_validator(
        "objective",
        "non_claims",
        "reviewer_checklist",
        "safe_inspection_commands",
        "limitations",
        mode="before",
    )
    @classmethod
    def redact_text_values(cls, value: object) -> object:
        if isinstance(value, str):
            return redact_review_brief_text(value)
        if isinstance(value, list):
            return [
                redact_review_brief_text(item) if isinstance(item, str) else item
                for item in value
            ]
        return value


def review_brief_artifact_json(artifact: ReviewBriefArtifact) -> str:
    """Serialize a review brief artifact as stable, sorted JSON."""

    return json.dumps(
        artifact.model_dump(mode="json"),
        indent=2,
        sort_keys=True,
    )


def review_brief_markdown(artifact: ReviewBriefArtifact) -> str:
    """Render the reviewer-safe Markdown target for one review brief."""

    sections = [
        ("Objective", artifact.objective),
        ("Change Summary", _section_markdown(artifact.change_summary)),
        ("Changed-File Inventory", _section_markdown(artifact.changed_file_inventory)),
    ]
    if artifact.affected_subsystems is not None:
        sections.append(
            (
                "Affected Subsystems",
                _section_markdown(artifact.affected_subsystems),
            )
        )
    sections.extend(
        [
            ("Provenance", _section_markdown(artifact.provenance)),
        ]
    )
    if artifact.lifecycle_summary is not None:
        sections.append(
            ("Lifecycle Summary", _section_markdown(artifact.lifecycle_summary))
        )
    if artifact.review_feedback is not None:
        sections.append(
            ("Review Feedback", _section_markdown(artifact.review_feedback))
        )
    if artifact.review_responses is not None:
        sections.append(
            ("Review Responses", _section_markdown(artifact.review_responses))
        )
    if artifact.manual_evidence is not None:
        sections.append(
            ("Manual Evidence", _section_markdown(artifact.manual_evidence))
        )
    if artifact.live_review_evidence is not None:
        sections.append(
            ("Live Review Evidence", _section_markdown(artifact.live_review_evidence))
        )
    sections.append(("Verification", _section_markdown(artifact.verification)))
    if artifact.stale_verification is not None:
        sections.append(
            ("Stale Verification", _section_markdown(artifact.stale_verification))
        )
    sections.append(("Command Evidence", _section_markdown(artifact.command_evidence)))
    if artifact.branch_candidate_rationale is not None:
        sections.append(
            (
                "Branch-Candidate Rationale",
                _section_markdown(artifact.branch_candidate_rationale),
            )
        )
    if artifact.publication_boundary is not None:
        sections.append(
            ("Publication Boundary", _section_markdown(artifact.publication_boundary))
        )
    sections.extend(
        [
            ("Risks", _section_markdown(artifact.risks)),
            ("Reviewer Checklist", _list_markdown(artifact.reviewer_checklist)),
            (
                "Safe Inspection Commands",
                _list_markdown(artifact.safe_inspection_commands),
            ),
            ("Non-Claims", _list_markdown(artifact.non_claims)),
        ]
    )
    if artifact.limitations:
        sections.append(("Limitations", _list_markdown(artifact.limitations)))
    body = "\n\n".join(f"## {title}\n\n{content}" for title, content in sections)
    return (
        f"# Review Brief: {artifact.changeset_id}\n\n"
        f"- Schema version: {artifact.schema_version}\n"
        f"- Redaction: {artifact.redaction}\n"
        f"- Local only: {str(artifact.local_only).lower()}\n\n"
        f"{body}\n"
    )


def redact_review_brief_text(value: str) -> str:
    """Apply reviewer-brief redaction to text fields and commands."""

    redacted = _SECRET_RE.sub("[secret-redacted]", value)
    redacted = _GLASSBOX_PATH_RE.sub(" [glassbox-artifact-ref]", redacted)
    return _LOCAL_PATH_RE.sub("[local-path]", redacted)


def _section_markdown(section: ReviewBriefSection) -> str:
    lines = [section.body]
    if section.evidence_refs:
        lines.append("")
        lines.append("Evidence:")
        lines.extend(
            f"- {ref.kind}: {ref.summary} ({ref.identifier})"
            for ref in section.evidence_refs
        )
    return "\n".join(lines)


def _list_markdown(items: Iterable[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


__all__ = [
    "REVIEW_BRIEF_ARTIFACT_KIND",
    "REVIEW_BRIEF_ARTIFACT_SCHEMA_VERSION",
    "REVIEW_BRIEF_REDACTION",
    "ReviewBriefArtifact",
    "ReviewBriefEvidenceRef",
    "ReviewBriefSection",
    "redact_review_brief_text",
    "review_brief_artifact_json",
    "review_brief_markdown",
]
