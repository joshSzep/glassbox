"""Verification plan enum contracts shared across Glassbox surfaces."""

from enum import StrEnum


class VerificationCheckKind(StrEnum):
    """Supported verification check families."""

    COMMAND = "command"
    TEST = "test"
    EVAL = "eval"
    LINT = "lint"
    TYPECHECK = "typecheck"
    PACKAGE = "package"
    CUSTOM = "custom"


class VerificationPlanSource(StrEnum):
    """Signals used to select a verification plan entry."""

    CHANGESET_INVENTORY = "changeset_inventory"
    COMMAND_RECIPE = "command_recipe"
    EVAL_RECOMMENDATION = "eval_recommendation"
    MANUAL_EVIDENCE = "manual_evidence"
    RELEASE_GATE = "release_gate"
    REPOSITORY_INTELLIGENCE = "repository_intelligence"
    WORKSPACE_PROFILE = "workspace_profile"
    CHANGED_PATHS = "changed_paths"
    TASK_TYPE = "task_type"
    POLICY_BUDGET = "policy_budget"
    OPERATOR = "operator"


class VerificationPlanLifecycleState(StrEnum):
    """Reviewable lifecycle states for planned verification checks."""

    PROPOSED = "proposed"
    SELECTED = "selected"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    STALE = "stale"
    SUPERSEDED = "superseded"
    ACCEPTED_RISK = "accepted-risk"
    MANUAL_ONLY = "manual-only"
    BLOCKED = "blocked"


class VerificationFailureCategory(StrEnum):
    """Evidence-based categories for verification failure output."""

    ASSERTION = "assertion"
    LINT = "lint"
    TYPECHECK = "typecheck"
    PACKAGE = "package"
    POLICY = "policy"
    BUDGET = "budget"
    TIMEOUT = "timeout"
    INFRASTRUCTURE = "infrastructure"
    FLAKY = "flaky"
    UNKNOWN = "unknown"


__all__ = [
    "VerificationCheckKind",
    "VerificationFailureCategory",
    "VerificationPlanLifecycleState",
    "VerificationPlanSource",
]
