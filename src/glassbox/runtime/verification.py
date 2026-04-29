"""Verification plan helpers and failure classification."""

from glassbox.core.models import VerificationFailureDigest
from glassbox.core.types import VerificationFailureCategory


def classify_verification_failure(
    output: str,
    *,
    exit_code: int | None = None,
    timed_out: bool = False,
) -> VerificationFailureDigest:
    """Return a compact evidence-based failure digest for verification output."""

    normalized = output.lower()
    category = VerificationFailureCategory.UNKNOWN
    if timed_out or "timed out" in normalized or "timeout" in normalized:
        category = VerificationFailureCategory.TIMEOUT
    elif "budget exhausted" in normalized:
        category = VerificationFailureCategory.BUDGET
    elif "policy" in normalized and ("blocked" in normalized or "denied" in normalized):
        category = VerificationFailureCategory.POLICY
    elif "mypy" in normalized or "type error" in normalized:
        category = VerificationFailureCategory.TYPECHECK
    elif "ruff" in normalized or "flake8" in normalized or "lint" in normalized:
        category = VerificationFailureCategory.LINT
    elif "build failed" in normalized or "packaging" in normalized:
        category = VerificationFailureCategory.PACKAGE
    elif "connection refused" in normalized or "no such file" in normalized:
        category = VerificationFailureCategory.INFRASTRUCTURE
    elif "flaky" in normalized or "rerun" in normalized:
        category = VerificationFailureCategory.FLAKY
    elif "assert" in normalized or "failed" in normalized:
        category = VerificationFailureCategory.ASSERTION

    first_relevant_line = _first_nonempty_line(output)
    summary = first_relevant_line or (
        f"verification exited with code {exit_code}"
        if exit_code is not None
        else "verification failed without output"
    )
    return VerificationFailureDigest(
        category=category,
        summary=summary[:4000],
        exit_code=exit_code,
        timed_out=timed_out,
        first_relevant_line=first_relevant_line,
    )


def _first_nonempty_line(output: str) -> str | None:
    for line in output.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:1000]
    return None


__all__ = ["classify_verification_failure"]
