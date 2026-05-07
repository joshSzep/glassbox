"""Review-loop command guide section data."""

from glassbox.cli.command_guide_models import CommandGuideEntry
from glassbox.cli.command_guide_models import CommandGuideSection

REVIEW_LOOP_COMMAND_GUIDE_SECTION = CommandGuideSection(
    key="review-loop",
    title="Review Loop",
    summary=(
        "Inspect and continue local changeset review evidence without "
        "claiming approval or publishing mutations."
    ),
    entries=(
        CommandGuideEntry(
            "glassbox session chat --plain --cwd .",
            (
                "Use /review create from plain interactive mode when the "
                "TUI is unavailable."
            ),
        ),
        CommandGuideEntry(
            "glassbox changeset show CHANGESET_ID --cwd .",
            (
                "Inspect changeset evidence, feedback, verification, and "
                "safe next actions."
            ),
        ),
        CommandGuideEntry(
            "glassbox changeset verification-plan CHANGESET_ID --cwd .",
            "Preview review-loop-aware verification without running commands.",
        ),
        CommandGuideEntry(
            "glassbox changeset feedback status CHANGESET_ID --cwd .",
            (
                "Inspect response-linked fixup inventory posture, stale checks, "
                "blockers, accepted risks, and non-approval claims before "
                "recording fixup evidence."
            ),
        ),
        CommandGuideEntry(
            (
                "glassbox changeset feedback resolve FEEDBACK_ID "
                "--summary SUMMARY --cwd ."
            ),
            (
                "Record local response text; attach response-linked fixup "
                "inventory separately before treating the response as ready "
                "for handoff."
            ),
        ),
        CommandGuideEntry(
            (
                "glassbox changeset evidence attach CHANGESET_ID "
                "--summary SUMMARY --source-label LABEL --cwd ."
            ),
            "Attach manual evidence as local evidence, not retained command proof.",
        ),
        CommandGuideEntry(
            (
                "glassbox changeset evidence dashboard CHANGESET_ID "
                "--route ROUTE --viewport WIDTHxHEIGHT --skipped-case REASON "
                "--cwd ."
            ),
            (
                "Record advisory dashboard evidence or an explicit skipped case "
                "without calling it a pass."
            ),
        ),
        CommandGuideEntry(
            "glassbox changeset brief CHANGESET_ID --cwd .",
            (
                "Generate a reviewer-safe lifecycle brief after inspecting "
                "feedback, evidence, and verification posture."
            ),
        ),
        CommandGuideEntry(
            "glassbox changeset handoff-readiness CHANGESET_ID --cwd .",
            (
                "Inspect final handoff posture without staging, committing, "
                "pushing, or opening a PR."
            ),
        ),
    ),
)

__all__ = ["REVIEW_LOOP_COMMAND_GUIDE_SECTION"]
