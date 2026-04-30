"""Working-set derivation helpers for runtime context assembly."""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime

from glassbox.core.events import ModelToolCallRequested
from glassbox.core.events import ToolArtifactRecorded
from glassbox.core.ids import SessionId
from glassbox.core.models import ApprovalRecord
from glassbox.core.models import RuntimeNoteRecord
from glassbox.core.models import SessionRecord
from glassbox.core.models import ToolCallRecord
from glassbox.core.types import ApprovalStatus
from glassbox.core.types import ToolExecutionStatus
from glassbox.runtime.context_models import WorkingSetItemSnapshot
from glassbox.runtime.context_models import WorkingSetSnapshot
from glassbox.services import SessionRepository

_DEFAULT_WORKING_SET_LIMIT = 8
_WORKING_SET_SIGNAL_PRIORITY = {
    "approval": 100,
    "tool_request_test_path": 92,
    "tool_request_path": 90,
    "tool_artifact": 80,
    "runtime_note": 70,
    "inherited_runtime_note": 60,
    "tool_call": 50,
    "lineage": 40,
}


def build_working_set_snapshot(
    session_repository: SessionRepository,
    session_id: SessionId,
    *,
    item_limit: int = _DEFAULT_WORKING_SET_LIMIT,
) -> WorkingSetSnapshot:
    """Derive a bounded working set from explicit session state and events."""

    session = session_repository.get_session(session_id)
    if session is None:
        raise ValueError(f"unknown session_id: {session_id}")

    working_items: dict[tuple[str, str], _WorkingSetCandidate] = {}
    insertion_counter = 0

    def register_candidate(
        *,
        subject_kind: str,
        subject: str,
        summary: str,
        reason: str,
        signal_type: str,
        inherited: bool = False,
        recency_offset: int = 0,
    ) -> None:
        nonlocal insertion_counter
        normalized_subject = subject.strip()
        if normalized_subject == "":
            return

        key = (subject_kind, normalized_subject.casefold())
        candidate = working_items.get(key)
        score = _WORKING_SET_SIGNAL_PRIORITY[signal_type] - recency_offset
        if candidate is None:
            working_items[key] = _WorkingSetCandidate(
                item=WorkingSetItemSnapshot(
                    subject_kind=subject_kind,
                    subject=normalized_subject,
                    summary=summary,
                    reasons=[reason],
                    signal_types=[signal_type],
                    inherited=inherited,
                ),
                score=score,
                first_seen=insertion_counter,
            )
            insertion_counter += 1
            return

        candidate.score = max(candidate.score, score)
        candidate.item.summary = candidate.item.summary or summary
        candidate.item.inherited = candidate.item.inherited and inherited
        if reason not in candidate.item.reasons:
            candidate.item.reasons.append(reason)
        if signal_type not in candidate.item.signal_types:
            candidate.item.signal_types.append(signal_type)

    recent_events = list(reversed(session_repository.read_session_events(session_id)))
    for recency_offset, event in enumerate(recent_events):
        payload = event.payload
        if isinstance(payload, ModelToolCallRequested):
            _register_tool_request_candidates(
                payload,
                register_candidate,
                recency_offset=recency_offset,
            )
            continue
        if (
            isinstance(payload, ToolArtifactRecorded)
            and payload.path
            and _include_artifact_in_working_set(payload.artifact_kind)
        ):
            register_candidate(
                subject_kind="artifact",
                subject=payload.path,
                summary=_artifact_summary(payload.artifact_kind),
                reason=(f"{payload.artifact_kind} artifact recorded at {payload.path}"),
                signal_type="tool_artifact",
                recency_offset=recency_offset,
            )

    recent_approvals = sorted(
        session_repository.list_approvals(session_id),
        key=lambda approval: approval.requested_at,
        reverse=True,
    )
    for recency_offset, approval in enumerate(recent_approvals):
        register_candidate(
            subject_kind="approval",
            subject=approval.subject,
            summary=(
                "pending approval focus"
                if approval.status == ApprovalStatus.PENDING
                else "recent approval context"
            ),
            reason=_approval_reason(approval),
            signal_type="approval",
            recency_offset=recency_offset,
        )

    runtime_notes = sorted(
        session_repository.list_runtime_notes(session_id),
        key=lambda note: note.created_at,
        reverse=True,
    )
    for recency_offset, note in enumerate(runtime_notes):
        inherited = note.inherited
        register_candidate(
            subject_kind="note",
            subject=f"[{note.category}] {note.message}",
            summary=("inherited runtime note" if inherited else "runtime note"),
            reason=_runtime_note_reason(note),
            signal_type=("inherited_runtime_note" if inherited else "runtime_note"),
            inherited=inherited,
            recency_offset=recency_offset,
        )

    recent_tool_calls = sorted(
        session_repository.list_tool_calls(session_id),
        key=_tool_call_sort_key,
        reverse=True,
    )
    for recency_offset, tool_call in enumerate(recent_tool_calls):
        if (
            tool_call.status == ToolExecutionStatus.SUCCEEDED
            and tool_call.summary is None
        ):
            continue
        register_candidate(
            subject_kind="tool",
            subject=tool_call.tool_name,
            summary="recent tool execution",
            reason=_tool_call_reason(tool_call),
            signal_type="tool_call",
            recency_offset=recency_offset,
        )

    if session.parent_session_id is not None:
        lineage_subject = (
            session.branch_label
            if session.branch_label is not None
            else f"parent {str(session.parent_session_id)[:8]}"
        )
        register_candidate(
            subject_kind="branch",
            subject=lineage_subject,
            summary="inherited branch context",
            reason=_lineage_reason(session),
            signal_type="lineage",
            inherited=True,
        )

    ordered_candidates = sorted(
        working_items.values(),
        key=lambda candidate: (
            -candidate.score,
            candidate.first_seen,
            candidate.item.subject,
        ),
    )
    limited_candidates = ordered_candidates[:item_limit]

    return WorkingSetSnapshot(
        items=[candidate.item for candidate in limited_candidates],
        additional_item_count=max(len(ordered_candidates) - len(limited_candidates), 0),
    )


@dataclass(slots=True)
class _WorkingSetCandidate:
    item: WorkingSetItemSnapshot
    score: int
    first_seen: int


def _register_tool_request_candidates(
    payload: ModelToolCallRequested,
    register_candidate,
    *,
    recency_offset: int,
) -> None:
    arguments = _decode_tool_arguments(payload.arguments_json)
    if payload.tool_name == "run_tests":
        for raw_path in _string_list(arguments.get("paths")):
            register_candidate(
                subject_kind="test",
                subject=raw_path,
                summary="recent test target",
                reason=f"run_tests targeted {raw_path}",
                signal_type="tool_request_test_path",
                recency_offset=recency_offset,
            )
        return

    for raw_path in _extract_path_arguments(arguments):
        register_candidate(
            subject_kind="file",
            subject=raw_path,
            summary="recently targeted workspace path",
            reason=f"{payload.tool_name} targeted {raw_path}",
            signal_type="tool_request_path",
            recency_offset=recency_offset,
        )


def _decode_tool_arguments(arguments_json: str) -> dict[str, object]:
    try:
        decoded = json.loads(arguments_json)
    except json.JSONDecodeError:
        return {}
    if not isinstance(decoded, dict):
        return {}
    return {str(key): value for key, value in decoded.items()}


def _extract_path_arguments(arguments: dict[str, object]) -> list[str]:
    extracted_paths: list[str] = []
    for key in ("path", "paths"):
        value = arguments.get(key)
        extracted_paths.extend(_string_list(value))
    return extracted_paths


def _string_list(value: object) -> list[str]:
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [
            item.strip()
            for item in value
            if isinstance(item, str) and item.strip() != ""
        ]
    return []


def _artifact_summary(artifact_kind: str) -> str:
    if "test" in artifact_kind.casefold() or "pytest" in artifact_kind.casefold():
        return "recent test artifact"
    return "recent artifact"


def _include_artifact_in_working_set(artifact_kind: str) -> bool:
    return not artifact_kind.startswith("tool_output_")


def _approval_reason(approval: ApprovalRecord) -> str:
    status_text = "pending" if approval.status == ApprovalStatus.PENDING else "resolved"
    return f"{status_text} approval: {approval.reason}"


def _runtime_note_reason(note: RuntimeNoteRecord) -> str:
    note_prefix = "inherited runtime note" if note.inherited else "runtime note"
    return f"{note_prefix} [{note.category}] {note.message}"


def _tool_call_reason(tool_call: ToolCallRecord) -> str:
    summary = tool_call.summary or tool_call.status.value.replace("_", " ")
    return f"{tool_call.tool_name}: {summary}"


def _lineage_reason(session: SessionRecord) -> str:
    parent_prefix = (
        str(session.parent_session_id)[:8]
        if session.parent_session_id is not None
        else "unknown"
    )
    if session.branch_label is not None:
        return f"branch '{session.branch_label}' inherited from {parent_prefix}"
    return f"session inherited branch context from {parent_prefix}"


def _tool_call_sort_key(tool_call: ToolCallRecord):
    timestamp = tool_call.completed_at or tool_call.started_at
    return (timestamp is not None, timestamp or datetime.min.replace(tzinfo=UTC))
