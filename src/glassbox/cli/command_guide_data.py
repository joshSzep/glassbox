"""Workflow-oriented command guide section data."""

from glassbox.cli.command_guide_models import CommandGuideEntry
from glassbox.cli.command_guide_models import CommandGuideSection
from glassbox.cli.command_guide_review import REVIEW_LOOP_COMMAND_GUIDE_SECTION

COMMAND_GUIDE_SECTIONS: tuple[CommandGuideSection, ...] = (
    CommandGuideSection(
        key="start-work",
        title="Start Work",
        summary="Prepare a workspace and begin a local operator session.",
        entries=(
            CommandGuideEntry(
                "glassbox readiness check --cwd .",
                "Check first-run workspace readiness and get next actions.",
            ),
            CommandGuideEntry(
                "glassbox session chat --cwd .",
                "Start the default terminal session with dashboard handoff.",
            ),
            CommandGuideEntry(
                'glassbox session run "Inspect the repository" --cwd .',
                "Run a one-shot session when an interactive shell is unnecessary.",
            ),
            CommandGuideEntry(
                "glassbox dashboard serve --cwd .",
                "Serve the packaged dashboard when no chat process is hosting it.",
            ),
        ),
    ),
    CommandGuideSection(
        key="inspect-state",
        title="Inspect State",
        summary=("Read sessions, tasks, workspace health, and the dashboard cockpit."),
        entries=(
            CommandGuideEntry(
                "glassbox session list --cwd .",
                "List persisted sessions in the workspace.",
            ),
            CommandGuideEntry(
                "glassbox session status SESSION_ID --cwd .",
                (
                    "Inspect one session's transcript, actions, evidence, and "
                    "runtime state."
                ),
            ),
            CommandGuideEntry(
                "glassbox session evidence-graph SESSION_ID --summary --cwd .",
                (
                    "Inspect session claim support, stale projections, missing "
                    "operator decisions, and safe next actions."
                ),
            ),
            CommandGuideEntry(
                "glassbox task list --cwd .",
                "List durable task plans and their next actions.",
            ),
            CommandGuideEntry(
                "glassbox task show TASK_ID --cwd .",
                "Inspect task plan steps, budget posture, stop reasons, and evidence.",
            ),
            CommandGuideEntry(
                "glassbox observability status --cwd .",
                "Summarize runtime, projection, and verification health.",
            ),
        ),
    ),
    CommandGuideSection(
        key="unblock-work",
        title="Unblock Work",
        summary="Resolve pending operator decisions and bounded continuation points.",
        entries=(
            CommandGuideEntry(
                "glassbox session answer SESSION_ID QUESTION_ID ANSWER --cwd .",
                "Answer a pending operator question.",
            ),
            CommandGuideEntry(
                "glassbox session approve SESSION_ID APPROVAL_ID --cwd .",
                "Approve a pending action after reviewing policy evidence.",
            ),
            CommandGuideEntry(
                "glassbox session deny SESSION_ID APPROVAL_ID --cwd .",
                "Deny a pending action and retain the decision.",
            ),
            CommandGuideEntry(
                "glassbox session cancel SESSION_ID --cwd .",
                "Request cancellation for an active turn.",
            ),
            CommandGuideEntry(
                "glassbox session message SESSION_ID PROMPT --cwd .",
                "Continue an existing session with a new prompt.",
            ),
            CommandGuideEntry(
                "glassbox task continue TASK_ID --cwd .",
                "Enqueue a bounded background continuation job for a task.",
            ),
        ),
    ),
    CommandGuideSection(
        key="long-run-recovery",
        title="Long-Run Recovery",
        summary=(
            "Start with safe inspection before resuming, retrying, or cancelling "
            "bounded long work."
        ),
        entries=(
            CommandGuideEntry(
                "glassbox session status SESSION_ID --cwd .",
                (
                    "Inspect live phase, heartbeat, checkpoint, tool-attempt, "
                    "and recovery posture."
                ),
            ),
            CommandGuideEntry(
                "glassbox task show TASK_ID --cwd .",
                (
                    "Inspect continuation budget, pause windows, verification "
                    "state, and stop reason."
                ),
            ),
            CommandGuideEntry(
                "glassbox job list --cwd .",
                "Find queued, running, stale, failed, and paused daemon jobs.",
            ),
            CommandGuideEntry(
                "glassbox daemon status --cwd .",
                "Confirm the local mutation owner before recovery actions.",
            ),
            CommandGuideEntry(
                "glassbox session resume SESSION_ID --cwd .",
                (
                    "Resume a session only after reviewing checkpoint and "
                    "recovery posture."
                ),
            ),
            CommandGuideEntry(
                "glassbox task continue TASK_ID --cwd .",
                "Continue a durable task within its configured local budget.",
            ),
        ),
    ),
    CommandGuideSection(
        key="compaction",
        title="Compaction",
        summary=(
            "Inspect, create, refresh, or invalidate artifact-backed context evidence."
        ),
        entries=(
            CommandGuideEntry(
                "glassbox session compactions SESSION_ID --cwd .",
                "List retained compaction artifacts and freshness before using them.",
            ),
            CommandGuideEntry(
                (
                    "glassbox session compact SESSION_ID --source-start-sequence "
                    "START --source-end-sequence END --cwd ."
                ),
                (
                    "Create a bounded deterministic compaction for an explicit "
                    "event range."
                ),
            ),
            CommandGuideEntry(
                "glassbox session compaction-refresh SESSION_ID COMPACTION_ID --cwd .",
                (
                    "Plan a stale compaction refresh; add --yes after reviewing "
                    "the mutation."
                ),
            ),
            CommandGuideEntry(
                (
                    "glassbox session compaction-invalidate SESSION_ID "
                    "COMPACTION_ID --reason REASON --cwd ."
                ),
                "Mark stale or unsafe compaction evidence as not prompt-usable.",
            ),
        ),
    ),
    CommandGuideSection(
        key="tool-attempts",
        title="Tool Attempts",
        summary=(
            "Recover resumable or stale tool work without losing retained evidence."
        ),
        entries=(
            CommandGuideEntry(
                "glassbox session tool-attempts SESSION_ID --cwd .",
                "List durable tool attempts, heartbeat state, and retry posture.",
            ),
            CommandGuideEntry(
                (
                    "glassbox session tool-attempt inspect SESSION_ID "
                    "TOOL_ATTEMPT_ID --cwd ."
                ),
                "Inspect one attempt before retrying or abandoning it.",
            ),
            CommandGuideEntry(
                (
                    "glassbox session tool-attempt output SESSION_ID "
                    "TOOL_ATTEMPT_ID --tail 80 --cwd ."
                ),
                "Read retained attempt output without rerunning the tool.",
            ),
            CommandGuideEntry(
                (
                    "glassbox session tool-attempt retry SESSION_ID "
                    "TOOL_ATTEMPT_ID --cwd ."
                ),
                "Plan a retry for a stale or failed attempt; add --yes to mutate.",
            ),
            CommandGuideEntry(
                (
                    "glassbox session tool-attempt abandon SESSION_ID "
                    "TOOL_ATTEMPT_ID --reason REASON --cwd ."
                ),
                "Record that an attempt should not be retried after inspection.",
            ),
        ),
    ),
    CommandGuideSection(
        key="checkpoint-inspection",
        title="Checkpoint Inspection",
        summary="Decide whether a checkpoint is usable before continuing long work.",
        entries=(
            CommandGuideEntry(
                "glassbox session status SESSION_ID --cwd .",
                "Show the latest checkpoint or an explicit no-checkpoint explanation.",
            ),
            CommandGuideEntry(
                "glassbox task show TASK_ID --cwd .",
                (
                    "Inspect last-known-good checkpoint evidence and continuation "
                    "guidance."
                ),
            ),
            CommandGuideEntry(
                "glassbox session export SESSION_ID handoff.zip --cwd .",
                "Export redacted checkpoint history for inspection-only handoff.",
            ),
            CommandGuideEntry(
                "glassbox session resume SESSION_ID --cwd .",
                "Resume only after checkpoint safety, drift, and blockers are clear.",
            ),
        ),
    ),
    CommandGuideSection(
        key="verify-work",
        title="Verification Recommendations",
        summary=(
            "Choose the cheapest trustworthy verification command for local changes."
        ),
        entries=(
            CommandGuideEntry(
                "glassbox eval recommend PATH --cwd .",
                (
                    "Explain matching rules and show the smallest recommended "
                    "next command."
                ),
            ),
            CommandGuideEntry(
                "glassbox repo recommend PATH --cwd .",
                "Use repository intelligence to explain verification options.",
            ),
            CommandGuideEntry(
                "glassbox eval recommend PATH --execute --cwd .",
                "Run deterministic recommended checks after reviewing the plan.",
            ),
            CommandGuideEntry(
                "glassbox eval run --profile commit-smoke --cwd .",
                "Run the cheap deterministic commit-time eval profile.",
            ),
            CommandGuideEntry(
                "glassbox replay run SESSION_ID --cwd .",
                "Replay a recorded session offline.",
            ),
            CommandGuideEntry(
                "glassbox eval audit --cwd .",
                "Audit capability coverage for the selected eval portfolio.",
            ),
        ),
    ),
    CommandGuideSection(
        key="provider-posture",
        title="Provider Posture",
        summary="Inspect live-provider readiness and advisory recovery evidence.",
        entries=(
            CommandGuideEntry(
                "glassbox provider diagnostics --cwd .",
                "Inspect redacted provider configuration and credential readiness.",
            ),
            CommandGuideEntry(
                (
                    "glassbox provider recommend --task-kind coding "
                    "--autonomy-mode test-driven --cwd ."
                ),
                "Get advisory provider posture for a workflow before longer work.",
            ),
            CommandGuideEntry(
                "glassbox provider canary evidence --cwd .",
                "Inspect retained advisory provider canary freshness and gaps.",
            ),
            CommandGuideEntry(
                "glassbox provider canary run --cwd .",
                (
                    "Collect optional live-provider evidence when credentials "
                    "are configured."
                ),
            ),
        ),
    ),
    CommandGuideSection(
        key="knowledge-freshness",
        title="Knowledge Freshness",
        summary=(
            "Check whether local memory, repository intelligence, compactions, "
            "verification, and provider evidence are fresh enough to trust."
        ),
        entries=(
            CommandGuideEntry(
                "glassbox memory list --cwd .",
                "Review confirmed, invalidated, and pruned workspace memory.",
            ),
            CommandGuideEntry(
                "glassbox memory candidates --session SESSION_ID --cwd .",
                "Inspect reviewable memory candidates from explicit session signals.",
            ),
            CommandGuideEntry(
                "glassbox repo status --cwd .",
                "Inspect index and topology freshness with safe next actions.",
            ),
            CommandGuideEntry(
                "glassbox repo stale --cwd .",
                "Show stale, missing, degraded, or conflicting intelligence cues.",
            ),
            CommandGuideEntry(
                "glassbox session compactions SESSION_ID --cwd .",
                "Review compaction freshness and artifact provenance for a session.",
            ),
            CommandGuideEntry(
                "glassbox observability status --cwd .",
                (
                    "Check projection, verification, artifact, provider, and "
                    "runtime health together."
                ),
            ),
            CommandGuideEntry(
                "glassbox repo refresh --cwd .",
                "Refresh repository intelligence after reviewing stale status.",
            ),
            CommandGuideEntry(
                "glassbox repo path PATH --cwd .",
                "Inspect packages, subsystems, recipes, and owners for one path.",
            ),
            CommandGuideEntry(
                "glassbox repo recipes list --cwd .",
                "List advisory command recipes with provenance and risk labels.",
            ),
        ),
    ),
    CommandGuideSection(
        key="branch-search-review",
        title="Branch-Search Review",
        summary="Compare bounded candidate branches without mutating parent history.",
        entries=(
            CommandGuideEntry(
                "glassbox branch-search list --cwd .",
                "List recent branch-search workflows and their selected status.",
            ),
            CommandGuideEntry(
                "glassbox branch-search show BRANCH_SEARCH_ID --cwd .",
                (
                    "Compare candidate status, verification posture, and "
                    "recorded evidence."
                ),
            ),
            CommandGuideEntry(
                (
                    "glassbox branch-search needs-review BRANCH_SEARCH_ID "
                    "CANDIDATE_ID --reason REASON --cwd ."
                ),
                "Mark a candidate for human review when evidence is not decisive.",
            ),
            CommandGuideEntry(
                (
                    "glassbox branch-search select BRANCH_SEARCH_ID CANDIDATE_ID "
                    "--reason REASON --cwd ."
                ),
                "Record a selected candidate after verification and review.",
            ),
            CommandGuideEntry(
                (
                    "glassbox branch-search reject BRANCH_SEARCH_ID CANDIDATE_ID "
                    "--reason REASON --cwd ."
                ),
                "Record why a candidate should not be used.",
            ),
        ),
    ),
    REVIEW_LOOP_COMMAND_GUIDE_SECTION,
    CommandGuideSection(
        key="recover-workspace",
        title="Recover Workspace",
        summary=(
            "Diagnose local runtime, projection, artifact, backup, and job problems."
        ),
        entries=(
            CommandGuideEntry(
                "glassbox daemon status --cwd .",
                "Inspect the workspace daemon and local mutation owner.",
            ),
            CommandGuideEntry(
                "glassbox job list --cwd .",
                "List daemon-owned background jobs and retryable failures.",
            ),
            CommandGuideEntry(
                "glassbox projection check --all --cwd .",
                "Inspect derived projection health without rebuilding.",
            ),
            CommandGuideEntry(
                "glassbox artifacts inspect --cwd .",
                "Inspect managed artifact state before pruning.",
            ),
            CommandGuideEntry(
                "glassbox backup create --cwd .",
                "Create a local workspace backup before risky maintenance.",
            ),
            CommandGuideEntry(
                "glassbox repo index build --cwd .",
                "Refresh rebuildable repository intelligence explicitly.",
            ),
        ),
    ),
    CommandGuideSection(
        key="release-evidence",
        title="Release Evidence",
        summary=(
            "Generate retained deterministic, package, and advisory evidence "
            "for reviewers."
        ),
        entries=(
            CommandGuideEntry(
                "glassbox command tree",
                "Print the exhaustive structural command surface.",
            ),
            CommandGuideEntry(
                (
                    "glassbox eval report commit-smoke push-confirmation "
                    "release-candidate --cwd ."
                ),
                "Generate deterministic release sign-off evidence from eval profiles.",
            ),
            CommandGuideEntry(
                "glassbox provider canary evidence --cwd .",
                "Inspect retained advisory provider canary evidence.",
            ),
            CommandGuideEntry(
                "python scripts/validate_package_contents.py",
                "Validate package contents before release publication.",
            ),
        ),
    ),
)
__all__ = ["COMMAND_GUIDE_SECTIONS"]
