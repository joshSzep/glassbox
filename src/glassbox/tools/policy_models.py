"""Shared tool-policy context and internal decision models."""

from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core import ApprovalMode
from glassbox.core import AutonomyBudget
from glassbox.core import AutonomyMode
from glassbox.core.models import PolicyDecisionSourceKind
from glassbox.tools.policy_config import ToolAutonomyPolicyAction
from glassbox.tools.policy_config import ToolPolicyAction
from glassbox.tools.policy_config import ToolPolicyManifest


class ToolPolicyContext(BaseModel):
    """Inputs required to evaluate one tool request against local policy."""

    model_config = ConfigDict(extra="forbid")

    workspace_root: Path
    approval_mode: ApprovalMode
    autonomy_mode: AutonomyMode = AutonomyMode.MANUAL
    autonomy_budget: AutonomyBudget | None = None
    policy_manifest: ToolPolicyManifest = Field(default_factory=ToolPolicyManifest)


@dataclass(frozen=True, slots=True)
class ResolvedPolicyOutcome:
    """Resolved tool-policy outcome before approval-mode handling."""

    action: ToolPolicyAction
    source_kind: PolicyDecisionSourceKind
    source_label: str
    autonomy_action: ToolAutonomyPolicyAction | None = None
    budget_field: str | None = None


@dataclass(frozen=True, slots=True)
class PolicyDecisionMessages:
    """Stable reason strings for one policy decision branch."""

    allow_reason: str
    deny_reason: str
    approval_reason: str
    blocked_reason: str
