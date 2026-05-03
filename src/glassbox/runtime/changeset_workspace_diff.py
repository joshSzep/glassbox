"""Workspace diff helpers for changeset review surfaces."""

import hashlib
import subprocess
from pathlib import Path

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.tools.workflow import DiffSummaryArtifact
from glassbox.tools.workflow import DiffSummaryResult


class WorkspaceDiffSnapshot(BaseModel):
    """Filtered local git status snapshot for a workspace."""

    model_config = ConfigDict(extra="forbid")

    changed_paths: list[str] = Field(default_factory=list)
    digest: str | None = None
    error: str | None = None


class WorkspaceSourceDigest(BaseModel):
    """Digest posture for the current local workspace source state."""

    model_config = ConfigDict(extra="forbid")

    digest: str | None = None
    error: str | None = None


class GitBytesResult(BaseModel):
    """Bounded result for git commands that feed source digests."""

    model_config = ConfigDict(extra="forbid")

    digest_payload: bytes = b""
    digest: str | None = None
    error: str | None = None


def workspace_diff_snapshot(workspace_root: Path) -> WorkspaceDiffSnapshot:
    """Return a local git status snapshot without mutating the workspace."""

    try:
        result = subprocess.run(
            ["git", "status", "--short", "--untracked-files=all"],
            cwd=workspace_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        return WorkspaceDiffSnapshot(error="git executable not found")
    except subprocess.TimeoutExpired:
        return WorkspaceDiffSnapshot(error="git status timed out")
    if result.returncode != 0:
        return WorkspaceDiffSnapshot(error=result.stderr.strip() or "git status failed")
    changed_paths = sorted(_parse_status_paths(result.stdout))
    return WorkspaceDiffSnapshot(
        changed_paths=changed_paths,
        digest=_changed_path_digest(changed_paths),
    )


def workspace_diff_reason(diff: WorkspaceDiffSnapshot) -> str:
    """Return the stable source reason text for a workspace diff changeset."""

    if diff.error is not None:
        return "created from workspace diff request with unavailable git status"
    if not diff.changed_paths:
        return "created from workspace diff request with no local diff"
    return (
        "created from workspace diff request "
        f"({len(diff.changed_paths)} changed path(s), digest {diff.digest})"
    )


def workspace_diff_source_digest(workspace_root: Path) -> WorkspaceSourceDigest:
    """Return a digest for local status, diffs, and untracked file contents."""

    digest = hashlib.sha256()
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
            cwd=workspace_root,
            check=False,
            capture_output=True,
            timeout=10,
        )
    except FileNotFoundError:
        return WorkspaceSourceDigest(error="git executable not found")
    except subprocess.TimeoutExpired:
        return WorkspaceSourceDigest(error="git status timed out")
    if status.returncode != 0:
        return WorkspaceSourceDigest(
            error=status.stderr.decode("utf-8", errors="replace").strip()
            or "git status failed"
        )
    digest.update(b"status\0")
    digest.update(_filter_status_porcelain_z(status.stdout))
    for label, command in (
        (
            b"unstaged-diff\0",
            ["git", "diff", "--no-ext-diff", "--binary", "--"],
        ),
        (
            b"staged-diff\0",
            ["git", "diff", "--cached", "--no-ext-diff", "--binary", "--"],
        ),
    ):
        result = _run_git_bytes(workspace_root, command)
        if result.error is not None:
            return WorkspaceSourceDigest(error=result.error)
        digest.update(label)
        digest.update(result.digest_payload)
    untracked = _run_git_bytes(
        workspace_root,
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
    )
    if untracked.error is not None:
        return WorkspaceSourceDigest(error=untracked.error)
    digest.update(b"untracked-content\0")
    for path_text in sorted(
        path.decode("utf-8", errors="replace")
        for path in untracked.digest_payload.split(b"\0")
        if path and not _is_local_state_path(path.decode("utf-8", errors="replace"))
    ):
        digest.update(path_text.encode("utf-8", errors="replace"))
        digest.update(b"\0")
        file_path = (workspace_root / path_text).resolve(strict=False)
        try:
            if file_path.is_file():
                digest.update(
                    hashlib.sha256(file_path.read_bytes()).hexdigest().encode()
                )
        except OSError as exc:
            digest.update(f"unreadable:{exc}".encode("utf-8", errors="replace"))
        digest.update(b"\0")
    return WorkspaceSourceDigest(digest=f"sha256:{digest.hexdigest()}")


def diff_summary_without_local_state(
    diff_summary: DiffSummaryResult,
) -> DiffSummaryResult:
    """Drop local Glassbox state paths from a diff summary."""

    files = [
        file_summary
        for file_summary in diff_summary.files
        if not _is_local_state_path(file_summary.path)
    ]
    artifact_payload = diff_summary.artifact_payload
    if artifact_payload is not None:
        artifact_payload = DiffSummaryArtifact(
            artifact_kind=artifact_payload.artifact_kind,
            scope=artifact_payload.scope,
            path_filters=artifact_payload.path_filters,
            risk_summary=artifact_payload.risk_summary,
            files=[
                file_summary
                for file_summary in artifact_payload.files
                if not _is_local_state_path(file_summary.path)
            ],
            redaction=artifact_payload.redaction,
        )
    return diff_summary.model_copy(
        update={
            "files": files,
            "artifact_payload": artifact_payload,
            "clean": not files and artifact_payload is None,
        }
    )


def _parse_status_paths(output: str) -> list[str]:
    paths: list[str] = []
    for line in output.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.rsplit(" -> ", maxsplit=1)[-1]
        if path:
            paths.append(path.replace("\\", "/"))
    return paths


def _changed_path_digest(paths: list[str]) -> str | None:
    if not paths:
        return None
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _filter_status_porcelain_z(output: bytes) -> bytes:
    filtered_entries = []
    for entry in output.split(b"\0"):
        if not entry:
            continue
        path_text = entry[3:].decode("utf-8", errors="replace")
        if not _is_local_state_path(path_text):
            filtered_entries.append(entry)
    return b"\0".join(filtered_entries) + (b"\0" if filtered_entries else b"")


def _is_local_state_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return normalized == ".glassbox" or normalized.startswith(".glassbox/")


def _run_git_bytes(workspace_root: Path, command: list[str]) -> GitBytesResult:
    try:
        result = subprocess.run(
            command,
            cwd=workspace_root,
            check=False,
            capture_output=True,
            timeout=10,
        )
    except FileNotFoundError:
        return GitBytesResult(error="git executable not found")
    except subprocess.TimeoutExpired:
        return GitBytesResult(error=f"{' '.join(command[:3])} timed out")
    if result.returncode != 0:
        return GitBytesResult(
            error=result.stderr.decode("utf-8", errors="replace").strip()
            or f"{' '.join(command[:3])} failed"
        )
    return GitBytesResult(digest_payload=result.stdout)


__all__ = [
    "GitBytesResult",
    "WorkspaceDiffSnapshot",
    "WorkspaceSourceDigest",
    "diff_summary_without_local_state",
    "workspace_diff_reason",
    "workspace_diff_snapshot",
    "workspace_diff_source_digest",
]
