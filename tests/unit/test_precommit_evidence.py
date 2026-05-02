"""Tests for retained pre-commit/eval evidence state mapping."""

from glassbox.core import ChangesetReadinessState
from glassbox.runtime.precommit_evidence import precommit_evidence_readiness_state


def test_precommit_evidence_readiness_state_mapping() -> None:
    assert precommit_evidence_readiness_state("passed") == ChangesetReadinessState.READY
    assert (
        precommit_evidence_readiness_state("failed")
        == ChangesetReadinessState.FAILED_CHECKS
    )
    assert (
        precommit_evidence_readiness_state("stale")
        == ChangesetReadinessState.STALE_INVENTORY
    )
    assert (
        precommit_evidence_readiness_state("missing")
        == ChangesetReadinessState.NEEDS_VERIFICATION
    )
