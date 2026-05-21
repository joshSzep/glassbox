"""Local handoff command guide section data."""

from glassbox.cli.command_guide_models import CommandGuideEntry
from glassbox.cli.command_guide_models import CommandGuideSection

LOCAL_HANDOFF_COMMAND_GUIDE_SECTION = CommandGuideSection(
    key="local-handoff",
    title="Local Handoff",
    summary=(
        "Prepare, inspect, import, and record local handoff workflow state "
        "without implying approval or publication."
    ),
    entries=(
        CommandGuideEntry(
            "glassbox handoff prepare session SESSION_ID handoff.json --cwd .",
            "Export a redacted session package through the unified handoff path.",
        ),
        CommandGuideEntry(
            (
                "glassbox handoff prepare changeset CHANGESET_ID "
                "changeset-review.json --cwd ."
            ),
            (
                "Export a reviewer-safe changeset handoff package with the "
                "shared recipient profile flags."
            ),
        ),
        CommandGuideEntry(
            "glassbox handoff inspect handoff.json --cwd .",
            (
                "Inspect compatibility, redaction posture, local-only gaps, "
                "safe first commands, and non-claims before import."
            ),
        ),
        CommandGuideEntry(
            "glassbox handoff import handoff.json --cwd .",
            "Import a supported session handoff as historical inspection state.",
        ),
        CommandGuideEntry(
            "glassbox handoff accept SESSION_ID PACKAGE_ID --cwd .",
            (
                "Record local custody acceptance without treating it as review, "
                "verification, or release approval."
            ),
        ),
        CommandGuideEntry(
            "glassbox handoff reject SESSION_ID PACKAGE_ID --reason REASON --cwd .",
            "Retain a rejection reason and safe next actions for the sender.",
        ),
        CommandGuideEntry(
            "/handoff readiness [SESSION_ID]",
            "Render compact session readiness commands from the full-screen TUI.",
        ),
        CommandGuideEntry(
            "/handoff preview [SESSION_ID]",
            ("Render redaction preview and export commands without writing a package."),
        ),
        CommandGuideEntry(
            "/handoff inspect handoff.json",
            "Render package inspection and import-triage commands from the TUI.",
        ),
        CommandGuideEntry(
            "/handoff custody SESSION_ID PACKAGE_ID",
            (
                "Render guidance, accept, reject, and archive commands without "
                "recording custody."
            ),
        ),
        CommandGuideEntry(
            "/handoff dashboard",
            "Open the local dashboard handoff cockpit when a dashboard is available.",
        ),
        CommandGuideEntry(
            "glassbox session export SESSION_ID handoff.json --cwd .",
            "Legacy session export remains a supported alias for handoff prepare.",
        ),
        CommandGuideEntry(
            "glassbox changeset export CHANGESET_ID changeset-review.json --cwd .",
            "Legacy changeset export remains the review-centered handoff path.",
        ),
    ),
)

__all__ = ["LOCAL_HANDOFF_COMMAND_GUIDE_SECTION"]
