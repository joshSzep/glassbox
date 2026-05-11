"""Review-loop command guide section data."""

from glassbox.cli.command_guide_models import CommandGuideEntry
from glassbox.cli.command_guide_models import CommandGuideSection

REVIEW_LOOP_COMMAND_GUIDE_SECTION = CommandGuideSection(
    key="review-loop",
    title="Review Loop Maturity",
    summary=(
        "Inspect, record, and hand off local changeset review evidence without "
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
            "glassbox changeset workup --session SESSION_ID --cwd .",
            (
                "Guide the local review path from preview through explicit "
                "create, refresh, verification disposition, brief, and handoff "
                "steps. Durable steps require confirmation flags such as "
                "--confirm-create, --confirm-refresh, or --confirm-brief."
            ),
        ),
        CommandGuideEntry(
            "glassbox changeset workup-preview --cwd .",
            (
                "Preview changed paths, candidate changeset grouping, "
                "verification plan, repository impact, review risks, memory "
                "cues, and safe next commands without creating changeset "
                "evidence or running commands."
            ),
        ),
        CommandGuideEntry(
            (
                "glassbox changeset create --from workspace-diff "
                "--objective OBJECTIVE --cwd ."
            ),
            (
                "Create local changeset evidence from the current workspace "
                "diff; this does not stage, commit, push, or open a PR."
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
            "glassbox changeset refresh CHANGESET_ID --cwd .",
            (
                "Refresh structured inventory evidence before relying on "
                "feedback, fixup, brief, or handoff posture."
            ),
        ),
        CommandGuideEntry(
            "glassbox changeset verification-plan CHANGESET_ID --cwd .",
            "Preview review-loop-aware verification without running commands.",
        ),
        CommandGuideEntry(
            (
                "glassbox changeset verification-select CHANGESET_ID "
                "--verification VERIFICATION_ID --cwd ."
            ),
            (
                "Record that the operator selected a previewed check; this "
                "does not run the command or mark it passed."
            ),
        ),
        CommandGuideEntry(
            (
                "glassbox changeset verification-run CHANGESET_ID "
                "--verification VERIFICATION_ID --confirm --cwd ."
            ),
            (
                "Run one explicitly selected command through local command "
                "policy and retained tool-attempt evidence."
            ),
        ),
        CommandGuideEntry(
            (
                "glassbox changeset verification-skip CHANGESET_ID "
                "--verification VERIFICATION_ID --reason REASON --cwd ."
            ),
            "Record an explicit skip as local evidence, not a pass.",
        ),
        CommandGuideEntry(
            (
                "glassbox changeset verification-accept-risk CHANGESET_ID "
                "--verification VERIFICATION_ID --reason REASON --risk RISK --cwd ."
            ),
            (
                "Record accepted residual risk for one planned check without "
                "turning it into release approval."
            ),
        ),
        CommandGuideEntry(
            "glassbox changeset evidence-graph CHANGESET_ID --summary --cwd .",
            (
                "Inspect claim support, stale evidence, missing evidence, "
                "manual-only support, and accepted risk without raw logs."
            ),
        ),
        CommandGuideEntry(
            (
                "glassbox changeset feedback add CHANGESET_ID "
                "--kind requested_change --summary SUMMARY --cwd ."
            ),
            (
                "Record local review feedback as evidence, not a hosted review "
                "decision or approval state."
            ),
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
            "glassbox changeset feedback fixup FEEDBACK_ID --cwd .",
            (
                "Record bounded response-linked fixup inventory from the current "
                "workspace or repeated --path values; this is evidence, not "
                "reviewer approval."
            ),
        ),
        CommandGuideEntry(
            (
                "glassbox changeset evidence attach CHANGESET_ID --kind "
                "external_check --summary SUMMARY --source-label LABEL --cwd ."
            ),
            "Attach manual evidence as local evidence, not retained command proof.",
        ),
        CommandGuideEntry(
            (
                "glassbox changeset evidence dashboard CHANGESET_ID "
                "--capture-state not_run --skip-reason REASON "
                "--skipped-case CASE --cwd ."
            ),
            (
                "Record an explicit skipped dashboard case without inventing a "
                "viewport or calling it a pass."
            ),
        ),
        CommandGuideEntry(
            (
                "glassbox changeset feedback accept-risk FEEDBACK_ID "
                "--risk-summary SUMMARY --reason REASON --cwd ."
            ),
            (
                "Record an explicit local residual-risk disposition when the "
                "response should not be treated as fully resolved."
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
