"""Suite selection for repository-local replay eval cases."""

from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.runtime.eval_case_models import EvalCase
from glassbox.runtime.eval_constants import normalize_identifier
from glassbox.runtime.eval_discovery import discover_eval_case_files
from glassbox.runtime.eval_discovery import load_eval_case
from glassbox.runtime.eval_discovery import load_eval_profile
from glassbox.runtime.eval_profile_models import EvalProfileDefinition


class EvalSuiteSelection(BaseModel):
    """Resolved eval suite selection, including an optional named profile."""

    model_config = ConfigDict(extra="forbid")

    profile: EvalProfileDefinition | None = None
    cases: list[EvalCase] = Field(default_factory=list)


def load_eval_suite(
    workspace_root: Path,
    *,
    profile_id: str | None = None,
    case_ids: Sequence[str] | None = None,
    tags: Sequence[str] | None = None,
    cases_dir: Path | None = None,
    profiles_path: Path | None = None,
    validate_bundle_exists: bool = True,
) -> list[EvalCase]:
    """Load, normalize, and filter the repository-local eval suite."""

    return resolve_eval_suite_selection(
        workspace_root,
        profile_id=profile_id,
        case_ids=case_ids,
        tags=tags,
        cases_dir=cases_dir,
        profiles_path=profiles_path,
        validate_bundle_exists=validate_bundle_exists,
    ).cases


def resolve_eval_suite_selection(
    workspace_root: Path,
    *,
    profile_id: str | None = None,
    case_ids: Sequence[str] | None = None,
    tags: Sequence[str] | None = None,
    cases_dir: Path | None = None,
    profiles_path: Path | None = None,
    validate_bundle_exists: bool = True,
) -> EvalSuiteSelection:
    """Resolve one suite selection from optional profile, case, and tag filters."""

    workspace_root = workspace_root.resolve()
    loaded_cases = [
        load_eval_case(
            case_path,
            workspace_root=workspace_root,
            validate_bundle_exists=validate_bundle_exists,
        )
        for case_path in discover_eval_case_files(workspace_root, cases_dir=cases_dir)
    ]
    loaded_cases.sort(key=lambda case: case.case_id)

    profile: EvalProfileDefinition | None = None
    if profile_id is not None:
        profile = load_eval_profile(
            workspace_root,
            profile_id=profile_id,
            profiles_path=profiles_path,
        )
        loaded_cases = _select_cases_for_profile(loaded_cases, profile)

    if case_ids:
        loaded_cases = _filter_cases_by_case_ids(
            loaded_cases,
            case_ids,
            profile=profile,
        )

    if tags:
        loaded_cases = _filter_cases_by_tags(loaded_cases, tags)

    return EvalSuiteSelection(profile=profile, cases=loaded_cases)


def _select_cases_for_profile(
    loaded_cases: list[EvalCase],
    profile: EvalProfileDefinition,
) -> list[EvalCase]:
    selected_cases = loaded_cases
    if profile.case_ids:
        selected_cases = _filter_cases_by_case_ids(
            selected_cases,
            profile.case_ids,
            profile=profile,
            selection_scope="definition",
        )
        if profile.tags:
            required_tags = set(profile.tags)
            missing_tags = [
                case.case_id
                for case in selected_cases
                if not required_tags.issubset(set(case.tags))
            ]
            if missing_tags:
                raise ValueError(
                    f"eval profile {profile.profile_id} defines case ids missing "
                    f"required tag"
                    f"{'s' if len(required_tags) > 1 else ''}: "
                    + ", ".join(missing_tags)
                )

    if profile.tags:
        selected_cases = _filter_cases_by_tags(selected_cases, profile.tags)

    if profile.case_ids:
        missing_stage = [
            case.case_id
            for case in selected_cases
            if profile.verification_stage
            not in case.release_contract.verification_stages
        ]
        if missing_stage:
            raise ValueError(
                f"eval profile {profile.profile_id} includes case"
                f"{'s' if len(missing_stage) > 1 else ''} without verification stage "
                f"{profile.verification_stage}: " + ", ".join(missing_stage)
            )

    selected_cases = [
        case
        for case in selected_cases
        if profile.verification_stage in case.release_contract.verification_stages
    ]
    return selected_cases


def _filter_cases_by_case_ids(
    loaded_cases: list[EvalCase],
    case_ids: Sequence[str],
    *,
    profile: EvalProfileDefinition | None,
    selection_scope: Literal["selection", "definition"] = "selection",
) -> list[EvalCase]:
    normalized_case_ids = [
        normalize_identifier(case_id, kind="case_id") for case_id in case_ids
    ]
    cases_by_id = {case.case_id: case for case in loaded_cases}
    missing_case_ids = [
        case_id for case_id in normalized_case_ids if case_id not in cases_by_id
    ]
    if missing_case_ids:
        if profile is None:
            raise ValueError(
                "unknown eval case id"
                + ("s" if len(missing_case_ids) > 1 else "")
                + ": "
                + ", ".join(missing_case_ids)
            )
        scope_phrase = (
            "defines" if selection_scope == "definition" else "does not select"
        )
        raise ValueError(
            f"eval profile {profile.profile_id} {scope_phrase} eval case id"
            f"{'s' if len(missing_case_ids) > 1 else ''}: "
            + ", ".join(missing_case_ids)
        )
    return [cases_by_id[case_id] for case_id in normalized_case_ids]


def _filter_cases_by_tags(
    loaded_cases: list[EvalCase],
    tags: Sequence[str],
) -> list[EvalCase]:
    required_tags = {normalize_identifier(tag, kind="tag") for tag in tags}
    return [case for case in loaded_cases if required_tags.issubset(set(case.tags))]
