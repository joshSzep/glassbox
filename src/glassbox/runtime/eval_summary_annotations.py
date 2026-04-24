"""Automation annotation helpers for eval summary reporting."""

from pathlib import Path

from glassbox.runtime.eval_runner import EvalCaseResult
from glassbox.runtime.eval_runner import EvalSuiteResult
from glassbox.runtime.eval_summary_models import AnnotationLevel
from glassbox.runtime.eval_summary_models import EvalAutomationAnnotation


def build_eval_suite_annotations(
    result: EvalSuiteResult,
    *,
    artifact_root: str,
) -> list[EvalAutomationAnnotation]:
    """Build per-case annotations for quick automation triage."""

    normalized_root = normalized_artifact_root(artifact_root)
    annotations: list[EvalAutomationAnnotation] = []
    for case in result.cases:
        if case.passed:
            continue
        artifact_path = artifact_display_path(
            artifact_root=normalized_root,
            output_dir=result.output_dir,
            artifact_path=case.artifact_path,
        )
        detail = (
            case.triage_headline
            or case.message
            or "See retained case artifact for details."
        )
        first_change = case.first_relevant_mismatch or case.triage_first_relevant_change
        next_inspect = case.triage_recommended_inspection_path
        if first_change is not None:
            detail += f" First change: {first_change}."
        if next_inspect is not None:
            detail += f" Next inspect: {next_inspect}."
        annotations.append(
            EvalAutomationAnnotation(
                level=annotation_level_for_case(case),
                title=f"{case.case_id}: {case.replay_outcome}",
                message=f"{detail} Artifact: {artifact_path}",
            )
        )
    return annotations


def format_github_actions_annotation(annotation: EvalAutomationAnnotation) -> str:
    """Render one GitHub Actions workflow command for an annotation."""

    title = escape_github_actions_value(annotation.title)
    message = escape_github_actions_value(annotation.message)
    return f"::{annotation.level} title={title}::{message}"


def normalized_artifact_root(artifact_root: str) -> str:
    return artifact_root.rstrip("/")


def artifact_display_path(
    *,
    artifact_root: str,
    output_dir: Path,
    artifact_path: Path,
) -> str:
    try:
        relative_path = artifact_path.relative_to(output_dir)
    except ValueError:
        return str(artifact_path)
    return f"{artifact_root}/{relative_path.as_posix()}"


def annotation_level_for_case(case: EvalCaseResult) -> AnnotationLevel:
    if case.replay_outcome == "exact_match":
        return "notice"
    if case.replay_outcome == "behavioral_drift" and case.severity in {
        "low",
        "medium",
    }:
        return "warning"
    return "error"


def escape_github_actions_value(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
