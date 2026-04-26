"""CLI command handlers for replay workflows."""

import argparse
import asyncio
from pathlib import Path

from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_optional_output_path
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.cli.replay_eval_formatters import _print_replay_report
from glassbox.cli.replay_eval_formatters import _replay_exit_code
from glassbox.cli.replay_eval_formatters import _replay_result_payload
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.replay import ReplayRunner
from glassbox.runtime.replay_models import ReplayBundle


def _replay_command(args: argparse.Namespace) -> int:
    if args.replay_command == "run":
        return asyncio.run(_replay_run_command_async(args))
    if args.replay_command == "bundle":
        return _replay_bundle_command(args)
    raise ValueError("specify a replay subcommand")


async def _replay_run_command_async(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    session_id = args.session_id

    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        result = await ReplayRunner(
            runtime_context.repositories.sessions,
            runtime_context.repositories.artifacts,
        ).replay_session(session_id)

    if args.json:
        print_json_output(_replay_result_payload(result))
    else:
        _print_replay_report(result)

    return _replay_exit_code(result)


def _replay_bundle_command(args: argparse.Namespace) -> int:
    if args.replay_bundle_command == "export":
        return _replay_export_command(args)
    if args.replay_bundle_command == "inspect":
        return _replay_bundle_inspect_command(args)
    if args.replay_bundle_command == "run":
        return asyncio.run(_replay_bundle_run_command_async(args))
    raise ValueError("specify a replay bundle subcommand")


def _replay_bundle_inspect_command(args: argparse.Namespace) -> int:
    bundle_path = Path(args.bundle_path).resolve()
    bundle = ReplayRunner().load_bundle_file(bundle_path)
    payload = _replay_bundle_inspection_payload(bundle_path, bundle)

    if args.json:
        print_json_output(payload)
    else:
        _print_replay_bundle_inspection(payload)
    return 0


async def _replay_bundle_run_command_async(args: argparse.Namespace) -> int:
    cwd, _db_path = resolve_runtime_location(args)
    del _db_path

    result = await ReplayRunner().replay_bundle_file(
        Path(args.bundle_path),
        workspace_root=cwd,
    )

    if args.json:
        print_json_output(_replay_result_payload(result))
    else:
        _print_replay_report(result)

    return _replay_exit_code(result)


def _replay_bundle_inspection_payload(
    bundle_path: Path,
    bundle: ReplayBundle,
) -> dict[str, object]:
    return {
        "bundle_path": str(bundle_path),
        "bundle_kind": bundle.bundle_kind,
        "bundle_version": bundle.bundle_version,
        "source_session_id": str(bundle.source_session_id),
        "model_name": bundle.session_config.model_name,
        "approval_mode": bundle.session_config.approval_mode,
        "source_cwd": str(bundle.session_config.cwd),
        "branch_label": bundle.session_config.branch_label,
        "has_lineage": bundle.baseline.lineage is not None,
        "inherited_message_count": len(bundle.inherited_messages),
        "inherited_runtime_note_count": len(bundle.inherited_runtime_notes),
        "action_count": len(bundle.actions),
        "model_call_count": len(bundle.model_calls),
        "tool_request_count": len(bundle.tool_requests),
        "tool_result_count": len(bundle.tool_results),
        "turn_output_count": len(bundle.turn_outputs),
        "baseline_transcript_message_count": len(bundle.baseline.transcript),
        "baseline_tool_call_count": len(bundle.baseline.tool_calls),
        "baseline_approval_count": len(bundle.baseline.approvals),
        "baseline_question_count": len(bundle.baseline.questions),
        "baseline_event_family_count": len(bundle.baseline.event_families),
        "final_state_status": bundle.baseline.final_state.status,
    }


def _print_replay_bundle_inspection(payload: dict[str, object]) -> None:
    print(f"Replay bundle: {payload['bundle_path']}")
    print(f"Source session: {payload['source_session_id']}")
    print(f"Bundle: {payload['bundle_kind']} v{payload['bundle_version']}")
    print(f"Model: {payload['model_name']}")
    print(f"Approval mode: {payload['approval_mode']}")
    print(f"Source cwd: {payload['source_cwd']}")
    if payload["branch_label"] is not None:
        print(f"Branch: {payload['branch_label']}")
    print(f"Lineage: {'yes' if payload['has_lineage'] else 'no'}")
    print(
        "Contains "
        f"{payload['action_count']} action(s), "
        f"{payload['model_call_count']} model call(s), "
        f"{payload['tool_request_count']} tool request(s), "
        f"{payload['tool_result_count']} tool result(s), "
        f"{payload['turn_output_count']} turn output(s)"
    )
    print(
        "Baseline: "
        f"{payload['baseline_transcript_message_count']} transcript message(s), "
        f"{payload['baseline_tool_call_count']} tool call(s), "
        f"{payload['baseline_approval_count']} approval(s), "
        f"{payload['baseline_question_count']} question(s), "
        f"{payload['baseline_event_family_count']} event family/families, "
        f"final state {payload['final_state_status']}"
    )
    print(
        "Inherited: "
        f"{payload['inherited_message_count']} message(s), "
        f"{payload['inherited_runtime_note_count']} runtime note(s)"
    )


def _replay_export_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    output_path = resolve_optional_output_path(
        cwd,
        args.output,
        default_name=f"glassbox-replay-{args.session_id}.json",
    )

    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        exported_path = ReplayRunner(
            runtime_context.repositories.sessions,
            runtime_context.repositories.artifacts,
        ).export_session_bundle(args.session_id, output_path)

    print(f"Exported replay bundle for session {args.session_id}: {exported_path}")
    return 0
