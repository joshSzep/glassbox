"""Change-impact recommendations for replay-backed eval cases and profiles."""

from fnmatch import fnmatch
from pathlib import Path
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

from glassbox.runtime.eval_coverage import DEFAULT_EVAL_COVERAGE_PATH
from glassbox.runtime.eval_coverage import EvalCapabilityDefinition
from glassbox.runtime.eval_coverage import load_eval_coverage_manifest
from glassbox.runtime.evals import EvalCase
from glassbox.runtime.evals import EvalProfileDefinition
from glassbox.runtime.evals import EvalProfileTrack
from glassbox.runtime.evals import _ensure_path_within_root
from glassbox.runtime.evals import _normalize_identifier
from glassbox.runtime.evals import discover_eval_case_files
from glassbox.runtime.evals import load_eval_case
from glassbox.runtime.evals import load_eval_profiles

EVAL_IMPACT_MANIFEST_VERSION = 1
DEFAULT_EVAL_IMPACT_PATH = Path("evals") / "impact.json"

type EvalRecommendationConfidence = Literal[
    "direct",
    "owner-derived",
    "capability-derived",
    "stage-derived",
    "fallback",
]

_CONFIDENCE_PRIORITY: dict[EvalRecommendationConfidence, int] = {
    "direct": 5,
    "owner-derived": 4,
    "capability-derived": 3,
    "stage-derived": 2,
    "fallback": 1,
}


class EvalImpactRule(BaseModel):
    """Repository-owned path heuristics for replay/eval change impact."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str
    title: str
    path_globs: list[str] = Field(default_factory=list)
    owners: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    case_ids: list[str] = Field(default_factory=list)
    profile_ids: list[str] = Field(default_factory=list)
    notes: str | None = None

    @field_validator("rule_id")
    @classmethod
    def validate_rule_id(cls, value: str) -> str:
        return _normalize_identifier(value, kind="rule_id")

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("title must not be empty")
        return title

    @field_validator("path_globs")
    @classmethod
    def validate_path_globs(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for item in value:
            candidate = item.strip()
            if not candidate:
                raise ValueError("path_globs entries must not be empty")
            if candidate not in normalized:
                normalized.append(candidate)
        return normalized

    @field_validator("owners")
    @classmethod
    def validate_owners(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for owner in value:
            candidate = _normalize_identifier(owner, kind="owner")
            if candidate not in normalized:
                normalized.append(candidate)
        return normalized

    @field_validator("capabilities")
    @classmethod
    def validate_capabilities(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for capability in value:
            candidate = _normalize_identifier(capability, kind="capability_id")
            if candidate not in normalized:
                normalized.append(candidate)
        return normalized

    @field_validator("case_ids")
    @classmethod
    def validate_case_ids(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for case_id in value:
            candidate = _normalize_identifier(case_id, kind="case_id")
            if candidate not in normalized:
                normalized.append(candidate)
        return normalized

    @field_validator("profile_ids")
    @classmethod
    def validate_profile_ids(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for profile_id in value:
            candidate = _normalize_identifier(profile_id, kind="profile_id")
            if candidate not in normalized:
                normalized.append(candidate)
        return normalized

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        notes = value.strip()
        return notes or None

    @model_validator(mode="after")
    def validate_rule_targets(self) -> EvalImpactRule:
        if not self.path_globs:
            raise ValueError("impact rule must declare at least one path glob")
        if not any([self.owners, self.capabilities, self.case_ids, self.profile_ids]):
            raise ValueError(
                "impact rule must declare at least one owner, capability, "
                "case, or profile target"
            )
        return self


class EvalImpactManifest(BaseModel):
    """On-disk manifest for repository-owned replay/eval impact rules."""

    model_config = ConfigDict(extra="forbid")

    manifest_version: int = EVAL_IMPACT_MANIFEST_VERSION
    rules: list[EvalImpactRule] = Field(default_factory=list)

    @field_validator("manifest_version")
    @classmethod
    def validate_manifest_version(cls, value: int) -> int:
        if value != EVAL_IMPACT_MANIFEST_VERSION:
            raise ValueError(f"unsupported eval impact manifest version: {value}")
        return value

    @field_validator("rules")
    @classmethod
    def validate_rules(cls, value: list[EvalImpactRule]) -> list[EvalImpactRule]:
        seen_rule_ids: set[str] = set()
        for rule in value:
            if rule.rule_id in seen_rule_ids:
                raise ValueError(f"duplicate eval impact rule id: {rule.rule_id}")
            seen_rule_ids.add(rule.rule_id)
        return value


class EvalRecommendationReason(BaseModel):
    """One explanation for why a case or profile was recommended."""

    model_config = ConfigDict(extra="forbid")

    confidence: EvalRecommendationConfidence
    summary: str
    matched_path: str | None = None
    rule_id: str | None = None
    owner: str | None = None
    capability_id: str | None = None
    verification_stage: str | None = None


class EvalCaseRecommendation(BaseModel):
    """Recommended replay/eval case for one change set."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    title: str
    confidence: EvalRecommendationConfidence
    owner: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    verification_stages: list[str] = Field(default_factory=list)
    reasons: list[EvalRecommendationReason] = Field(default_factory=list)


class EvalProfileRecommendation(BaseModel):
    """Recommended eval profile for one change set."""

    model_config = ConfigDict(extra="forbid")

    profile_id: str
    title: str
    confidence: EvalRecommendationConfidence
    verification_stage: str
    track: EvalProfileTrack
    blocking: bool
    reasons: list[EvalRecommendationReason] = Field(default_factory=list)


class EvalRecommendationReport(BaseModel):
    """Structured replay/eval recommendation report for one change set."""

    model_config = ConfigDict(extra="forbid")

    workspace_root: Path
    touched_paths: list[str] = Field(default_factory=list)
    matched_rule_ids: list[str] = Field(default_factory=list)
    unmatched_paths: list[str] = Field(default_factory=list)
    coverage_audit_recommended: bool = False
    warnings: list[str] = Field(default_factory=list)
    cases: list[EvalCaseRecommendation] = Field(default_factory=list)
    profiles: list[EvalProfileRecommendation] = Field(default_factory=list)
    suggested_commands: list[str] = Field(default_factory=list)


class _PathRuleMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule: EvalImpactRule
    matched_path: str


def recommend_eval_change_impact(
    workspace_root: Path,
    *,
    touched_paths: list[str],
    impact_path: Path | None = None,
    coverage_path: Path | None = None,
) -> EvalRecommendationReport:
    """Recommend replay/eval cases and profiles for one changed path set."""

    resolved_workspace_root = workspace_root.resolve()
    normalized_paths = [
        _normalize_touched_path(resolved_workspace_root, touched_path)
        for touched_path in touched_paths
    ]

    cases = _load_all_eval_cases(resolved_workspace_root)
    cases_by_id = {case.case_id: case for case in cases}
    case_paths = {
        str(case.case_path.relative_to(resolved_workspace_root)).replace("\\", "/"): (
            case
        )
        for case in cases
    }
    profiles = [
        profile
        for profile in load_eval_profiles(resolved_workspace_root)
        if profile.track == "deterministic"
    ]
    profiles_by_id = {profile.profile_id: profile for profile in profiles}
    capabilities = _load_capabilities(
        resolved_workspace_root,
        coverage_path=coverage_path,
    )
    capabilities_by_id = {
        capability.capability_id: capability for capability in capabilities
    }
    impact_manifest = maybe_load_eval_impact_manifest(
        resolved_workspace_root,
        impact_path=impact_path,
    )
    rules = [] if impact_manifest is None else impact_manifest.rules

    case_reasons: dict[str, list[EvalRecommendationReason]] = {}
    profile_reasons: dict[str, list[EvalRecommendationReason]] = {}
    matched_rule_ids: set[str] = set()
    matched_paths: set[str] = set()
    warnings: list[str] = []
    coverage_audit_recommended = False

    for touched_path in normalized_paths:
        if touched_path in case_paths:
            case = case_paths[touched_path]
            _add_reason(
                case_reasons,
                case.case_id,
                EvalRecommendationReason(
                    confidence="direct",
                    summary=f"touched eval case manifest {touched_path}",
                    matched_path=touched_path,
                ),
            )
            matched_paths.add(touched_path)

        if touched_path == str(DEFAULT_EVAL_COVERAGE_PATH):
            coverage_audit_recommended = True
            warnings.append(
                "Touched eval coverage manifest; run eval audit because "
                "capability-to-case expectations may have changed."
            )
            matched_paths.add(touched_path)

        if touched_path == str(DEFAULT_EVAL_IMPACT_PATH):
            warnings.append(
                "Touched eval impact manifest; review recommendations as "
                "metadata-driven guidance."
            )
            matched_paths.add(touched_path)

        if touched_path == str(Path("evals") / "profiles.json"):
            for profile in profiles:
                _add_reason(
                    profile_reasons,
                    profile.profile_id,
                    EvalRecommendationReason(
                        confidence="direct",
                        summary=f"touched eval profile manifest {touched_path}",
                        matched_path=touched_path,
                    ),
                )
            matched_paths.add(touched_path)

    rule_matches = _match_rules(normalized_paths, rules)
    matched_rule_ids.update(match.rule.rule_id for match in rule_matches)
    matched_paths.update(match.matched_path for match in rule_matches)

    matched_owners: dict[str, list[_PathRuleMatch]] = {}
    matched_capabilities: dict[str, list[_PathRuleMatch]] = {}

    for match in rule_matches:
        rule = match.rule
        for case_id in rule.case_ids:
            if case_id in cases_by_id:
                _add_reason(
                    case_reasons,
                    case_id,
                    EvalRecommendationReason(
                        confidence="direct",
                        summary=(
                            f"impact rule {rule.rule_id} matched "
                            f"{match.matched_path} and names case {case_id}"
                        ),
                        matched_path=match.matched_path,
                        rule_id=rule.rule_id,
                    ),
                )

        for profile_id in rule.profile_ids:
            profile = profiles_by_id.get(profile_id)
            if profile is None:
                continue
            _add_reason(
                profile_reasons,
                profile_id,
                EvalRecommendationReason(
                    confidence="direct",
                    summary=(
                        f"impact rule {rule.rule_id} matched "
                        f"{match.matched_path} and names profile {profile_id}"
                    ),
                    matched_path=match.matched_path,
                    rule_id=rule.rule_id,
                ),
            )

        for owner in rule.owners:
            matched_owners.setdefault(owner, []).append(match)
        for capability in rule.capabilities:
            matched_capabilities.setdefault(capability, []).append(match)

    for owner, owner_matches in matched_owners.items():
        owner_cases = [case for case in cases if case.release_contract.owner == owner]
        for case in owner_cases:
            for match in owner_matches:
                _add_reason(
                    case_reasons,
                    case.case_id,
                    EvalRecommendationReason(
                        confidence="owner-derived",
                        summary=(
                            f"impact rule {match.rule.rule_id} matched "
                            f"{match.matched_path} and maps to owner {owner}"
                        ),
                        matched_path=match.matched_path,
                        rule_id=match.rule.rule_id,
                        owner=owner,
                    ),
                )

    for capability_id, capability_matches in matched_capabilities.items():
        capability = capabilities_by_id.get(capability_id)
        capability_case_ids: set[str] = set()
        if capability is not None:
            capability_case_ids.update(capability.expected_case_ids)
        capability_case_ids.update(
            case.case_id
            for case in cases
            if capability_id in case.release_contract.capabilities
        )
        for case_id in sorted(capability_case_ids):
            if case_id not in cases_by_id:
                continue
            for match in capability_matches:
                _add_reason(
                    case_reasons,
                    case_id,
                    EvalRecommendationReason(
                        confidence="capability-derived",
                        summary=(
                            f"impact rule {match.rule.rule_id} matched "
                            f"{match.matched_path} and maps to capability "
                            f"{capability_id}"
                        ),
                        matched_path=match.matched_path,
                        rule_id=match.rule.rule_id,
                        capability_id=capability_id,
                    ),
                )

    impacted_stages: set[str] = set()
    for case_id, reasons in case_reasons.items():
        del reasons
        impacted_stages.update(
            cases_by_id[case_id].release_contract.verification_stages
        )
    for capability_id in matched_capabilities:
        capability = capabilities_by_id.get(capability_id)
        if capability is not None:
            impacted_stages.update(capability.verification_stages)

    for profile in profiles:
        if profile.verification_stage not in impacted_stages:
            continue
        _add_reason(
            profile_reasons,
            profile.profile_id,
            EvalRecommendationReason(
                confidence="stage-derived",
                summary=(
                    f"verification stage {profile.verification_stage} is "
                    "impacted by the matched cases or capabilities"
                ),
                verification_stage=profile.verification_stage,
            ),
        )

    if not case_reasons and not profile_reasons:
        fallback_profiles = [
            profile
            for profile in profiles
            if profile.verification_stage == "commit-time" and profile.blocking
        ]
        runtime_like_change = any(path.startswith("src/") for path in normalized_paths)
        if runtime_like_change and fallback_profiles:
            for profile in fallback_profiles:
                _add_reason(
                    profile_reasons,
                    profile.profile_id,
                    EvalRecommendationReason(
                        confidence="fallback",
                        summary=(
                            "no stronger replay/eval mapping was found; use "
                            "the smallest deterministic commit-time profile "
                            "as a conservative fallback"
                        ),
                    ),
                )
        elif not warnings:
            warnings.append(
                "No confident replay or eval recommendation was found for "
                "the touched paths."
            )

    case_recommendations = _build_case_recommendations(cases_by_id, case_reasons)
    profile_recommendations = _build_profile_recommendations(
        profiles_by_id,
        profile_reasons,
    )
    unmatched_paths = [path for path in normalized_paths if path not in matched_paths]
    suggested_commands = _build_suggested_commands(
        case_recommendations,
        profile_recommendations,
        coverage_audit_recommended=coverage_audit_recommended,
    )

    return EvalRecommendationReport(
        workspace_root=resolved_workspace_root,
        touched_paths=normalized_paths,
        matched_rule_ids=sorted(matched_rule_ids),
        unmatched_paths=unmatched_paths,
        coverage_audit_recommended=coverage_audit_recommended,
        warnings=_dedupe_strings(warnings),
        cases=case_recommendations,
        profiles=profile_recommendations,
        suggested_commands=suggested_commands,
    )


def load_eval_impact_manifest(
    workspace_root: Path,
    *,
    impact_path: Path | None = None,
) -> EvalImpactManifest:
    """Load repository-owned replay/eval impact rules from disk."""

    resolved_impact_path = _resolve_impact_path(workspace_root, impact_path=impact_path)
    try:
        raw_manifest = resolved_impact_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(
            f"missing eval impact manifest: {resolved_impact_path}"
        ) from exc

    try:
        manifest = EvalImpactManifest.model_validate_json(raw_manifest)
    except ValueError as exc:
        raise ValueError(
            f"invalid eval impact manifest {resolved_impact_path}: {exc}"
        ) from exc

    _ensure_path_within_root(
        resolved_impact_path,
        workspace_root.resolve(),
        kind="eval impact manifest",
    )
    return manifest


def maybe_load_eval_impact_manifest(
    workspace_root: Path,
    *,
    impact_path: Path | None = None,
) -> EvalImpactManifest | None:
    """Load replay/eval impact rules when the repository provides them."""

    resolved_impact_path = _resolve_impact_path(workspace_root, impact_path=impact_path)
    if not resolved_impact_path.is_file():
        return None
    return load_eval_impact_manifest(workspace_root, impact_path=impact_path)


def _resolve_impact_path(workspace_root: Path, *, impact_path: Path | None) -> Path:
    if impact_path is None:
        return (workspace_root.resolve() / DEFAULT_EVAL_IMPACT_PATH).resolve()
    if impact_path.is_absolute():
        return impact_path.resolve()
    return (workspace_root.resolve() / impact_path).resolve()


def _normalize_touched_path(workspace_root: Path, touched_path: str) -> str:
    raw_path = Path(touched_path)
    resolved_path = (
        raw_path.resolve()
        if raw_path.is_absolute()
        else (workspace_root / raw_path).resolve()
    )
    _ensure_path_within_root(resolved_path, workspace_root, kind="touched path")
    return str(resolved_path.relative_to(workspace_root)).replace("\\", "/")


def _load_all_eval_cases(workspace_root: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    for case_path in discover_eval_case_files(workspace_root):
        cases.append(load_eval_case(case_path, workspace_root=workspace_root))
    cases.sort(key=lambda case: case.case_id)
    return cases


def _load_capabilities(
    workspace_root: Path,
    *,
    coverage_path: Path | None,
) -> list[EvalCapabilityDefinition]:
    try:
        return load_eval_coverage_manifest(
            workspace_root,
            coverage_path=coverage_path,
        ).capabilities
    except ValueError as exc:
        resolved_path = _resolve_optional_manifest_path(
            workspace_root,
            coverage_path,
            DEFAULT_EVAL_COVERAGE_PATH,
        )
        if "missing eval coverage manifest" in str(exc) and not resolved_path.exists():
            return []
        raise


def _resolve_optional_manifest_path(
    workspace_root: Path,
    path: Path | None,
    default_path: Path,
) -> Path:
    if path is None:
        return (workspace_root.resolve() / default_path).resolve()
    if path.is_absolute():
        return path.resolve()
    return (workspace_root.resolve() / path).resolve()


def _match_rules(
    normalized_paths: list[str],
    rules: list[EvalImpactRule],
) -> list[_PathRuleMatch]:
    matches: list[_PathRuleMatch] = []
    for normalized_path in normalized_paths:
        pure_path = PurePosixPath(normalized_path)
        for rule in rules:
            if any(
                pure_path.match(path_glob) or fnmatch(normalized_path, path_glob)
                for path_glob in rule.path_globs
            ):
                matches.append(_PathRuleMatch(rule=rule, matched_path=normalized_path))
    return matches


def _add_reason(
    destination: dict[str, list[EvalRecommendationReason]],
    key: str,
    reason: EvalRecommendationReason,
) -> None:
    reasons = destination.setdefault(key, [])
    if any(existing.summary == reason.summary for existing in reasons):
        return
    reasons.append(reason)


def _build_case_recommendations(
    cases_by_id: dict[str, EvalCase],
    case_reasons: dict[str, list[EvalRecommendationReason]],
) -> list[EvalCaseRecommendation]:
    recommendations: list[EvalCaseRecommendation] = []
    for case_id, reasons in case_reasons.items():
        case = cases_by_id.get(case_id)
        if case is None:
            continue
        sorted_reasons = _sort_reasons(reasons)
        recommendations.append(
            EvalCaseRecommendation(
                case_id=case.case_id,
                title=case.title,
                confidence=_strongest_confidence(sorted_reasons),
                owner=case.release_contract.owner,
                capabilities=list(case.release_contract.capabilities),
                verification_stages=list(case.release_contract.verification_stages),
                reasons=sorted_reasons,
            )
        )
    recommendations.sort(
        key=lambda recommendation: (
            -_CONFIDENCE_PRIORITY[recommendation.confidence],
            recommendation.case_id,
        )
    )
    return recommendations


def _build_profile_recommendations(
    profiles_by_id: dict[str, EvalProfileDefinition],
    profile_reasons: dict[str, list[EvalRecommendationReason]],
) -> list[EvalProfileRecommendation]:
    recommendations: list[EvalProfileRecommendation] = []
    for profile_id, reasons in profile_reasons.items():
        profile = profiles_by_id.get(profile_id)
        if profile is None:
            continue
        sorted_reasons = _sort_reasons(reasons)
        recommendations.append(
            EvalProfileRecommendation(
                profile_id=profile.profile_id,
                title=profile.title,
                confidence=_strongest_confidence(sorted_reasons),
                verification_stage=profile.verification_stage,
                track=profile.track,
                blocking=profile.blocking,
                reasons=sorted_reasons,
            )
        )
    recommendations.sort(
        key=lambda recommendation: (
            -_CONFIDENCE_PRIORITY[recommendation.confidence],
            recommendation.profile_id,
        )
    )
    return recommendations


def _sort_reasons(
    reasons: list[EvalRecommendationReason],
) -> list[EvalRecommendationReason]:
    return sorted(
        reasons,
        key=lambda reason: (
            -_CONFIDENCE_PRIORITY[reason.confidence],
            reason.summary,
        ),
    )


def _strongest_confidence(
    reasons: list[EvalRecommendationReason],
) -> EvalRecommendationConfidence:
    strongest = max(reasons, key=lambda reason: _CONFIDENCE_PRIORITY[reason.confidence])
    return strongest.confidence


def _build_suggested_commands(
    case_recommendations: list[EvalCaseRecommendation],
    profile_recommendations: list[EvalProfileRecommendation],
    *,
    coverage_audit_recommended: bool,
) -> list[str]:
    commands: list[str] = []
    if case_recommendations:
        case_ids = " ".join(
            recommendation.case_id for recommendation in case_recommendations
        )
        commands.append(f"uv run glassbox eval run {case_ids} --cwd .")
    for recommendation in profile_recommendations:
        commands.append(
            f"uv run glassbox eval run --profile {recommendation.profile_id} --cwd ."
        )
    if coverage_audit_recommended:
        commands.append("uv run glassbox eval audit --cwd .")
    return _dedupe_strings(commands)


def _dedupe_strings(values: list[str]) -> list[str]:
    unique: list[str] = []
    for value in values:
        if value not in unique:
            unique.append(value)
    return unique
