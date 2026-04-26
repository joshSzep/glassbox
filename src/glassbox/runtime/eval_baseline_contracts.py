"""Expectation and release-contract helpers for eval baseline workflows."""

from typing import cast

from glassbox.runtime.eval_baseline_models import EvalExpectationMode
from glassbox.runtime.evals import EvalBaselineRefreshPolicy
from glassbox.runtime.evals import EvalCaseExpectation
from glassbox.runtime.evals import EvalCaseReleaseContract
from glassbox.runtime.evals import EvalCaseSeverity
from glassbox.runtime.evals import EvalInvariant
from glassbox.runtime.evals import EvalVerificationStage


def build_expectation(
    *,
    expectation_mode: str | None,
    invariants: list[str] | None,
) -> EvalCaseExpectation:
    if expectation_mode is None and invariants:
        expectation_mode = "selected_invariants"
    return EvalCaseExpectation(
        mode=cast(EvalExpectationMode, expectation_mode or "exact_match"),
        invariants=[cast(EvalInvariant, invariant) for invariant in invariants or []],
    )


def merge_expectation(
    existing: EvalCaseExpectation,
    *,
    expectation_mode: str | None,
    invariants: list[str] | None,
) -> EvalCaseExpectation:
    payload = existing.model_dump(mode="json")
    if expectation_mode is not None:
        payload["mode"] = expectation_mode
    if invariants is not None:
        payload["invariants"] = list(invariants)
        if expectation_mode is None:
            payload["mode"] = "selected_invariants"
    return EvalCaseExpectation.model_validate(payload)


def build_release_contract(
    *,
    owner: str | None,
    capabilities: list[str] | None,
    severity: str | None,
    verification_stages: list[str] | None,
    baseline_refresh_policy: str | None,
) -> EvalCaseReleaseContract:
    return EvalCaseReleaseContract(
        owner=owner,
        capabilities=list(capabilities or []),
        severity=cast(EvalCaseSeverity, severity or "medium"),
        verification_stages=[
            cast(EvalVerificationStage, stage)
            for stage in verification_stages or ["advisory"]
        ],
        baseline_refresh_policy=cast(
            EvalBaselineRefreshPolicy,
            baseline_refresh_policy or "review_required",
        ),
    )


def merge_release_contract(
    existing: EvalCaseReleaseContract,
    *,
    owner: str | None,
    capabilities: list[str] | None,
    severity: str | None,
    verification_stages: list[str] | None,
    baseline_refresh_policy: str | None,
) -> EvalCaseReleaseContract:
    payload = existing.model_dump(mode="json")
    if owner is not None:
        payload["owner"] = owner
    if capabilities is not None:
        payload["capabilities"] = list(capabilities)
    if severity is not None:
        payload["severity"] = severity
    if verification_stages is not None:
        payload["verification_stages"] = list(verification_stages)
    if baseline_refresh_policy is not None:
        payload["baseline_refresh_policy"] = baseline_refresh_policy
    return EvalCaseReleaseContract.model_validate(payload)


def validate_curated_release_contract(
    case_id: str,
    release_contract: EvalCaseReleaseContract,
) -> None:
    if not refresh_requires_acknowledgement(release_contract):
        return
    if release_contract.owner is None or not release_contract.capabilities:
        raise ValueError(
            "blocking or release-candidate eval case requires owner and "
            f"capabilities metadata before baseline updates: {case_id}"
        )


def refresh_requires_acknowledgement(
    release_contract: EvalCaseReleaseContract,
) -> bool:
    return bool(
        set(release_contract.verification_stages)
        & {"commit-time", "push-time", "release-candidate"}
    )
