"""Source-range planning for deterministic context compactions."""

from dataclasses import dataclass

from glassbox.core.events import EventEnvelope
from glassbox.runtime.context_compaction import CONTEXT_COMPACTION_SOURCE_REFERENCE_CAP


@dataclass(frozen=True)
class ContextCompactionSuggestedRange:
    """A bounded source range that can fit the compaction artifact contract."""

    label: str
    source_start_sequence: int
    source_end_sequence: int
    selected_event_count: int

    def to_json_payload(self) -> dict[str, int | str]:
        return {
            "label": self.label,
            "source_start_sequence": self.source_start_sequence,
            "source_end_sequence": self.source_end_sequence,
            "selected_event_count": self.selected_event_count,
        }


class ContextCompactionRangeError(ValueError):
    """Raised when a requested range cannot fit source-reference limits."""

    def __init__(
        self,
        *,
        selected_event_count: int,
        source_reference_cap: int,
        source_start_sequence: int,
        source_end_sequence: int,
        suggested_ranges: list[ContextCompactionSuggestedRange],
    ) -> None:
        self.selected_event_count = selected_event_count
        self.source_reference_cap = source_reference_cap
        self.source_start_sequence = source_start_sequence
        self.source_end_sequence = source_end_sequence
        self.suggested_ranges = suggested_ranges
        super().__init__(self._message())

    def _message(self) -> str:
        suggestions = "; ".join(
            (
                f"{item.label} {item.source_start_sequence}-"
                f"{item.source_end_sequence} ({item.selected_event_count} event(s))"
            )
            for item in self.suggested_ranges
        )
        return (
            "Selected source range contains "
            f"{self.selected_event_count} event(s), but context compaction "
            f"artifacts support at most {self.source_reference_cap} source "
            "reference(s). Retry with a bounded range"
            f"{': ' + suggestions if suggestions else '.'}"
        )

    def to_json_payload(self) -> dict[str, object]:
        return {
            "error": "source_range_exceeds_cap",
            "message": str(self),
            "selected_event_count": self.selected_event_count,
            "source_reference_cap": self.source_reference_cap,
            "source_start_sequence": self.source_start_sequence,
            "source_end_sequence": self.source_end_sequence,
            "suggested_ranges": [
                item.to_json_payload() for item in self.suggested_ranges
            ],
        }


def validate_source_range_within_reference_cap(
    source_events: list[EventEnvelope],
    *,
    source_start_sequence: int,
    source_end_sequence: int,
) -> None:
    """Reject source ranges that cannot fit the artifact provenance cap."""

    selected_event_count = len(source_events)
    if selected_event_count <= CONTEXT_COMPACTION_SOURCE_REFERENCE_CAP:
        return

    raise ContextCompactionRangeError(
        selected_event_count=selected_event_count,
        source_reference_cap=CONTEXT_COMPACTION_SOURCE_REFERENCE_CAP,
        source_start_sequence=source_start_sequence,
        source_end_sequence=source_end_sequence,
        suggested_ranges=suggest_bounded_ranges(
            source_events,
            cap=CONTEXT_COMPACTION_SOURCE_REFERENCE_CAP,
        ),
    )


def suggest_bounded_ranges(
    source_events: list[EventEnvelope],
    *,
    cap: int,
) -> list[ContextCompactionSuggestedRange]:
    """Suggest first/latest event ranges that fit the configured source cap."""

    suggestions: list[ContextCompactionSuggestedRange] = []
    seen: set[tuple[int, int]] = set()
    for label, bounded_events in (
        ("first", source_events[:cap]),
        ("latest", source_events[-cap:]),
    ):
        if not bounded_events:
            continue
        start = bounded_events[0].sequence
        end = bounded_events[-1].sequence
        key = (start, end)
        if key in seen:
            continue
        seen.add(key)
        suggestions.append(
            ContextCompactionSuggestedRange(
                label=label,
                source_start_sequence=start,
                source_end_sequence=end,
                selected_event_count=len(bounded_events),
            )
        )
    return suggestions


__all__ = [
    "ContextCompactionRangeError",
    "ContextCompactionSuggestedRange",
    "suggest_bounded_ranges",
    "validate_source_range_within_reference_cap",
]
