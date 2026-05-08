"""Manual and advisory evidence changeset CLI command handlers."""

import argparse
from datetime import datetime
from typing import cast

from glassbox.cli.changeset_command_formatters import _print_manual_evidence_list
from glassbox.cli.changeset_command_formatters import _print_manual_evidence_result
from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.core import ManualEvidenceFreshness
from glassbox.core import ManualEvidenceKind
from glassbox.core import ManualEvidenceState
from glassbox.core import ManualEvidenceTargetKind
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.changesets import AccessibilityEvidenceActionService
from glassbox.runtime.changesets import BrowserEvidenceActionService
from glassbox.runtime.changesets import ChangesetQueryService
from glassbox.runtime.changesets import ChangesetRepository
from glassbox.runtime.changesets import ManualEvidenceActionService


def _changeset_evidence_command(args: argparse.Namespace) -> int:
    command = getattr(args, "evidence_command", None)
    if command == "attach":
        return _evidence_attach_command(args)
    if command in {"browser", "dashboard"}:
        return _evidence_browser_dashboard_command(args)
    if command == "accessibility":
        return _evidence_accessibility_command(args)
    if command == "list":
        return _evidence_list_command(args)
    raise ValueError("specify an evidence subcommand")


def _evidence_attach_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        result = ManualEvidenceActionService(
            cast(ChangesetRepository, runtime_context.repositories.sessions),
            runtime_context.repositories.artifacts,
        ).attach(
            args.changeset_id,
            evidence_kind=ManualEvidenceKind(args.kind),
            summary=args.summary,
            source_label=args.source_label,
            actor=args.actor,
            target_kind=ManualEvidenceTargetKind(args.target_kind),
            target_id=args.target_id,
            feedback_id=args.feedback_id,
            note=args.note,
            command_text=args.command_text,
            external_url_label=args.external_url_label,
            local_file_label=args.local_file_label,
            local_file_path_hint=args.local_file,
            freshness=ManualEvidenceFreshness(args.freshness),
        )
    return _print_manual_evidence_result(result, args.json)


def _evidence_browser_dashboard_command(args: argparse.Namespace) -> int:
    width: int | None = None
    height: int | None = None
    if args.viewport is not None:
        width, height = args.viewport
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        result = BrowserEvidenceActionService(
            cast(ChangesetRepository, runtime_context.repositories.sessions),
            runtime_context.repositories.artifacts,
        ).attach(
            args.changeset_id,
            capture_state=args.capture_state,
            capture_kind=args.evidence_capture_kind,
            summary=args.summary,
            source_label=args.source_label,
            route_label=args.route_label,
            environment=args.environment,
            browser=args.browser,
            viewport_width=width,
            viewport_height=height,
            observed_at=_parse_optional_datetime(args.observed_at),
            input_method=args.input_method,
            console_checked=args.console_checked,
            skip_reason=args.skip_reason,
            screenshot_path_hint=args.screenshot_path_hint,
            screenshot_label=args.screenshot_label,
            screenshot_media_type=args.screenshot_media_type,
            screenshot_size_bytes=args.screenshot_size_bytes,
            screenshot_width=args.screenshot_width,
            screenshot_height=args.screenshot_height,
            skipped_cases=args.skipped_case,
            limitations=args.limitation,
            actor=args.actor,
            target_kind=ManualEvidenceTargetKind(args.target_kind),
            target_id=args.target_id,
            feedback_id=args.feedback_id,
            freshness=ManualEvidenceFreshness(args.freshness),
        )
    return _print_manual_evidence_result(result, args.json)


def _evidence_accessibility_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        result = AccessibilityEvidenceActionService(
            cast(ChangesetRepository, runtime_context.repositories.sessions),
            runtime_context.repositories.artifacts,
        ).attach(
            args.changeset_id,
            capture_state=args.capture_state,
            observation_kind=args.observation_kind,
            summary=args.summary,
            source_label=args.source_label,
            environment=args.environment,
            observed_issue=args.observed_issue,
            tool=args.tool,
            route_label=args.route_label,
            reviewer_label=args.reviewer_label,
            severity=args.severity,
            disposition=args.disposition,
            follow_up=args.follow_up,
            paired_tool_output_label=args.paired_tool_output_label,
            skip_reason=args.skip_reason,
            skipped_cases=args.skipped_case,
            limitations=args.limitation,
            actor=args.actor,
            target_kind=ManualEvidenceTargetKind(args.target_kind),
            target_id=args.target_id,
            feedback_id=args.feedback_id,
            freshness=ManualEvidenceFreshness(args.freshness),
        )
    return _print_manual_evidence_result(result, args.json)


def _evidence_list_command(args: argparse.Namespace) -> int:
    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit must be greater than zero")
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        evidence = ChangesetQueryService(
            cast(ChangesetRepository, runtime_context.repositories.sessions)
        ).list_manual_evidence(
            session_id=args.session_id,
            changeset_id=args.changeset_id,
            state=ManualEvidenceState(args.state) if args.state is not None else None,
            include_archived=args.include_archived,
            include_rejected=args.include_rejected,
            include_superseded=args.include_superseded,
            limit=args.limit,
        )
    if args.json:
        print_json_output([item.model_dump(mode="json") for item in evidence])
    else:
        _print_manual_evidence_list(evidence)
    return 0


def _parse_optional_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    normalized = value.removesuffix("Z")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("--observed-at must be an ISO-8601 datetime") from exc
