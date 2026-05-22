"""Markdown rendering wrapper for reviewer-safe changeset exports."""

from typing import Any

from glassbox.runtime.handoff_markdown import (
    build_changeset_export_markdown as render_changeset_export_markdown,
)


def build_changeset_export_markdown(payload: Any) -> str:
    """Render a compact reviewer-safe Markdown summary."""

    return render_changeset_export_markdown(payload)


__all__ = [
    "build_changeset_export_markdown",
]
