"""Unit tests for shared Glassbox core types."""

from uuid import UUID

import pytest
from pydantic import TypeAdapter
from pydantic import ValidationError

from glassbox.core import ApprovalDecision
from glassbox.core import ApprovalMode
from glassbox.core import ApprovalStatus
from glassbox.core import SessionStatus
from glassbox.core import ToolExecutionStatus
from glassbox.core import TurnStatus
from glassbox.core import new_approval_id
from glassbox.core import new_artifact_id
from glassbox.core import new_event_id
from glassbox.core import new_message_id
from glassbox.core import new_session_id
from glassbox.core import new_tool_call_id
from glassbox.core import new_turn_id


@pytest.mark.parametrize(
    ("adapter_type", "raw_value", "expected"),
    [
        (SessionStatus, "running", SessionStatus.RUNNING),
        (TurnStatus, "cancelled", TurnStatus.CANCELLED),
        (ToolExecutionStatus, "authorized", ToolExecutionStatus.AUTHORIZED),
        (ApprovalStatus, "pending", ApprovalStatus.PENDING),
        (ApprovalMode, "confirm", ApprovalMode.CONFIRM),
        (ApprovalDecision, "approved", ApprovalDecision.APPROVED),
    ],
)
def test_state_types_validate_from_strings(
    adapter_type: type[object],
    raw_value: str,
    expected: object,
) -> None:
    adapter = TypeAdapter(adapter_type)

    assert adapter.validate_python(raw_value) == expected
    assert adapter.dump_python(expected) == raw_value


@pytest.mark.parametrize(
    ("adapter_type", "raw_value"),
    [
        (SessionStatus, "paused"),
        (TurnStatus, "running"),
        (ToolExecutionStatus, "complete"),
        (ApprovalStatus, "awaiting"),
        (ApprovalMode, "manual"),
        (ApprovalDecision, "pending"),
    ],
)
def test_state_types_reject_invalid_values(
    adapter_type: type[object],
    raw_value: str,
) -> None:
    adapter = TypeAdapter(adapter_type)

    with pytest.raises(ValidationError):
        adapter.validate_python(raw_value)


def test_identifier_factories_return_uuids() -> None:
    generated_ids = [
        new_session_id(),
        new_turn_id(),
        new_message_id(),
        new_tool_call_id(),
        new_approval_id(),
        new_event_id(),
        new_artifact_id(),
    ]

    assert all(isinstance(identifier, UUID) for identifier in generated_ids)
    assert len(set(generated_ids)) == len(generated_ids)
