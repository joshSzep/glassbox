"""Repository index persistence and freshness helpers."""

import json
from pathlib import Path

from pydantic import ValidationError

from glassbox.core.models import RepositoryIndexSnapshot
from glassbox.core.types import RepositoryIndexFreshness
from glassbox.runtime.repository_index_discovery import repository_index_path
from glassbox.runtime.repository_index_discovery import scan_indexable_files
from glassbox.runtime.repository_index_discovery import source_digest

SUPPORTED_REPOSITORY_INDEX_SCHEMA_VERSION = 2


class RepositoryIndexNotFoundError(ValueError):
    """Raised when repository index reads require a missing snapshot."""


class RepositoryIndexLoadError(ValueError):
    """Raised when a retained repository index exists but cannot be used."""

    def __init__(
        self,
        *,
        reason: str,
        detail: str,
        path: Path,
        safe_next_actions: list[str],
    ) -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail
        self.path = path
        self.safe_next_actions = safe_next_actions


def write_repository_index(
    workspace_root: Path,
    snapshot: RepositoryIndexSnapshot,
) -> Path:
    """Write a repository index snapshot to the local artifact path."""

    path = repository_index_path(workspace_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_repository_index(workspace_root: Path) -> RepositoryIndexSnapshot:
    """Load the local index snapshot and mark it stale if sources changed."""

    path = repository_index_path(workspace_root)
    if not path.exists():
        raise RepositoryIndexNotFoundError("repository index has not been built")
    raw = _read_index_payload(path)
    _raise_for_unsupported_schema(raw, path, workspace_root)
    try:
        snapshot = RepositoryIndexSnapshot.model_validate(raw)
    except ValidationError as exc:
        raise _load_error(
            workspace_root,
            path,
            reason="invalid_snapshot",
            detail=(
                "repository intelligence snapshot is invalid; rebuild the local "
                "index before relying on repository recommendations"
            ),
            source_error=exc,
        ) from exc
    current_digest = source_digest(
        workspace_root.resolve(),
        scan_indexable_files(workspace_root.resolve()).files,
    )
    if snapshot.source_digest is not None and snapshot.source_digest != current_digest:
        return snapshot.model_copy(update={"status": RepositoryIndexFreshness.STALE})
    return snapshot


def failed_repository_index_snapshot_from_error(
    workspace_root: Path,
    error: RepositoryIndexLoadError,
) -> RepositoryIndexSnapshot:
    """Return a degraded status snapshot for unreadable retained artifacts."""

    return RepositoryIndexSnapshot(
        schema_version=SUPPORTED_REPOSITORY_INDEX_SCHEMA_VERSION,
        workspace_root=workspace_root.resolve(),
        status=RepositoryIndexFreshness.FAILED,
        failure_reason=error.detail,
        limitations=[
            f"repository index load failed: {error.reason}",
            *error.safe_next_actions,
        ],
    )


def _read_index_payload(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise _load_error(
            path.parent.parent,
            path,
            reason="corrupted_snapshot",
            detail=(
                "repository intelligence snapshot is not valid JSON; rebuild the "
                "local index before relying on repository recommendations"
            ),
            source_error=exc,
        ) from exc
    except OSError as exc:
        raise _load_error(
            path.parent.parent,
            path,
            reason="unreadable_snapshot",
            detail=(
                "repository intelligence snapshot could not be read; inspect file "
                "permissions or rebuild the local index"
            ),
            source_error=exc,
        ) from exc
    if not isinstance(payload, dict):
        raise _load_error(
            path.parent.parent,
            path,
            reason="invalid_snapshot",
            detail=(
                "repository intelligence snapshot must be a JSON object; rebuild "
                "the local index before relying on repository recommendations"
            ),
        )
    return payload


def _raise_for_unsupported_schema(
    payload: dict[str, object],
    path: Path,
    workspace_root: Path,
) -> None:
    schema_version = payload.get("schema_version")
    if not isinstance(schema_version, int):
        return
    if schema_version <= SUPPORTED_REPOSITORY_INDEX_SCHEMA_VERSION:
        return
    raise _load_error(
        workspace_root,
        path,
        reason="unsupported_schema_version",
        detail=(
            "repository intelligence snapshot uses unsupported schema version "
            f"{schema_version}; rebuild with this Glassbox version before relying "
            "on repository recommendations"
        ),
    )


def _load_error(
    workspace_root: Path,
    path: Path,
    *,
    reason: str,
    detail: str,
    source_error: Exception | None = None,
) -> RepositoryIndexLoadError:
    if source_error is not None:
        detail = f"{detail}: {source_error}"
    if len(detail) > 1900:
        detail = f"{detail[:1897]}..."
    root = workspace_root.resolve()
    return RepositoryIndexLoadError(
        reason=reason,
        detail=detail,
        path=path,
        safe_next_actions=[
            f"glassbox repo index status --cwd {root} --json",
            f"glassbox repo index build --cwd {root}",
        ],
    )


__all__ = [
    "RepositoryIndexLoadError",
    "RepositoryIndexNotFoundError",
    "SUPPORTED_REPOSITORY_INDEX_SCHEMA_VERSION",
    "failed_repository_index_snapshot_from_error",
    "load_repository_index",
    "write_repository_index",
]
