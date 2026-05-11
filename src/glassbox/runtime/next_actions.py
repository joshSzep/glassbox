"""Compatibility helpers for shared advisory next-action records."""

from collections.abc import Iterable
from hashlib import sha256
from shlex import split as shlex_split

from glassbox.core import NextAction
from glassbox.core import NextActionCommandRecipe
from glassbox.core import NextActionEvidenceRef
from glassbox.core import NextActionKind
from glassbox.core import NextActionPriority
from glassbox.core import NextActionSafetyClass
from glassbox.core import NextActionSeverity
from glassbox.core import NextActionSurface
from glassbox.core import NextActionTarget
from glassbox.core import NextActionTargetKind


def next_action_from_summary(
    summary: str,
    *,
    target_kind: NextActionTargetKind = NextActionTargetKind.UNKNOWN,
    target_id: str | None = None,
    kind: NextActionKind = NextActionKind.INSPECT,
    priority: NextActionPriority = NextActionPriority.RECOMMENDED,
    severity: NextActionSeverity = NextActionSeverity.INFO,
    safety_class: NextActionSafetyClass = NextActionSafetyClass.READ_ONLY,
    supporting_evidence: Iterable[NextActionEvidenceRef] = (),
    missing_evidence: Iterable[NextActionEvidenceRef] = (),
    stale_evidence: Iterable[NextActionEvidenceRef] = (),
    limitations: Iterable[str] = (),
    recommended_surfaces: Iterable[NextActionSurface] = (),
) -> NextAction:
    """Wrap an existing prose next-action string in the shared typed model."""

    normalized_summary = summary.strip()
    action_id = _action_id(normalized_summary, target_kind, target_id)
    return NextAction(
        action_id=action_id,
        title=_title_from_summary(normalized_summary),
        summary=normalized_summary,
        kind=kind,
        priority=priority,
        severity=severity,
        safety_class=safety_class,
        target=NextActionTarget(kind=target_kind, target_id=target_id),
        supporting_evidence=list(supporting_evidence),
        missing_evidence=list(missing_evidence),
        stale_evidence=list(stale_evidence),
        limitations=list(dict.fromkeys(limitations)),
        recommended_surfaces=list(dict.fromkeys(recommended_surfaces)),
    )


def next_actions_from_summaries(
    summaries: Iterable[str],
    *,
    target_kind: NextActionTargetKind = NextActionTargetKind.UNKNOWN,
    target_id: str | None = None,
    kind: NextActionKind = NextActionKind.INSPECT,
    priority: NextActionPriority = NextActionPriority.RECOMMENDED,
    severity: NextActionSeverity = NextActionSeverity.INFO,
    safety_class: NextActionSafetyClass = NextActionSafetyClass.READ_ONLY,
    recommended_surfaces: Iterable[NextActionSurface] = (),
) -> list[NextAction]:
    """Convert existing string lists into stable typed next-action records."""

    actions: list[NextAction] = []
    seen: set[str] = set()
    for summary in summaries:
        normalized = summary.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        actions.append(
            next_action_from_summary(
                normalized,
                target_kind=target_kind,
                target_id=target_id,
                kind=kind,
                priority=priority,
                severity=severity,
                safety_class=safety_class,
                recommended_surfaces=recommended_surfaces,
            )
        )
    return actions


def next_action_from_command(
    display: str,
    *,
    target_kind: NextActionTargetKind = NextActionTargetKind.UNKNOWN,
    target_id: str | None = None,
    title: str | None = None,
    purpose: str = "Inspect the recommended status surface.",
    kind: NextActionKind = NextActionKind.INSPECT,
    priority: NextActionPriority = NextActionPriority.RECOMMENDED,
    severity: NextActionSeverity = NextActionSeverity.INFO,
    requires_approval: bool = False,
    supporting_evidence: Iterable[NextActionEvidenceRef] = (),
    limitations: Iterable[str] = (),
    recommended_surfaces: Iterable[NextActionSurface] = (),
) -> NextAction:
    """Build a typed next-action record for an existing CLI command string."""

    normalized_display = display.strip()
    command = _command_words(normalized_display)
    return NextAction(
        action_id=_action_id(normalized_display, target_kind, target_id),
        title=title or _title_from_summary(normalized_display),
        summary=purpose,
        kind=kind,
        priority=priority,
        severity=severity,
        safety_class=NextActionSafetyClass.COMMAND_RECIPE,
        target=NextActionTarget(kind=target_kind, target_id=target_id),
        command=NextActionCommandRecipe(
            command=command,
            display=normalized_display,
            purpose=purpose,
            requires_approval=requires_approval,
        ),
        supporting_evidence=list(supporting_evidence),
        limitations=list(dict.fromkeys(limitations)),
        recommended_surfaces=list(dict.fromkeys(recommended_surfaces)),
    )


def _action_id(
    summary: str,
    target_kind: NextActionTargetKind,
    target_id: str | None,
) -> str:
    digest = sha256(
        f"{target_kind.value}:{target_id or ''}:{summary}".encode()
    ).hexdigest()[:16]
    return f"next-action:{target_kind.value}:{digest}"


def _title_from_summary(summary: str) -> str:
    title = summary.strip().splitlines()[0]
    if len(title) <= 80:
        return title
    return f"{title[:77].rstrip()}..."


def _command_words(display: str) -> list[str]:
    try:
        words = shlex_split(display)
    except ValueError:
        words = display.split()
    return words or [display]


__all__ = [
    "next_action_from_command",
    "next_action_from_summary",
    "next_actions_from_summaries",
]
