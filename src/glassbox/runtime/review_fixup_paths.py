"""Path-scope helpers for response-linked fixup inventory."""

from pathlib import Path

from glassbox.core import ReviewFeedbackFixupPathSummary
from glassbox.core import ReviewFeedbackScopeRecord
from glassbox.runtime.change_inventory import ChangeInventoryPathEntry


def feedback_scope_paths(scopes: list[ReviewFeedbackScopeRecord]) -> set[str]:
    """Return normalized file paths from review feedback scopes."""

    return {
        normalize_review_fixup_path(scope.file_path)
        for scope in scopes
        if scope.file_path is not None
    }


def review_fixup_path_matches_scope(
    entry: ChangeInventoryPathEntry,
    scope_paths: set[str],
) -> bool:
    """Return whether a changed path matches feedback file scope."""

    if not scope_paths:
        return False
    path = normalize_review_fixup_path(entry.path)
    return path in scope_paths or any(
        path.startswith(f"{scope_path}/") for scope_path in scope_paths
    )


def review_fixup_path_summary(
    entry: ChangeInventoryPathEntry,
    *,
    matches_feedback_scope: bool,
) -> ReviewFeedbackFixupPathSummary:
    """Build the persisted safe summary for one response-linked fixup path."""

    return ReviewFeedbackFixupPathSummary(
        path=entry.path,
        change_kind=entry.change_kind,
        generated=entry.generated,
        test_file=entry.test_file,
        docs_file=entry.docs_file,
        policy_sensitive=entry.policy_sensitive,
        risk_level=entry.risk_level,
        provenance_confidence=entry.provenance_confidence,
        matches_feedback_scope=matches_feedback_scope,
        summary=_safe_path_summary(
            entry, matches_feedback_scope=matches_feedback_scope
        ),
    )


def normalize_review_fixup_path(path: str | Path) -> str:
    """Normalize persisted and workspace paths for response fixup matching."""

    return str(path).replace("\\", "/").strip().lstrip("./")


def _safe_path_summary(
    entry: ChangeInventoryPathEntry,
    *,
    matches_feedback_scope: bool,
) -> str:
    labels: list[str] = []
    if matches_feedback_scope:
        labels.append("matches feedback scope")
    if entry.generated:
        labels.append("generated output")
    if entry.test_file:
        labels.append("test path")
    if entry.docs_file:
        labels.append("docs path")
    if entry.policy_sensitive:
        labels.append("policy-sensitive path")
    if entry.risk_level in {"high", "medium"}:
        labels.append(f"{entry.risk_level} risk")
    if entry.provenance_confidence == "unknown":
        labels.append("manual or external provenance")
    if not labels:
        labels.append("changed path")
    return f"{entry.path}: {', '.join(labels)}"


__all__ = [
    "feedback_scope_paths",
    "normalize_review_fixup_path",
    "review_fixup_path_matches_scope",
    "review_fixup_path_summary",
]
