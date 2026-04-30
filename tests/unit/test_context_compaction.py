"""Tests for the v10 context compaction artifact contract."""

from datetime import UTC
from datetime import datetime

import pytest
from pydantic import ValidationError

from glassbox.core import ContextCompactionScope
from glassbox.core import new_context_compaction_id
from glassbox.core import new_session_id
from glassbox.runtime.context_compaction import CONTEXT_COMPACTION_ARTIFACT_KIND
from glassbox.runtime.context_compaction import ContextCompactionArtifact
from glassbox.runtime.context_compaction import ContextCompactionEvidenceItem
from glassbox.runtime.context_compaction import ContextCompactionSourceReference


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
