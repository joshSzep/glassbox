"""Runtime-specific exceptions for failure classification."""

from __future__ import annotations


class SessionRuntimeFailure(ValueError):
    """Raised when a persisted session cannot continue without reconfiguration."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable
