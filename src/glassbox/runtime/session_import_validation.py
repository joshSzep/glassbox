"""Validation helpers for portable session import packages."""

import re
from pathlib import Path

from glassbox.runtime.session_export import SESSION_EXPORT_VERSION
from glassbox.runtime.session_export import SessionExportPayload

_UNREDACTED_SECRET_PATTERNS = (
    re.compile(
        r"(?i)\b(?:openai|anthropic|api|access|secret|token|password)"
        r"[_-]?(?:api[_-]?)?(?:key|token|secret|password)?\s*=\s*"
        r"(?!<redacted>)[^\s,;\"]+"
    ),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
)


def load_session_export_package(package_path: Path) -> SessionExportPayload:
    """Load and validate a supported portable session export package."""

    resolved_path = package_path.resolve()
    try:
        raw_package = resolved_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"missing session export package: {resolved_path}") from exc

    if contains_unredacted_secret(raw_package):
        raise ValueError(
            "session export package appears to contain unredacted secret material"
        )

    try:
        package = SessionExportPayload.model_validate_json(raw_package)
    except ValueError as exc:
        raise ValueError(
            f"invalid session export package {resolved_path}: {exc}"
        ) from exc

    if package.export_version != SESSION_EXPORT_VERSION:
        raise ValueError(
            f"unsupported session export version: {package.export_version}"
        )
    return package


def contains_unredacted_secret(raw_package: str) -> bool:
    return any(pattern.search(raw_package) for pattern in _UNREDACTED_SECRET_PATTERNS)
