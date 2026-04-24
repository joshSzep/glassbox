"""Typed eval suite selection, filesystem loading, and output shaping helpers."""

import json
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path

from glassbox.runtime.eval_coverage import EvalCoverageAuditResult
from glassbox.runtime.eval_coverage import maybe_audit_eval_coverage
from glassbox.runtime.evals import EvalSuiteSelection
from glassbox.runtime.evals import resolve_eval_suite_selection


@dataclass(frozen=True, slots=True)
class EvalSuiteInput:
    """Resolved eval suite inputs ready for execution and reporting."""

    workspace_root: Path
    selection: EvalSuiteSelection
    coverage_audit: EvalCoverageAuditResult | None
    output_dir: Path


def resolve_eval_suite_input(
    workspace_root: Path,
    *,
    profile_id: str | None = None,
    case_ids: list[str] | None = None,
    tags: list[str] | None = None,
    output_dir: Path | None = None,
    refresh_output_dir: bool = False,
    require_cases: bool = True,
) -> EvalSuiteInput:
    """Resolve selection, optional coverage audit, and output directory for a suite."""

    resolved_workspace_root = workspace_root.resolve()
    selection = resolve_eval_suite_selection(
        resolved_workspace_root,
        profile_id=profile_id,
        case_ids=case_ids,
        tags=tags,
    )
    if require_cases and not selection.cases:
        raise ValueError("no eval cases selected")

    coverage_audit = maybe_audit_eval_coverage(
        resolved_workspace_root,
        profile_id=profile_id,
        case_ids=case_ids,
        tags=tags,
    )
    resolved_output_dir = resolve_eval_output_dir(
        resolved_workspace_root,
        output_dir=output_dir,
    )
    if refresh_output_dir:
        refresh_eval_output_dir(
            resolved_workspace_root,
            output_dir=resolved_output_dir,
        )
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    return EvalSuiteInput(
        workspace_root=resolved_workspace_root,
        selection=selection,
        coverage_audit=coverage_audit,
        output_dir=resolved_output_dir,
    )


def resolve_eval_output_dir(
    workspace_root: Path,
    *,
    output_dir: Path | None,
) -> Path:
    """Resolve the eval output directory for one suite execution."""

    if output_dir is not None:
        return output_dir.resolve()
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return (workspace_root / ".glassbox" / "evals" / timestamp).resolve()


def refresh_eval_output_dir(workspace_root: Path, *, output_dir: Path) -> None:
    """Delete JSON artifacts under a managed eval output directory."""

    managed_root = (workspace_root / ".glassbox" / "evals").resolve()
    if not output_dir.is_relative_to(managed_root):
        raise ValueError(
            "--refresh-output-dir requires an output directory under .glassbox/evals"
        )
    if not output_dir.exists():
        return
    for child in output_dir.iterdir():
        if child.is_file() and child.suffix == ".json":
            child.unlink()


def load_eval_suite_result(summary_path: Path, suite_result_type):
    """Load one structured eval suite summary from disk using the caller type."""

    return suite_result_type.model_validate_json(
        summary_path.read_text(encoding="utf-8")
    )


def load_json_file(path: Path) -> dict[str, object]:
    """Load one JSON object file from disk."""

    return json.loads(path.read_text(encoding="utf-8"))
