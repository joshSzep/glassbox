"""Validation helpers for packaged SPA static assets."""

import re
from pathlib import Path

_ASSET_ATTRIBUTE_RE = re.compile(r"(?:href|src)=['\"](/app/_next/[^'\"]+)['\"]")


def validate_spa_static_assets(static_root: Path) -> list[str]:
    """Return packaging/serving problems for a static Next.js export."""

    index_path = static_root / "index.html"
    if not index_path.is_file():
        return [f"missing SPA shell: {index_path}"]

    problems: list[str] = []
    for asset_url in sorted(set(_ASSET_ATTRIBUTE_RE.findall(index_path.read_text()))):
        relative_path = asset_url.removeprefix("/app/").split("?", maxsplit=1)[0]
        if relative_path == "":
            continue
        if _resolve_static_asset(static_root, relative_path) is None:
            problems.append(f"missing SPA asset referenced by index.html: {asset_url}")

    return problems


def _resolve_static_asset(static_root: Path, relative_path: str) -> Path | None:
    resolved_root = static_root.resolve()
    candidate = (resolved_root / relative_path).resolve()
    if candidate == resolved_root or resolved_root not in candidate.parents:
        return None
    return candidate if candidate.is_file() else None
