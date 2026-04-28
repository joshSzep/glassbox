"""CLI command handlers for provider diagnostics."""

import argparse
from pathlib import Path

from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.runtime.provider_canary import ProviderCanarySummary
from glassbox.runtime.provider_canary import run_provider_canary_sync
from glassbox.runtime.provider_diagnostics import ProviderDiagnosticsReport
from glassbox.runtime.provider_diagnostics import build_provider_diagnostics_report
from glassbox.runtime.workspace_profile import DEFAULT_MODEL_NAME


def _provider_command(args: argparse.Namespace) -> int:
    provider_command = getattr(args, "provider_command", None)
    if provider_command == "diagnostics":
        return _provider_diagnostics_command(args)
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


def _print_provider_diagnostics(report: ProviderDiagnosticsReport) -> None:
    print(f"Provider diagnostics: {report.state}")
    print(
        f"Selected model: {report.selected_model_name} ({report.selected_model_source})"
    )
    print(f"Selected provider: {report.selected_provider}")
    print(f"Runtime mode: {report.runtime_mode}")
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


def _provider_canary_command(args: argparse.Namespace) -> int:
    provider_canary_command = getattr(args, "provider_canary_command", None)
    if provider_canary_command != "run":
        raise ValueError("specify a provider canary subcommand")

    cwd, _db_path = resolve_runtime_location(args)
    model_name = args.model_name or DEFAULT_MODEL_NAME
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else cwd / ".glassbox" / "evals" / "provider-canary"
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
