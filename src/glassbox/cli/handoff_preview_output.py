"""CLI rendering helpers for handoff redaction previews."""

from glassbox.runtime.handoff_redaction_preview import HandoffRedactionPreview


def print_handoff_redaction_preview(preview: HandoffRedactionPreview) -> None:
    """Print a compact human-readable redaction preview."""

    print(f"Redaction preview: {preview.source.kind.value}")
    if preview.source.primary_id is not None:
        print(f"Source: {preview.source.primary_id}")
    print(f"Intent: {preview.intent.value}")
    if preview.profile is not None:
        print(f"Profile: {preview.profile.profile_id.value}")
    print(
        "Sections: "
        f"{len(preview.included_sections)} included "
        f"({', '.join(preview.included_sections[:8])})"
    )
    print(
        "Redaction: "
        f"{preview.redaction.posture.value}, "
        f"{preview.redaction.redacted_field_count} redacted field(s)"
    )
    if preview.redaction.redacted_categories:
        print("Redacted categories:")
        for category in preview.redaction.redacted_categories:
            print(f"  - {category}")
    if preview.local_only.category_counts:
        print("Local-only evidence:")
        for category, count in preview.local_only.category_counts.items():
            print(f"  - {category}: {count}")
    if preview.local_only_inventory.items:
        print("Local-only inventory:")
        for item in preview.local_only_inventory.items[:10]:
            print(f"  - {item.category}: {item.count} ({item.reason.value})")
            print(f"    Limitation: {item.recipient_limitation}")
    if preview.omitted_raw_categories:
        print("Omitted raw categories:")
        for category in preview.omitted_raw_categories:
            print(f"  - {category}")
    if preview.unsupported_evidence:
        print("Unsupported evidence:")
        for item in preview.unsupported_evidence:
            print(f"  - {item}")
    if preview.package_limitations:
        print("Limitations:")
        for limitation in preview.package_limitations:
            print(f"  - {limitation}")
    if preview.safe_inspection_commands:
        print("Safe inspection commands:")
        for command in preview.safe_inspection_commands:
            print(f"  - {command.display}")


__all__ = ["print_handoff_redaction_preview"]
