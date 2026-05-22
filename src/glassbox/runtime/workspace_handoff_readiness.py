"""Workspace and release-candidate v17 handoff readiness facade."""

from glassbox.runtime.workspace_handoff_readiness_release import (
    derive_release_handoff_readiness,
)
from glassbox.runtime.workspace_handoff_readiness_workspace import (
    derive_workspace_handoff_readiness,
)

__all__ = [
    "derive_release_handoff_readiness",
    "derive_workspace_handoff_readiness",
]
