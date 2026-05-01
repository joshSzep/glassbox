"""Local session action helpers for interactive CLI commands."""

import argparse
import asyncio

from glassbox.cli.interactive_autonomy import print_autonomy_config_summary
from glassbox.core import SessionConfig
from glassbox.core.ids import SessionId
from glassbox.core.types import ApprovalDecision
from glassbox.runtime.context import RuntimeContext


async def submit_prompt_if_present(
    runtime_context: RuntimeContext,
    session_id: SessionId,
    prompt: str | None,
) -> None:
    if not prompt:
        return
    await runtime_context.services.session_service.submit_user_message(
        session_id,
        prompt,
    )
    await asyncio.sleep(0)


async def resume_session_locally(
    runtime_context: RuntimeContext,
    args: argparse.Namespace,
    autonomy_config: SessionConfig | None,
) -> None:
    if autonomy_config is not None:
        print_autonomy_config_summary(autonomy_config)
    await runtime_context.services.session_service.resume_session(args.session_id)
    await asyncio.sleep(0)


async def submit_session_message_locally(
    runtime_context: RuntimeContext,
    args: argparse.Namespace,
    autonomy_config: SessionConfig | None,
) -> None:
    if autonomy_config is not None:
        print_autonomy_config_summary(autonomy_config)
    await runtime_context.services.session_service.submit_user_message(
        args.session_id,
        args.prompt,
    )
    await asyncio.sleep(0)


async def cancel_session_turn_locally(
    runtime_context: RuntimeContext,
    args: argparse.Namespace,
) -> None:
    await runtime_context.services.session_service.cancel_turn(
        args.session_id,
        turn_id=args.turn_id,
        requested_by="cli",
        reason=args.reason,
    )
    await asyncio.sleep(0)
    print(f"Cancellation requested for session {args.session_id}")


async def fork_session_locally(
    runtime_context: RuntimeContext,
    args: argparse.Namespace,
) -> None:
    forked_session = await runtime_context.services.session_service.fork_session(
        args.session_id,
        turn_id=args.turn_id,
        branch_label=args.branch_label,
    )
    await asyncio.sleep(0)
    print(
        "Forked session "
        f"{forked_session.child_session_id} "
        f"from {forked_session.parent_session_id} "
        f"at turn {forked_session.forked_from_turn_id} "
        f"(sequence {forked_session.forked_from_sequence})"
    )
    print(
        "Imported "
        f"{forked_session.inherited_message_count} transcript messages "
        "into child session"
    )
    if forked_session.branch_label is not None:
        print(f"Branch label: {forked_session.branch_label}")
    if args.prompt:
        await submit_prompt_if_present(
            runtime_context,
            forked_session.child_session_id,
            args.prompt,
        )


async def answer_question_locally(
    runtime_context: RuntimeContext,
    args: argparse.Namespace,
) -> None:
    await runtime_context.services.session_service.provide_user_answer(
        args.session_id,
        args.question_id,
        args.answer,
    )
    await asyncio.sleep(0)


async def resolve_approval_locally(
    runtime_context: RuntimeContext,
    args: argparse.Namespace,
    decision: ApprovalDecision,
) -> None:
    await runtime_context.services.session_service.resolve_approval(
        args.session_id,
        args.approval_id,
        decision,
    )
    await asyncio.sleep(0)


__all__ = [
    "answer_question_locally",
    "cancel_session_turn_locally",
    "fork_session_locally",
    "resolve_approval_locally",
    "resume_session_locally",
    "submit_prompt_if_present",
    "submit_session_message_locally",
]
