"""Tests for the v10 context compaction artifact contract."""

from collections.abc import Sequence
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from glassbox.core import ContextCompactionScope
from glassbox.core import EventEnvelope
from glassbox.core import RuntimeNoteRecorded
from glassbox.core import SessionRecord
from glassbox.core import SessionStatus
from glassbox.core import new_context_compaction_id
from glassbox.core import new_session_id
from glassbox.runtime.context_compaction import CONTEXT_COMPACTION_ARTIFACT_KIND
from glassbox.runtime.context_compaction import CONTEXT_COMPACTION_SOURCE_REFERENCE_CAP
from glassbox.runtime.context_compaction import ContextCompactionArtifact
from glassbox.runtime.context_compaction import ContextCompactionEvidenceItem
from glassbox.runtime.context_compaction import ContextCompactionSourceReference
from glassbox.runtime.context_compaction_service import ContextCompactionRangeError
from glassbox.runtime.context_compaction_service import (
    create_deterministic_context_compaction,
)
from glassbox.services import ArtifactRepository
from glassbox.services import SessionRepository


def test_context_compaction_artifact_preserves_provenance_contract() -> None:
    artifact = ContextCompactionArtifact(
        compaction_id=new_context_compaction_id(),
        session_id=new_session_id(),
        scope=ContextCompactionScope.TRANSCRIPT,
        source_start_sequence=1,
        source_end_sequence=8,
        transcript_start_sequence=1,
        transcript_end_sequence=6,
        created_at=datetime(2026, 4, 30, 12, 0, tzinfo=UTC),
        summary="The operator approved the patch and verification is pending.",
        source_references=[
            ContextCompactionSourceReference(
                source_type="event",
                label="approval-event",
                sequence=4,
            ),
            ContextCompactionSourceReference(
                source_type="artifact",
                label="pytest-output",
                artifact_path=".glassbox/artifacts/pytest.txt",
            ),
        ],
        decisions=[
            ContextCompactionEvidenceItem(
                summary="Use the checkpoint projection as handoff evidence.",
                source_refs=["approval-event"],
            )
        ],
        verification_state=[
            ContextCompactionEvidenceItem(
                summary="Focused tests still need to run.",
                source_refs=["pytest-output"],
            )
        ],
        touched_files=["src/glassbox/runtime/context_compaction.py"],
        limitations=["Raw transcript text is omitted."],
    )

    assert artifact.artifact_kind == CONTEXT_COMPACTION_ARTIFACT_KIND
    assert artifact.schema_version == 1
    assert artifact.source_start_sequence == 1
    assert artifact.decisions[0].source_refs == ["approval-event"]


def test_context_compaction_artifact_requires_source_references() -> None:
    with pytest.raises(ValidationError, match="source_references"):
        ContextCompactionArtifact(
            compaction_id=new_context_compaction_id(),
            session_id=new_session_id(),
            scope=ContextCompactionScope.TRANSCRIPT,
            source_start_sequence=1,
            source_end_sequence=2,
            created_at=datetime(2026, 4, 30, 12, 0, tzinfo=UTC),
            summary="Missing source references is invalid.",
            source_references=[],
        )


def test_context_compaction_artifact_rejects_unresolved_source_refs() -> None:
    with pytest.raises(ValidationError, match="source_refs must reference"):
        ContextCompactionArtifact(
            compaction_id=new_context_compaction_id(),
            session_id=new_session_id(),
            scope=ContextCompactionScope.TASK,
            source_start_sequence=1,
            source_end_sequence=2,
            created_at=datetime(2026, 4, 30, 12, 0, tzinfo=UTC),
            summary="Decision references missing provenance.",
            source_references=[
                ContextCompactionSourceReference(
                    source_type="event",
                    label="known-event",
                    sequence=1,
                )
            ],
            decisions=[
                ContextCompactionEvidenceItem(
                    summary="Use the compacted decision.",
                    source_refs=["missing-event"],
                )
            ],
        )


def test_deterministic_compaction_rejects_source_ranges_over_reference_cap() -> None:
    session_id = new_session_id()
    source_events = [
        EventEnvelope(
            session_id=session_id,
            sequence=sequence,
            payload=RuntimeNoteRecorded(
                category="audit",
                message=f"source event {sequence}",
            ),
        )
        for sequence in range(1, CONTEXT_COMPACTION_SOURCE_REFERENCE_CAP + 6)
    ]
    session_repository = _CompactionSessionRepository(session_id, source_events)

    with pytest.raises(ContextCompactionRangeError) as exc_info:
        create_deterministic_context_compaction(
            cast(SessionRepository, session_repository),
            cast(ArtifactRepository, object()),
            session_id,
            scope=ContextCompactionScope.TRANSCRIPT,
        )

    error = exc_info.value
    payload = error.to_json_payload()

    assert error.selected_event_count == CONTEXT_COMPACTION_SOURCE_REFERENCE_CAP + 5
    assert error.source_reference_cap == CONTEXT_COMPACTION_SOURCE_REFERENCE_CAP
    assert "source_range_exceeds_cap" == payload["error"]
    assert payload["suggested_ranges"] == [
        {
            "label": "first",
            "source_start_sequence": 1,
            "source_end_sequence": CONTEXT_COMPACTION_SOURCE_REFERENCE_CAP,
            "selected_event_count": CONTEXT_COMPACTION_SOURCE_REFERENCE_CAP,
        },
        {
            "label": "latest",
            "source_start_sequence": 6,
            "source_end_sequence": CONTEXT_COMPACTION_SOURCE_REFERENCE_CAP + 5,
            "selected_event_count": CONTEXT_COMPACTION_SOURCE_REFERENCE_CAP,
        },
    ]
    assert "Retry with a bounded range" in str(error)


class _CompactionSessionRepository:
    def __init__(
        self,
        session_id,
        source_events: Sequence[EventEnvelope],
    ) -> None:
        self._session_id = session_id
        self._source_events = list(source_events)

    def get_session(self, session_id):
        if session_id != self._session_id:
            return None
        timestamp = datetime(2026, 4, 30, 12, 0, tzinfo=UTC)
        return SessionRecord(
            session_id=session_id,
            status=SessionStatus.COMPLETED,
            created_at=timestamp,
            updated_at=timestamp,
            cwd=Path("."),
            model_name="local-test-model",
            approval_mode="review",
            last_sequence=len(self._source_events),
        )

    def read_session_events(self, session_id):
        if session_id != self._session_id:
            return []
        return list(self._source_events)
