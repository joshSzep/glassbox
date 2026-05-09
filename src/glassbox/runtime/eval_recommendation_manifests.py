"""Manifest loading helpers for eval recommendation reports."""

from pathlib import Path

from glassbox.runtime.eval_coverage import DEFAULT_EVAL_COVERAGE_PATH
from glassbox.runtime.eval_coverage import EvalCapabilityDefinition
from glassbox.runtime.eval_coverage import load_eval_coverage_manifest
from glassbox.runtime.evals import EvalCase
from glassbox.runtime.evals import discover_eval_case_files
from glassbox.runtime.evals import load_eval_case


def load_all_eval_cases(workspace_root: Path) -> list[EvalCase]:
    """Load all repository eval cases in deterministic order."""

    cases: list[EvalCase] = []
    for case_path in discover_eval_case_files(workspace_root):
        cases.append(load_eval_case(case_path, workspace_root=workspace_root))
    cases.sort(key=lambda case: case.case_id)
    return cases


def load_capabilities(
    workspace_root: Path,
    *,
    coverage_path: Path | None,
) -> list[EvalCapabilityDefinition]:
    """Load eval coverage capabilities when the repository provides them."""

    try:
        return load_eval_coverage_manifest(
            workspace_root,
            coverage_path=coverage_path,
        ).capabilities
    except ValueError as exc:
        resolved_path = _resolve_optional_manifest_path(
            workspace_root,
            coverage_path,
            DEFAULT_EVAL_COVERAGE_PATH,
        )
        if "missing eval coverage manifest" in str(exc) and not resolved_path.exists():
            return []
        raise


def _resolve_optional_manifest_path(
    workspace_root: Path,
    path: Path | None,
    default_path: Path,
) -> Path:
    if path is None:
        return (workspace_root.resolve() / default_path).resolve()
    if path.is_absolute():
        return path.resolve()
    return (workspace_root.resolve() / path).resolve()


__all__ = ["load_all_eval_cases", "load_capabilities"]
