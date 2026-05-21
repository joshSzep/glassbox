"""Command registry for the terminal app command palette."""

from dataclasses import dataclass
from enum import StrEnum

from glassbox.cli.tui.conversation import TerminalConversationState


class TerminalCommandId(StrEnum):
    STATUS = "status"
    OPEN_DASHBOARD = "open_dashboard"
    COPY_SESSION_ID = "copy_session_id"
    COPY_DASHBOARD_URL = "copy_dashboard_url"
    COPY_ARTIFACT_PATH = "copy_artifact_path"
    OPEN_ARTIFACT_PATH = "open_artifact_path"
    TOGGLE_DETAILS = "toggle_details"
    TOGGLE_MARKDOWN = "toggle_markdown"
    JUMP_LATEST = "jump_latest"
    APPROVE = "approve"
    DENY = "deny"
    SUBMIT_ANSWER = "submit_answer"
    INTERRUPT = "interrupt"
    CLEAR_TRANSCRIPT = "clear_transcript"
    REVIEW_CREATE_CHANGESET = "review_create_changeset"
    REVIEW_OPERATOR_QUEUE = "review_operator_queue"
    REVIEW_NEXT_ACTIONS = "review_next_actions"
    REVIEW_WORKUP_GUIDE = "review_workup_guide"
    REVIEW_REFRESH_INVENTORY = "review_refresh_inventory"
    REVIEW_OPEN_DASHBOARD = "review_open_dashboard"
    REVIEW_GENERATE_BRIEF = "review_generate_brief"
    REVIEW_PREVIEW_VERIFICATION = "review_preview_verification"
    REVIEW_EVIDENCE_GRAPH = "review_evidence_graph"
    REVIEW_INSPECT_HANDOFF = "review_inspect_handoff"
    REVIEW_MAINTENANCE_CHECKS = "review_maintenance_checks"
    REVIEW_SHOW_FEEDBACK_STATUS = "review_show_feedback_status"
    REVIEW_RECORD_FEEDBACK_FIXUP = "review_record_feedback_fixup"
    HANDOFF_READINESS = "handoff_readiness"
    HANDOFF_PREPARE_PREVIEW = "handoff_prepare_preview"
    HANDOFF_PACKAGE_INSPECT = "handoff_package_inspect"
    HANDOFF_CUSTODY_ACTIONS = "handoff_custody_actions"
    HANDOFF_SAFE_COMMANDS = "handoff_safe_commands"
    HANDOFF_OPEN_DASHBOARD = "handoff_open_dashboard"
    QUIT = "quit"


@dataclass(frozen=True, slots=True)
class TerminalCommandSpec:
    command_id: TerminalCommandId
    title: str
    description: str
    shortcut: str | None = None
    slash_aliases: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TerminalCommandItem:
    spec: TerminalCommandSpec
    enabled: bool
    disabled_reason: str | None = None


@dataclass(frozen=True, slots=True)
class TerminalSlashCommand:
    command_id: TerminalCommandId
    argument: str | None = None


_COMMAND_SPECS: tuple[TerminalCommandSpec, ...] = (
    TerminalCommandSpec(
        TerminalCommandId.STATUS,
        "Show Status",
        "Show current session and runtime status",
        slash_aliases=("/status",),
    ),
    TerminalCommandSpec(
        TerminalCommandId.OPEN_DASHBOARD,
        "Open Dashboard",
        "Open the co-hosted dashboard for this session",
        "Ctrl+D",
        ("/dashboard", "/open-dashboard"),
    ),
    TerminalCommandSpec(
        TerminalCommandId.COPY_SESSION_ID,
        "Copy Session ID",
        "Copy the current session identifier",
        slash_aliases=("/copy-session",),
    ),
    TerminalCommandSpec(
        TerminalCommandId.COPY_DASHBOARD_URL,
        "Copy Dashboard URL",
        "Copy the dashboard URL for this session",
        "Alt+D",
        slash_aliases=("/copy-dashboard",),
    ),
    TerminalCommandSpec(
        TerminalCommandId.COPY_ARTIFACT_PATH,
        "Copy Artifact Path",
        "Copy the latest artifact path from this session",
        slash_aliases=("/copy-artifact",),
    ),
    TerminalCommandSpec(
        TerminalCommandId.OPEN_ARTIFACT_PATH,
        "Open Artifact Path",
        "Open the latest local artifact path",
        slash_aliases=("/open-artifact",),
    ),
    TerminalCommandSpec(
        TerminalCommandId.TOGGLE_DETAILS,
        "Toggle Details",
        "Show or hide the details surface",
        "Ctrl+E",
        ("/details",),
    ),
    TerminalCommandSpec(
        TerminalCommandId.TOGGLE_MARKDOWN,
        "Toggle Markdown Rendering",
        "Render chat messages as Markdown in the transcript",
        slash_aliases=("/markdown", "/md"),
    ),
    TerminalCommandSpec(
        TerminalCommandId.JUMP_LATEST,
        "Jump To Bottom",
        "Scroll the transcript to the newest output",
        "Ctrl+L",
        ("/latest",),
    ),
    TerminalCommandSpec(
        TerminalCommandId.APPROVE,
        "Approve",
        "Approve the pending action",
        "Alt+A",
        slash_aliases=("/approve",),
    ),
    TerminalCommandSpec(
        TerminalCommandId.DENY,
        "Deny",
        "Deny the pending action",
        "Alt+X",
        slash_aliases=("/deny",),
    ),
    TerminalCommandSpec(
        TerminalCommandId.SUBMIT_ANSWER,
        "Submit Answer",
        "Submit the current draft as the pending answer",
        "Ctrl+R",
        slash_aliases=("/answer",),
    ),
    TerminalCommandSpec(
        TerminalCommandId.INTERRUPT,
        "Interrupt",
        "Request interruption of the active turn",
        "Ctrl+C",
        ("/interrupt",),
    ),
    TerminalCommandSpec(
        TerminalCommandId.CLEAR_TRANSCRIPT,
        "Clear Visual Transcript",
        "Clear the visible transcript without changing session history",
        slash_aliases=("/clear",),
    ),
    TerminalCommandSpec(
        TerminalCommandId.REVIEW_WORKUP_GUIDE,
        "Review: Guided Workup",
        "Guide local changes through changeset, verification, brief, and handoff",
        slash_aliases=("/review workup", "/review guide", "/changeset workup"),
    ),
    TerminalCommandSpec(
        TerminalCommandId.REVIEW_OPERATOR_QUEUE,
        "Review: Operator Queue",
        "Inspect ranked queue items, evidence summaries, and safe next actions",
        slash_aliases=(
            "/queue",
            "/operator-queue",
            "/operator queue",
            "/review queue",
        ),
    ),
    TerminalCommandSpec(
        TerminalCommandId.REVIEW_NEXT_ACTIONS,
        "Review: Next Actions",
        "Show action-needed queue entries without leaving the conversation",
        slash_aliases=("/next-actions", "/next action", "/review next-actions"),
    ),
    TerminalCommandSpec(
        TerminalCommandId.REVIEW_CREATE_CHANGESET,
        "Review: Create Changeset",
        "Create local review changeset evidence from the current workspace diff",
        slash_aliases=("/review create", "/review new", "/changeset create"),
    ),
    TerminalCommandSpec(
        TerminalCommandId.REVIEW_REFRESH_INVENTORY,
        "Review: Refresh Inventory",
        "Refresh inventory before fixup, verification, brief, or handoff checks",
        slash_aliases=("/review refresh", "/changeset refresh"),
    ),
    TerminalCommandSpec(
        TerminalCommandId.REVIEW_OPEN_DASHBOARD,
        "Review: Open Dashboard",
        "Open the dashboard changeset review surface",
        slash_aliases=("/review dashboard", "/changeset dashboard"),
    ),
    TerminalCommandSpec(
        TerminalCommandId.REVIEW_GENERATE_BRIEF,
        "Review: Generate Lifecycle Brief",
        "Generate the missing reviewer-safe lifecycle brief for handoff",
        slash_aliases=("/review brief", "/changeset brief"),
    ),
    TerminalCommandSpec(
        TerminalCommandId.REVIEW_PREVIEW_VERIFICATION,
        "Review: Preview Verification",
        "Preview stale or missing review-loop verification without running commands",
        slash_aliases=(
            "/review verify",
            "/review verification",
            "/changeset verify",
            "/changeset verification",
        ),
    ),
    TerminalCommandSpec(
        TerminalCommandId.REVIEW_EVIDENCE_GRAPH,
        "Review: Evidence Graph",
        "Inspect claim support, missing evidence, stale evidence, and limitations",
        slash_aliases=(
            "/evidence-graph",
            "/evidence graph",
            "/review evidence-graph",
            "/changeset evidence-graph",
        ),
    ),
    TerminalCommandSpec(
        TerminalCommandId.REVIEW_INSPECT_HANDOFF,
        "Review: Inspect Handoff",
        "Inspect blockers, missing brief, skipped evidence, and handoff posture",
        slash_aliases=("/review handoff", "/changeset handoff"),
    ),
    TerminalCommandSpec(
        TerminalCommandId.REVIEW_MAINTENANCE_CHECKS,
        "Review: Maintenance Checks",
        "Inspect queue-linked projection, background job, and runtime health cues",
        slash_aliases=(
            "/maintenance",
            "/maintenance checks",
            "/review maintenance",
        ),
    ),
    TerminalCommandSpec(
        TerminalCommandId.REVIEW_SHOW_FEEDBACK_STATUS,
        "Review: Show Feedback Status",
        "Inspect missing fixup inventory, skipped evidence, and stale verification",
        slash_aliases=(
            "/review",
            "/review status",
            "/review feedback",
            "/changeset",
            "/changeset status",
            "/changeset feedback",
        ),
    ),
    TerminalCommandSpec(
        TerminalCommandId.REVIEW_RECORD_FEEDBACK_FIXUP,
        "Review: Record Fixup Inventory",
        "Record response-linked changed-path inventory for one feedback ID",
        slash_aliases=("/review fixup", "/changeset fixup"),
    ),
    TerminalCommandSpec(
        TerminalCommandId.HANDOFF_READINESS,
        "Handoff: Readiness",
        "Show session handoff readiness commands and non-claims",
        slash_aliases=("/handoff readiness", "/handoff status"),
    ),
    TerminalCommandSpec(
        TerminalCommandId.HANDOFF_PREPARE_PREVIEW,
        "Handoff: Prepare Preview",
        "Show redaction preview and export commands without writing a package",
        slash_aliases=("/handoff preview", "/handoff prepare-preview"),
    ),
    TerminalCommandSpec(
        TerminalCommandId.HANDOFF_PACKAGE_INSPECT,
        "Handoff: Inspect Package",
        "Show package inspect and import triage commands",
        slash_aliases=("/handoff inspect", "/handoff triage"),
    ),
    TerminalCommandSpec(
        TerminalCommandId.HANDOFF_CUSTODY_ACTIONS,
        "Handoff: Custody Actions",
        "Show accept, reject, archive, and guidance commands explicitly",
        slash_aliases=("/handoff custody", "/handoff accept", "/handoff reject"),
    ),
    TerminalCommandSpec(
        TerminalCommandId.HANDOFF_OPEN_DASHBOARD,
        "Handoff: Open Dashboard",
        "Open the local handoff cockpit in the dashboard",
        slash_aliases=("/handoff dashboard", "/handoff cockpit"),
    ),
    TerminalCommandSpec(
        TerminalCommandId.HANDOFF_SAFE_COMMANDS,
        "Handoff: Safe Commands",
        "List safe first commands for inspection-first handoff work",
        slash_aliases=("/handoff", "/handoff safe", "/handoff commands"),
    ),
    TerminalCommandSpec(
        TerminalCommandId.QUIT,
        "Quit",
        "Exit the terminal app",
        "Ctrl+Esc",
        ("/quit", "/exit"),
    ),
)


def command_items_for_state(
    state: TerminalConversationState,
) -> tuple[TerminalCommandItem, ...]:
    from glassbox.cli.tui.command_state import item_for_spec

    return tuple(item_for_spec(spec, state) for spec in _COMMAND_SPECS)


def filter_command_items(
    items: tuple[TerminalCommandItem, ...],
    query: str,
) -> tuple[TerminalCommandItem, ...]:
    normalized = query.strip().lower()
    if not normalized:
        return items
    return tuple(
        item
        for item in items
        if normalized in item.spec.title.lower()
        or normalized in item.spec.description.lower()
        or any(normalized in alias for alias in item.spec.slash_aliases)
    )


def command_from_slash(text: str) -> TerminalCommandId | None:
    slash = slash_command_from_text(text)
    return slash.command_id if slash is not None else None


def slash_command_from_text(text: str) -> TerminalSlashCommand | None:
    parts = text.strip().split(maxsplit=1)
    if not parts:
        return None
    normalized = parts[0].lower()
    if not normalized.startswith("/"):
        return None
    if normalized in {"/review", "/changeset"}:
        from glassbox.cli.tui.review_commands import review_slash_command

        return review_slash_command(parts[1] if len(parts) > 1 else "")
    normalized_text = text.strip().lower()
    for spec in _COMMAND_SPECS:
        for alias in sorted(spec.slash_aliases, key=len, reverse=True):
            if normalized_text == alias:
                return TerminalSlashCommand(spec.command_id)
            if normalized_text.startswith(f"{alias} "):
                return TerminalSlashCommand(
                    spec.command_id,
                    text.strip()[len(alias) :].strip(),
                )
        if normalized in spec.slash_aliases:
            return TerminalSlashCommand(
                spec.command_id,
                parts[1] if len(parts) > 1 else None,
            )
    return None


def command_item_by_id(
    items: tuple[TerminalCommandItem, ...],
    command_id: TerminalCommandId,
) -> TerminalCommandItem | None:
    for item in items:
        if item.spec.command_id == command_id:
            return item
    return None
