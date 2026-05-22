"""Package inspection command handlers for the handoff CLI."""

import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from glassbox.cli.handoff_command_formatters import print_changeset_export_inspection
from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_optional_explicit_path
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.cli.session_state_commands import _print_handoff_import_triage
from glassbox.runtime.changeset_export import CHANGESET_EXPORT_KIND
from glassbox.runtime.changeset_export import ChangesetExportPayload
from glassbox.runtime.changeset_export import build_changeset_export_markdown
from glassbox.runtime.changeset_export import inspect_changeset_export_package
from glassbox.runtime.handoff_import_triage import triage_handoff_import
from glassbox.runtime.handoff_markdown import build_session_export_markdown
from glassbox.runtime.session_export import SESSION_EXPORT_KIND
from glassbox.runtime.session_export_models import SessionExportPayload


def handoff_inspect_command(args: argparse.Namespace) -> int:
    cwd, _db_path = resolve_runtime_location(args)
    package_path = resolve_optional_explicit_path(cwd, args.package)
    assert package_path is not None
    package_kind = package_export_kind(package_path)
    if args.markdown:
        return print_handoff_package_markdown(package_path, package_kind)
    if package_kind == CHANGESET_EXPORT_KIND:
        summary = inspect_changeset_export_package(package_path)
        if args.json:
            print_json_output(summary)
        else:
            print_changeset_export_inspection(summary)
        return 0

    triage = triage_handoff_import(package_path)
    if args.json:
        print_json_output(triage.model_dump(mode="json"))
    else:
        _print_handoff_import_triage(triage)
    return 0


def package_export_kind(package_path: Path) -> str | None:
    try:
        raw_payload = json.loads(package_path.read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError:
        return None
    if not isinstance(raw_payload, dict):
        return None
    export_kind = raw_payload.get("export_kind")
    return export_kind if isinstance(export_kind, str) else None


def print_handoff_package_markdown(
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


__all__ = [
    "handoff_inspect_command",
    "package_export_kind",
    "print_handoff_package_markdown",
]
