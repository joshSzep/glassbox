"""CLI command handlers for provider diagnostics."""

import argparse
from pathlib import Path

from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.core.types import AutonomyMode
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.provider_canary import ProviderCanaryEvidenceSummary
from glassbox.runtime.provider_canary import ProviderCanarySummary
from glassbox.runtime.provider_canary import load_provider_canary_evidence
from glassbox.runtime.provider_canary import run_provider_canary_sync
from glassbox.runtime.provider_diagnostics import ProviderDiagnosticsReport
from glassbox.runtime.provider_diagnostics import build_provider_diagnostics_report
from glassbox.runtime.provider_recommendations import ProviderRecommendation
from glassbox.runtime.provider_recommendations import ProviderTaskKind
from glassbox.runtime.provider_recommendations import recommend_provider
from glassbox.runtime.workspace_profile import DEFAULT_MODEL_NAME


def _provider_command(args: argparse.Namespace) -> int:
    provider_command = getattr(args, "provider_command", None)
    if provider_command == "diagnostics":
        return _provider_diagnostics_command(args)
    if provider_command == "recommend":
        return _provider_recommend_command(args)
    if provider_command == "canary":
        return _provider_canary_command(args)
    raise ValueError("specify a provider subcommand")


def _provider_diagnostics_command(args: argparse.Namespace) -> int:
    cwd, _db_path = resolve_runtime_location(args)
    report = build_provider_diagnostics_report(
        cwd,
        explicit_model_name=args.model_name,
    )
    if args.json:
        print_json_output(report.model_dump(mode="json"))
    else:
        _print_provider_diagnostics(report)
    return 0


def _provider_recommend_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    provider_recovery_history = []
    if args.session_id is not None:
        with open_runtime_context(cwd, db_path=db_path) as runtime_context:
            provider_recovery_history = (
                runtime_context.repositories.sessions.list_provider_recovery(
                    args.session_id,
                    limit=5,
                )
            )
    recommendation = recommend_provider(
        cwd,
        task_kind=ProviderTaskKind(args.task_kind),
        autonomy_mode=AutonomyMode(args.autonomy_mode),
        model_name=args.model_name,
        provider_recovery_history=provider_recovery_history,
    )
    if args.json:
        print_json_output(recommendation.model_dump(mode="json"))
    else:
        _print_provider_recommendation(recommendation)
    return 0


def _print_provider_diagnostics(report: ProviderDiagnosticsReport) -> None:
    print(f"Provider diagnostics: {report.state}")
    print(
        f"Selected model: {report.selected_model_name} ({report.selected_model_source})"
    )
    print(f"Selected provider: {report.selected_provider}")
    print(f"Runtime mode: {report.runtime_mode}")
    print("Capability preflight:")
    print(
        f"  provider={report.capability_preflight.provider_family}; "
        f"credential_source={report.capability_preflight.credential_source}; "
        f"base_url={report.capability_preflight.base_url_posture}"
    )
    print(
        f"  streaming={report.capability_preflight.streaming_assumption}; "
        f"tool_calls={report.capability_preflight.tool_call_assumption}"
    )
    for scenario in report.capability_preflight.scenario_preflight:
        print(f"  - {scenario.scenario_id}: {scenario.status} ({scenario.reason})")
    for diagnostic in report.diagnostics:
        print(
            f"{diagnostic.provider}: "
            f"api key {'present' if diagnostic.api_key_present else 'missing'} "
            f"({diagnostic.api_key_source}), "
            f"base URL {'present' if diagnostic.base_url_present else 'missing'} "
            f"({diagnostic.base_url_source})"
        )
    if report.problems:
        print("Problems:")
        for problem in report.problems:
            print(f"  - {problem}")
    if report.next_actions:
        print("Next:")
        for action in report.next_actions:
            print(f"  - {action}")
    print("First-run checklist:")
    for step in report.onboarding_steps:
        print(f"  - {step}")


def _print_provider_recommendation(recommendation: ProviderRecommendation) -> None:
    print("Provider recommendation: advisory")
    print(f"Task kind: {recommendation.task_kind.value}")
    print(f"Autonomy mode: {recommendation.autonomy_mode.value}")
    print(f"Model: {recommendation.recommended_model_name}")
    print(f"Provider: {recommendation.provider}")
    print(f"Posture: {recommendation.posture.value}")
    print(f"Confidence: {recommendation.confidence.value}")
    print(f"Capability fit: {recommendation.capability_fit.value}")
    print(f"Risk posture: {recommendation.risk_posture.value}")
    print(f"Evidence freshness: {recommendation.evidence_freshness}")
    print(f"Credential readiness: {recommendation.credential_readiness.value}")
    print(f"Recommended action: {recommendation.recommended_action.value}")
    print(f"Failure posture: {recommendation.failure_posture.state}")
    if recommendation.failure_posture.latest_reason is not None:
        print(
            f"Latest provider failure: {recommendation.failure_posture.latest_reason}"
        )
    if recommendation.budget_impact.budget_warning is not None:
        print(f"Budget impact: {recommendation.budget_impact.budget_warning}")
    print("Required capabilities:")
    for capability in recommendation.required_capabilities:
        print(f"  - {capability}")
    print("Reasons:")
    for reason in recommendation.reasons:
        print(f"  - {reason}")
    if recommendation.warnings:
        print("Warnings:")
        for warning in recommendation.warnings:
            print(f"  - {warning}")
    if recommendation.unknowns:
        print("Unknowns:")
        for unknown in recommendation.unknowns:
            print(f"  - {unknown}")
    if recommendation.next_actions:
        print("Next:")
        for action in recommendation.next_actions:
            print(f"  - {action}")


def _provider_canary_command(args: argparse.Namespace) -> int:
    provider_canary_command = getattr(args, "provider_canary_command", None)
    if provider_canary_command == "evidence":
        return _provider_canary_evidence_command(args)
    if provider_canary_command != "run":
        raise ValueError("specify a provider canary subcommand")

    cwd, _db_path = resolve_runtime_location(args)
    model_name = args.model_name or DEFAULT_MODEL_NAME
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else cwd / ".glassbox" / "provider-canary"
    )
    if not output_dir.is_absolute():
        output_dir = cwd / output_dir
    summary = run_provider_canary_sync(
        cwd,
        model_name=model_name,
        output_dir=output_dir,
        scenarios=args.scenario,
    )
    if args.json:
        print_json_output(summary.model_dump(mode="json"))
    else:
        _print_provider_canary_summary(summary)
    return 0


def _provider_canary_evidence_command(args: argparse.Namespace) -> int:
    cwd, _db_path = resolve_runtime_location(args)
    evidence = load_provider_canary_evidence(
        cwd,
        summary_path=Path(args.path) if args.path else None,
    )
    if args.json:
        print_json_output(evidence.model_dump(mode="json"))
    else:
        _print_provider_canary_evidence(evidence)
    return 0


def _print_provider_canary_summary(summary: ProviderCanarySummary) -> None:
    print("Provider canary: advisory")
    print(f"Provider: {summary.provider}")
    print(f"Model: {summary.model_name}")
    print(f"Summary: {summary.output_path}")
    for scenario in summary.scenarios:
        print(f"{scenario.scenario_id}: {scenario.outcome} ({scenario.detail})")
    print("Capability matrix:")
    for entry in summary.capability_matrix.entries:
        print(
            f"  - {entry.scenario_id}: {entry.result}; "
            f"credentials={entry.credential_state}; "
            f"redaction={entry.redaction_status}"
        )
    if summary.next_actions:
        print("Next:")
        for action in summary.next_actions:
            print(f"  - {action}")


def _print_provider_canary_evidence(evidence: ProviderCanaryEvidenceSummary) -> None:
    print(f"Provider canary evidence: {evidence.latest_status}")
    print(f"Freshness: {evidence.freshness_status}")
    print(f"Retained summaries: {evidence.summary_count}")
    if evidence.latest_summary_path is not None:
        print(f"Latest summary: {evidence.latest_summary_path}")
    if evidence.provider is not None:
        print(f"Provider: {evidence.provider}")
    if evidence.model_name is not None:
        print(f"Model: {evidence.model_name}")
    if evidence.configured_model_name is not None:
        print(f"Configured model: {evidence.configured_model_name}")
    if evidence.identity_matches_current_config is not None:
        print(
            "Model identity matches config: "
            f"{'yes' if evidence.identity_matches_current_config else 'no'}"
        )
    print(
        "Scenarios: "
        f"{evidence.passed_count} passed, "
        f"{evidence.skipped_count} skipped, "
        f"{evidence.warning_count} warning, "
        f"{evidence.failed_count} failed"
    )
    print(f"Capability matrix rows: {evidence.matrix_entry_count}")
    if evidence.missing_scenarios:
        print("Missing scenarios:")
        for scenario_id in evidence.missing_scenarios:
            print(f"  - {scenario_id}")
    print(f"Stale: {'yes' if evidence.stale else 'no'}")
    if evidence.next_actions:
        print("Next:")
        for action in evidence.next_actions:
            print(f"  - {action}")
