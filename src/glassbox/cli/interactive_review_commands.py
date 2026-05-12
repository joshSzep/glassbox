"""Interactive terminal helpers for /review and /changeset commands."""

from typing import Literal
from urllib.parse import quote
from urllib.parse import urlsplit
from urllib.parse import urlunsplit
from uuid import UUID

from glassbox.cli.interactive_client import InteractiveClientError
from glassbox.cli.interactive_client import LocalInteractiveSessionClient
from glassbox.cli.interactive_client import ReviewLoopAction
from glassbox.cli.interactive_client import ReviewLoopActionResult
from glassbox.cli.status_formatters import _dashboard_url_from_events
from glassbox.runtime.context import RuntimeContext


class _ParsedReviewCommand:
    def __init__(
        self,
        action: ReviewLoopAction | Literal["create", "dashboard"],
        argument: str | None = None,
    ) -> None:
        self.action = action
        self.argument = argument


def _parse_review_command(text: str) -> _ParsedReviewCommand:
    parts = text.strip().split(maxsplit=2)
    root = parts[0].lower() if parts else "/review"
    if root not in {"/review", "/changeset"}:
        raise ValueError("Review commands must start with /review or /changeset.")
    subcommand = parts[1].lower() if len(parts) > 1 else "status"
    argument = parts[2].strip() if len(parts) > 2 and parts[2].strip() else None
    if subcommand in {"create", "new"}:
        return _ParsedReviewCommand("create", argument)
    if subcommand in {"workup", "guide", "guided"}:
        return _ParsedReviewCommand(ReviewLoopAction.WORKUP_GUIDE, argument)
    if subcommand in {"queue", "operator-queue"}:
        return _ParsedReviewCommand(ReviewLoopAction.OPERATOR_QUEUE, argument)
    if subcommand in {"next", "next-action", "next-actions"}:
        return _ParsedReviewCommand(ReviewLoopAction.NEXT_ACTIONS, argument)
    if subcommand in {"status", "feedback", "responses"}:
        return _ParsedReviewCommand(ReviewLoopAction.SHOW_FEEDBACK_STATUS, argument)
    if subcommand in {"fixup", "record-fixup"}:
        return _ParsedReviewCommand(ReviewLoopAction.RECORD_FEEDBACK_FIXUP, argument)
    if subcommand == "refresh":
        return _ParsedReviewCommand(ReviewLoopAction.REFRESH_INVENTORY, argument)
    if subcommand in {"brief", "lifecycle-brief"}:
        return _ParsedReviewCommand(ReviewLoopAction.GENERATE_BRIEF, argument)
    if subcommand in {"verify", "verification", "verification-plan"}:
        return _ParsedReviewCommand(ReviewLoopAction.PREVIEW_VERIFICATION, argument)
    if subcommand in {"evidence", "evidence-graph", "graph"}:
        return _ParsedReviewCommand(ReviewLoopAction.EVIDENCE_GRAPH, argument)
    if subcommand in {"handoff", "handoff-readiness"}:
        return _ParsedReviewCommand(ReviewLoopAction.INSPECT_HANDOFF, argument)
    if subcommand in {"maintenance", "maintenance-checks"}:
        return _ParsedReviewCommand(ReviewLoopAction.MAINTENANCE_CHECKS, argument)
    if subcommand in {"dashboard", "open-dashboard"}:
        return _ParsedReviewCommand("dashboard", argument)
    return _ParsedReviewCommand(
        ReviewLoopAction.SHOW_FEEDBACK_STATUS,
        f"{subcommand} {argument}".strip() if argument else subcommand,
    )


def _dashboard_review_url(
    dashboard_url: str | None,
    changeset_id: str | None,
) -> str | None:
    if dashboard_url is None:
        return None
    parts = urlsplit(dashboard_url)
    path = "/app/changesets"
    if changeset_id:
        path += "/" + quote(changeset_id, safe="")
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def _resolve_interactive_dashboard_url(
    runtime_context: RuntimeContext,
    session_id: UUID,
    dashboard_url: str | None,
) -> str | None:
    if dashboard_url is not None:
        return dashboard_url
    events = runtime_context.repositories.sessions.read_session_events(session_id)
    return _dashboard_url_from_events(events)


def _print_review_result(
    result: ReviewLoopActionResult,
    *,
    dashboard_url: str | None,
) -> None:
    print(result.headline)
    for detail in result.details:
        print(f"  {detail}")
    if result.limitations:
        print("Limitations:")
        for item in result.limitations[:5]:
            print(f"  - {item}")
    if result.safe_next_actions:
        print("Safe next actions:")
        for item in result.safe_next_actions[:5]:
            print(f"  - {item}")
    if result.dashboard_path is not None:
        review_url = _dashboard_review_url(dashboard_url, result.changeset_id)
        if review_url is not None:
            print(f"Dashboard: {review_url}")
        else:
            print(
                "Dashboard: unavailable; run "
                "glassbox dashboard serve --cwd . and open /app/changesets."
            )


async def _execute_interactive_review_command(
    runtime_context: RuntimeContext,
    session_id: UUID,
    text: str,
    *,
    dashboard_url: str | None,
) -> None:
    command = _parse_review_command(text)
    client = LocalInteractiveSessionClient(
        runtime_context=runtime_context,
        session_id=session_id,
        dashboard_url=_resolve_interactive_dashboard_url(
            runtime_context,
            session_id,
            dashboard_url,
        ),
    )
    try:
        if command.action == "create":
            result = await client.create_review_changeset(objective=command.argument)
        elif command.action == "dashboard":
            result = await client.run_review_action(
                ReviewLoopAction.STATUS,
                changeset_id=command.argument,
            )
        elif isinstance(command.action, ReviewLoopAction):
            result = await client.run_review_action(
                command.action,
                changeset_id=command.argument,
            )
        else:
            raise ValueError(f"unsupported review action: {command.action}")
    except InteractiveClientError as exc:
        print(str(exc))
        if exc.kind.value == "validation_error":
            print("Safe next action: /review create")
        return
    except ValueError as exc:
        print(str(exc))
        return

    _print_review_result(result, dashboard_url=client.dashboard_url)
