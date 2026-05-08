"""Shared helpers for advisory review-loop readiness signals."""

from collections.abc import Iterable
from collections.abc import Sequence
from typing import Protocol
from typing import TypeVar

from glassbox.core import ChangesetReadinessKind
from glassbox.core import ChangesetReadinessRecord

StateT = TypeVar("StateT")


class ReadinessSignalLike(Protocol[StateT]):
    """Structural signal shape shared by commit and handoff readiness."""

    signal_id: str
    state: StateT
    summary: str
    blocking: bool
    paths: list[str]


def blocking_signal_summaries[StateT](
    signals: Sequence[ReadinessSignalLike[StateT]],
    *,
    limit: int | None = None,
) -> list[str]:
    """Return summaries for blocking signals, preserving signal order."""

    summaries = [signal.summary for signal in signals if signal.blocking]
    if limit is None:
        return summaries
    return summaries[:limit]


def first_blocking_state[StateT](
    signals: Sequence[ReadinessSignalLike[StateT]],
    precedence: Sequence[StateT],
) -> StateT | None:
    """Return the highest-priority blocking state, if any."""

    blocking_states = [signal.state for signal in signals if signal.blocking]
    for state in precedence:
        if state in blocking_states:
            return state
    return None


def has_signal_state[StateT](
    signals: Sequence[ReadinessSignalLike[StateT]],
    state: StateT,
) -> bool:
    """Return whether any signal has the given state."""

    return any(signal.state == state for signal in signals)


def signal_ids[StateT](signals: Sequence[ReadinessSignalLike[StateT]]) -> set[str]:
    """Return all signal identifiers in a readiness signal list."""

    return {signal.signal_id for signal in signals}


def has_signal_id[StateT](
    signals: Sequence[ReadinessSignalLike[StateT]],
    signal_id: str,
) -> bool:
    """Return whether a readiness signal list contains the exact identifier."""

    return any(signal.signal_id == signal_id for signal in signals)


def has_signal_prefix[StateT](
    signals: Sequence[ReadinessSignalLike[StateT]],
    prefix: str,
) -> bool:
    """Return whether a readiness signal list contains an identifier prefix."""

    return any(signal.signal_id.startswith(prefix) for signal in signals)


def limitations_for_signal_ids[StateT](
    signals: Sequence[ReadinessSignalLike[StateT]],
    limitation_by_signal_id: Iterable[tuple[str, str]],
    *,
    limit: int = 20,
) -> list[str]:
    """Return ordered limitation text for matching signal identifiers."""

    ids = signal_ids(signals)
    limitations = [
        limitation
        for signal_id, limitation in limitation_by_signal_id
        if signal_id in ids
    ]
    return limitations[:limit]


def dedupe_actions(actions: Sequence[str], *, limit: int = 20) -> list[str]:
    """Return non-empty actions in first-seen order."""

    return list(dict.fromkeys(action for action in actions if action))[:limit]


def latest_readiness(
    readiness: Sequence[ChangesetReadinessRecord],
    kind: ChangesetReadinessKind,
) -> ChangesetReadinessRecord | None:
    """Return the latest projected readiness record for a readiness kind."""

    for item in readiness:
        if item.readiness_kind == kind:
            return item
    return None


__all__ = [
    "ReadinessSignalLike",
    "blocking_signal_summaries",
    "dedupe_actions",
    "first_blocking_state",
    "has_signal_id",
    "has_signal_prefix",
    "has_signal_state",
    "latest_readiness",
    "limitations_for_signal_ids",
    "signal_ids",
]
