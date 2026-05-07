"""Compatibility facade for review-loop SQLite repository mixins."""

from glassbox.store.repository_manual_evidence import _SQLiteManualEvidenceMethods
from glassbox.store.repository_review_feedback import _SQLiteReviewFeedbackMethods


class _SQLiteReviewLoopMethods(
    _SQLiteReviewFeedbackMethods,
    _SQLiteManualEvidenceMethods,
):
    """Compatibility mixin for the full local review-loop read surface."""


__all__ = [
    "_SQLiteManualEvidenceMethods",
    "_SQLiteReviewFeedbackMethods",
    "_SQLiteReviewLoopMethods",
]
