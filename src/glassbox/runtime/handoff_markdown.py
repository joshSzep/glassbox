"""Reviewer-safe Markdown rendering for local handoff exports."""

from typing import Any


def build_session_export_markdown(payload: Any) -> str:
    """Render a human handoff summary from a redacted session export payload."""

    handoff = payload.handoff
    summary = handoff.summary
    profile = payload.profile
    objective = (
        summary.latest_objective if summary is not None else handoff.next_action_summary
    )
    lines = [
        "# Session Handoff",
        "",
        f"- Session: `{payload.metadata.session_id}`",
        "- Source: `session`",
        f"- Intent: `{handoff.intent.value}`",
        f"- Recipient: {handoff.recipient or 'unspecified'}",
        f"- Status: `{payload.metadata.status}`",
        f"- Objective: {objective}",
        f"- Current posture: {handoff.next_action_summary}",
        "",
        "## Evidence Included",
        "",
        *_section_lines(_included_sections(payload)),
        "",
        "## Local-Only Evidence",
        "",
        *_local_only_lines(payload.local_only_inventory),
        "",
        "## Stale Or Missing Evidence",
        "",
        *_session_gap_lines(summary),
        "",
        "## Accepted Risks",
        "",
        *_plain_lines(summary.accepted_risks if summary is not None else []),
        "",
        "## Safe First Commands",
        "",
        *_command_lines(
            _profile_commands(profile) or _session_summary_commands(summary)
        ),
        "",
        "## Recipient Checklist",
        "",
        *_checklist_lines(profile),
        "",
        "## Non-Claims",
        "",
        *_plain_lines(_profile_non_claims(profile)),
        "",
        "## Redaction",
        "",
        *_plain_lines(payload.redaction_notes),
        "",
    ]
    return "\n".join(lines)


def build_changeset_export_markdown(payload: Any) -> str:
    """Render a human handoff summary from a reviewer-safe changeset payload."""

    graph_summary = payload.evidence_graph["summary"]
    profile = payload.profile
    intent = profile.profile_id.value if profile is not None else "review-only"
    lines = [
        "# Changeset Handoff",
        "",
        f"- Changeset: `{payload.changeset['changeset_id']}`",
        "- Source: `changeset`",
        f"- Intent: `{intent}`",
        f"- Recipient: {payload.recipient or 'unspecified'}",
        f"- Status: `{payload.changeset['status']}`",
        f"- Objective: {payload.changeset['objective']}",
        f"- Current posture: `{payload.handoff_readiness['state']}`",
        f"- Verification: `{payload.verification['readiness']['state']}`",
        (
            f"- Evidence graph: {graph_summary['node_count']} node(s), "
            f"{graph_summary['claim_count']} claim(s)"
        ),
        "",
        "## Evidence Included",
        "",
        *_section_lines(_included_sections(payload)),
        "",
        "## Local-Only Evidence",
        "",
        *_local_only_lines(payload.local_only_inventory),
        "",
        "## Stale Or Missing Evidence",
        "",
        *_changeset_gap_lines(payload),
        "",
        "## Accepted Risks",
        "",
        *_plain_lines(_changeset_accepted_risks(payload)),
        "",
        "## Safe First Commands",
        "",
        *_command_lines(
            _profile_commands(profile), fallback=payload.safe_inspection_commands
        ),
        "",
        "## Recipient Checklist",
        "",
        *_checklist_lines(profile),
        "",
        "## Non-Claims",
        "",
        *_plain_lines(payload.non_claims),
        "",
        "## Redaction",
        "",
        *_plain_lines(payload.redaction_report),
        "",
    ]
    return "\n".join(lines)


def _included_sections(payload: Any) -> list[str]:
    if payload.profile is not None:
        return list(payload.profile.required_sections)
    return [
        key
        for key, value in payload.model_dump(mode="json", exclude_none=True).items()
        if value not in ([], {})
    ]


def _local_only_lines(inventory: Any | None) -> list[str]:
    if inventory is None or not inventory.items:
        return ["- No local-only evidence inventory items are recorded."]
    return [
        f"- {item.category}: {item.count} item(s). {item.recipient_limitation}"
        for item in inventory.items[:20]
    ]


def _session_gap_lines(summary: Any | None) -> list[str]:
    if summary is None:
        return ["- No handoff summary was retained; inspect session status locally."]
    return [
        f"- Checkpoint: {summary.checkpoint_posture}",
        f"- Compaction: {summary.compaction_posture}",
        f"- Verification: {summary.verification_state}",
    ]


def _changeset_gap_lines(payload: Any) -> list[str]:
    gaps = list(payload.repository_intelligence_limitations)
    readiness = payload.verification.get("readiness", {})
    if readiness.get("state") not in {None, "ready", "passed"}:
        gaps.append(f"Verification readiness is {readiness.get('state')}.")
    if not gaps:
        return ["- No stale or missing evidence limitations are recorded."]
    return _plain_lines(gaps)


def _changeset_accepted_risks(payload: Any) -> list[str]:
    risks: list[str] = []
    accepted = payload.review_responses.get("accepted_risk_count", 0)
    if accepted:
        risks.append(f"{accepted} review response accepted risk item(s).")
    for item in payload.readiness:
        if item.get("accepted_risk_count", 0):
            risks.append(item["reason"])
    return risks


def _profile_commands(profile: Any | None) -> list[str]:
    if profile is None:
        return []
    return [command.display for command in profile.safe_inspection_commands]


def _session_summary_commands(summary: Any | None) -> list[str]:
    if summary is None:
        return []
    return list(summary.safe_inspection_commands)


def _profile_non_claims(profile: Any | None) -> list[str]:
    if profile is None:
        return [
            "handoff does not approve review, verification, release, or publication",
            "handoff does not prove source workspace completeness",
        ]
    return list(profile.non_claims)


def _section_lines(sections: list[str]) -> list[str]:
    return _plain_lines(sections)


def _command_lines(
    commands: list[str], *, fallback: list[str] | None = None
) -> list[str]:
    chosen = commands or list(fallback or [])
    if not chosen:
        return ["- No safe first commands are recorded."]
    return [f"- `{command}`" for command in chosen[:20]]


def _checklist_lines(profile: Any | None) -> list[str]:
    first = (
        profile.recipient_next_action
        if profile is not None
        else "Inspect the package before acting."
    )
    return [
        f"- [ ] {first}",
        "- [ ] Review local-only evidence limitations.",
        "- [ ] Inspect safe commands before any mutation.",
        "- [ ] Keep non-claims attached to downstream review or continuation.",
    ]


def _plain_lines(items: list[str]) -> list[str]:
    if not items:
        return ["- None recorded."]
    return [f"- {item}" for item in items[:50]]


__all__ = ["build_changeset_export_markdown", "build_session_export_markdown"]
