"""Runtime-specific exceptions for failure classification."""


class SessionRuntimeFailure(ValueError):
    """Raised when a persisted session cannot continue without reconfiguration."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class ProviderRuntimeConfigFailure(SessionRuntimeFailure):
    """Raised when provider auth or runtime configuration is invalid."""
