"""Discovery and manifest loading for replay-backed evals."""

from pathlib import Path

from glassbox.runtime.eval_case_models import EvalCase
from glassbox.runtime.eval_case_models import EvalCaseManifest
from glassbox.runtime.eval_constants import DEFAULT_EVAL_CASES_DIR
from glassbox.runtime.eval_constants import DEFAULT_EVAL_PROFILES_PATH
from glassbox.runtime.eval_constants import EvalProfileTrack
from glassbox.runtime.eval_constants import ensure_path_within_root
from glassbox.runtime.eval_constants import normalize_identifier
from glassbox.runtime.eval_profile_models import EvalProfileDefinition
from glassbox.runtime.eval_profile_models import EvalProfileManifest


def discover_eval_case_files(
    workspace_root: Path,
    *,
    cases_dir: Path | None = None,
) -> list[Path]:
    """Return discovered eval case manifest files under the repository layout."""

    root = _resolve_cases_dir(workspace_root, cases_dir=cases_dir)
    if not root.exists():
        return []
    return sorted(path.resolve() for path in root.rglob("*.json") if path.is_file())


def load_eval_case(
    case_path: Path,
    *,
    workspace_root: Path | None = None,
    validate_bundle_exists: bool = True,
) -> EvalCase:
    """Load and resolve one eval case manifest from disk."""

    resolved_case_path = case_path.resolve()
    try:
        raw_manifest = resolved_case_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"missing eval case file: {resolved_case_path}") from exc

    try:
        manifest = EvalCaseManifest.model_validate_json(raw_manifest)
    except ValueError as exc:
        raise ValueError(f"invalid eval case file {resolved_case_path}: {exc}") from exc

    resolved_workspace_root = (
        workspace_root.resolve() if workspace_root is not None else None
    )
    if resolved_workspace_root is not None:
        ensure_path_within_root(
            resolved_case_path,
            resolved_workspace_root,
            kind="eval case file",
        )

    resolved_bundle_path = (resolved_case_path.parent / manifest.bundle_path).resolve()
    if resolved_workspace_root is not None:
        ensure_path_within_root(
            resolved_bundle_path,
            resolved_workspace_root,
            kind="eval bundle path",
        )
    if validate_bundle_exists and not resolved_bundle_path.is_file():
        raise ValueError(
            f"eval case bundle_path does not exist: {resolved_bundle_path}"
        )

    return EvalCase(
        manifest_version=manifest.manifest_version,
        case_id=manifest.case_id,
        title=manifest.title,
        case_path=resolved_case_path,
        bundle_path=resolved_bundle_path,
        tags=manifest.tags,
        notes=manifest.notes,
        expectation=manifest.expectation,
        release_contract=manifest.release_contract,
        baseline_history=list(manifest.baseline_history),
    )


def load_eval_profile(
    workspace_root: Path,
    *,
    profile_id: str,
    profiles_path: Path | None = None,
) -> EvalProfileDefinition:
    """Load one named eval verification profile from the repository manifest."""

    normalized_profile_id = normalize_identifier(profile_id, kind="profile_id")
    manifest = load_eval_profile_manifest(
        workspace_root,
        profiles_path=profiles_path,
    )
    profiles_by_id = {profile.profile_id: profile for profile in manifest.profiles}
    try:
        return profiles_by_id[normalized_profile_id]
    except KeyError as exc:
        raise ValueError(f"unknown eval profile: {normalized_profile_id}") from exc


def load_eval_profiles(
    workspace_root: Path,
    *,
    track: EvalProfileTrack | None = None,
    profiles_path: Path | None = None,
) -> list[EvalProfileDefinition]:
    """Load repository-owned eval profiles, optionally narrowed by track."""

    manifest = load_eval_profile_manifest(
        workspace_root,
        profiles_path=profiles_path,
    )
    profiles = list(manifest.profiles)
    if track is not None:
        profiles = [profile for profile in profiles if profile.track == track]
    return profiles


def load_eval_profile_manifest(
    workspace_root: Path,
    *,
    profiles_path: Path | None = None,
) -> EvalProfileManifest:
    """Load the repository-local eval profile manifest from disk."""

    resolved_profile_path = _resolve_profiles_path(
        workspace_root,
        profiles_path=profiles_path,
    )
    try:
        raw_manifest = resolved_profile_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(
            f"missing eval profile manifest: {resolved_profile_path}"
        ) from exc

    try:
        manifest = EvalProfileManifest.model_validate_json(raw_manifest)
    except ValueError as exc:
        raise ValueError(
            f"invalid eval profile manifest {resolved_profile_path}: {exc}"
        ) from exc

    ensure_path_within_root(
        resolved_profile_path,
        workspace_root.resolve(),
        kind="eval profile manifest",
    )
    return manifest


def _resolve_cases_dir(workspace_root: Path, *, cases_dir: Path | None) -> Path:
    if cases_dir is None:
        return (workspace_root.resolve() / DEFAULT_EVAL_CASES_DIR).resolve()
    if cases_dir.is_absolute():
        return cases_dir.resolve()
    return (workspace_root.resolve() / cases_dir).resolve()


def _resolve_profiles_path(
    workspace_root: Path,
    *,
    profiles_path: Path | None,
) -> Path:
    if profiles_path is None:
        return (workspace_root.resolve() / DEFAULT_EVAL_PROFILES_PATH).resolve()
    if profiles_path.is_absolute():
        return profiles_path.resolve()
    return (workspace_root.resolve() / profiles_path).resolve()
