"""CLI command handlers for workspace observability summaries."""

import argparse

from glassbox.cli.json_output import print_json_output
from glassbox.cli.next_action_output import next_action_record_payloads
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.cli.status_observability import print_observability_report
from glassbox.cli.status_observability_next_actions import (
    observability_next_action_records,
)
from glassbox.core import HandoffIntent
from glassbox.core import HandoffReadiness
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.daemon import inspect_runtime_owner
from glassbox.runtime.knowledge_posture import build_workspace_knowledge_posture
from glassbox.runtime.observability import build_workspace_observability_report
from glassbox.runtime.workspace_handoff_readiness import (
    derive_release_handoff_readiness,
)
from glassbox.runtime.workspace_handoff_readiness import (
    derive_workspace_handoff_readiness,
)


def _observability_command(args: argparse.Namespace) -> int:
    observability_command = getattr(args, "observability_command", None)
    if observability_command == "status":
        return _observability_status_command(args)
    if observability_command == "handoff-readiness":
        return _observability_handoff_readiness_command(args)
    raise ValueError("specify an observability subcommand")


def _observability_status_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    runtime_status = inspect_runtime_owner(cwd, db_path=db_path)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        report = build_workspace_observability_report(
            workspace_root=cwd,
            runtime_status=runtime_status,
            session_repository=runtime_context.repositories.sessions,
            event_transport_stats=runtime_context.infrastructure.event_transport.stats(),
        )
        knowledge_posture = build_workspace_knowledge_posture(
            cwd,
            runtime_context.repositories.sessions,
        )

    if args.json:
        payload = report.model_dump(mode="json")
        payload["knowledge_posture"] = knowledge_posture.model_dump(mode="json")
        payload["next_action_records"] = next_action_record_payloads(
            observability_next_action_records(report)
        )
        print_json_output(payload)
    else:
        print_observability_report(report, knowledge_posture)
    return 0


def _observability_handoff_readiness_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    runtime_status = inspect_runtime_owner(cwd, db_path=db_path)
    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        report = build_workspace_observability_report(
            workspace_root=cwd,
            runtime_status=runtime_status,
            session_repository=runtime_context.repositories.sessions,
            event_transport_stats=runtime_context.infrastructure.event_transport.stats(),
        )

    source = getattr(args, "source", "workspace")
    intent = _handoff_intent(args.intent, source=source)
    if source == "release":
        readiness = derive_release_handoff_readiness(report, intent=intent)
    else:
        readiness = derive_workspace_handoff_readiness(report, intent=intent)

    if args.json:
        print_json_output(readiness.model_dump(mode="json"))
    else:
        _print_handoff_readiness(readiness)
    return 0


def _handoff_intent(intent: str | None, *, source: str) -> HandoffIntent:
    if intent is not None:
        return HandoffIntent(intent)
    if source == "release":
        return HandoffIntent.RELEASE_SIGNOFF
    return HandoffIntent.FUTURE_SELF


def _print_handoff_readiness(readiness: HandoffReadiness) -> None:
    print(f"Handoff source: {readiness.source.kind}")
    print(f"Intent: {readiness.intent}")
    print(
        "Readiness: "
        f"{readiness.state} "
        f"(confidence {readiness.confidence}, freshness {readiness.freshness})"
    )
    if readiness.reasons:
        print("Reasons:")
        for reason in readiness.reasons:
            print(f"  - {reason.kind}: {reason.summary}")
    print(
        "Evidence: "
        f"{len(readiness.supporting_evidence)} supporting, "
        f"{len(readiness.missing_evidence)} missing, "
        f"{len(readiness.stale_evidence)} stale, "
        f"{len(readiness.local_only_evidence)} local-only"
    )
    if readiness.limitations:
        print("Limitations:")
        for limitation in readiness.limitations:
            print(f"  - {limitation}")
    if readiness.safe_first_commands:
        print("Safe first commands:")
        for command in readiness.safe_first_commands:
            print(f"  - {command.display}")
    if readiness.non_claims:
        print("Non-claims:")
        for non_claim in readiness.non_claims:
            print(f"  - {non_claim}")
