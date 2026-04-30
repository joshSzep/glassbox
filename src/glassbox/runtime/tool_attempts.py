"""Retry and resume posture classification for durable tool attempts."""

import shlex
from collections.abc import Mapping

from pydantic import BaseModel
from pydantic import ConfigDict

from glassbox.core.models import PolicyDecision
from glassbox.core.types import ToolAttemptRetryClassification
from glassbox.core.types import ToolAttemptStatus
from glassbox.tools.registry import ToolRiskLevel
from glassbox.tools.registry import ToolSpec


class ToolAttemptRetryAssessment(BaseModel):
    """Operator-facing retry posture derived from status, command, and policy."""

    model_config = ConfigDict(extra="forbid")

    classification: ToolAttemptRetryClassification
    safe_to_retry: bool | None
    reason: str
    requires_approval: bool
    policy_reason: str | None = None


def classify_tool_attempt_retry(
    *,
    status: ToolAttemptStatus,
    tool_name: str,
    tool_spec: ToolSpec | None = None,
    arguments: BaseModel | Mapping[str, object] | None = None,
    output_payload: Mapping[str, object] | None = None,
    policy_decision: PolicyDecision | None = None,
) -> ToolAttemptRetryAssessment:
    """Classify whether a durable tool attempt can be retried or resumed.

    The result is advisory evidence for operators and later recovery actions.
    It is intentionally conservative when command side effects are unclear.
    """

    risk_level = tool_spec.risk_level if tool_spec is not None else None
    if status in {
        ToolAttemptStatus.STARTED,
        ToolAttemptStatus.RUNNING,
        ToolAttemptStatus.WAITING,
    }:
        return _assessment(
            ToolAttemptRetryClassification.ALREADY_RUNNING,
            safe=False,
            reason="attempt is still active; inspect or wait before retrying",
        )

    if status is ToolAttemptStatus.ABANDONED:
        return _assessment(
            ToolAttemptRetryClassification.ABANDONED,
            safe=False,
            reason=(
                "attempt was abandoned; inspect retained evidence before starting "
                "new work"
            ),
        )

    if status is ToolAttemptStatus.SUCCEEDED:
        return _assessment(
            ToolAttemptRetryClassification.UNSAFE_TO_RETRY,
            safe=False,
            reason="attempt already succeeded; retrying could duplicate completed work",
        )

    if status is ToolAttemptStatus.RETRIED:
        return _assessment(
            ToolAttemptRetryClassification.UNKNOWN,
            safe=None,
            reason="attempt has already been retried; inspect the latest attempt first",
            requires_approval=_risk_requires_approval(risk_level, policy_decision),
            policy_reason=_policy_reason(policy_decision),
        )

    command = _command_text(tool_spec, arguments)
    command_kind, command_reason = _classify_command(command)
    failure_category = _failure_category(output_payload)
    status_reason = _status_reason(status, failure_category)

    if command_kind == _CommandRetryKind.IDEMPOTENT:
        return _assessment(
            ToolAttemptRetryClassification.IDEMPOTENT,
            safe=True,
            reason=f"{status_reason}; {command_reason}",
            requires_approval=_risk_requires_approval(risk_level, policy_decision),
            policy_reason=_policy_reason(policy_decision),
        )

    if command_kind == _CommandRetryKind.UNSAFE:
        return _assessment(
            ToolAttemptRetryClassification.UNSAFE_TO_RETRY,
            safe=False,
            reason=f"{status_reason}; {command_reason}",
        )

    if risk_level is ToolRiskLevel.READ_ONLY:
        return _assessment(
            ToolAttemptRetryClassification.RETRYABLE,
            safe=True,
            reason=f"{status_reason}; read-only tools do not mutate workspace state",
            requires_approval=False,
            policy_reason=_policy_reason(policy_decision),
        )

    if tool_name in {"test_discovery", "test_target_selection"}:
        return _assessment(
            ToolAttemptRetryClassification.IDEMPOTENT,
            safe=True,
            reason=f"{status_reason}; test discovery tools are read-only",
            requires_approval=False,
            policy_reason=_policy_reason(policy_decision),
        )

    return _assessment(
        ToolAttemptRetryClassification.UNKNOWN,
        safe=None,
        reason=(
            f"{status_reason}; retry side effects are unknown from retained evidence"
        ),
        requires_approval=_risk_requires_approval(risk_level, policy_decision)
        or risk_level in {ToolRiskLevel.WORKSPACE_WRITE, ToolRiskLevel.COMMAND},
        policy_reason=_policy_reason(policy_decision),
    )


def _assessment(
    classification: ToolAttemptRetryClassification,
    *,
    safe: bool | None,
    reason: str,
    requires_approval: bool = False,
    policy_reason: str | None = None,
) -> ToolAttemptRetryAssessment:
    return ToolAttemptRetryAssessment(
        classification=classification,
        safe_to_retry=safe,
        reason=reason,
        requires_approval=requires_approval,
        policy_reason=policy_reason if requires_approval else None,
    )


class _CommandRetryKind:
    IDEMPOTENT = "idempotent"
    UNSAFE = "unsafe"
    UNKNOWN = "unknown"


def _command_text(
    tool_spec: ToolSpec | None,
    arguments: BaseModel | Mapping[str, object] | None,
) -> str | None:
    if tool_spec is None or tool_spec.command_argument_name is None:
        return None
    values: Mapping[str, object]
    if arguments is None:
        return None
    if isinstance(arguments, BaseModel):
        values = arguments.model_dump(mode="python")
    else:
        values = arguments
    value = values.get(tool_spec.command_argument_name)
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _classify_command(command: str | None) -> tuple[str, str]:
    if command is None:
        return _CommandRetryKind.UNKNOWN, "no command arguments were retained"
    if _has_shell_write_operator(command):
        return (
            _CommandRetryKind.UNSAFE,
            "command uses shell output redirection or tee, so rerun side effects "
            "are unclear",
        )

    tokens = _command_tokens(command)
    if not tokens:
        return _CommandRetryKind.UNKNOWN, "command could not be parsed"
    first = tokens[0]

    if first == "git" and len(tokens) > 1:
        if tokens[1] in {"status", "diff", "show", "log"}:
            return _CommandRetryKind.IDEMPOTENT, "git inspection command is idempotent"
        return _CommandRetryKind.UNSAFE, "git mutation command requires manual review"

    if first in {"rm", "mv", "cp", "rsync", "curl", "wget", "scp", "ssh"}:
        return (
            _CommandRetryKind.UNSAFE,
            f"{first} can mutate local or remote state when rerun",
        )

    if first in {"npm", "pnpm", "yarn"} and len(tokens) > 1:
        if tokens[1] in {"install", "add", "remove", "update", "publish"}:
            return (
                _CommandRetryKind.UNSAFE,
                f"{first} {tokens[1]} can mutate dependencies or publish state",
            )

    if first == "uv" and len(tokens) > 1 and tokens[1] in {"add", "remove", "sync"}:
        return _CommandRetryKind.UNSAFE, f"uv {tokens[1]} can mutate dependency state"

    if _is_pytest_command(tokens):
        return _CommandRetryKind.IDEMPOTENT, "pytest command is verification-only"
    if _is_frontend_verification_command(tokens):
        return (
            _CommandRetryKind.IDEMPOTENT,
            "frontend lint, typecheck, build, or test command is repeatable "
            "verification",
        )
    if _is_python_validation_command(tokens):
        return _CommandRetryKind.IDEMPOTENT, "validation script command is repeatable"
    if _is_static_check_command(tokens):
        return _CommandRetryKind.IDEMPOTENT, "static check command is repeatable"
    if first in {"rg", "ls", "sed", "cat", "head", "tail", "wc", "pwd"}:
        return _CommandRetryKind.IDEMPOTENT, f"{first} is an inspection command"

    return _CommandRetryKind.UNKNOWN, "command is not recognized as idempotent"


def _command_tokens(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return []


def _has_shell_write_operator(command: str) -> bool:
    return ">" in command or " tee " in f" {command} "


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


def _is_frontend_verification_command(tokens: list[str]) -> bool:
    if not tokens or tokens[0] not in {"npm", "pnpm", "yarn"}:
        return False
    command = _package_script(tokens)
    return command in {"lint", "test", "typecheck", "build"}


def _package_script(tokens: list[str]) -> str | None:
    ignored_option_values = {"--dir", "--filter", "--workspace", "-C"}
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token in ignored_option_values:
            index += 2
            continue
        if token.startswith("-"):
            index += 1
            continue
        return token
    return None


def _is_python_validation_command(tokens: list[str]) -> bool:
    if tokens[:3] != ["uv", "run", "python"] and tokens[:1] != ["python"]:
        return False
    script = tokens[3] if tokens[:3] == ["uv", "run", "python"] else tokens[1]
    return script.startswith("scripts/validate_") or script.startswith(
        "scripts/background_"
    )


def _is_static_check_command(tokens: list[str]) -> bool:
    return (
        (tokens[:3] == ["uv", "run", "ty"] and len(tokens) > 3 and tokens[3] == "check")
        or tokens[:4] == ["uv", "run", "ruff", "check"]
        or tokens[:5] == ["uv", "run", "ruff", "format", "--check"]
        or tokens[:2] == ["ruff", "check"]
        or tokens[:3] == ["ruff", "format", "--check"]
        or tokens[:2] == ["ty", "check"]
    )


def _failure_category(output_payload: Mapping[str, object] | None) -> str | None:
    if output_payload is None:
        return None
    value = output_payload.get("failure_category")
    return value if isinstance(value, str) else None


def _status_reason(
    status: ToolAttemptStatus,
    failure_category: str | None,
) -> str:
    if status is ToolAttemptStatus.STALE:
        return "attempt heartbeat is stale"
    if status is ToolAttemptStatus.CANCELLED:
        return "attempt was cancelled before completion"
    if failure_category == "timed_out":
        return "attempt timed out before completion"
    if failure_category == "interrupted":
        return "attempt was interrupted before completion"
    if status is ToolAttemptStatus.FAILED:
        return "attempt failed before completion"
    return f"attempt is {status.value}"


def _risk_requires_approval(
    risk_level: ToolRiskLevel | None,
    policy_decision: PolicyDecision | None,
) -> bool:
    if policy_decision is not None and policy_decision.requires_approval:
        return True
    return risk_level in {ToolRiskLevel.WORKSPACE_WRITE, ToolRiskLevel.COMMAND}


def _policy_reason(policy_decision: PolicyDecision | None) -> str | None:
    if policy_decision is None:
        return None
    return policy_decision.reason


__all__ = ["ToolAttemptRetryAssessment", "classify_tool_attempt_retry"]
