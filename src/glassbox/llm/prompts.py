"""System prompt composition for Glassbox model turns."""

import json
from collections.abc import Sequence

from glassbox.runtime.context_builder import PolicyContext
from glassbox.runtime.context_builder import ToolSchema
from glassbox.runtime.context_builder import TurnContext
from glassbox.runtime.context_builder import format_repository_intelligence_for_prompt
from glassbox.runtime.context_builder import normalize_tool_schemas
from glassbox.runtime.task_plan_capture import build_task_plan_prompt_fragment


def build_system_prompt(turn_context: TurnContext) -> str:
    """Build a stable system prompt from typed runtime context."""

    sections = [
        build_runtime_prompt_fragment(),
        build_output_style_prompt_fragment(),
        build_task_plan_prompt_fragment(),
        build_tool_usage_prompt_fragment(turn_context.available_tools),
        build_approval_policy_prompt_fragment(turn_context.policy),
    ]

    if (
        turn_context.repo_context is not None
        and turn_context.repo_context.strip() != ""
    ):
        sections.append(build_repo_context_prompt_fragment(turn_context.repo_context))
    if turn_context.repository_intelligence is not None:
        sections.append(
            build_repository_intelligence_prompt_fragment(
                turn_context.repository_intelligence
            )
        )
    if turn_context.memory_notes:
        sections.append(build_memory_notes_prompt_fragment(turn_context.memory_notes))
    if turn_context.checkpoint_context is not None:
        sections.append(
            build_checkpoint_resume_prompt_fragment(turn_context.checkpoint_context)
        )
    if (
        turn_context.context_compactions is not None
        and turn_context.context_compactions.items
    ):
        sections.append(
            build_context_compactions_prompt_fragment(turn_context.context_compactions)
        )
    if turn_context.working_set is not None and turn_context.working_set.items:
        sections.append(build_working_set_prompt_fragment(turn_context.working_set))
    if (
        turn_context.artifact_context is not None
        and turn_context.artifact_context.summaries
    ):
        sections.append(
            build_artifact_backed_context_prompt_fragment(turn_context.artifact_context)
        )

    return "\n\n".join(section for section in sections if section != "")


def build_runtime_prompt_fragment() -> str:
    """Return baseline runtime instructions for Glassbox behavior."""

    return "\n".join(
        [
            (
                "You are Glassbox, a terminal-first agent running inside an "
                "event-driven runtime."
            ),
            (
                "Work from the transcript, tool results, and supplied context "
                "rather than inventing hidden state."
            ),
            (
                "Treat tool calls and approvals as explicit runtime actions, "
                "not as assumptions."
            ),
        ]
    )


def build_output_style_prompt_fragment() -> str:
    """Return response-style instructions for baseline model behavior."""

    return "\n".join(
        [
            "Output style:",
            "- Be concise, factual, and explicit about uncertainty.",
            (
                "- Do not claim an action succeeded unless the transcript or "
                "a tool result shows it succeeded."
            ),
            (
                "- If you are blocked by policy, approvals, or missing tool "
                "access, say so directly."
            ),
        ]
    )


def build_tool_usage_prompt_fragment(tool_schemas: Sequence[ToolSchema]) -> str:
    """Return instructions for using the currently available tools."""

    lines = [
        "Tool usage:",
        (
            "- Use tools when they materially improve correctness or let you "
            "inspect the workspace."
        ),
        "- Never invent tool outputs, side effects, or file changes.",
        "- Arguments for tool calls must match the declared JSON schema.",
    ]

    normalized_tools = normalize_tool_schemas(tool_schemas)
    if not normalized_tools:
        lines.append("- No tools are currently available for this turn.")
        return "\n".join(lines)

    lines.append("Available tools:")
    for tool in normalized_tools:
        schema_text = json.dumps(tool.parameters_json_schema, sort_keys=True)
        lines.append(f"{tool.name}: {tool.description}")
        lines.append(f"Schema: {schema_text}")
    return "\n".join(lines)


def build_approval_policy_prompt_fragment(policy: PolicyContext) -> str:
    """Return approval-policy instructions visible to the model."""

    lines = [
        "Approval policy:",
        f"- Current approval mode: {policy.approval_mode}.",
        (
            "- If a requested action needs approval, stop and ask for "
            "approval rather than implying it already happened."
        ),
    ]
    if policy.pending_approval_id is None:
        lines.append("- No approval request is currently pending.")
    else:
        lines.append(f"- Pending approval id: {policy.pending_approval_id}.")
        lines.append("- Do not assume that pending approval has been granted.")
    return "\n".join(lines)


def build_repo_context_prompt_fragment(repo_context: str) -> str:
    """Return repository-specific context for the current turn."""

    return "\n".join(["Repository context:", repo_context.strip()])


def build_repository_intelligence_prompt_fragment(repository_intelligence) -> str:
    """Return bounded repository-intelligence context for the current turn."""

    return format_repository_intelligence_for_prompt(repository_intelligence)


def build_memory_notes_prompt_fragment(memory_notes: Sequence[str]) -> str:
    """Return durable operator or runtime notes for the model."""

    lines = ["Memory notes:"]
    for note in memory_notes:
        lines.append(f"- {note}")
    return "\n".join(lines)


def build_checkpoint_resume_prompt_fragment(checkpoint) -> str:
    """Return checkpoint-derived resume context with explicit caveats."""

    lines = [
        "Checkpoint resume context:",
        f"- Status: {checkpoint.status}.",
        f"- Context source: {checkpoint.context_source}.",
        f"- Reason: {checkpoint.reason}",
        (
            "- Provenance: source events "
            f"{checkpoint.source_start_sequence}-{checkpoint.source_end_sequence}; "
            f"checkpoint event {checkpoint.checkpoint_sequence}; latest session "
            f"event {checkpoint.latest_session_sequence}."
        ),
        f"- Objective: {checkpoint.objective}",
        f"- Next action: {checkpoint.next_action}",
        f"- Recovery guidance: {checkpoint.recovery_guidance}",
    ]
    if checkpoint.current_phase is not None:
        lines.append(f"- Current phase: {checkpoint.current_phase.value}.")
    if checkpoint.completed_step:
        lines.append(f"- Last completed step: {checkpoint.completed_step}")
    if checkpoint.blockers:
        lines.append("- Blockers: " + "; ".join(checkpoint.blockers[:5]))
    if checkpoint.touched_files:
        lines.append("- Touched files: " + ", ".join(checkpoint.touched_files[:8]))
    if checkpoint.workspace_drift_paths:
        lines.append(
            "- Workspace drift: " + ", ".join(checkpoint.workspace_drift_paths[:8])
        )
    if checkpoint.verification_status:
        lines.append(f"- Verification posture: {checkpoint.verification_status}")
    if checkpoint.budget_status:
        lines.append(f"- Budget posture: {checkpoint.budget_status}")
    for limitation in checkpoint.limitations[:3]:
        lines.append(f"- Limitation: {limitation}")
    if not checkpoint.safe_to_use:
        lines.append(
            "- Do not treat this checkpoint as an active continuation point until "
            "the reason above is resolved."
        )
    return "\n".join(lines)


def build_context_compactions_prompt_fragment(compactions) -> str:
    """Return fresh compaction summaries with provenance and caveats."""

    lines = ["Context compactions:"]
    for item in compactions.items:
        lines.append(
            f"- [{item.scope.value}] {item.summary} "
            f"(source events {item.source_start_sequence}-{item.source_end_sequence}; "
            f"artifact {item.artifact_id})"
        )
        if item.limitations:
            lines.append("  Limitations: " + "; ".join(item.limitations[:2]))
    if compactions.additional_item_count:
        lines.append(f"- +{compactions.additional_item_count} more fresh compaction(s)")
    if compactions.stale_item_count:
        lines.append(f"- {compactions.stale_item_count} stale compaction(s) excluded.")
    return "\n".join(lines)


def build_working_set_prompt_fragment(working_set) -> str:
    """Return the bounded working-set summary for the current turn."""

    lines = ["Working set:"]
    for item in working_set.items:
        reason_text = "; ".join(item.reasons[:2])
        lines.append(
            f"- [{item.subject_kind}] {item.subject}: {item.summary}"
            + (f" ({reason_text})" if reason_text else "")
        )
    if working_set.additional_item_count:
        lines.append(f"- +{working_set.additional_item_count} more working-set item(s)")
    return "\n".join(lines)


def build_artifact_backed_context_prompt_fragment(artifact_context) -> str:
    """Return fresh artifact-backed context summaries for the current turn."""

    fresh_summaries = [
        summary
        for summary in artifact_context.summaries
        if summary.freshness == "fresh"
    ]
    if not fresh_summaries:
        return ""

    lines = ["Artifact-backed context:"]
    for summary in fresh_summaries:
        lines.append(f"- [{summary.summary_kind}] {summary.summary}")
        if summary.failing_tests:
            lines.append("  Failing tests: " + ", ".join(summary.failing_tests[:3]))
    if artifact_context.additional_summary_count:
        lines.append(
            "- +"
            f"{artifact_context.additional_summary_count} more artifact summary "
            "item(s)"
        )
    return "\n".join(lines)
