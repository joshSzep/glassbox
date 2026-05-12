"""Review-loop action result shaping for interactive clients."""

from collections.abc import Mapping
from typing import Any
from typing import cast
from uuid import UUID

from glassbox.cli.interactive_client_models import ReviewLoopAction
from glassbox.cli.interactive_client_models import ReviewLoopActionResult
from glassbox.cli.interactive_review_guidance import handoff_evidence_guidance
from glassbox.cli.interactive_review_guidance import payload_handoff_evidence_guidance
from glassbox.cli.interactive_review_guidance import review_evidence_guidance


def create_changeset_result(
    changeset_id: str,
    *,
    limitations: tuple[str, ...],
) -> ReviewLoopActionResult:
    return ReviewLoopActionResult(
        action="create",
        headline=f"Created review changeset {changeset_id}",
        changeset_id=changeset_id,
        details=(
            "Source: current workspace diff for this chat session.",
            "No tests, staging, commit, push, PR, or merge was run.",
        ),
        limitations=limitations,
        safe_next_actions=(
            f"glassbox changeset show {changeset_id} --cwd .",
            f"glassbox changeset verification-plan {changeset_id} --cwd .",
            f"glassbox changeset brief {changeset_id} --cwd .",
            f"glassbox changeset handoff-readiness {changeset_id} --cwd .",
        ),
        dashboard_path=f"/app/changesets/{changeset_id}",
    )


def workup_guide_result(
    *,
    changeset_id: str | None,
    changed_path_count: int,
    plan_entry_count: int | None = None,
    handoff_state: str | None = None,
) -> ReviewLoopActionResult:
    safe_next_actions = [
        "glassbox changeset workup --session SESSION_ID --cwd .",
    ]
    if changeset_id is not None:
        safe_next_actions = [
            f"glassbox changeset workup --changeset {changeset_id} --cwd .",
            (
                "glassbox changeset workup "
                f"--changeset {changeset_id} --confirm-refresh --cwd ."
            ),
            f"glassbox changeset verification-plan {changeset_id} --cwd .",
            (
                "glassbox changeset workup "
                f"--changeset {changeset_id} --confirm-brief --cwd ."
            ),
            f"glassbox changeset handoff-readiness {changeset_id} --cwd .",
        ]
    details = [
        f"Workspace preview: {changed_path_count} changed path(s).",
        "Durable steps require explicit CLI confirmation flags.",
    ]
    if plan_entry_count is not None:
        details.append(f"Verification plan: {plan_entry_count} entry(s).")
    if handoff_state is not None:
        details.append(f"Handoff posture: {handoff_state}.")
    return ReviewLoopActionResult(
        action=ReviewLoopAction.WORKUP_GUIDE,
        headline=(
            f"Guided workup for changeset {changeset_id}"
            if changeset_id is not None
            else "Guided workup preview"
        ),
        changeset_id=changeset_id,
        details=tuple(details),
        limitations=(
            "The guide does not run commands, stage, commit, push, or publish.",
        ),
        safe_next_actions=tuple(safe_next_actions),
        dashboard_path=(
            f"/app/changesets/{changeset_id}" if changeset_id is not None else None
        ),
    )


def fixup_inventory_result(
    feedback_id: UUID,
    result: Any,
    response_status: Any,
) -> ReviewLoopActionResult:
    return ReviewLoopActionResult(
        action=ReviewLoopAction.RECORD_FEEDBACK_FIXUP,
        headline=f"Recorded fixup inventory for feedback {feedback_id}",
        changeset_id=str(result.changeset_id),
        details=(
            f"Artifact: {result.artifact.artifact_id}",
            (
                f"Paths: {result.inventory.changed_path_count} changed, "
                f"{result.inventory.matched_scope_path_count} scoped matches."
            ),
            f"Verification: {response_status.verification_state.value}.",
            "No tests, staging, commit, push, PR, or merge was run.",
        ),
        limitations=tuple(result.inventory.limitations),
        safe_next_actions=tuple(response_status.safe_next_actions),
        dashboard_path=f"/app/changesets/{result.changeset_id}",
    )


def review_status_result_from_detail(
    changeset_id: UUID,
    detail: Any,
) -> ReviewLoopActionResult:
    summary = detail.review_response_summary
    skipped_total, skipped_browser, skipped_accessibility = (
        local_skipped_evidence_counts(detail.manual_evidence)
    )
    changeset_id_text = str(changeset_id)
    return ReviewLoopActionResult(
        action=ReviewLoopAction.STATUS,
        headline=f"Review status for changeset {changeset_id}",
        changeset_id=changeset_id_text,
        details=(
            f"{summary.total_feedback_count} feedback item(s), "
            f"{summary.unresolved_count} unresolved, "
            f"{summary.stale_response_count} stale response check(s).",
            f"Inventory: {detail.inventory_status.freshness.value}.",
            *review_evidence_guidance(
                changeset_id=changeset_id_text,
                missing_fixup_feedback_ids=missing_fixup_feedback_ids(summary),
                stale_response_count=summary.stale_response_count,
                review_brief_count=len(detail.review_briefs),
                skipped_live_evidence_count=skipped_total,
                skipped_browser_evidence_count=skipped_browser,
                skipped_accessibility_evidence_count=skipped_accessibility,
            ),
        ),
        limitations=tuple(detail.limitations),
        safe_next_actions=tuple(detail.safe_next_actions),
        dashboard_path=f"/app/changesets/{changeset_id}",
    )


def payload_review_status_result(
    changeset_id: str,
    payload: dict[str, Any],
) -> ReviewLoopActionResult:
    review_summary = payload["review_response_summary"]
    inventory_status = payload["inventory_status"]
    skipped_total, skipped_browser, skipped_accessibility = (
        payload_skipped_evidence_counts(payload.get("manual_evidence", []))
    )
    return ReviewLoopActionResult(
        action=ReviewLoopAction.STATUS,
        headline=f"Review status for changeset {changeset_id}",
        changeset_id=changeset_id,
        details=(
            (
                f"{review_summary['total_feedback_count']} feedback item(s), "
                f"{review_summary['unresolved_count']} unresolved, "
                f"{review_summary['stale_response_count']} stale response check(s)."
            ),
            f"Inventory: {inventory_status['freshness']}.",
            *review_evidence_guidance(
                changeset_id=changeset_id,
                missing_fixup_feedback_ids=payload_missing_fixup_feedback_ids(
                    review_summary
                ),
                stale_response_count=int(review_summary.get("stale_response_count", 0)),
                review_brief_count=len(payload.get("review_briefs", [])),
                skipped_live_evidence_count=skipped_total,
                skipped_browser_evidence_count=skipped_browser,
                skipped_accessibility_evidence_count=skipped_accessibility,
            ),
        ),
        limitations=string_tuple(payload.get("limitations", [])),
        safe_next_actions=string_tuple(payload.get("safe_next_actions", [])),
        dashboard_path=f"/app/changesets/{changeset_id}",
    )


def refresh_inventory_result(changeset_id: UUID, result: Any) -> ReviewLoopActionResult:
    return ReviewLoopActionResult(
        action=ReviewLoopAction.REFRESH_INVENTORY,
        headline=f"Refreshed review inventory for {changeset_id}",
        changeset_id=str(changeset_id),
        details=(
            f"Inventory artifact: {result.artifact.artifact_id}",
            f"Freshness: {result.freshness.value}",
        ),
        safe_next_actions=(
            f"glassbox changeset show {changeset_id} --cwd .",
            f"glassbox changeset verification-plan {changeset_id} --cwd .",
        ),
        dashboard_path=f"/app/changesets/{changeset_id}",
    )


def payload_refresh_inventory_result(
    changeset_id: str,
    payload: dict[str, Any],
) -> ReviewLoopActionResult:
    detail = payload.get("detail", {})
    inventory = detail.get("inventory") or {}
    return ReviewLoopActionResult(
        action=ReviewLoopAction.REFRESH_INVENTORY,
        headline=f"Refreshed review inventory for {changeset_id}",
        changeset_id=changeset_id,
        details=(
            f"Inventory artifact: {inventory.get('artifact_id', 'unknown')}",
            f"Status: {payload.get('status', 'refreshed')}",
        ),
        safe_next_actions=(
            f"glassbox changeset show {changeset_id} --cwd .",
            f"glassbox changeset verification-plan {changeset_id} --cwd .",
        ),
        dashboard_path=f"/app/changesets/{changeset_id}",
    )


def generate_brief_result(
    changeset_id: str,
    *,
    artifact_id: str,
    limitations: tuple[str, ...],
) -> ReviewLoopActionResult:
    return ReviewLoopActionResult(
        action=ReviewLoopAction.GENERATE_BRIEF,
        headline=f"Generated lifecycle brief for {changeset_id}",
        changeset_id=changeset_id,
        details=(f"Brief artifact: {artifact_id}",),
        limitations=limitations,
        safe_next_actions=(
            f"glassbox changeset show {changeset_id} --cwd .",
            f"glassbox changeset handoff-readiness {changeset_id} --cwd .",
        ),
        dashboard_path=f"/app/changesets/{changeset_id}",
    )


def preview_verification_result(
    changeset_id: str,
    *,
    readiness_state: str,
    command_count: int,
    limitations: tuple[str, ...],
    safe_next_actions: tuple[str, ...],
) -> ReviewLoopActionResult:
    return ReviewLoopActionResult(
        action=ReviewLoopAction.PREVIEW_VERIFICATION,
        headline=f"Previewed verification for {changeset_id}",
        changeset_id=changeset_id,
        details=(
            f"Readiness: {readiness_state}",
            f"{command_count} recommended command(s); none were run.",
        ),
        limitations=limitations,
        safe_next_actions=safe_next_actions,
        dashboard_path=f"/app/changesets/{changeset_id}",
    )


def handoff_readiness_result(
    changeset_id: UUID, readiness: Any
) -> ReviewLoopActionResult:
    return ReviewLoopActionResult(
        action=ReviewLoopAction.INSPECT_HANDOFF,
        headline=f"Handoff readiness for {changeset_id}",
        changeset_id=str(changeset_id),
        details=(
            f"State: {readiness.state}",
            readiness.reason,
            f"{len(readiness.blockers)} blocker(s).",
            *handoff_evidence_guidance(readiness),
        ),
        limitations=tuple(readiness.limitations),
        safe_next_actions=tuple(readiness.safe_next_actions),
        dashboard_path=f"/app/changesets/{changeset_id}",
    )


def payload_handoff_readiness_result(
    changeset_id: str,
    payload: dict[str, Any],
) -> ReviewLoopActionResult:
    blockers = payload.get("blockers", [])
    return ReviewLoopActionResult(
        action=ReviewLoopAction.INSPECT_HANDOFF,
        headline=f"Handoff readiness for {changeset_id}",
        changeset_id=changeset_id,
        details=(
            f"State: {payload.get('state', 'unknown')}",
            str(payload.get("reason", "No reason returned.")),
            f"{len(blockers)} blocker(s).",
            *payload_handoff_evidence_guidance(payload),
        ),
        limitations=string_tuple(payload.get("limitations", [])),
        safe_next_actions=string_tuple(payload.get("safe_next_actions", [])),
        dashboard_path=f"/app/changesets/{changeset_id}",
    )


def feedback_status_result(changeset_id: UUID, summary: Any) -> ReviewLoopActionResult:
    changeset_id_text = str(changeset_id)
    return ReviewLoopActionResult(
        action=ReviewLoopAction.SHOW_FEEDBACK_STATUS,
        headline=f"Feedback status for {changeset_id}",
        changeset_id=changeset_id_text,
        details=(
            f"{summary.total_feedback_count} feedback item(s), "
            f"{summary.unresolved_count} unresolved.",
            f"{summary.stale_response_count} stale response check(s).",
            *review_evidence_guidance(
                changeset_id=changeset_id_text,
                missing_fixup_feedback_ids=missing_fixup_feedback_ids(summary),
                stale_response_count=summary.stale_response_count,
                review_brief_count=None,
                skipped_live_evidence_count=None,
                skipped_browser_evidence_count=None,
                skipped_accessibility_evidence_count=None,
            ),
        ),
        safe_next_actions=tuple(summary.safe_next_actions),
        dashboard_path=f"/app/changesets/{changeset_id}",
    )


def payload_feedback_status_result(
    changeset_id: str,
    summary: dict[str, Any],
) -> ReviewLoopActionResult:
    return ReviewLoopActionResult(
        action=ReviewLoopAction.SHOW_FEEDBACK_STATUS,
        headline=f"Feedback status for {changeset_id}",
        changeset_id=changeset_id,
        details=(
            (
                f"{summary.get('total_feedback_count', 0)} feedback item(s), "
                f"{summary.get('unresolved_count', 0)} unresolved."
            ),
            f"{summary.get('stale_response_count', 0)} stale response check(s).",
            *review_evidence_guidance(
                changeset_id=changeset_id,
                missing_fixup_feedback_ids=payload_missing_fixup_feedback_ids(summary),
                stale_response_count=int(summary.get("stale_response_count", 0)),
                review_brief_count=None,
                skipped_live_evidence_count=None,
                skipped_browser_evidence_count=None,
                skipped_accessibility_evidence_count=None,
            ),
        ),
        safe_next_actions=string_tuple(summary.get("safe_next_actions", [])),
        dashboard_path=f"/app/changesets/{changeset_id}",
    )


def operator_queue_result(
    *,
    action: ReviewLoopAction,
    view: str,
    payload: Mapping[str, Any],
) -> ReviewLoopActionResult:
    """Shape the typed operator queue into a bounded terminal summary."""

    items = [
        item
        for item in cast(list[Any], payload.get("operator_queue", []))
        if isinstance(item, dict) and _queue_view_matches(item, view)
    ]
    counts = cast(dict[str, Any], payload.get("operator_queue_counts", {}))
    headline = {
        ReviewLoopAction.OPERATOR_QUEUE: "Operator queue",
        ReviewLoopAction.NEXT_ACTIONS: "Next actions",
        ReviewLoopAction.MAINTENANCE_CHECKS: "Maintenance checks",
    }.get(action, "Operator queue")
    details = [
        _queue_counts_line(counts),
        f"View: {view}; showing {min(len(items), 5)} of {len(items)} item(s).",
        *_queue_item_lines(items[:5]),
    ]
    safe_next_actions = {
        ReviewLoopAction.NEXT_ACTIONS: (
            "glassbox queue list --view action-needed --cwd .",
            "glassbox session status SESSION_ID --cwd .",
        ),
        ReviewLoopAction.MAINTENANCE_CHECKS: (
            "glassbox queue list --view maintenance --cwd .",
            "glassbox observability status --cwd .",
        ),
    }.get(
        action,
        (
            "glassbox queue list --view action-needed --cwd .",
            "glassbox queue list --view maintenance --cwd .",
        ),
    )
    return ReviewLoopActionResult(
        action=action,
        headline=headline,
        details=tuple(details),
        limitations=(
            "Queue entries are derived from local state and remain advisory.",
        ),
        safe_next_actions=safe_next_actions,
    )


def evidence_graph_summary_result(
    *,
    summary: Mapping[str, Any],
    target_label: str,
    changeset_id: str | None = None,
    session_id: str | None = None,
) -> ReviewLoopActionResult:
    """Shape evidence graph counts into a concise terminal detail view."""

    target_kind = str(summary.get("target_kind", "unknown"))
    target_id = summary.get("target_id")
    details = (
        f"Target: {target_kind} {target_id or target_label}",
        (
            "Counts: "
            f"{summary.get('node_count', 0)} nodes, "
            f"{summary.get('edge_count', 0)} edges, "
            f"{summary.get('claim_count', 0)} claims."
        ),
        (
            "Claim posture: "
            f"{summary.get('stale_claim_count', 0)} stale, "
            f"{summary.get('missing_claim_count', 0)} missing, "
            f"{summary.get('contradicted_claim_count', 0)} contradicted."
        ),
        (
            "Manual/risk posture: "
            f"{summary.get('manual_only_claim_count', 0)} manual-only, "
            f"{summary.get('accepted_risk_claim_count', 0)} accepted risk, "
            f"{summary.get('limitation_count', 0)} limitation(s)."
        ),
    )
    if changeset_id is not None:
        safe_next_actions = (
            f"glassbox changeset evidence-graph {changeset_id} --summary --cwd .",
            f"glassbox changeset verification-plan {changeset_id} --cwd .",
        )
        dashboard_path = f"/app/changesets/{changeset_id}"
    else:
        resolved_session_id = session_id or "SESSION_ID"
        safe_next_actions = (
            f"glassbox session evidence-graph {resolved_session_id} --summary --cwd .",
            "glassbox queue list --view action-needed --cwd .",
        )
        dashboard_path = None
    return ReviewLoopActionResult(
        action=ReviewLoopAction.EVIDENCE_GRAPH,
        headline=f"Evidence graph summary for {target_label}",
        changeset_id=changeset_id,
        details=details,
        limitations=(
            "The terminal summary is bounded; inspect the dashboard or CLI graph "
            "for node and edge details.",
        ),
        safe_next_actions=safe_next_actions,
        dashboard_path=dashboard_path,
    )


def review_feedback_message(result: ReviewLoopActionResult) -> str:
    parts = [result.headline]
    if result.limitations:
        parts.append(f"Limitation: {result.limitations[0]}")
    if result.safe_next_actions:
        parts.append(f"Next: {result.safe_next_actions[0]}")
    return " ".join(parts)


def string_tuple(items: object) -> tuple[str, ...]:
    if not isinstance(items, list):
        return ()
    return tuple(str(item) for item in items)


def _queue_counts_line(counts: Mapping[str, Any]) -> str:
    return (
        "Counts: "
        f"{counts.get('total', 0)} total, "
        f"{counts.get('work_blocking', 0)} work, "
        f"{counts.get('review_blocking', 0)} review, "
        f"{counts.get('verification_blocking', 0)} verification, "
        f"{counts.get('maintenance', 0)} maintenance."
    )


def _queue_item_lines(items: list[dict[str, Any]]) -> tuple[str, ...]:
    if not items:
        return ("No queue items currently match this view.",)
    lines: list[str] = []
    for index, item in enumerate(items, start=1):
        action = cast(dict[str, Any], item.get("safe_next_action") or {})
        evidence = cast(dict[str, Any], item.get("evidence_summary") or {})
        target = cast(dict[str, Any], item.get("target") or {})
        target_label = target.get("label") or target.get("target_id") or "workspace"
        title = str(action.get("title") or item.get("owner_label") or "Inspect item")
        lines.append(
            f"{index}. {item.get('priority')}/{item.get('severity')} "
            f"{item.get('family')}: {title}"
        )
        lines.append(f"   Target: {target_label}")
        lines.append(f"   Evidence: {evidence.get('summary', 'local state')}")
        command = cast(dict[str, Any], action.get("command") or {})
        if command.get("display"):
            lines.append(f"   Command: {command['display']}")
    return tuple(lines)


def _queue_view_matches(item: Mapping[str, Any], view: str) -> bool:
    if view == "all":
        return True
    if view == "action-needed":
        return bool(item.get("action_needed"))
    if view == "maintenance":
        return item.get("family") == "maintenance"
    if view == "verification":
        return item.get("family") == "verification_blocking"
    if view == "review":
        return item.get("family") == "review_blocking"
    return True


def missing_fixup_feedback_ids(summary: Any) -> tuple[str, ...]:
    ids: list[str] = []
    for item in getattr(summary, "items", ()):
        response_state = getattr(item, "response_state", "")
        if str(response_state) in {"accepted_with_risk", "not_applicable"}:
            continue
        if getattr(item, "fixup_inventory_count", 0) == 0:
            ids.append(str(item.feedback_id))
    return tuple(ids)


def payload_missing_fixup_feedback_ids(summary: Any) -> tuple[str, ...]:
    if not isinstance(summary, dict):
        return ()
    ids: list[str] = []
    for item in summary.get("items", []):
        if not isinstance(item, dict):
            continue
        if item.get("response_state") in {"accepted_with_risk", "not_applicable"}:
            continue
        if int(item.get("fixup_inventory_count", 0)) == 0:
            ids.append(str(item.get("feedback_id")))
    return tuple(ids)


def local_skipped_evidence_counts(manual_evidence: Any) -> tuple[int, int, int]:
    from glassbox.runtime.skipped_evidence import skipped_live_evidence_counts

    return skipped_live_evidence_counts(manual_evidence)


def payload_skipped_evidence_counts(items: Any) -> tuple[int, int, int]:
    if not isinstance(items, list):
        return (0, 0, 0)
    evidence_items = [
        cast(dict[str, Any], item) for item in items if isinstance(item, dict)
    ]
    skipped = [
        item
        for item in evidence_items
        if item.get("evidence_kind")
        in {"browser_observation", "screenshot", "accessibility_note"}
        and _payload_is_skipped_evidence(item)
    ]
    skipped_browser = [
        item
        for item in skipped
        if item.get("evidence_kind") in {"browser_observation", "screenshot"}
    ]
    skipped_accessibility = [
        item for item in skipped if item.get("evidence_kind") == "accessibility_note"
    ]
    return (len(skipped), len(skipped_browser), len(skipped_accessibility))


def _payload_is_skipped_evidence(item: dict[str, Any]) -> bool:
    text = [
        *[str(value) for value in item.get("limitations", []) if value is not None],
        *[str(value) for value in item.get("non_claims", []) if value is not None],
    ]
    normalized = {value.strip().lower() for value in text}
    return bool(
        {
            "capture state: not_run",
            "capture state: not_applicable",
        }
        & normalized
    )
