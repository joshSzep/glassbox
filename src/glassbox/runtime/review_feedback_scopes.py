"""Review-feedback scope helpers."""

from glassbox.core import ReviewFeedbackScopeKind


def resolve_feedback_scope_kind(
    scope_kind: ReviewFeedbackScopeKind,
    *,
    file_path: str | None,
) -> ReviewFeedbackScopeKind:
    """Infer file scope when a file path is supplied to changeset-scope input."""

    if file_path is not None and scope_kind == ReviewFeedbackScopeKind.CHANGESET:
        return ReviewFeedbackScopeKind.FILE
    return scope_kind


def default_feedback_scope_reason(scope_kind: ReviewFeedbackScopeKind) -> str:
    if scope_kind == ReviewFeedbackScopeKind.FILE:
        return "feedback applies to the referenced file scope"
    if scope_kind == ReviewFeedbackScopeKind.TASK:
        return "feedback applies to the linked task evidence"
    if scope_kind == ReviewFeedbackScopeKind.TURN:
        return "feedback applies to the linked turn evidence"
    if scope_kind == ReviewFeedbackScopeKind.ARTIFACT:
        return "feedback applies to the linked artifact evidence"
    if scope_kind == ReviewFeedbackScopeKind.VERIFICATION:
        return "feedback applies to the linked verification evidence"
    if scope_kind == ReviewFeedbackScopeKind.BRANCH_CANDIDATE:
        return "feedback applies to the linked branch-candidate evidence"
    return "feedback applies to the whole changeset"


__all__ = ["default_feedback_scope_reason", "resolve_feedback_scope_kind"]
