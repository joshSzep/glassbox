"""Compatibility facade for changeset SQLite repository mixins."""

from glassbox.store.repository_changeset_detail import _SQLiteChangesetDetailMethods
from glassbox.store.repository_changeset_readiness import (
    _SQLiteChangesetReviewReadinessMethods,
)


class _SQLiteChangesetMethods(
    _SQLiteChangesetDetailMethods,
    _SQLiteChangesetReviewReadinessMethods,
):
    """Compatibility mixin for the full changeset repository read surface."""


__all__ = [
    "_SQLiteChangesetDetailMethods",
    "_SQLiteChangesetMethods",
    "_SQLiteChangesetReviewReadinessMethods",
]
