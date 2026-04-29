"""Path helpers for terminal app handoff actions."""

from pathlib import Path


def local_artifact_path(raw_path: str, cwd: str | None) -> Path:
    path = Path(raw_path).expanduser()
    if path.is_absolute():
        return path
    if cwd is not None:
        return Path(cwd).expanduser() / path
    return path.absolute()
