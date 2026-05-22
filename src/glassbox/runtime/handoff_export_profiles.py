"""Recipient-oriented export profile contracts for v17 handoff packages."""

from collections.abc import Sequence

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core import HandoffIntent
from glassbox.core import HandoffPackageKind
from glassbox.core import HandoffSafeCommand
from glassbox.core import HandoffSourceKind
from glassbox.core import HandoffSourceRef

HANDOFF_OUTPUT_FORMATS = ("json", "json+markdown")


class HandoffExportProfile(BaseModel):
    """Typed export profile chosen from the recipient's next intended action."""

    model_config = ConfigDict(extra="forbid")

    profile_id: HandoffIntent
    source: HandoffSourceRef
    package_kind: HandoffPackageKind
    output_format: str = Field(default="json", min_length=1, max_length=80)
    required_sections: list[str] = Field(default_factory=list, max_length=100)
    optional_sections: list[str] = Field(default_factory=list, max_length=100)
    safe_inspection_commands: list[HandoffSafeCommand] = Field(
        default_factory=list,
        max_length=20,
    )
    non_claims: list[str] = Field(default_factory=list, max_length=50)
    local_only_treatment: str = Field(min_length=1, max_length=1000)
    recipient_next_action: str = Field(min_length=1, max_length=1000)


def parse_handoff_intent(value: str | HandoffIntent | None) -> HandoffIntent:
    """Parse CLI intent values while preserving the stable default."""

    if value is None:
        return HandoffIntent.REVIEW_ONLY
    if isinstance(value, HandoffIntent):
        return value
    try:
        return HandoffIntent(value)
    except ValueError as exc:
        supported = ", ".join(intent.value for intent in HandoffIntent)
        raise ValueError(
            f"unsupported handoff intent {value!r}; use {supported}"
        ) from exc


def build_handoff_export_profile(
    *,
    source: HandoffSourceRef,
    package_kind: HandoffPackageKind,
    intent: HandoffIntent = HandoffIntent.REVIEW_ONLY,
    output_format: str = "json",
    included_sections: Sequence[str] = (),
) -> HandoffExportProfile:
    """Build profile metadata for a portable handoff export."""

    output_format = validate_handoff_output_format(output_format)
    required_sections = _required_sections(source.kind, intent, included_sections)
    optional_sections = _optional_sections(source.kind, intent)
    return HandoffExportProfile(
        profile_id=intent,
        source=source,
        package_kind=package_kind,
        output_format=output_format,
        required_sections=required_sections,
        optional_sections=optional_sections,
        safe_inspection_commands=_safe_commands(source, intent),
        non_claims=_non_claims(intent),
        local_only_treatment=_local_only_treatment(intent),
        recipient_next_action=_recipient_next_action(intent),
    )


def validate_handoff_output_format(
    output_format: str,
    *,
    supported_formats: Sequence[str] = HANDOFF_OUTPUT_FORMATS,
) -> str:
    """Validate a handoff package output format for profile metadata."""

    if output_format in supported_formats:
        return output_format
    supported = ", ".join(supported_formats)
    raise ValueError(
        f"unsupported handoff output format {output_format!r}; use {supported}"
    )


def _required_sections(
    source_kind: HandoffSourceKind,
    intent: HandoffIntent,
    included_sections: Sequence[str],
) -> list[str]:
    common = [
        "profile",
        "redaction",
        "local_only_inventory",
        "safe_inspection_commands",
        "non_claims",
    ]
    source_sections = {
        HandoffSourceKind.SESSION: [
            "metadata",
            "handoff",
            "transcript",
            "events",
        ],
        HandoffSourceKind.CHANGESET: [
            "changeset",
            "evidence_graph",
            "verification",
            "handoff_readiness",
        ],
    }.get(source_kind, [])
    intent_sections = {
        HandoffIntent.REVIEW_ONLY: ["reviewer_safe_summary"],
        HandoffIntent.CONTINUE_WORK: ["continuation_posture"],
        HandoffIntent.VERIFICATION_NEEDED: ["verification"],
        HandoffIntent.FAILURE_TRIAGE: ["failure_posture"],
        HandoffIntent.RELEASE_SIGNOFF: ["release_evidence"],
        HandoffIntent.FUTURE_SELF: ["future_self_context"],
        HandoffIntent.FORK_RECOMMENDED: ["fork_guidance"],
    }[intent]
    return _dedupe([*common, *source_sections, *intent_sections, *included_sections])


def _optional_sections(
    source_kind: HandoffSourceKind,
    intent: HandoffIntent,
) -> list[str]:
    optional = [
        "recipient",
        "expected_custodian",
        "exported_by",
        "note",
        "markdown_summary",
    ]
    if source_kind == HandoffSourceKind.SESSION:
        optional.extend(["branch_search_summaries", "checkpoint_history"])
    if source_kind == HandoffSourceKind.CHANGESET:
        optional.extend(["review_feedback", "manual_evidence", "review_responses"])
    if intent in {
        HandoffIntent.CONTINUE_WORK,
        HandoffIntent.FORK_RECOMMENDED,
        HandoffIntent.FUTURE_SELF,
    }:
        optional.append("task_summaries")
    return _dedupe(optional)


def _safe_commands(
    source: HandoffSourceRef,
    intent: HandoffIntent,
) -> list[HandoffSafeCommand]:
    source_id = source.primary_id or "SOURCE_ID"
    if source.kind == HandoffSourceKind.SESSION:
        commands = [
            _safe_command(
                f"glassbox session status {source_id} --cwd .",
                "Inspect session status before acting on the handoff.",
            ),
            _safe_command(
                f"glassbox session handoff-readiness {source_id} --cwd .",
                "Inspect recipient-specific session handoff readiness.",
            ),
        ]
    elif source.kind == HandoffSourceKind.CHANGESET:
        commands = [
            _safe_command(
                f"glassbox changeset show {source_id} --cwd .",
                "Inspect changeset state and retained evidence summaries.",
            ),
            _safe_command(
                f"glassbox changeset handoff-readiness {source_id} --cwd .",
                "Inspect changeset handoff readiness before review or follow-up.",
            ),
        ]
    else:
        commands = [
            _safe_command(
                "glassbox observability status --cwd .",
                "Inspect workspace posture before accepting a handoff.",
            )
        ]
    if intent == HandoffIntent.VERIFICATION_NEEDED:
        commands.append(
            _safe_command(
                "glassbox eval audit --cwd .",
                "Inspect retained deterministic eval evidence before verification.",
            )
        )
    return commands


def _non_claims(intent: HandoffIntent) -> list[str]:
    claims = [
        "export profile does not grant continuation authority",
        "export profile does not approve review, verification, release, or publication",
        "export profile does not prove source workspace completeness",
        "export profile does not include raw local evidence unless declared",
    ]
    if intent == HandoffIntent.REVIEW_ONLY:
        claims.append("review-only profile is not approval to continue work")
    if intent == HandoffIntent.CONTINUE_WORK:
        claims.append("continue-work profile still requires local policy approval")
    if intent == HandoffIntent.RELEASE_SIGNOFF:
        claims.append("release-signoff profile is not publication approval")
    return claims


def _local_only_treatment(intent: HandoffIntent) -> str:
    if intent == HandoffIntent.FUTURE_SELF:
        return (
            "Local-only evidence is inventoried for the same operator to inspect "
            "later; raw contents still remain outside the portable package."
        )
    if intent == HandoffIntent.CONTINUE_WORK:
        return (
            "Recipient must inspect local-only evidence gaps before continuation "
            "or choose a fork/new-session path."
        )
    if intent == HandoffIntent.RELEASE_SIGNOFF:
        return (
            "Local-only release evidence is advisory unless backed by deterministic "
            "retained release artifacts."
        )
    return (
        "Local-only evidence is disclosed as limitations and category counts; raw "
        "contents stay in the source workspace."
    )


def _recipient_next_action(intent: HandoffIntent) -> str:
    return {
        HandoffIntent.REVIEW_ONLY: "Inspect the package and provide review feedback.",
        HandoffIntent.CONTINUE_WORK: "Inspect readiness before starting new work.",
        HandoffIntent.VERIFICATION_NEEDED: (
            "Inspect gaps, then run chosen verification."
        ),
        HandoffIntent.FAILURE_TRIAGE: (
            "Inspect failure posture before attempting repair."
        ),
        HandoffIntent.RELEASE_SIGNOFF: "Inspect release evidence without publishing.",
        HandoffIntent.FUTURE_SELF: "Inspect context before resuming later work.",
        HandoffIntent.FORK_RECOMMENDED: "Inspect fork guidance before mutating state.",
    }[intent]


def _safe_command(display: str, purpose: str) -> HandoffSafeCommand:
    return HandoffSafeCommand(command=display.split(), display=display, purpose=purpose)


def _dedupe(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))[:100]


__all__ = [
    "HANDOFF_OUTPUT_FORMATS",
    "HandoffExportProfile",
    "build_handoff_export_profile",
    "parse_handoff_intent",
    "validate_handoff_output_format",
]
