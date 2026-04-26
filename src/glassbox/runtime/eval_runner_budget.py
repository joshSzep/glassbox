"""Profile-budget evaluation for replay-backed eval suites."""

import json
from pathlib import Path

from glassbox.runtime.eval_runner_models import EvalCaseResult
from glassbox.runtime.eval_runner_models import EvalProfileBudgetEnforcement
from glassbox.runtime.eval_runner_models import EvalProfileBudgetHealth
from glassbox.runtime.eval_runner_models import EvalProfileBudgetStatus
from glassbox.runtime.eval_runner_models import EvalProfileBudgetViolation
from glassbox.runtime.evals import EvalCase
from glassbox.runtime.evals import EvalProfileBudget
from glassbox.runtime.evals import EvalProfileDefinition


def evaluate_profile_budget(
    *,
    profile: EvalProfileDefinition | None,
    eval_cases: list[EvalCase],
    case_results: list[EvalCaseResult],
) -> EvalProfileBudgetHealth | None:
    if profile is None or profile.budget is None:
        return None

    budget = profile.budget
    enforcement: EvalProfileBudgetEnforcement = (
        "enforced" if profile.blocking else "warning"
    )
    selected_invariant_case_ids = [
        case.case_id
        for case in eval_cases
        if case.expectation.mode == "selected_invariants"
    ]
    advisory_case_ids = [
        case.case_id
        for case in eval_cases
        if case.release_contract.baseline_refresh_policy == "advisory"
    ]
    unsupported_case_ids = [
        case_result.case_id
        for case_result in case_results
        if case_result.replay_outcome == "unsupported_session"
    ]
    recorded_model_call_count = sum(
        _bundle_model_call_count(case.bundle_path) for case in eval_cases
    )
    case_artifact_bytes = sum(
        case_result.artifact_path.stat().st_size
        for case_result in case_results
        if case_result.artifact_path.is_file()
    )
    allow_unsupported_cases = _effective_allow_unsupported_cases(profile, budget)
    allow_advisory_cases = _effective_allow_advisory_cases(profile, budget)

    violations: list[EvalProfileBudgetViolation] = []
    if (
        budget.max_selected_case_count is not None
        and len(eval_cases) > budget.max_selected_case_count
    ):
        violations.append(
            EvalProfileBudgetViolation(
                code="selected_case_count",
                message=(
                    f"selected case count {len(eval_cases)} exceeds profile budget "
                    f"{budget.max_selected_case_count}"
                ),
                actual=len(eval_cases),
                limit=budget.max_selected_case_count,
                case_ids=[case.case_id for case in eval_cases],
            )
        )
    if (
        budget.max_selected_invariant_case_count is not None
        and len(selected_invariant_case_ids) > budget.max_selected_invariant_case_count
    ):
        violations.append(
            EvalProfileBudgetViolation(
                code="selected_invariant_case_count",
                message=(
                    "selected-invariant case count "
                    f"{len(selected_invariant_case_ids)} exceeds profile budget "
                    f"{budget.max_selected_invariant_case_count}"
                ),
                actual=len(selected_invariant_case_ids),
                limit=budget.max_selected_invariant_case_count,
                case_ids=selected_invariant_case_ids,
            )
        )
    if (
        budget.max_recorded_model_call_count is not None
        and recorded_model_call_count > budget.max_recorded_model_call_count
    ):
        violations.append(
            EvalProfileBudgetViolation(
                code="recorded_model_call_count",
                message=(
                    f"recorded model-call count {recorded_model_call_count} exceeds "
                    f"profile budget {budget.max_recorded_model_call_count}"
                ),
                actual=recorded_model_call_count,
                limit=budget.max_recorded_model_call_count,
                case_ids=[case.case_id for case in eval_cases],
            )
        )
    if (
        budget.max_case_artifact_bytes is not None
        and case_artifact_bytes > budget.max_case_artifact_bytes
    ):
        violations.append(
            EvalProfileBudgetViolation(
                code="case_artifact_bytes",
                message=(
                    f"case artifact bytes {case_artifact_bytes} exceed profile budget "
                    f"{budget.max_case_artifact_bytes}"
                ),
                actual=case_artifact_bytes,
                limit=budget.max_case_artifact_bytes,
                case_ids=[case_result.case_id for case_result in case_results],
            )
        )
    if advisory_case_ids and not allow_advisory_cases:
        violations.append(
            EvalProfileBudgetViolation(
                code="advisory_cases",
                message=(
                    "profile budget disallows advisory baseline cases: "
                    + ", ".join(advisory_case_ids)
                ),
                actual=len(advisory_case_ids),
                limit=0,
                case_ids=advisory_case_ids,
            )
        )
    if unsupported_case_ids and not allow_unsupported_cases:
        violations.append(
            EvalProfileBudgetViolation(
                code="unsupported_cases",
                message=(
                    "profile budget disallows unsupported replay cases: "
                    + ", ".join(unsupported_case_ids)
                ),
                actual=len(unsupported_case_ids),
                limit=0,
                case_ids=unsupported_case_ids,
            )
        )

    status: EvalProfileBudgetStatus = "ok"
    if violations:
        status = "violated" if enforcement == "enforced" else "warning"

    return EvalProfileBudgetHealth(
        status=status,
        enforcement=enforcement,
        max_selected_case_count=budget.max_selected_case_count,
        selected_case_count=len(eval_cases),
        max_selected_invariant_case_count=budget.max_selected_invariant_case_count,
        selected_invariant_case_count=len(selected_invariant_case_ids),
        max_recorded_model_call_count=budget.max_recorded_model_call_count,
        recorded_model_call_count=recorded_model_call_count,
        max_case_artifact_bytes=budget.max_case_artifact_bytes,
        case_artifact_bytes=case_artifact_bytes,
        allow_unsupported_cases=allow_unsupported_cases,
        unsupported_case_count=len(unsupported_case_ids),
        allow_advisory_cases=allow_advisory_cases,
        advisory_case_count=len(advisory_case_ids),
        promotion_policy=budget.promotion_policy,
        demotion_policy=budget.demotion_policy,
        violations=violations,
    )


def _effective_allow_unsupported_cases(
    profile: EvalProfileDefinition,
    budget: EvalProfileBudget,
) -> bool:
    if budget.allow_unsupported_cases is not None:
        return budget.allow_unsupported_cases
    return not profile.blocking


def _effective_allow_advisory_cases(
    profile: EvalProfileDefinition,
    budget: EvalProfileBudget,
) -> bool:
    if budget.allow_advisory_cases is not None:
        return budget.allow_advisory_cases
    return not profile.blocking


def _bundle_model_call_count(bundle_path: Path) -> int:
    try:
        payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    except FileNotFoundError, ValueError:
        return 0
    model_calls = payload.get("model_calls")
    if isinstance(model_calls, list):
        return len(model_calls)
    return 0
