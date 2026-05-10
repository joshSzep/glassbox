"""Common helpers for repository intelligence layout discovery."""

import hashlib
import json
import tomllib
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from glassbox.core.models import RepositoryIndexProvenance
from glassbox.core.types import RepositoryIndexSourceType

EXCLUDED_PATH_LIMITATION = (
    "Excluded from file crawling; retained as path-level posture only."
)


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    return list(dict.fromkeys(paths))


def _existing_paths(root: Path, candidates: Sequence[str | Path]) -> list[Path]:
    paths: list[Path] = []
    for candidate in candidates:
        relative = Path(candidate)
        if relative.is_absolute() or ".." in relative.parts:
            continue
        if (root / relative).exists():
            paths.append(relative)
    return paths


def _provenance(
    source_type: RepositoryIndexSourceType,
    path: Path,
) -> RepositoryIndexProvenance:
    return RepositoryIndexProvenance(source_type=source_type, path=path)


def _file_digest(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    return hashlib.sha256(data).hexdigest()


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except OSError:
        return {}
    except tomllib.TOMLDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError:
        return {}
    if isinstance(data, dict):
        return data
    return {}


def _dedupe_by_id[T](items: list[T], field_name: str) -> list[T]:
    seen: set[str] = set()
    deduped: list[T] = []
    for item in items:
        value = str(getattr(item, field_name))
        if value in seen:
            continue
        seen.add(value)
        deduped.append(item)
    return deduped


def _slug(path: Path) -> str:
    value = path.as_posix()
    if value in {"", "."}:
        return "root"
    return value.replace("/", ":")


__all__ = [
    "EXCLUDED_PATH_LIMITATION",
    "_dedupe_by_id",
    "_dedupe_paths",
    "_existing_paths",
    "_file_digest",
    "_provenance",
    "_read_json",
    "_read_toml",
    "_slug",
]
