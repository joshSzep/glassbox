"""Unit tests for changeset source derivation."""

from datetime import UTC
from datetime import datetime
from pathlib import Path

import pytest

from glassbox.core import BranchCandidateRecord
from glassbox.core import BranchCandidateStatus
from glassbox.core import BranchCandidateVerificationStatus
from glassbox.core import BranchSearchRecord
from glassbox.core import BranchSearchStatus
from glassbox.core import ChangesetSourceAttached
from glassbox.core import EventEnvelope
from glassbox.core import ProjectionHealth
from glassbox.core import SessionRecord
from glassbox.core import SessionState
from glassbox.core import SessionStatus
from glassbox.core import TaskPlanStatus
from glassbox.core import TaskRecord
from glassbox.core import new_branch_candidate_id
from glassbox.core import new_branch_search_id
from glassbox.core import new_session_id
from glassbox.core import new_task_id
from glassbox.runtime.changesets import ChangesetDerivationService


class FakeChangesetRepository:
    def __init__(self) -> None:
        self.session_id = new_session_id()
        now = datetime.now(UTC)
        self.session = SessionRecord(
            session_id=self.session_id,
            status=SessionStatus.RUNNING,
            created_at=now,
            updated_at=now,
            cwd=Path("/tmp/glassbox"),
            model_name="openai:gpt-5.4",
            approval_mode="confirm",
        )
        self.state: SessionState | None = SessionState(
            session_id=self.session_id,
            status=SessionStatus.RUNNING,
        )
        self.health = ProjectionHealth(
            state="ok",
            canonical_last_sequence=0,
            projected_last_sequence=0,
        )
        self.task_id = new_task_id()
        self.task = TaskRecord(
            task_id=self.task_id,
            session_id=self.session_id,
            title="Add query surface",
            goal="Make changeset evidence queryable",
            status=TaskPlanStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            last_sequence=1,
        )
        self.search_id = new_branch_search_id()
        self.candidate_id = new_branch_candidate_id()
        self.other_candidate_id = new_branch_candidate_id()
        self.search = BranchSearchRecord(
            search_id=self.search_id,
            session_id=self.session_id,
            parent_session_id=self.session_id,
            status=BranchSearchStatus.COMPLETED,
            objective="try variants",
            selected_candidate_id=self.candidate_id,
            candidate_count=1,
            created_at=now,
            updated_at=now,
            last_sequence=3,
        )
        self.candidates = [
            BranchCandidateRecord(
                search_id=self.search_id,
                candidate_id=self.candidate_id,
                parent_session_id=self.session_id,
                candidate_session_id=new_session_id(),
                strategy_label="smallest diff",
                status=BranchCandidateStatus.SELECTED,
                verification_status=BranchCandidateVerificationStatus.PASSED,
                selection_state=BranchCandidateStatus.SELECTED,
                verification_summary="tests passed",
                created_at=now,
                updated_at=now,
                last_sequence=3,
            )
        ]
        self.events: list[EventEnvelope] = []

    def get_session(self, session_id):
        return self.session if session_id == self.session_id else None

    def get_session_state(self, session_id):
        return self.state if session_id == self.session_id else None

    def inspect_session_projection_health(self, session_id):
        return self.health

    def get_task(self, task_id):
        return self.task if task_id == self.task_id else None

    def get_branch_search(self, search_id):
        return self.search if search_id == self.search_id else None

    def list_branch_candidates(self, session_id, search_id):
        return list(self.candidates)

    def append_events(self, events):
        stored = [
            event.model_copy(update={"sequence": len(self.events) + index})
            for index, event in enumerate(events, start=1)
        ]
        self.events.extend(stored)
        return stored


def test_changeset_derivation_records_degraded_task_limitations() -> None:
    repository = FakeChangesetRepository()
    repository.state = None
    repository.health = ProjectionHealth(
        state="stale",
        canonical_last_sequence=5,
        projected_last_sequence=3,
        degraded=True,
        detail="session_state projection is 2 event(s) behind",
    )

    result = ChangesetDerivationService(repository).create_from_task(repository.task_id)

    assert result.limitations == [
        "session state projection is unavailable",
        "projection health is stale: session_state projection is 2 event(s) behind",
        "task is active, not terminal",
    ]
    assert [event.event_type for event in result.stored_events] == [
        "ChangesetCreated",
        "ChangesetSourceAttached",
    ]
    source_payload = result.stored_events[1].payload
    assert isinstance(source_payload, ChangesetSourceAttached)
    assert source_payload.limitation is not None


def test_changeset_derivation_requires_selected_branch_candidate() -> None:
    repository = FakeChangesetRepository()

    with pytest.raises(ValueError, match="not selected"):
        ChangesetDerivationService(repository).create_from_branch_candidate(
            repository.search_id,
            repository.other_candidate_id,
        )
