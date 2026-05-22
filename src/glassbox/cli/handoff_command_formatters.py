"""CLI formatting helpers for local handoff workflows."""

from typing import Any

from glassbox.cli.json_output import print_json_output
from glassbox.core import HandoffProjectionRecord
from glassbox.runtime.handoff_decisions import HandoffDecisionResult
from glassbox.runtime.handoff_decisions import custody_action_state
from glassbox.runtime.handoff_guidance import HandoffGuidance


def print_decision_result(
    result: HandoffDecisionResult,
    *,
    json_output: bool,
) -> int:
    if json_output:
        print_json_output(decision_payload(result))
    else:
        print(f"Recorded {result.event_type} for {result.record.package_id}")
        print_handoff_record(result.record)
    return 0


def print_changeset_export_inspection(summary: dict[str, Any]) -> None:
    print(f"Handoff package: {summary['bundle_path']}")
    print(
        f"Package: {summary['export_kind']} v{summary['schema_version']} "
        f"for changeset {summary['changeset_id']}"
    )
    print(f"Status: {summary['status']}")
    if summary.get("profile_id"):
        print(f"Profile: {summary['profile_id']}")
    print(f"Verification: {summary['verification_state']}")
    print(f"Handoff: {summary['handoff_state']}")
    print(f"Local-only evidence: {summary['local_only_evidence_count']}")
    print(
        "Evidence graph: "
        f"{summary['evidence_graph_node_count']} node(s), "
        f"{summary['evidence_graph_claim_count']} claim(s)"
    )
    print(f"Feedback: {summary['feedback_count']}")
    print(f"Manual evidence: {summary['manual_evidence_count']}")
    print(f"Redaction rows: {summary['redaction_report_count']}")
    print("Safe inspection commands:")
    for command in summary["safe_inspection_commands"][:5]:
        print(f"  - {command}")
    print("Non-claims:")
    for claim in summary["non_claims"][:5]:
        print(f"  - {claim}")


def print_handoff_records(records: list[HandoffProjectionRecord]) -> None:
    if not records:
        print("No handoff records found")
        return
    print(f"Handoff records: {len(records)}")
    for record in records:
        print_handoff_record(record)


def print_handoff_record(record: HandoffProjectionRecord) -> None:
    print(
        f"{record.package_id}  {record.custody_state.value}  "
        f"updated {record.updated_at.isoformat()}"
    )
    print(f"  Session: {record.session_id}")
    print(f"  Source: {record.source_kind.value} {record.source_id or ''}".rstrip())
    print(f"  Action state: {custody_action_state(record)}")
    if record.decision_reason:
        print(f"  Reason: {record.decision_reason}")
    if record.follow_up_intent is not None:
        print(f"  Follow-up intent: {record.follow_up_intent.value}")
    if record.safe_next_actions:
        print("  Safe next actions:")
        for action in record.safe_next_actions:
            print(f"    - {action}")


def print_handoff_guidance(guidance: HandoffGuidance) -> None:
    print(f"Handoff guidance: {guidance.package_id}")
    print(f"State: {guidance.state}")
    print(f"Summary: {guidance.summary}")
    if guidance.blockers:
        print("Blockers:")
        for blocker in guidance.blockers:
            print(f"  - {blocker.kind}: {blocker.summary}")
    print("Paths:")
    for path in guidance.paths:
        marker = "recommended" if path.recommended else "available"
        print(f"  - {path.path_id} ({marker}): {path.summary}")
    print("Safe commands:")
    for command in guidance.safe_commands:
        print(f"  - {command.display}")
    print("Non-claims:")
    for non_claim in guidance.non_claims:
        print(f"  - {non_claim}")


def decision_payload(result: HandoffDecisionResult) -> dict[str, object]:
    return {
        "event_type": result.event_type,
        "record": record_payload(result.record),
        "non_claims": result.non_claims,
    }


def record_payload(record: HandoffProjectionRecord) -> dict[str, object]:
    payload = record.model_dump(mode="json")
    payload["action_state"] = custody_action_state(record)
    return payload


__all__ = [
    "decision_payload",
    "print_changeset_export_inspection",
    "print_decision_result",
    "print_handoff_guidance",
    "print_handoff_record",
    "print_handoff_records",
    "record_payload",
]
