"""Unit tests for v17 local handoff core contracts."""

from datetime import UTC
from datetime import datetime

import pytest
from pydantic import ValidationError

import glassbox.core.models as core_models
import glassbox.core.types as core_types
from glassbox.core import HandoffCompatibilityState
from glassbox.core import HandoffCompatibilitySummary
from glassbox.core import HandoffEvidenceFreshness
from glassbox.core import HandoffIntent
from glassbox.core import HandoffLabel
from glassbox.core import HandoffLabelMetadataPosture
from glassbox.core import HandoffLocalOnlyEvidenceItem
from glassbox.core import HandoffLocalOnlyInventory
from glassbox.core import HandoffLocalOnlySummary
from glassbox.core import HandoffPackageKind
from glassbox.core import HandoffPackageManifest
from glassbox.core import HandoffPackageV2
from glassbox.core import HandoffReadiness
from glassbox.core import HandoffReadinessReason
from glassbox.core import HandoffReadinessReasonKind
from glassbox.core import HandoffReadinessState
from glassbox.core import HandoffRedactionPosture
from glassbox.core import HandoffRedactionSummary
from glassbox.core import HandoffSafeCommand
from glassbox.core import HandoffSourceKind
from glassbox.core import HandoffSourceRef
from glassbox.core.models_handoff import HandoffPackageManifest as OwnerManifest
from glassbox.core.types_handoff import HandoffIntent as OwnerIntent
from glassbox.runtime.handoff_source_resolution import HandoffSourceResolutionError
from glassbox.runtime.handoff_source_resolution import resolve_handoff_prepare_source
from glassbox.runtime.handoff_source_resolution import resolve_handoff_source


def _source() -> HandoffSourceRef:
    return HandoffSourceRef(
        kind=HandoffSourceKind.SESSION,
        primary_id="session-123",
        identifiers={"cwd_digest": "abc123"},
        label="implementation session",
    )


def _safe_command() -> HandoffSafeCommand:
    return HandoffSafeCommand(
        command=["glassbox", "session", "show", "session-123"],
        display="glassbox session show session-123",
        purpose="Inspect the imported session without resuming it.",
    )


def test_handoff_models_and_types_keep_core_compatibility_exports() -> None:
    assert HandoffPackageManifest is OwnerManifest
    assert core_models.HandoffPackageManifest is OwnerManifest
    assert core_models.HandoffPackageV2 is HandoffPackageV2
    assert HandoffIntent is OwnerIntent
    assert core_types.HandoffIntent is OwnerIntent


def test_handoff_source_resolution_normalizes_supported_sources() -> None:
    session = resolve_handoff_source(" Session ", " session-123 ")
    workspace = resolve_handoff_source("workspace")
    prepare = resolve_handoff_prepare_source("changeset")

    assert session.source_kind == "session"
    assert session.require_source_id() == "session-123"
    assert session.source_id_required is True
    assert workspace.source_kind == "workspace"
    assert workspace.source_id is None
    assert workspace.source_id_required is False
    assert prepare.source_kind == "changeset"


def test_handoff_source_resolution_rejects_unsupported_sources() -> None:
    with pytest.raises(HandoffSourceResolutionError) as missing_id:
        resolve_handoff_source("task")
    with pytest.raises(HandoffSourceResolutionError) as unsupported:
        resolve_handoff_source("database")
    with pytest.raises(HandoffSourceResolutionError) as prepare_unsupported:
        resolve_handoff_prepare_source("workspace")

    assert missing_id.value.reason == "missing-source-id"
    assert str(missing_id.value) == "source_id is required"
    assert unsupported.value.reason == "unsupported-source-kind"
    assert str(unsupported.value) == "unsupported handoff source"
    assert prepare_unsupported.value.reason == "unsupported-source-kind"


def test_handoff_package_manifest_serializes_default_non_claims() -> None:
    readiness = HandoffReadiness(
        source=_source(),
        intent=HandoffIntent.REVIEW_ONLY,
        state=HandoffReadinessState.READY,
        freshness=HandoffEvidenceFreshness.FRESH,
        safe_first_commands=[_safe_command()],
    )
    manifest = HandoffPackageManifest(
        package_kind=HandoffPackageKind.SESSION,
        source=_source(),
        generated_at=datetime(2026, 5, 14, tzinfo=UTC),
        intent=HandoffIntent.REVIEW_ONLY,
        exported_by=HandoffLabel(label="local operator"),
        readiness=readiness,
        included_sections=["manifest", "handoff.summary"],
        redaction=HandoffRedactionSummary(
            posture=HandoffRedactionPosture.REVIEWER_SAFE,
            redacted_field_count=3,
            redacted_categories=["secret-like-value", "local-path"],
        ),
        safe_inspection_commands=[_safe_command()],
    )

    restored = HandoffPackageManifest.model_validate(manifest.model_dump(mode="python"))

    assert restored == manifest
    assert restored.schema_version == "glassbox-handoff-package.v2"
    assert "handoff does not grant continuation authority" in restored.non_claims
    assert restored.redaction.raw_logs_included is False


def test_handoff_manifest_rejects_mismatched_readiness_intent() -> None:
    readiness = HandoffReadiness(
        source=_source(),
        intent=HandoffIntent.REVIEW_ONLY,
        state=HandoffReadinessState.READY,
    )

    with pytest.raises(ValidationError, match="manifest intent must match"):
        HandoffPackageManifest(
            package_kind=HandoffPackageKind.SESSION,
            source=_source(),
            generated_at=datetime(2026, 5, 14, tzinfo=UTC),
            intent=HandoffIntent.CONTINUE_WORK,
            readiness=readiness,
        )


def test_label_local_only_metadata_requires_matching_posture() -> None:
    with pytest.raises(ValidationError, match="local-only metadata posture"):
        HandoffLabel(label="alice", local_only_metadata=True)

    label = HandoffLabel(
        label="alice",
        local_only_metadata=True,
        metadata_posture=HandoffLabelMetadataPosture.LOCAL_ONLY,
    )

    assert label.local_only_metadata is True


def test_readiness_requires_local_only_details_for_local_only_state() -> None:
    with pytest.raises(ValidationError, match="local_only_evidence"):
        HandoffReadiness(
            source=_source(),
            intent=HandoffIntent.CONTINUE_WORK,
            state=HandoffReadinessState.LOCAL_ONLY_EVIDENCE,
        )

    readiness = HandoffReadiness(
        source=_source(),
        intent=HandoffIntent.CONTINUE_WORK,
        state=HandoffReadinessState.LOCAL_ONLY_EVIDENCE,
        local_only_evidence=[
            HandoffReadinessReason(
                kind=HandoffReadinessReasonKind.LOCAL_ONLY_EVIDENCE,
                summary="Raw command logs were retained locally and not exported.",
                portable=False,
            )
        ],
    )

    assert readiness.local_only_evidence[0].portable is False


def test_unsupported_compatibility_state_requires_explanation() -> None:
    with pytest.raises(ValidationError, match="unsupported compatibility states"):
        HandoffCompatibilitySummary(state=HandoffCompatibilityState.FUTURE_VERSION)

    summary = HandoffCompatibilitySummary(
        state=HandoffCompatibilityState.FUTURE_VERSION,
        unsupported_values=["schema_version=glassbox-handoff-manifest.v99"],
        warnings=["Inspect with a newer Glassbox before trusting package contents."],
    )

    assert summary.state == HandoffCompatibilityState.FUTURE_VERSION


def test_unknown_enum_values_are_rejected_not_silently_mapped() -> None:
    payload = {
        "package_kind": "session-handoff",
        "source": {"kind": "session", "primary_id": "session-123"},
        "generated_at": datetime(2026, 5, 14, tzinfo=UTC),
        "intent": "continue-with-admin-rights",
    }

    with pytest.raises(ValidationError):
        HandoffPackageManifest.model_validate(payload)


def test_safe_command_is_read_only() -> None:
    with pytest.raises(ValidationError, match="safe commands must be read-only"):
        HandoffSafeCommand(
            command=["glassbox", "session", "resume", "session-123"],
            display="glassbox session resume session-123",
            purpose="Resume work.",
            read_only=False,
        )


def test_local_only_summary_keeps_contents_out_of_categories() -> None:
    summary = HandoffLocalOnlySummary(
        category_counts={"raw-command-log": 2, "screenshot": 1},
        affected_claim_ids=["claim.verify-tests"],
        limitations=["Recipient cannot inspect omitted raw logs from the package."],
        safe_local_inspection_commands=[_safe_command()],
    )

    assert summary.category_counts["raw-command-log"] == 2
    assert summary.safe_local_inspection_commands[0].read_only is True


def test_local_only_inventory_groups_counts_without_contents() -> None:
    inventory = HandoffLocalOnlyInventory(
        source=_source(),
        intent=HandoffIntent.REVIEW_ONLY,
        items=[
            HandoffLocalOnlyEvidenceItem(
                category="raw-command-log",
                count=2,
                summary="Two command logs remain local-only.",
                affected_claim_ids=["claim.verify-tests"],
                recipient_limitation=(
                    "Recipient cannot inspect raw logs from the package."
                ),
                safe_local_inspection_commands=[_safe_command()],
            ),
            HandoffLocalOnlyEvidenceItem(
                category="screenshot",
                summary="Screenshot stays local.",
                recipient_limitation=(
                    "Recipient cannot inspect screenshots from the package."
                ),
            ),
        ],
        limitations=["Raw evidence must be inspected in the source workspace."],
    )

    assert inventory.total_count == 3
    assert inventory.category_counts == {"raw-command-log": 2, "screenshot": 1}
    assert inventory.items[0].affected_claim_ids == ["claim.verify-tests"]


def test_local_only_inventory_item_rejects_portable_claim() -> None:
    with pytest.raises(ValidationError, match="must not be portable"):
        HandoffLocalOnlyEvidenceItem(
            category="raw-command-log",
            summary="Command log is local.",
            recipient_limitation="Recipient cannot inspect it from the package.",
            portable=True,
        )
