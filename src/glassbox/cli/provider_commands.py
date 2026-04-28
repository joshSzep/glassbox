"""CLI command handlers for provider diagnostics."""

import argparse

from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.runtime.provider_diagnostics import ProviderDiagnosticsReport
from glassbox.runtime.provider_diagnostics import build_provider_diagnostics_report


def _provider_command(args: argparse.Namespace) -> int:
    provider_command = getattr(args, "provider_command", None)
    if provider_command == "diagnostics":
        return _provider_diagnostics_command(args)
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
