"""Path and package-family helpers for handoff routes."""

import json
from pathlib import Path

from glassbox.web.routes.handoff_route_errors import handoff_bad_request


def resolve_local_package_path(
    workspace_root: Path,
    path_text: str | None,
    *,
    default_name: str | None = None,
) -> Path:
    """Resolve a route-local package path relative to the workspace root."""

    value = path_text or default_name
    if value is None:
        raise handoff_bad_request("package path is required")
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = workspace_root / path
    return path.resolve()


def package_export_kind(package_path: Path) -> str | None:
    """Read the export kind from a local JSON package, if present."""

    try:
        raw_payload = json.loads(package_path.read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError:
        return None
    if not isinstance(raw_payload, dict):
        return None
    export_kind = raw_payload.get("export_kind")
    return export_kind if isinstance(export_kind, str) else None


__all__ = [
    "package_export_kind",
    "resolve_local_package_path",
]
