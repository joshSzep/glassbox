"""Profile row detail helpers for eval recommendations."""

from glassbox.runtime.evals import EvalProfileDefinition


def profile_safe_next_commands(profile: EvalProfileDefinition) -> list[str]:
    """Return safe CLI commands for deterministic profile execution."""

    if profile.track == "live-provider-canary":
        return []
    return [f"uv run glassbox eval run --profile {profile.profile_id} --cwd ."]


def profile_budget_implications(profile: EvalProfileDefinition) -> list[str]:
    """Summarize profile budget posture for recommendation output."""

    implications: list[str] = []
    if profile.blocking:
        implications.append("Profile is blocking for its verification stage.")
    else:
        implications.append("Profile is non-blocking advisory guidance.")
    if profile.track == "live-provider-canary":
        implications.append(
            "Live-provider canary profiles require explicit operator selection."
        )
    if profile.budget is None:
        return implications

    budget = profile.budget
    if budget.max_selected_case_count is not None:
        implications.append(
            f"Budget allows up to {budget.max_selected_case_count} selected cases."
        )
    if budget.max_recorded_model_call_count is not None:
        implications.append(
            "Budget allows up to "
            f"{budget.max_recorded_model_call_count} recorded model calls."
        )
    if budget.allow_advisory_cases is not None:
        posture = "allows" if budget.allow_advisory_cases else "excludes"
        implications.append(f"Budget {posture} advisory cases.")
    return implications


__all__ = ["profile_budget_implications", "profile_safe_next_commands"]
