"""CLI helpers for exposing typed next-action records beside legacy strings."""

from collections.abc import Iterable
from collections.abc import Sequence

from glassbox.core import NextAction
from glassbox.core import NextActionEvidenceKind
from glassbox.core import NextActionEvidenceRef
from glassbox.core import NextActionKind
from glassbox.core import NextActionPriority
from glassbox.core import NextActionSeverity
from glassbox.core import NextActionSurface
from glassbox.core import NextActionTargetKind
from glassbox.runtime.next_actions import next_action_from_command
from glassbox.runtime.next_actions import next_action_from_summary


def next_action_records_for_cli(
    actions: Iterable[str],
    *,
    target_kind: NextActionTargetKind,
    target_id: str | None = None,
    purpose: str,
    evidence_summary: str,
    kind: NextActionKind = NextActionKind.INSPECT,
    priority: NextActionPriority = NextActionPriority.RECOMMENDED,
    severity: NextActionSeverity = NextActionSeverity.INFO,
    limitations: Iterable[str] = (),
) -> list[NextAction]:
    """Convert current CLI next-action strings into typed advisory records."""

    evidence = NextActionEvidenceRef(
        kind=NextActionEvidenceKind.CLI_OUTPUT,
        ref_id=target_id or target_kind.value,
        summary=evidence_summary,
    )
    records: list[NextAction] = []
    seen: set[str] = set()
    for action in actions:
        normalized = action.strip().strip("`")
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        if _looks_like_command(normalized):
            records.append(
                next_action_from_command(
                    normalized,
                    target_kind=target_kind,
                    target_id=target_id,
                    purpose=purpose,
                    kind=kind,
                    priority=priority,
                    severity=severity,
                    supporting_evidence=[evidence],
                    limitations=limitations,
                    recommended_surfaces=[NextActionSurface.CLI],
                )
            )
        else:
            records.append(
                next_action_from_summary(
                    normalized,
                    target_kind=target_kind,
                    target_id=target_id,
                    kind=kind,
                    priority=priority,
                    severity=severity,
                    supporting_evidence=[evidence],
                    limitations=limitations,
                    recommended_surfaces=[NextActionSurface.CLI],
                )
            )
    return records


def next_action_record_payloads(actions: Sequence[NextAction]) -> list[dict]:
    """Return JSON-ready next-action records."""

    return [action.model_dump(mode="json") for action in actions]


def print_next_action_records(
    actions: Sequence[NextAction],
    *,
    heading: str = "Next action records:",
) -> None:
    """Print a compact human rendering of typed next actions."""

    if not actions:
        return
    print(heading)
    for action in actions:
        command = f"; command: {action.command.display}" if action.command else ""
        print(
            f"  - {action.title} "
            f"({action.priority.value}/{action.severity.value}){command}"
        )
        if action.supporting_evidence:
            print(f"    evidence: {action.supporting_evidence[0].summary}")
        if action.limitations:
            print(f"    limitation: {action.limitations[0]}")


def _looks_like_command(action: str) -> bool:
    return action.startswith(("glassbox ", "uv ", "pnpm ", "git ", "open "))


__all__ = [
    "next_action_record_payloads",
    "next_action_records_for_cli",
    "print_next_action_records",
]
