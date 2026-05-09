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
from glassbox.runtime.repository_index_discovery import is_generated_repository_path
from glassbox.runtime.repository_index_persistence import RepositoryIndexNotFoundError
from glassbox.runtime.repository_index_persistence import load_repository_index
from glassbox.runtime.workspace_topology import WorkspaceTopologyNotFoundError
from glassbox.runtime.workspace_topology import load_workspace_topology

VerificationDriftPosture = Literal[
    "not_assessed",
    "fresh",
    "stale",
    "missing_coverage",
    "docs_only_drift",
    "generated_drift",
    "unknown",
]
StaleEvidenceKind = Literal[
    "verification",
    "repository-intelligence",
    "topology",
    "command-recipe",
    "workspace-memory",
    "eval-metadata",
]
StaleEvidenceState = Literal["stale", "missing", "degraded"]

_POLICY_DOC_PREFIXES = (
    "docs/tasks-v",
    "docs/tool-policy",
    "docs/replay-evals",
    "docs/version-release-policy",
)


class StaleEvidenceRecommendation(BaseModel):
    """Actionable stale-evidence row for repository-aware verification."""

    model_config = ConfigDict(extra="forbid")

    kind: StaleEvidenceKind
    state: StaleEvidenceState
    reason: str
    changed_paths: list[str] = Field(default_factory=list)
    source_id: str | None = None
    safe_next_actions: list[str] = Field(default_factory=list)
    blocking: bool = False


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
    stale_evidence: list[StaleEvidenceRecommendation] = Field(default_factory=list)
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
    stale_evidence = _stale_evidence_recommendations(
        workspace_root,
        material_paths=material_paths,
        stale_verification_ids=[entry.verification_id for entry in stale_entries],
        stale_paths=stale_paths,
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
        stale_evidence=stale_evidence,
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
    return [
        path
        for line in output.splitlines()
        if (path := line.strip().replace("\\", "/")) and not _is_artifact_churn(path)
    ]


def _stale_evidence_recommendations(
    workspace_root: Path,
    *,
    material_paths: list[str],
    stale_verification_ids: list[TaskVerificationId],
    stale_paths: list[str],
) -> list[StaleEvidenceRecommendation]:
    recommendations: list[StaleEvidenceRecommendation] = []
    if stale_verification_ids:
        recommendations.append(
            StaleEvidenceRecommendation(
                kind="verification",
                state="stale",
                reason="previously passed verification overlaps material changes",
                changed_paths=stale_paths,
                safe_next_actions=["rerun the stale verification command"],
                blocking=True,
            )
        )
    if not material_paths:
        return recommendations

    recommendations.extend(
        _repository_index_stale_evidence(workspace_root, material_paths)
    )
    recommendations.extend(_topology_stale_evidence(workspace_root, material_paths))
    return recommendations


def _repository_index_stale_evidence(
    workspace_root: Path,
    material_paths: list[str],
) -> list[StaleEvidenceRecommendation]:
    try:
        snapshot = load_repository_index(workspace_root)
    except RepositoryIndexNotFoundError:
        return [
            StaleEvidenceRecommendation(
                kind="repository-intelligence",
                state="missing",
                reason="repository intelligence snapshot is missing",
                changed_paths=material_paths,
                safe_next_actions=["glassbox repo index build --cwd ."],
            )
        ]
    except ValueError as exc:
        return [
            StaleEvidenceRecommendation(
                kind="repository-intelligence",
                state="degraded",
                reason=f"repository intelligence snapshot could not be read: {exc}",
                changed_paths=material_paths,
                safe_next_actions=["glassbox repo index status --cwd . --json"],
            )
        ]
    if snapshot.status == "stale":
        return [
            StaleEvidenceRecommendation(
                kind="repository-intelligence",
                state="stale",
                reason="repository intelligence digest differs from current sources",
                changed_paths=material_paths,
                source_id="repository-index",
                safe_next_actions=["glassbox repo index build --cwd ."],
            )
        ]
    if snapshot.status == "failed":
        return [
            StaleEvidenceRecommendation(
                kind="repository-intelligence",
                state="degraded",
                reason=snapshot.failure_reason or "repository intelligence failed",
                changed_paths=material_paths,
                source_id="repository-index",
                safe_next_actions=["glassbox repo index status --cwd . --json"],
            )
        ]
    return []


def _topology_stale_evidence(
    workspace_root: Path,
    material_paths: list[str],
) -> list[StaleEvidenceRecommendation]:
    try:
        topology = load_workspace_topology(workspace_root)
    except WorkspaceTopologyNotFoundError:
        return []
    except ValueError as exc:
        return [
            StaleEvidenceRecommendation(
                kind="topology",
                state="degraded",
                reason=f"workspace topology could not be read: {exc}",
                changed_paths=material_paths,
                safe_next_actions=["glassbox repo topology status --cwd . --json"],
            )
        ]
    if topology.freshness == "stale":
        return [
            StaleEvidenceRecommendation(
                kind="topology",
                state="stale",
                reason="workspace topology digest differs from current sources",
                changed_paths=material_paths,
                source_id="workspace-topology",
                safe_next_actions=["glassbox repo topology build --cwd ."],
            )
        ]
    if topology.freshness == "failed":
        return [
            StaleEvidenceRecommendation(
                kind="topology",
                state="degraded",
                reason=topology.failure_reason or "workspace topology failed",
                changed_paths=material_paths,
                source_id="workspace-topology",
                safe_next_actions=["glassbox repo topology status --cwd . --json"],
            )
        ]
    return []


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
    return is_generated_repository_path(path)


def _is_docs_only_path(path: str) -> bool:
    if path.startswith(_POLICY_DOC_PREFIXES):
        return False
    return path.startswith("docs/") or path.endswith(".md")


def _is_artifact_churn(path: str) -> bool:
    return path == ".glassbox" or path.startswith(".glassbox/")


def _diff_summary_command(task_id: TaskId) -> str:
    return f"glassbox task show {task_id} --json"


__all__ = [
    "VerificationDriftAssessment",
    "VerificationDriftPosture",
    "StaleEvidenceRecommendation",
    "assess_verification_drift",
    "not_assessed_verification_drift",
]
