"""Changeset-derived rows for the unified operator queue.

The current workspace queue aggregate does not load changeset detail,
verification, inventory, feedback, or handoff inputs. Keep this boundary
explicit and empty rather than fabricating changeset authority from session
summary rows.
"""

from glassbox.core import OperatorQueueItem


def build_changeset_queue_items() -> list[OperatorQueueItem]:
    """Return current changeset queue rows from existing aggregate inputs."""

    return []


__all__ = ["build_changeset_queue_items"]
