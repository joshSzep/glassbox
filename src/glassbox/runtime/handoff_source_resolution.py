"""Transport-agnostic handoff source-kind resolution."""

from collections.abc import Collection
from dataclasses import dataclass

HANDOFF_SOURCE_KINDS = ("session", "task", "changeset", "workspace", "release")
HANDOFF_SOURCE_KINDS_REQUIRING_ID = frozenset({"session", "task", "changeset"})
HANDOFF_PREPARE_SOURCE_KINDS = ("session", "changeset")


class HandoffSourceResolutionError(ValueError):
    """Raised when a handoff source kind or source ID is unsupported."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason


@dataclass(frozen=True)
class HandoffSourceResolution:
    """Normalized handoff source metadata shared by transports."""

    source_kind: str
    source_id: str | None
    source_id_required: bool

    def require_source_id(self) -> str:
        """Return source ID after resolution has validated it is present."""

        if self.source_id is None:
            raise HandoffSourceResolutionError(
                "missing-source-id",
                "source_id is required",
            )
        return self.source_id


def resolve_handoff_source(
    source_kind: str | None,
    source_id: str | None = None,
    *,
    supported_source_kinds: Collection[str] = HANDOFF_SOURCE_KINDS,
    source_id_required_for: Collection[str] = HANDOFF_SOURCE_KINDS_REQUIRING_ID,
) -> HandoffSourceResolution:
    """Normalize and validate handoff source kind and ID requirements."""

    normalized_kind = _normalize_source_kind(source_kind)
    supported = frozenset(supported_source_kinds)
    if normalized_kind not in supported:
        raise HandoffSourceResolutionError(
            "unsupported-source-kind",
            "unsupported handoff source",
        )
    source_id_required = normalized_kind in source_id_required_for
    normalized_source_id = _normalize_source_id(source_id)
    if source_id_required and normalized_source_id is None:
        raise HandoffSourceResolutionError(
            "missing-source-id",
            "source_id is required",
        )
    return HandoffSourceResolution(
        source_kind=normalized_kind,
        source_id=normalized_source_id,
        source_id_required=source_id_required,
    )


def resolve_handoff_prepare_source(
    source_kind: str | None,
) -> HandoffSourceResolution:
    """Normalize the source kinds supported by handoff prepare flows."""

    try:
        return resolve_handoff_source(
            source_kind,
            supported_source_kinds=HANDOFF_PREPARE_SOURCE_KINDS,
            source_id_required_for=(),
        )
    except HandoffSourceResolutionError as exc:
        raise HandoffSourceResolutionError(
            exc.reason,
            "specify a handoff prepare source",
        ) from exc


def _normalize_source_kind(source_kind: str | None) -> str:
    if source_kind is None or not source_kind.strip():
        raise HandoffSourceResolutionError(
            "missing-source-kind",
            "source_kind is required",
        )
    return source_kind.strip().lower()


def _normalize_source_id(source_id: str | None) -> str | None:
    if source_id is None:
        return None
    stripped = source_id.strip()
    return stripped or None


__all__ = [
    "HANDOFF_PREPARE_SOURCE_KINDS",
    "HANDOFF_SOURCE_KINDS",
    "HANDOFF_SOURCE_KINDS_REQUIRING_ID",
    "HandoffSourceResolution",
    "HandoffSourceResolutionError",
    "resolve_handoff_prepare_source",
    "resolve_handoff_source",
]
