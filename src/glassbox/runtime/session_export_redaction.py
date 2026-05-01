"""Redaction helpers for portable session export packages."""

import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict

from glassbox.core.models import ApprovalRecord
from glassbox.core.models import TaskCheckpointRecord
from glassbox.runtime.session_queries import BranchableTurnView
from glassbox.runtime.session_queries import ChildSessionSummaryView

REDACTION_PLACEHOLDER = "<redacted>"
WORKSPACE_PLACEHOLDER = "<workspace-root>"
REDACTION_NOTES = [
    "absolute workspace paths are replaced with <workspace-root>",
    "common secret-like tokens and key assignments are replaced with <redacted>",
    "artifact contents are not embedded; only retained artifact references are listed",
]

_SECRET_PATTERNS = (
    re.compile(
        r"(?i)\b((?:openai|anthropic|api|access|secret|token|password)"
        r"[_-]?(?:api[_-]?)?(?:key|token|secret|password)?)\s*=\s*([^\s,;]+)"
    ),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
)


class RedactionContext(BaseModel):
    """Workspace-aware redaction state for portable handoff payloads."""

    model_config = ConfigDict(extra="forbid")
    workspace_root: Path


def redact_optional_text(
    value: str | None,
    redaction_context: RedactionContext,
) -> str | None:
    if value is None:
        return None
    return redact_text(value, redaction_context)


def redact_text(value: str, redaction_context: RedactionContext) -> str:
    redacted = value.replace(
        str(redaction_context.workspace_root), WORKSPACE_PLACEHOLDER
    )
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub(_secret_replacement, redacted)
    return redacted


def redact_json_value(value: Any, redaction_context: RedactionContext) -> Any:
    if isinstance(value, str):
        return redact_text(value, redaction_context)
    if isinstance(value, list):
        return [redact_json_value(item, redaction_context) for item in value]
    if isinstance(value, dict):
        return {
            key: redact_json_value(item, redaction_context)
            for key, item in value.items()
        }
    return value


def portable_artifact_path(
    path: str | None,
    redaction_context: RedactionContext,
) -> str | None:
    if path is None:
        return None
    candidate = Path(path)
    if candidate.is_absolute():
        return redact_text(path, redaction_context)
    if ".." in candidate.parts:
        return REDACTION_PLACEHOLDER
    return redact_text(path, redaction_context)


def redact_pending_approvals(
    approvals: Sequence[ApprovalRecord],
    redaction_context: RedactionContext,
) -> list[ApprovalRecord]:
    return [
        approval.model_copy(
            update={
                "subject": redact_text(approval.subject, redaction_context),
                "reason": redact_text(approval.reason, redaction_context),
                "policy_source_label": redact_optional_text(
                    approval.policy_source_label,
                    redaction_context,
                ),
                "decided_by": redact_optional_text(
                    approval.decided_by,
                    redaction_context,
                ),
            }
        )
        for approval in approvals
    ]


def redact_child_sessions(
    child_sessions: Sequence[ChildSessionSummaryView],
    redaction_context: RedactionContext,
) -> list[ChildSessionSummaryView]:
    return [
        child.model_copy(
            update={
                "branch_label": redact_optional_text(
                    child.branch_label,
                    redaction_context,
                ),
                "latest_message_summary": redact_optional_text(
                    child.latest_message_summary,
                    redaction_context,
                ),
            }
        )
        for child in child_sessions
    ]


def redact_branchable_turns(
    branchable_turns: Sequence[BranchableTurnView],
    redaction_context: RedactionContext,
) -> list[BranchableTurnView]:
    return [
        turn.model_copy(update={"label": redact_text(turn.label, redaction_context)})
        for turn in branchable_turns
    ]


def redact_checkpoints(
    checkpoints: Sequence[TaskCheckpointRecord],
    redaction_context: RedactionContext,
) -> list[TaskCheckpointRecord]:
    return [
        checkpoint.model_copy(
            update={
                "objective": redact_text(checkpoint.objective, redaction_context),
                "completed_step": redact_optional_text(
                    checkpoint.completed_step,
                    redaction_context,
                ),
                "next_action": redact_text(
                    checkpoint.next_action,
                    redaction_context,
                ),
                "blockers": [
                    redact_text(blocker, redaction_context)
                    for blocker in checkpoint.blockers
                ],
                "touched_files": [
                    redact_text(path, redaction_context)
                    for path in checkpoint.touched_files
                ],
                "recovery_guidance": redact_text(
                    checkpoint.recovery_guidance,
                    redaction_context,
                ),
            }
        )
        for checkpoint in checkpoints
    ]


def _secret_replacement(match: re.Match[str]) -> str:
    if match.lastindex and match.lastindex >= 2:
        return f"{match.group(1)}={REDACTION_PLACEHOLDER}"
    return REDACTION_PLACEHOLDER
