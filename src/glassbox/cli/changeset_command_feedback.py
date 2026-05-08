"""Review feedback changeset CLI command handlers."""

import argparse
import asyncio
from typing import cast

from glassbox.cli.changeset_command_formatters import _print_feedback_detail
from glassbox.cli.changeset_command_formatters import _print_feedback_list
from glassbox.cli.changeset_command_formatters import _print_feedback_result
from glassbox.cli.changeset_command_formatters import _print_fixup_inventory_result
from glassbox.cli.changeset_command_formatters import _print_review_response_summary
from glassbox.cli.changeset_command_payloads import _feedback_payload
from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.core import ReviewFeedbackDisposition
from glassbox.core import ReviewFeedbackKind
from glassbox.core import ReviewFeedbackProvenance
from glassbox.core import ReviewFeedbackScopeKind
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.changesets import ChangesetQueryService
from glassbox.runtime.changesets import ChangesetRepository
from glassbox.runtime.changesets import ReviewFeedbackActionService
from glassbox.runtime.changesets import ReviewFeedbackFixupInventoryService


def _changeset_feedback_command(args: argparse.Namespace) -> int:
    command = getattr(args, "feedback_command", None)
    if command == "add":
        return _feedback_add_command(args)
    if command == "list":
        return _feedback_list_command(args)
    if command == "show":
        return _feedback_show_command(args)
    if command == "status":
        return _feedback_status_command(args)
    if command == "resolve":
        return _feedback_resolve_command(args)
    if command == "fixup":
        return _feedback_fixup_command(args)
    if command == "reopen":
        return _feedback_reopen_command(args)
    if command == "archive":
        return _feedback_archive_command(args)
    if command == "accept-risk":
        return _feedback_accept_risk_command(args)
    raise ValueError("specify a feedback subcommand")


def _feedback_add_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        result = ReviewFeedbackActionService(
            cast(ChangesetRepository, runtime_context.repositories.sessions)
        ).add_feedback(
            args.changeset_id,
            feedback_kind=ReviewFeedbackKind(args.kind),
            provenance=ReviewFeedbackProvenance(args.provenance),
            summary=args.summary,
            body=args.body,
            source_label=args.source_label,
            reviewer_label=args.reviewer_label,
            created_by=args.actor,
            scope_kind=ReviewFeedbackScopeKind(args.scope_kind),
            scope_reason=args.scope_reason,
            file_path=args.file,
            line_start=args.line_start,
            line_end=args.line_end,
        )
    return _print_feedback_result(result, args.json, "Recorded review feedback")


def _feedback_list_command(args: argparse.Namespace) -> int:
    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit must be greater than zero")
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        feedback = ChangesetQueryService(
            cast(ChangesetRepository, runtime_context.repositories.sessions)
        ).list_review_feedback(
            session_id=args.session_id,
            changeset_id=args.changeset_id,
            disposition=(
                ReviewFeedbackDisposition(args.disposition)
                if args.disposition is not None
                else None
            ),
            include_archived=args.include_archived,
            file_path=args.file,
            limit=args.limit,
        )
    if args.json:
        print_json_output([item.model_dump(mode="json") for item in feedback])
    else:
        _print_feedback_list(feedback)
    return 0


def _feedback_show_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        repository = cast(ChangesetRepository, runtime_context.repositories.sessions)
        service = ChangesetQueryService(repository)
        feedback = service.get_review_feedback(args.feedback_id)
        if feedback is None:
            raise ValueError(f"unknown review feedback: {args.feedback_id}")
        scopes = service.list_review_feedback_scopes(
            feedback.session_id,
            feedback.feedback_id,
        )
        response_status = service.get_review_feedback_response_status(
            feedback.feedback_id,
            workspace_root=cwd,
        )
    payload = _feedback_payload(
        feedback,
        scopes=scopes,
        response_status=response_status,
    )
    if args.json:
        print_json_output(payload)
    else:
        _print_feedback_detail(feedback, scopes, response_status=response_status)
    return 0


def _feedback_status_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        summary = ChangesetQueryService(
            cast(ChangesetRepository, runtime_context.repositories.sessions)
        ).get_review_response_summary(args.changeset_id, workspace_root=cwd)
    if args.json:
        print_json_output(summary.model_dump(mode="json"))
    else:
        _print_review_response_summary(summary)
    return 0


def _feedback_resolve_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        result = ReviewFeedbackActionService(
            cast(ChangesetRepository, runtime_context.repositories.sessions)
        ).resolve_feedback(
            args.feedback_id,
            resolution_summary=args.summary,
            residual_risk=args.residual_risk,
            resolved_by=args.actor,
        )
    return _print_feedback_result(result, args.json, "Resolved review feedback locally")


def _feedback_fixup_command(args: argparse.Namespace) -> int:
    if args.from_workspace and args.paths:
        raise ValueError("feedback fixup accepts either --from-workspace or --path")
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        repository = cast(ChangesetRepository, runtime_context.repositories.sessions)
        service = ReviewFeedbackFixupInventoryService(
            repository,
            runtime_context.repositories.artifacts,
        )
        if args.paths:
            result = service.record_explicit_paths(
                args.feedback_id,
                cwd,
                paths=args.paths,
                source_summary=args.source_summary,
                recorded_by=args.actor,
            )
        else:
            result = asyncio.run(
                service.record_workspace_inventory(
                    args.feedback_id,
                    cwd,
                    source_summary=args.source_summary,
                    recorded_by=args.actor,
                )
            )
        response_status = ChangesetQueryService(
            repository
        ).get_review_feedback_response_status(
            result.feedback_id,
            workspace_root=cwd,
        )
    return _print_fixup_inventory_result(
        result,
        response_status=response_status,
        as_json=args.json,
    )


def _feedback_reopen_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        result = ReviewFeedbackActionService(
            cast(ChangesetRepository, runtime_context.repositories.sessions)
        ).reopen_feedback(
            args.feedback_id,
            reason=args.reason,
            reopened_by=args.actor,
        )
    return _print_feedback_result(result, args.json, "Reopened review feedback")


def _feedback_archive_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        result = ReviewFeedbackActionService(
            cast(ChangesetRepository, runtime_context.repositories.sessions)
        ).archive_feedback(
            args.feedback_id,
            reason=args.reason,
            archived_by=args.actor,
            replacement_feedback_id=args.replacement_feedback_id,
        )
    return _print_feedback_result(result, args.json, "Archived review feedback")


def _feedback_accept_risk_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        result = ReviewFeedbackActionService(
            cast(ChangesetRepository, runtime_context.repositories.sessions)
        ).accept_risk(
            args.feedback_id,
            risk_summary=args.risk_summary,
            acceptance_reason=args.reason,
            accepted_by=args.actor,
        )
    return _print_feedback_result(result, args.json, "Accepted review feedback risk")
