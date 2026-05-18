"""CLI handlers for local handoff custody decisions."""

import argparse
import json
from pathlib import Path
from typing import Any
from typing import cast

from pydantic import ValidationError

from glassbox.cli.changeset_command_lifecycle import _changeset_export_command
from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_optional_explicit_path
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.cli.session_state_commands import _print_handoff_import_triage
from glassbox.cli.session_state_commands import _session_command
from glassbox.core import HandoffIntent
from glassbox.core import HandoffProjectionRecord
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.changeset_export import CHANGESET_EXPORT_KIND
from glassbox.runtime.changeset_export import ChangesetExportPayload
from glassbox.runtime.changeset_export import build_changeset_export_markdown
from glassbox.runtime.changeset_export import inspect_changeset_export_package
from glassbox.runtime.handoff_decisions import HandoffDecisionRepository
from glassbox.runtime.handoff_decisions import HandoffDecisionResult
from glassbox.runtime.handoff_decisions import accept_handoff_custody
from glassbox.runtime.handoff_decisions import archive_handoff
from glassbox.runtime.handoff_decisions import custody_action_state
from glassbox.runtime.handoff_decisions import reject_handoff_custody
from glassbox.runtime.handoff_decisions import safe_next_actions_for_decision
from glassbox.runtime.handoff_guidance import HandoffGuidance
from glassbox.runtime.handoff_guidance import load_handoff_guidance
from glassbox.runtime.handoff_import_triage import triage_handoff_import
from glassbox.runtime.handoff_markdown import build_session_export_markdown
from glassbox.runtime.session_export import SESSION_EXPORT_KIND
from glassbox.runtime.session_export_models import SessionExportPayload


def _handoff_command(args: argparse.Namespace) -> int:
    if args.handoff_command == "prepare":
        return _handoff_prepare_command(args)
    if args.handoff_command == "inspect":
        return _handoff_inspect_command(args)
    if args.handoff_command == "import":
        return _handoff_import_command(args)
    if args.handoff_command == "list":
        return _handoff_list_command(args)
    if args.handoff_command == "show":
        return _handoff_show_command(args)
    if args.handoff_command == "guidance":
        return _handoff_guidance_command(args)
    if args.handoff_command == "accept":
        return _handoff_accept_command(args)
    if args.handoff_command == "reject":
        return _handoff_reject_command(args)
    if args.handoff_command == "archive":
        return _handoff_archive_command(args)
    raise ValueError("specify a handoff subcommand")


def _handoff_prepare_command(args: argparse.Namespace) -> int:
    source = getattr(args, "handoff_prepare_source", None)
    if source == "session":
        args.session_command = "export"
        return _session_command(args)
    if source == "changeset":
        if args.output_path is None:
            args.output_path = f"glassbox-changeset-{args.changeset_id}.json"
        return _changeset_export_command(args)
    raise ValueError("specify a handoff prepare source")


def _handoff_inspect_command(args: argparse.Namespace) -> int:
    cwd, _db_path = resolve_runtime_location(args)
    package_path = resolve_optional_explicit_path(cwd, args.package)
    assert package_path is not None
    package_kind = _package_export_kind(package_path)
    if args.markdown:
        return _print_handoff_package_markdown(package_path, package_kind)
    if package_kind == CHANGESET_EXPORT_KIND:
        summary = inspect_changeset_export_package(package_path)
        if args.json:
            print_json_output(summary)
        else:
            _print_changeset_export_inspection(summary)
        return 0

    triage = triage_handoff_import(package_path)
    if args.json:
        print_json_output(triage.model_dump(mode="json"))
    else:
        _print_handoff_import_triage(triage)
    return 0


def _handoff_import_command(args: argparse.Namespace) -> int:
    args.session_command = "import"
    args.triage = False
    return _session_command(args)


def _handoff_list_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        repository = cast(Any, runtime_context.repositories.sessions)
        records = repository.list_handoffs(
            session_id=args.session_id,
            include_archived=args.include_archived,
            limit=args.limit,
        )
    if args.json:
        print_json_output([_record_payload(record) for record in records])
    else:
        _print_handoff_records(records)
    return 0


def _handoff_show_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        repository = cast(Any, runtime_context.repositories.sessions)
        record = repository.get_handoff(
            args.session_id,
            args.package_id,
        )
    if record is None:
        raise ValueError(
            f"unknown handoff package for session {args.session_id}: {args.package_id}"
        )
    if args.json:
        print_json_output(_record_payload(record))
    else:
        _print_handoff_record(record)
    return 0


def _handoff_guidance_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        repository = cast(Any, runtime_context.repositories.sessions)
        guidance = load_handoff_guidance(
            repository,
            args.session_id,
            args.package_id,
        )
    if args.json:
        print_json_output(guidance.model_dump(mode="json"))
    else:
        _print_handoff_guidance(guidance)
    return 0


def _handoff_accept_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(
        args,
        require_daemon_unowned_for="record a handoff custody decision locally",
    )
    follow_up_intent = (
        HandoffIntent(args.follow_up_intent)
        if args.follow_up_intent is not None
        else None
    )
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        repository = cast(
            HandoffDecisionRepository,
            runtime_context.repositories.sessions,
        )
        record = _require_handoff_for_actions(
            repository,
            args.session_id,
            args.package_id,
        )
        result = accept_handoff_custody(
            repository,
            session_id=args.session_id,
            package_id=args.package_id,
            accepted_by=args.accepted_by,
            reason=args.reason,
            follow_up_intent=follow_up_intent,
            safe_next_actions=safe_next_actions_for_decision(record),
        )
    return _print_decision_result(result, json_output=args.json)


def _handoff_reject_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(
        args,
        require_daemon_unowned_for="record a handoff custody decision locally",
    )
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        repository = cast(
            HandoffDecisionRepository,
            runtime_context.repositories.sessions,
        )
        record = _require_handoff_for_actions(
            repository,
            args.session_id,
            args.package_id,
        )
        result = reject_handoff_custody(
            repository,
            session_id=args.session_id,
            package_id=args.package_id,
            rejected_by=args.rejected_by,
            reason=args.reason,
            safe_next_actions=safe_next_actions_for_decision(record),
        )
    return _print_decision_result(result, json_output=args.json)


def _handoff_archive_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(
        args,
        require_daemon_unowned_for="archive a handoff record locally",
    )
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        repository = cast(
            HandoffDecisionRepository,
            runtime_context.repositories.sessions,
        )
        result = archive_handoff(
            repository,
            session_id=args.session_id,
            package_id=args.package_id,
            archived_by=args.archived_by,
            reason=args.reason,
        )
    return _print_decision_result(result, json_output=args.json)


def _require_handoff_for_actions(repository, session_id, package_id):
    record = repository.get_handoff(session_id, package_id)
    if record is None:
        raise ValueError(
            f"unknown handoff package for session {session_id}: {package_id}"
        )
    return record


def _print_decision_result(
    result: HandoffDecisionResult,
    *,
    json_output: bool,
) -> int:
    if json_output:
        print_json_output(_decision_payload(result))
    else:
        print(f"Recorded {result.event_type} for {result.record.package_id}")
        _print_handoff_record(result.record)
    return 0


def _package_export_kind(package_path: Path) -> str | None:
    try:
        raw_payload = json.loads(package_path.read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError:
        return None
    if not isinstance(raw_payload, dict):
        return None
    export_kind = raw_payload.get("export_kind")
    return export_kind if isinstance(export_kind, str) else None


def _print_handoff_package_markdown(
    package_path: Path,
    package_kind: str | None,
) -> int:
    if package_kind == CHANGESET_EXPORT_KIND:
        payload = ChangesetExportPayload.model_validate_json(
            package_path.read_text(encoding="utf-8")
        )
        print(build_changeset_export_markdown(payload))
        return 0
    if package_kind == SESSION_EXPORT_KIND:
        payload = SessionExportPayload.model_validate_json(
            package_path.read_text(encoding="utf-8")
        )
        print(build_session_export_markdown(payload))
        return 0
    try:
        payload = SessionExportPayload.model_validate_json(
            package_path.read_text(encoding="utf-8")
        )
    except (OSError, ValidationError) as exc:
        raise ValueError(
            "--markdown is only supported for session and changeset handoff packages"
        ) from exc
    print(build_session_export_markdown(payload))
    return 0


def _print_changeset_export_inspection(summary: dict[str, Any]) -> None:
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


def _print_handoff_records(records: list[HandoffProjectionRecord]) -> None:
    if not records:
        print("No handoff records found")
        return
    print(f"Handoff records: {len(records)}")
    for record in records:
        _print_handoff_record(record)


def _print_handoff_record(record: HandoffProjectionRecord) -> None:
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


def _print_handoff_guidance(guidance: HandoffGuidance) -> None:
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


def _decision_payload(result: HandoffDecisionResult) -> dict[str, object]:
    return {
        "event_type": result.event_type,
        "record": _record_payload(result.record),
        "non_claims": result.non_claims,
    }


def _record_payload(record: HandoffProjectionRecord) -> dict[str, object]:
    payload = record.model_dump(mode="json")
    payload["action_state"] = custody_action_state(record)
    return payload


__all__ = ["_handoff_command"]
