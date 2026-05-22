"""Unit tests for handoff redaction preview helpers."""

from glassbox.core import HandoffIntent
from glassbox.core import HandoffLocalOnlySummary
from glassbox.core import HandoffPackageKind
from glassbox.core import HandoffSafeCommand
from glassbox.core import HandoffSourceKind
from glassbox.core import HandoffSourceRef
from glassbox.runtime.handoff_export_profiles import build_handoff_export_profile
from glassbox.runtime.handoff_export_profiles import parse_handoff_intent
from glassbox.runtime.handoff_local_only_inventory import build_local_only_inventory
from glassbox.runtime.handoff_redaction_preview import _redaction_marker_summary


def test_redaction_preview_detects_workspace_and_secret_markers() -> None:
    count, categories = _redaction_marker_summary(
        {
            "cwd": "<workspace-root>/project",
            "note": "OPENAI_API_KEY=<redacted>",
            "nested": ["safe", {"path": "<workspace-root>/logs/output.txt"}],
        }
    )

    assert count == 3
    assert categories == ["workspace-path", "secret-like-token"]


def test_local_only_inventory_builder_links_affected_claims() -> None:
    inventory = build_local_only_inventory(
        source=HandoffSourceRef(
            kind=HandoffSourceKind.CHANGESET,
            primary_id="chg-123",
        ),
        intent=HandoffIntent.REVIEW_ONLY,
        summary=HandoffLocalOnlySummary(
            category_counts={"manual_evidence": 2},
            affected_claim_ids=["claim.review"],
            safe_local_inspection_commands=[
                HandoffSafeCommand(
                    command=["glassbox", "changeset", "evidence", "list", "chg-123"],
                    display="glassbox changeset evidence list chg-123",
                    purpose="Inspect local evidence.",
                )
            ],
        ),
        omitted_raw_categories=["raw screenshots"],
        affected_claim_ids_by_category={
            "manual_evidence": ["claim.manual"],
            "raw screenshots": ["claim.browser"],
        },
    )

    assert inventory.total_count == 3
    assert inventory.category_counts["manual_evidence"] == 2
    assert inventory.items[0].reason == "manual-only-evidence"
    assert inventory.items[0].affected_claim_ids == ["claim.review", "claim.manual"]
    assert inventory.items[1].category == "raw screenshots"
    assert inventory.items[1].affected_claim_ids == ["claim.browser"]
    assert inventory.safe_local_inspection_commands[0].read_only is True
    assert inventory.safe_local_inspection_commands[0].requires_policy_approval is False


def test_handoff_export_profile_is_intent_specific() -> None:
    profile = build_handoff_export_profile(
        source=HandoffSourceRef(
            kind=HandoffSourceKind.SESSION,
            primary_id="session-123",
        ),
        package_kind=HandoffPackageKind.SESSION,
        intent=HandoffIntent.CONTINUE_WORK,
        output_format="json",
    )

    assert profile.profile_id == HandoffIntent.CONTINUE_WORK
    assert "continuation_posture" in profile.required_sections
    assert "local policy approval" in " ".join(profile.non_claims)
    assert profile.safe_inspection_commands[0].read_only is True


def test_parse_handoff_intent_rejects_unknown_profile() -> None:
    try:
        parse_handoff_intent("continue-with-admin-rights")
    except ValueError as exc:
        assert "unsupported handoff intent" in str(exc)
        assert "continue-work" in str(exc)
    else:
        raise AssertionError("unknown handoff intent should fail")
