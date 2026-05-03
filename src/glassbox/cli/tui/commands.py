"""Command registry for the terminal app command palette."""

from dataclasses import dataclass
from enum import StrEnum

from glassbox.cli.tui.conversation import TerminalConversationState
from glassbox.cli.tui.conversation import TerminalMode
from glassbox.cli.tui.conversation import TerminalStreamStatus
from glassbox.cli.tui.conversation import latest_artifact_path_from_state


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
    REVIEW_REFRESH_INVENTORY = "review_refresh_inventory"
    REVIEW_OPEN_DASHBOARD = "review_open_dashboard"
    REVIEW_GENERATE_BRIEF = "review_generate_brief"
    REVIEW_PREVIEW_VERIFICATION = "review_preview_verification"
    REVIEW_INSPECT_HANDOFF = "review_inspect_handoff"
    REVIEW_SHOW_FEEDBACK_STATUS = "review_show_feedback_status"
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
        TerminalCommandId.REVIEW_CREATE_CHANGESET,
        "Review: Create Changeset",
        "Create local review changeset evidence from the current workspace diff",
        slash_aliases=("/review create", "/review new", "/changeset create"),
    ),
    TerminalCommandSpec(
        TerminalCommandId.REVIEW_REFRESH_INVENTORY,
        "Review: Refresh Inventory",
        "Refresh structured change inventory for the current review changeset",
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
        "Generate a reviewer-safe lifecycle brief for the review changeset",
        slash_aliases=("/review brief", "/changeset brief"),
    ),
    TerminalCommandSpec(
        TerminalCommandId.REVIEW_PREVIEW_VERIFICATION,
        "Review: Preview Verification",
        "Preview review-loop-aware verification without running commands",
        slash_aliases=(
            "/review verify",
            "/review verification",
            "/changeset verify",
            "/changeset verification",
        ),
    ),
    TerminalCommandSpec(
        TerminalCommandId.REVIEW_INSPECT_HANDOFF,
        "Review: Inspect Handoff",
        "Inspect advisory final handoff posture without publishing",
        slash_aliases=("/review handoff", "/changeset handoff"),
    ),
    TerminalCommandSpec(
        TerminalCommandId.REVIEW_SHOW_FEEDBACK_STATUS,
        "Review: Show Feedback Status",
        "Inspect feedback, response, and stale verification status",
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
    return tuple(_item_for_spec(spec, state) for spec in _COMMAND_SPECS)


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
        return _review_slash_command(parts[1] if len(parts) > 1 else "")
    for spec in _COMMAND_SPECS:
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


def _item_for_spec(
    spec: TerminalCommandSpec,
    state: TerminalConversationState,
) -> TerminalCommandItem:
    disabled_reason = _disabled_reason(spec.command_id, state)
    return TerminalCommandItem(
        spec=spec,
        enabled=disabled_reason is None,
        disabled_reason=disabled_reason,
    )


def _disabled_reason(
    command_id: TerminalCommandId,
    state: TerminalConversationState,
) -> str | None:
    if command_id in {
        TerminalCommandId.OPEN_DASHBOARD,
        TerminalCommandId.COPY_DASHBOARD_URL,
    }:
        if state.header.dashboard_url is None:
            return "dashboard unavailable"
    if command_id in {
        TerminalCommandId.COPY_ARTIFACT_PATH,
        TerminalCommandId.OPEN_ARTIFACT_PATH,
    }:
        if latest_artifact_path_from_state(state) is None:
            return "no artifact path"
    if command_id in {TerminalCommandId.APPROVE, TerminalCommandId.DENY}:
        if (
            state.pending_approval is None
            or state.pending_approval.decision is not None
        ):
            return "no pending approval"
        if state.header.stream_status in {
            TerminalStreamStatus.RECONNECTING,
            TerminalStreamStatus.UNAVAILABLE,
            TerminalStreamStatus.HISTORICAL_ONLY,
        }:
            return "runtime unavailable"
    if command_id == TerminalCommandId.SUBMIT_ANSWER:
        if state.pending_question is None or state.pending_question.answer is not None:
            return "no pending question"
        if state.header.stream_status in {
            TerminalStreamStatus.RECONNECTING,
            TerminalStreamStatus.UNAVAILABLE,
            TerminalStreamStatus.HISTORICAL_ONLY,
        }:
            return "runtime unavailable"
        if not state.composer.text.strip():
            return "answer draft is empty"
    if command_id == TerminalCommandId.INTERRUPT:
        if state.header.mode not in {
            TerminalMode.THINKING,
            TerminalMode.RUNNING_TOOL,
            TerminalMode.AWAITING_APPROVAL,
            TerminalMode.AWAITING_ANSWER,
        }:
            return "no active turn"
    if command_id == TerminalCommandId.CLEAR_TRANSCRIPT:
        if not state.messages and not state.turns and state.failure is None:
            return "transcript is empty"
    if command_id in {
        TerminalCommandId.REVIEW_CREATE_CHANGESET,
        TerminalCommandId.REVIEW_REFRESH_INVENTORY,
        TerminalCommandId.REVIEW_GENERATE_BRIEF,
    }:
        if state.header.cwd is None:
            return "workspace unavailable"
        if state.header.stream_status in {
            TerminalStreamStatus.RECONNECTING,
            TerminalStreamStatus.UNAVAILABLE,
            TerminalStreamStatus.HISTORICAL_ONLY,
        }:
            return "runtime unavailable"
    if command_id in {
        TerminalCommandId.REVIEW_PREVIEW_VERIFICATION,
        TerminalCommandId.REVIEW_INSPECT_HANDOFF,
        TerminalCommandId.REVIEW_SHOW_FEEDBACK_STATUS,
    }:
        if state.header.cwd is None:
            return "workspace unavailable"
    if command_id == TerminalCommandId.REVIEW_OPEN_DASHBOARD:
        if state.header.dashboard_url is None:
            return "dashboard unavailable"
    return None


def _review_slash_command(rest: str) -> TerminalSlashCommand:
    parts = rest.strip().split(maxsplit=1)
    subcommand = parts[0].lower() if parts else "status"
    argument = parts[1] if len(parts) > 1 else None
    if subcommand in {"create", "new"}:
        return TerminalSlashCommand(TerminalCommandId.REVIEW_CREATE_CHANGESET, argument)
    if subcommand == "refresh":
        return TerminalSlashCommand(
            TerminalCommandId.REVIEW_REFRESH_INVENTORY, argument
        )
    if subcommand in {"dashboard", "open-dashboard"}:
        return TerminalSlashCommand(TerminalCommandId.REVIEW_OPEN_DASHBOARD, argument)
    if subcommand in {"brief", "lifecycle-brief"}:
        return TerminalSlashCommand(TerminalCommandId.REVIEW_GENERATE_BRIEF, argument)
    if subcommand in {"verify", "verification", "verification-plan"}:
        return TerminalSlashCommand(
            TerminalCommandId.REVIEW_PREVIEW_VERIFICATION, argument
        )
    if subcommand in {"handoff", "handoff-readiness"}:
        return TerminalSlashCommand(TerminalCommandId.REVIEW_INSPECT_HANDOFF, argument)
    if subcommand in {"status", "feedback", "responses"}:
        return TerminalSlashCommand(
            TerminalCommandId.REVIEW_SHOW_FEEDBACK_STATUS, argument
        )
    return TerminalSlashCommand(
        TerminalCommandId.REVIEW_SHOW_FEEDBACK_STATUS,
        f"{subcommand} {argument}".strip() if argument else subcommand,
    )
