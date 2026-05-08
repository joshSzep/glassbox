"""Terminal guidance copy shared by interactive review clients."""

from typing import Any


def review_evidence_guidance(
    *,
    changeset_id: str,
    missing_fixup_feedback_ids: tuple[str, ...],
    stale_response_count: int,
    review_brief_count: int | None,
    skipped_live_evidence_count: int | None,
    skipped_browser_evidence_count: int | None,
    skipped_accessibility_evidence_count: int | None,
) -> tuple[str, ...]:
    guidance: list[str] = []
    if missing_fixup_feedback_ids:
        first = missing_fixup_feedback_ids[0]
        guidance.append(
            "Missing fixup inventory: run "
            f"glassbox changeset feedback fixup {first} --cwd ."
        )
    if stale_response_count > 0:
        guidance.append(
            "Stale verification: run "
            f"glassbox changeset verification-plan {changeset_id} --cwd ."
        )
    if review_brief_count == 0:
        guidance.append(
            "Missing lifecycle brief: run "
            f"glassbox changeset brief {changeset_id} --cwd ."
        )
    if skipped_live_evidence_count is not None:
        if skipped_live_evidence_count > 0:
            guidance.append(
                "Skipped live evidence: "
                f"{skipped_live_evidence_count} skipped "
                f"({skipped_browser_evidence_count or 0} browser/dashboard, "
                f"{skipped_accessibility_evidence_count or 0} accessibility); "
                "this is not a pass."
            )
        else:
            guidance.append(
                "Live evidence: none recorded; record observed or skipped "
                f"advisory evidence for {changeset_id} when relevant."
            )
    return tuple(f"Evidence guidance: {item}" for item in guidance)


def handoff_evidence_guidance(readiness: Any) -> tuple[str, ...]:
    guidance = []
    blockers = tuple(getattr(readiness, "blockers", ()))
    if blockers:
        guidance.append(f"Handoff blocker: {blockers[0]}")
    evidence = getattr(readiness, "evidence", None)
    if evidence is not None and getattr(evidence, "skipped_live_evidence_count", 0):
        guidance.append(
            "Skipped live evidence remains advisory and not a pass; inspect "
            "glassbox changeset evidence list --changeset "
            f"{readiness.changeset_id} --cwd ."
        )
    if getattr(readiness, "review_brief_artifact_id", None) is None:
        guidance.append(
            "Missing lifecycle brief: run "
            f"glassbox changeset brief {readiness.changeset_id} --cwd ."
        )
    return tuple(f"Evidence guidance: {item}" for item in guidance)


def payload_handoff_evidence_guidance(payload: dict[str, Any]) -> tuple[str, ...]:
    guidance = []
    blockers = payload.get("blockers", [])
    if isinstance(blockers, list) and blockers:
        guidance.append(f"Handoff blocker: {blockers[0]}")
    evidence = payload.get("evidence", {})
    if (
        isinstance(evidence, dict)
        and int(evidence.get("skipped_live_evidence_count", 0)) > 0
    ):
        guidance.append(
            "Skipped live evidence remains advisory and not a pass; inspect "
            "glassbox changeset evidence list --changeset "
            f"{payload.get('changeset_id')} --cwd ."
        )
    if payload.get("review_brief_artifact_id") is None:
        guidance.append(
            "Missing lifecycle brief: run "
            f"glassbox changeset brief {payload.get('changeset_id')} --cwd ."
        )
    return tuple(f"Evidence guidance: {item}" for item in guidance)
