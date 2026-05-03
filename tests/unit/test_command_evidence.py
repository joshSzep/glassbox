"""Unit tests for review-oriented command evidence classification."""

from glassbox.core import CommandPurpose
from glassbox.core import CommandReviewRelevance
from glassbox.core import CommandToolchainVersion
from glassbox.runtime.command_evidence import capture_command_environment
from glassbox.runtime.command_evidence import classify_command_purpose
from glassbox.runtime.command_evidence import command_toolchain_drift_warnings


def test_classifies_inspection_command_as_review_context() -> None:
    assessment = classify_command_purpose("git diff --stat")

    assert assessment.purpose == CommandPurpose.INSPECT
    assert assessment.review_relevance == CommandReviewRelevance.INSPECTION
    assert assessment.supports_verification is False
    assert "inspection" in assessment.reason


def test_classifies_pytest_as_verification_evidence() -> None:
    assessment = classify_command_purpose("uv run pytest tests/unit")

    assert assessment.purpose == CommandPurpose.TEST
    assert assessment.review_relevance == CommandReviewRelevance.VERIFICATION
    assert assessment.supports_verification is True


def test_classifies_frontend_typecheck_with_package_options() -> None:
    assessment = classify_command_purpose("pnpm --dir frontend typecheck")

    assert assessment.purpose == CommandPurpose.TYPECHECK
    assert assessment.review_relevance == CommandReviewRelevance.VERIFICATION
    assert assessment.supports_verification is True


def test_classifies_release_gate_as_verification_evidence() -> None:
    assessment = classify_command_purpose(
        "uv run python scripts/validate_v11_release_gate.py"
    )

    assert assessment.purpose == CommandPurpose.RELEASE_GATE
    assert assessment.review_relevance == CommandReviewRelevance.VERIFICATION
    assert assessment.supports_verification is True


def test_classifies_publish_as_remote_mutation_not_verification() -> None:
    assessment = classify_command_purpose("pnpm publish")

    assert assessment.purpose == CommandPurpose.PUBLISH
    assert (
        assessment.review_relevance == CommandReviewRelevance.RELEASE_OR_REMOTE_MUTATION
    )
    assert assessment.supports_verification is False


def test_classifies_destructive_command_as_dangerous() -> None:
    assessment = classify_command_purpose("rm -rf build")

    assert assessment.purpose == CommandPurpose.DANGEROUS
    assert assessment.review_relevance == CommandReviewRelevance.CLEANUP_OR_DESTRUCTIVE
    assert assessment.supports_verification is False


def test_classifies_unknown_command_without_verification_claim() -> None:
    assessment = classify_command_purpose("python scripts/custom_migration.py")

    assert assessment.purpose == CommandPurpose.UNKNOWN
    assert assessment.review_relevance == CommandReviewRelevance.UNKNOWN
    assert assessment.supports_verification is False


def test_multi_command_uses_highest_risk_purpose() -> None:
    assessment = classify_command_purpose("rg command src && pnpm publish")

    assert assessment.purpose == CommandPurpose.PUBLISH
    assert (
        assessment.review_relevance == CommandReviewRelevance.RELEASE_OR_REMOTE_MUTATION
    )
    assert assessment.supports_verification is False
    assert "multi-command" in assessment.reason


def test_captures_bounded_redacted_environment_for_verification() -> None:
    assessment = classify_command_purpose("uv run pytest")

    summary = capture_command_environment(
        command="uv run pytest",
        assessment=assessment,
        environment={
            "CI": "true",
            "VIRTUAL_ENV": "/Users/example/project/.venv",
            "OPENAI_API_KEY": "secret",
        },
        version_lookup=lambda name: CommandToolchainVersion(
            name=name,
            version=f"{name} 1.0",
            available=True,
            source="fixture",
            redacted_executable=f"<redacted-path>/{name}",
        ),
    )

    assert summary is not None
    assert summary.command_purpose == CommandPurpose.TEST
    assert summary.environment == {
        "CI": "true",
        "VIRTUAL_ENV": "<redacted-path>",
    }
    assert "OPENAI_API_KEY" not in summary.environment
    assert {item.name for item in summary.toolchains} == {"python", "pytest", "uv"}
    assert all(
        "<redacted-path>" in (item.redacted_executable or "")
        for item in summary.toolchains
    )


def test_skips_environment_capture_for_inspection_commands() -> None:
    assessment = classify_command_purpose("git status")

    summary = capture_command_environment(
        command="git status",
        assessment=assessment,
        environment={"CI": "true"},
    )

    assert summary is None


def test_reports_toolchain_drift_against_current_versions() -> None:
    assessment = classify_command_purpose("pnpm --dir frontend test")
    recorded = capture_command_environment(
        command="pnpm --dir frontend test",
        assessment=assessment,
        environment={},
        version_lookup=lambda name: CommandToolchainVersion(
            name=name,
            version="old",
            available=True,
            source="fixture",
        ),
    )

    assert recorded is not None
    warnings = command_toolchain_drift_warnings(
        recorded,
        version_lookup=lambda name: CommandToolchainVersion(
            name=name,
            version="new",
            available=True,
            source="fixture",
        ),
    )

    assert any("version changed" in warning for warning in warnings)
