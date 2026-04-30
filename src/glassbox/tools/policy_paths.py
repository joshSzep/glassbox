"""Path-scope and path-rule helpers for tool policy."""

from collections.abc import Mapping
from pathlib import Path

from pydantic import BaseModel

from glassbox.tools.registry import ToolSpec


def normalize_tool_arguments(
    arguments: BaseModel | Mapping[str, object],
) -> dict[str, object]:
    """Normalize Pydantic or mapping arguments for policy matching."""

    if isinstance(arguments, BaseModel):
        return dict(arguments.model_dump(mode="python"))
    return dict(arguments)


def first_out_of_scope_path(
    tool_spec: ToolSpec,
    *,
    arguments: Mapping[str, object],
    workspace_root: Path,
) -> str | None:
    """Return the first path argument outside the workspace, if any."""

    for argument_name in tool_spec.path_argument_names:
        value = arguments.get(argument_name)
        for candidate in iter_path_values(value):
            resolved_candidate = resolve_scoped_path(candidate, workspace_root)
            if not is_within_workspace(resolved_candidate, workspace_root):
                return str(candidate)
    return None


def iter_path_values(value: object) -> tuple[Path, ...]:
    """Yield path-like argument values while ignoring unsupported shapes."""

    if value is None:
        return ()
    if isinstance(value, Path):
        return (value,)
    if isinstance(value, str):
        return (Path(value),)
    if isinstance(value, tuple | list):
        paths: list[Path] = []
        for item in value:
            if isinstance(item, Path):
                paths.append(item)
            elif isinstance(item, str):
                paths.append(Path(item))
        return tuple(paths)
    return ()


def resolve_scoped_path(candidate: Path, workspace_root: Path) -> Path:
    """Resolve a path argument relative to the workspace root."""

    if candidate.is_absolute():
        return candidate.resolve(strict=False)
    return (workspace_root / candidate).resolve(strict=False)


def is_within_workspace(candidate: Path, workspace_root: Path) -> bool:
    """Return whether a resolved candidate path is inside the workspace."""

    try:
        candidate.relative_to(workspace_root)
    except ValueError:
        return False
    return True


def path_argument_prefixes_match(
    tool_spec: ToolSpec,
    *,
    arguments: Mapping[str, object],
    prefixes: list[str],
    workspace_root: Path,
) -> bool:
    """Return whether all non-cwd path arguments match allowed prefixes."""

    path_argument_names = tuple(
        argument_name
        for argument_name in tool_spec.path_argument_names
        if argument_name != "cwd"
    )
    if not path_argument_names:
        return False
    return all(
        path_prefixes_match(
            arguments.get(argument_name),
            prefixes=prefixes,
            workspace_root=workspace_root,
        )
        for argument_name in path_argument_names
    )


def path_argument_values(
    tool_spec: ToolSpec,
    arguments: Mapping[str, object],
) -> list[Path]:
    """Return non-cwd path argument values."""

    paths: list[Path] = []
    for argument_name in tool_spec.path_argument_names:
        if argument_name == "cwd":
            continue
        paths.extend(iter_path_values(arguments.get(argument_name)))
    return paths


def path_extensions_match(
    paths: list[Path],
    *,
    extensions: list[str],
) -> bool:
    """Return whether every candidate path uses an allowed extension."""

    if not paths:
        return False
    return all(path.suffix.lower() in extensions for path in paths)


def path_prefixes_match(
    value: object,
    *,
    prefixes: list[str],
    workspace_root: Path,
) -> bool:
    """Return whether each path-like value sits under one configured prefix."""

    candidate_paths = iter_path_values(value)
    if not candidate_paths:
        return False
    resolved_prefixes = [
        (workspace_root / prefix).resolve(strict=False) for prefix in prefixes
    ]
    return all(
        any(
            is_within_workspace_prefix(
                resolve_scoped_path(candidate, workspace_root),
                prefix,
            )
            for prefix in resolved_prefixes
        )
        for candidate in candidate_paths
    )


def is_within_workspace_prefix(candidate: Path, prefix: Path) -> bool:
    """Return whether a resolved path is inside a resolved policy prefix."""

    try:
        candidate.relative_to(prefix)
    except ValueError:
        return False
    return True
