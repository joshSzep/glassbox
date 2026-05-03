"""Review-oriented command purpose classification."""

import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
from collections.abc import Callable
from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import BaseModel
from pydantic import ConfigDict

from glassbox.core.models import CommandEnvironmentSummary
from glassbox.core.models import CommandToolchainVersion
from glassbox.core.types import CommandPurpose
from glassbox.core.types import CommandReviewRelevance
from glassbox.tools.policy_command_risk import command_text
from glassbox.tools.policy_command_risk import is_destructive_command
from glassbox.tools.registry import ToolSpec


class CommandPurposeAssessment(BaseModel):
    """Conservative command-purpose evidence retained for review."""

    model_config = ConfigDict(extra="forbid")

    purpose: CommandPurpose
    review_relevance: CommandReviewRelevance
    supports_verification: bool
    reason: str


@dataclass(frozen=True, slots=True)
class CommandAttemptEvidence:
    """Optional command evidence fields for a tool-attempt heartbeat."""

    purpose: CommandPurpose | None = None
    review_relevance: CommandReviewRelevance | None = None
    supports_verification: bool | None = None
    reason: str | None = None
    environment: CommandEnvironmentSummary | None = None


VersionLookup = Callable[[str], CommandToolchainVersion]


def classify_command_purpose(command: str | None) -> CommandPurposeAssessment:
    """Classify one shell command for review evidence.

    The classifier is intentionally heuristic and conservative. Unknown commands
    never support verification evidence, even if they exit successfully.
    """

    if command is None or not command.strip():
        return _assessment(
            CommandPurpose.UNKNOWN,
            CommandReviewRelevance.UNKNOWN,
            "no command text was retained",
        )

    normalized_command = command.strip()
    if is_destructive_command(normalized_command):
        return _assessment(
            CommandPurpose.DANGEROUS,
            CommandReviewRelevance.CLEANUP_OR_DESTRUCTIVE,
            "command matches a destructive hard-block pattern",
        )

    segment_assessments = [
        _classify_simple_command(segment)
        for segment in _command_segments(normalized_command)
        if segment.strip()
    ]
    if not segment_assessments:
        return _assessment(
            CommandPurpose.UNKNOWN,
            CommandReviewRelevance.UNKNOWN,
            "command could not be parsed into a reviewable segment",
        )
    if len(segment_assessments) == 1:
        return segment_assessments[0]

    highest = _highest_priority(segment_assessments)
    if all(item.purpose == highest.purpose for item in segment_assessments):
        return highest
    purposes = ", ".join(sorted({item.purpose.value for item in segment_assessments}))
    return CommandPurposeAssessment(
        purpose=highest.purpose,
        review_relevance=highest.review_relevance,
        supports_verification=(
            highest.supports_verification
            and all(item.supports_verification for item in segment_assessments)
        ),
        reason=(
            f"multi-command shell line includes {purposes}; using highest-risk purpose"
        ),
    )


def capture_command_environment(
    *,
    command: str,
    assessment: CommandPurposeAssessment,
    environment: Mapping[str, str] | None = None,
    version_lookup: VersionLookup | None = None,
) -> CommandEnvironmentSummary | None:
    """Return a bounded environment summary for review-relevant commands."""

    if assessment.review_relevance not in {
        CommandReviewRelevance.VERIFICATION,
        CommandReviewRelevance.LOCAL_ARTIFACT,
    }:
        return None

    env = os.environ if environment is None else environment
    lookup = version_lookup or _toolchain_version
    tool_names = _toolchain_names_for_command(command)
    toolchains = [lookup(name) for name in tool_names]
    redacted_env, redaction_notes = _redacted_environment_subset(env)
    limitations: list[str] = []
    if not toolchains:
        limitations.append("no command-specific toolchain executables were detected")
    if any(not item.available for item in toolchains):
        limitations.append("one or more detected toolchain executables were missing")

    return CommandEnvironmentSummary(
        capture_scope="verification_or_local_artifact",
        command_purpose=assessment.purpose,
        platform=platform.system() or "unknown",
        python_version=_python_version(),
        toolchains=toolchains,
        environment=redacted_env,
        redaction_notes=redaction_notes,
        limitations=limitations,
    )


def command_attempt_evidence(
    tool_spec: ToolSpec,
    arguments: Mapping[str, object],
) -> CommandAttemptEvidence:
    """Classify command evidence fields from one tool request."""

    command = command_text(tool_spec, arguments)
    if command is None:
        return CommandAttemptEvidence()
    assessment = classify_command_purpose(command)
    return CommandAttemptEvidence(
        purpose=assessment.purpose,
        review_relevance=assessment.review_relevance,
        supports_verification=assessment.supports_verification,
        reason=assessment.reason,
        environment=capture_command_environment(
            command=command,
            assessment=assessment,
        ),
    )


def command_toolchain_drift_warnings(
    recorded: CommandEnvironmentSummary | None,
    *,
    version_lookup: VersionLookup | None = None,
) -> list[str]:
    """Compare retained toolchain evidence to the current local posture."""

    if recorded is None:
        return []
    lookup = version_lookup or _toolchain_version
    warnings: list[str] = []
    if recorded.python_version != _python_version():
        warnings.append(
            "python version changed from "
            f"{recorded.python_version} to {_python_version()}"
        )
    for item in recorded.toolchains:
        current = lookup(item.name)
        if item.available and not current.available:
            warnings.append(f"{item.name} is no longer available")
            continue
        if not item.available and current.available:
            warnings.append(f"{item.name} is now available but was missing before")
            continue
        if item.version != current.version:
            warnings.append(
                f"{item.name} version changed from "
                f"{item.version or 'unknown'} to {current.version or 'unknown'}"
            )
    return warnings


def _classify_simple_command(command: str) -> CommandPurposeAssessment:
    tokens = _command_tokens(command)
    if not tokens:
        return _assessment(
            CommandPurpose.UNKNOWN,
            CommandReviewRelevance.UNKNOWN,
            "command segment could not be parsed",
        )

    first = tokens[0]
    second = tokens[1] if len(tokens) > 1 else None
    script = _package_script(tokens)

    if first == "git" and second in {"status", "diff", "show", "log", "branch"}:
        return _assessment(
            CommandPurpose.INSPECT,
            CommandReviewRelevance.INSPECTION,
            "git inspection command provides review context",
        )
    if first in {"rg", "ls", "sed", "cat", "head", "tail", "wc", "pwd", "find"}:
        return _assessment(
            CommandPurpose.INSPECT,
            CommandReviewRelevance.INSPECTION,
            f"{first} is an inspection command",
        )

    if _is_pytest_command(tokens) or script in {"test", "vitest"}:
        return _assessment(
            CommandPurpose.TEST,
            CommandReviewRelevance.VERIFICATION,
            "test command can support verification evidence",
            supports_verification=True,
        )
    if _is_lint_command(tokens) or script in {"lint", "eslint"}:
        return _assessment(
            CommandPurpose.LINT,
            CommandReviewRelevance.VERIFICATION,
            "lint command can support verification evidence",
            supports_verification=True,
        )
    if _is_typecheck_command(tokens) or script in {"typecheck", "tsc"}:
        return _assessment(
            CommandPurpose.TYPECHECK,
            CommandReviewRelevance.VERIFICATION,
            "typecheck command can support verification evidence",
            supports_verification=True,
        )
    if script == "build" or _is_build_command(tokens):
        return _assessment(
            CommandPurpose.BUILD,
            CommandReviewRelevance.VERIFICATION,
            "local build command can support verification evidence",
            supports_verification=True,
        )
    if _is_eval_command(tokens):
        return _assessment(
            CommandPurpose.EVAL,
            CommandReviewRelevance.VERIFICATION,
            "Glassbox eval command can support deterministic review evidence",
            supports_verification=True,
        )
    if _is_release_gate_command(tokens):
        return _assessment(
            CommandPurpose.RELEASE_GATE,
            CommandReviewRelevance.VERIFICATION,
            "release-gate command can support release readiness evidence",
            supports_verification=True,
        )
    if _is_local_package_command(tokens):
        return _assessment(
            CommandPurpose.PACKAGE,
            CommandReviewRelevance.LOCAL_ARTIFACT,
            "local package-build command creates review-relevant artifacts",
        )
    if _is_publish_command(tokens):
        return _assessment(
            CommandPurpose.PUBLISH,
            CommandReviewRelevance.RELEASE_OR_REMOTE_MUTATION,
            "publish command may mutate remote package state",
        )
    if _is_deploy_command(tokens):
        return _assessment(
            CommandPurpose.DEPLOY,
            CommandReviewRelevance.RELEASE_OR_REMOTE_MUTATION,
            "deploy command may mutate remote runtime state",
        )
    if _is_cleanup_command(tokens):
        return _assessment(
            CommandPurpose.CLEANUP,
            CommandReviewRelevance.CLEANUP_OR_DESTRUCTIVE,
            "cleanup command may remove local evidence or files",
        )

    return _assessment(
        CommandPurpose.UNKNOWN,
        CommandReviewRelevance.UNKNOWN,
        "command is not recognized as inspection or verification evidence",
    )


def _assessment(
    purpose: CommandPurpose,
    review_relevance: CommandReviewRelevance,
    reason: str,
    *,
    supports_verification: bool = False,
) -> CommandPurposeAssessment:
    return CommandPurposeAssessment(
        purpose=purpose,
        review_relevance=review_relevance,
        supports_verification=supports_verification,
        reason=reason,
    )


def _command_segments(command: str) -> list[str]:
    return [
        segment.strip()
        for segment in re.split(r"\s*(?:&&|\|\||;|\|)\s*", command)
        if segment.strip()
    ]


def _command_tokens(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return []


def _toolchain_names_for_command(command: str) -> list[str]:
    names = ["python"]
    tokens = _command_tokens(command)
    if not tokens:
        return names
    first = tokens[0]
    if first in {"uv", "node", "npm", "pnpm", "yarn", "ruff", "ty", "pytest"}:
        names.append(first)
    script = _package_script(tokens)
    if first in {"npm", "pnpm", "yarn"}:
        names.append("node")
    if script in {"lint", "test", "typecheck", "build"}:
        names.append(first)
    for token in tokens:
        if token in {"ruff", "ty", "pytest"}:
            names.append(token)
    return sorted(dict.fromkeys(names))


def _toolchain_version(name: str) -> CommandToolchainVersion:
    if name == "python":
        return CommandToolchainVersion(
            name="python",
            version=_python_version(),
            available=True,
            source="runtime",
            redacted_executable=_redacted_executable(sys.executable),
        )
    executable = shutil.which(name)
    if executable is None:
        return CommandToolchainVersion(
            name=name,
            version=None,
            available=False,
            source="executable_version",
            error="executable not found on PATH",
        )
    version = _run_version_command(name)
    return CommandToolchainVersion(
        name=name,
        version=version,
        available=True,
        source="executable_version",
        redacted_executable=_redacted_executable(executable),
        error=None if version is not None else "version command produced no output",
    )


def _run_version_command(name: str) -> str | None:
    command = [name, "--version"]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except OSError, subprocess.TimeoutExpired:
        return None
    output = (completed.stdout or completed.stderr).strip()
    if not output:
        return None
    return output.splitlines()[0][:200]


def _redacted_executable(path: str) -> str:
    return f"<redacted-path>/{os.path.basename(path)}"


def _redacted_environment_subset(
    environment: Mapping[str, str],
) -> tuple[dict[str, str], list[str]]:
    captured: dict[str, str] = {}
    notes = ["environment capture is allowlist-only; raw environment is not stored"]
    for key in ("CI", "GITHUB_ACTIONS", "GIT_BRANCH", "VIRTUAL_ENV"):
        value = environment.get(key)
        if value is None:
            continue
        captured[key] = _redacted_environment_value(key, value)
    return captured, notes


def _redacted_environment_value(key: str, value: str) -> str:
    key_upper = key.upper()
    if any(marker in key_upper for marker in ("TOKEN", "SECRET", "KEY", "PASSWORD")):
        return "<redacted-secret>"
    if key_upper in {"VIRTUAL_ENV"}:
        return "<redacted-path>"
    return value[:200]


def _python_version() -> str:
    return platform.python_version()


def _package_script(tokens: list[str]) -> str | None:
    if not tokens or tokens[0] not in {"npm", "pnpm", "yarn"}:
        return None
    ignored_option_values = {"--dir", "--filter", "--workspace", "-C"}
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token in ignored_option_values:
            index += 2
            continue
        if token in {"run", "exec"}:
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        return token
    return None


def _is_pytest_command(tokens: list[str]) -> bool:
    return (
        tokens[:1] == ["pytest"]
        or tokens[:3] == ["python", "-m", "pytest"]
        or tokens[:3] == ["uv", "run", "pytest"]
        or (
            tokens[:4] == ["uv", "run", "python", "-m"]
            and len(tokens) > 4
            and tokens[4] == "pytest"
        )
    )


def _is_lint_command(tokens: list[str]) -> bool:
    return (
        tokens[:4] == ["uv", "run", "ruff", "check"]
        or tokens[:5] == ["uv", "run", "ruff", "format", "--check"]
        or tokens[:2] == ["ruff", "check"]
        or tokens[:3] == ["ruff", "format", "--check"]
        or tokens[:1] in (["eslint"], ["ruff"])
    )


def _is_typecheck_command(tokens: list[str]) -> bool:
    return (
        (tokens[:3] == ["uv", "run", "ty"] and len(tokens) > 3 and tokens[3] == "check")
        or tokens[:2] == ["ty", "check"]
        or tokens[:1] in (["mypy"], ["pyright"])
        or tokens[:2] == ["tsc", "--noEmit"]
    )


def _is_build_command(tokens: list[str]) -> bool:
    return tokens[:2] in (["next", "build"], ["vite", "build"])


def _is_eval_command(tokens: list[str]) -> bool:
    return (
        tokens[:3] == ["uv", "run", "glassbox"]
        and len(tokens) > 3
        and tokens[3] == "eval"
    ) or (tokens[:2] == ["glassbox", "eval"])


def _is_release_gate_command(tokens: list[str]) -> bool:
    if tokens[:3] == ["uv", "run", "python"] and len(tokens) > 3:
        return _is_release_gate_script(tokens[3])
    if tokens[:1] == ["python"] and len(tokens) > 1:
        return _is_release_gate_script(tokens[1])
    return False


def _is_release_gate_script(token: str) -> bool:
    return token.startswith("scripts/validate_") and token.endswith("_release_gate.py")


def _is_local_package_command(tokens: list[str]) -> bool:
    return (
        tokens[:2] == ["uv", "build"]
        or tokens[:3] == ["python", "-m", "build"]
        or tokens[:4] == ["uv", "run", "python", "-m"]
        and len(tokens) > 4
        and tokens[4] == "build"
        or _package_script(tokens) == "pack"
    )


def _is_publish_command(tokens: list[str]) -> bool:
    script = _package_script(tokens)
    return (
        script == "publish"
        or tokens[:2] in (["twine", "upload"], ["uv", "publish"], ["cargo", "publish"])
        or tokens[:3] == ["uv", "run", "twine"]
        and len(tokens) > 3
        and tokens[3] == "upload"
    )


def _is_deploy_command(tokens: list[str]) -> bool:
    if tokens[:2] in (
        ["vercel", "deploy"],
        ["netlify", "deploy"],
        ["fly", "deploy"],
        ["kubectl", "apply"],
        ["terraform", "apply"],
    ):
        return True
    return _package_script(tokens) in {"deploy", "release"}


def _is_cleanup_command(tokens: list[str]) -> bool:
    if tokens[:2] == ["git", "clean"]:
        return True
    return tokens[:1] in (["rm"], ["rmdir"])


def _highest_priority(
    assessments: list[CommandPurposeAssessment],
) -> CommandPurposeAssessment:
    priority = {
        CommandPurpose.DANGEROUS: 120,
        CommandPurpose.PUBLISH: 110,
        CommandPurpose.DEPLOY: 100,
        CommandPurpose.CLEANUP: 90,
        CommandPurpose.PACKAGE: 80,
        CommandPurpose.RELEASE_GATE: 70,
        CommandPurpose.EVAL: 60,
        CommandPurpose.BUILD: 50,
        CommandPurpose.TEST: 40,
        CommandPurpose.TYPECHECK: 35,
        CommandPurpose.LINT: 30,
        CommandPurpose.INSPECT: 20,
        CommandPurpose.UNKNOWN: 10,
    }
    return max(assessments, key=lambda item: priority[item.purpose])


__all__ = [
    "CommandAttemptEvidence",
    "CommandPurposeAssessment",
    "capture_command_environment",
    "command_attempt_evidence",
    "classify_command_purpose",
    "command_toolchain_drift_warnings",
]
