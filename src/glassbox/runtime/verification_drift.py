"""Workspace drift assessment for long-run verification evidence."""

import hashlib
import subprocess
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core.ids import TaskId
from glassbox.core.ids import TaskVerificationId
from glassbox.core.models import TaskVerificationLedgerRecord
from glassbox.core.types import TaskVerificationStatus

VerificationDriftPosture = Literal[
    "not_assessed",
    "fresh",
    "stale",
    "missing_coverage",
    "docs_only_drift",
    "generated_drift",
    "unknown",
]

_GENERATED_PATH_PREFIXES = (
    "frontend/generated/",
    "src/glassbox/web/static_next/",
)
_GENERATED_PATH_MARKERS = (
    "/generated/",
    "/static_next/",
)
_POLICY_DOC_PREFIXES = (
    "docs/tasks-v",
    "docs/tool-policy",
    "docs/replay-evals",
    "docs/version-release-policy",
)


class VerificationDriftAssessment(BaseModel):
    """Read-time workspace drift posture for a task verification ledger."""

    model_config = ConfigDict(extra="forbid")

    task_id: TaskId
    posture: VerificationDriftPosture
    workspace_clean: bool
    changed_paths: list[str] = Field(default_factory=list)
    material_changed_paths: list[str] = Field(default_factory=list)
    docs_only_changed_paths: list[str] = Field(default_factory=list)
    generated_changed_paths: list[str] = Field(default_factory=list)
    stale_verification_ids: list[TaskVerificationId] = Field(default_factory=list)
    stale_changed_paths: list[str] = Field(default_factory=list)
    changed_path_digest: str | None = None
    diff_summary_command: str | None = None
    reason: str
    error: str | None = None


def not_assessed_verification_drift(task_id: TaskId) -> VerificationDriftAssessment:
    """Build an explicit posture when no workspace root is available."""

    return VerificationDriftAssessment(
        task_id=task_id,
        posture="not_assessed",
        workspace_clean=True,
        reason="workspace drift was not assessed for this read",
    )


def assess_verification_drift(
    workspace_root: Path,
    *,
    task_id: TaskId,
    ledger: list[TaskVerificationLedgerRecord],
) -> VerificationDriftAssessment:
    """Compare verification coverage with the current local workspace diff."""

    changed_result = _git_changed_paths(workspace_root)
    if changed_result.error is not None:
        return VerificationDriftAssessment(
            task_id=task_id,
            posture="unknown",
            workspace_clean=False,
            reason="workspace diff could not be inspected",
            error=changed_result.error,
            diff_summary_command=_diff_summary_command(task_id),
        )

    changed_paths = changed_result.paths
    changed_path_digest = _changed_path_digest(changed_paths)
    docs_paths = [path for path in changed_paths if _is_docs_only_path(path)]
    generated_paths = [path for path in changed_paths if _is_generated_path(path)]
    material_paths = [
        path
        for path in changed_paths
        if path not in docs_paths and path not in generated_paths
    ]
    stale_entries = [
        entry
        for entry in ledger
        if entry.status == TaskVerificationStatus.PASSED
        and _intersects_material_paths(entry.changed_paths, material_paths)
    ]
    stale_paths = sorted(
        {
            path
            for entry in stale_entries
            for path in _normalized_paths(entry.changed_paths)
            if path in material_paths
        }
    )

    if stale_entries:
        posture: VerificationDriftPosture = "stale"
        reason = "material workspace changes overlap previously passed checks"
    elif material_paths:
        posture = "missing_coverage"
        reason = "material workspace changes are not covered by passed ledger paths"
    elif generated_paths:
        posture = "generated_drift"
        reason = "only generated workspace changes are present"
    elif docs_paths:
        posture = "docs_only_drift"
        reason = "only documentation workspace changes are present"
    else:
        posture = "fresh"
        reason = "workspace has no local drift from HEAD"

    return VerificationDriftAssessment(
        task_id=task_id,
        posture=posture,
        workspace_clean=not changed_paths,
        changed_paths=changed_paths,
        material_changed_paths=material_paths,
        docs_only_changed_paths=docs_paths,
        generated_changed_paths=generated_paths,
        stale_verification_ids=[entry.verification_id for entry in stale_entries],
        stale_changed_paths=stale_paths,
        changed_path_digest=changed_path_digest,
        diff_summary_command=_diff_summary_command(task_id),
        reason=reason,
    )


class _ChangedPathResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paths: list[str] = Field(default_factory=list)
    error: str | None = None


def _git_changed_paths(workspace_root: Path) -> _ChangedPathResult:
    root = workspace_root.resolve()
    diff = _run_git(root, ["git", "diff", "--name-only", "HEAD", "--"])
    if diff.returncode != 0:
        return _ChangedPathResult(error=diff.stderr.strip() or "git diff failed")
    untracked = _run_git(root, ["git", "ls-files", "--others", "--exclude-standard"])
    if untracked.returncode != 0:
        return _ChangedPathResult(
            error=untracked.stderr.strip() or "git ls-files failed"
        )
    paths = sorted(
        {
            *_parse_path_lines(diff.stdout),
            *_parse_path_lines(untracked.stdout),
        }
    )
    return _ChangedPathResult(paths=paths)


def _run_git(root: Path, command: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        return subprocess.CompletedProcess(command, 127, "", "git executable not found")
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(command, 124, "", "git command timed out")


def _parse_path_lines(output: str) -> list[str]:
    return [line.strip().replace("\\", "/") for line in output.splitlines() if line]


def _normalized_paths(paths: list[Path]) -> list[str]:
    return [str(path).replace("\\", "/") for path in paths]


def _intersects_material_paths(paths: list[Path], material_paths: list[str]) -> bool:
    material = set(material_paths)
    return any(path in material for path in _normalized_paths(paths))


def _changed_path_digest(paths: list[str]) -> str | None:
    if not paths:
        return None
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _is_generated_path(path: str) -> bool:
    return path.startswith(_GENERATED_PATH_PREFIXES) or any(
        marker in f"/{path}" for marker in _GENERATED_PATH_MARKERS
    )


def _is_docs_only_path(path: str) -> bool:
    if path.startswith(_POLICY_DOC_PREFIXES):
        return False
    return path.startswith("docs/") or path.endswith(".md")


def _diff_summary_command(task_id: TaskId) -> str:
    return f"glassbox task show {task_id} --json"


__all__ = [
    "VerificationDriftAssessment",
    "VerificationDriftPosture",
    "assess_verification_drift",
    "not_assessed_verification_drift",
]
