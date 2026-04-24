"""Shared path and runtime-location helpers for CLI command handlers."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path


def resolve_runtime_location(args) -> tuple[Path, Path | None]:
    """Resolve the selected workspace and optional database path."""

    cwd = Path(args.cwd).resolve()
    db_path = Path(args.db_path).resolve() if args.db_path is not None else None
    return cwd, db_path


def resolve_optional_output_path(
    cwd: Path,
    output: str | None,
    *,
    default_name: str,
) -> Path:
    """Resolve an optional output path relative to the selected workspace."""

    if output is None:
        return (cwd / default_name).resolve()

    output_path = Path(output).expanduser()
    if not output_path.is_absolute():
        output_path = cwd / output_path
    return output_path.resolve()


def resolve_optional_explicit_path(cwd: Path, output: str | None) -> Path | None:
    """Resolve an optional explicit output path or return None."""

    if output is None:
        return None

    output_path = Path(output).expanduser()
    if not output_path.is_absolute():
        output_path = cwd / output_path
    return output_path.resolve()


def resolve_eval_report_output_dir(cwd: Path, output_dir: str | None) -> Path:
    """Resolve the report output directory for eval sign-off output."""

    if output_dir is not None:
        return resolve_optional_output_path(
            cwd,
            output_dir,
            default_name="unused",
        )
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return (cwd / ".glassbox" / "evals" / f"release-signoff-{timestamp}").resolve()
