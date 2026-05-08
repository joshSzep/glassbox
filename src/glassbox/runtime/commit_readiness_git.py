"""Git status and diff summary helpers for commit readiness."""

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.tools.workflow import DiffSummaryResult
from glassbox.tools.workflow import GitStatusResult


class CommitReadinessGitSummary(BaseModel):
    """Bounded git status and diff posture used by commit readiness."""

    model_config = ConfigDict(extra="forbid")

    branch: str | None = None
    ahead: int = 0
    behind: int = 0
    staged_paths: list[str] = Field(default_factory=list, max_length=200)
    unstaged_paths: list[str] = Field(default_factory=list, max_length=200)
    untracked_paths: list[str] = Field(default_factory=list, max_length=200)
    workspace_path_count: int = 0
    staged_path_count: int = 0
    policy_sensitive_paths: list[str] = Field(default_factory=list, max_length=100)
    generated_paths: list[str] = Field(default_factory=list, max_length=100)
    clean: bool = False
    error: str | None = None


def derive_commit_git_summary(
    git_status: GitStatusResult,
    workspace_diff: DiffSummaryResult,
    staged_diff: DiffSummaryResult | None,
) -> CommitReadinessGitSummary:
    """Build the bounded git summary used by commit and handoff readiness."""

    staged_paths = list(dict.fromkeys(git_status.staged))
    unstaged_paths = list(dict.fromkeys(git_status.modified))
    untracked_paths = list(dict.fromkeys(git_status.untracked))
    return CommitReadinessGitSummary(
        branch=git_status.branch,
        ahead=git_status.ahead,
        behind=git_status.behind,
        staged_paths=staged_paths,
        unstaged_paths=unstaged_paths,
        untracked_paths=untracked_paths,
        workspace_path_count=workspace_diff.risk_summary.touched_files,
        staged_path_count=(
            staged_diff.risk_summary.touched_files if staged_diff is not None else 0
        ),
        policy_sensitive_paths=workspace_diff.risk_summary.policy_sensitive_paths,
        generated_paths=workspace_diff.risk_summary.generated_files,
        clean=git_status.clean,
        error=git_status.error or workspace_diff.error,
    )


__all__ = [
    "CommitReadinessGitSummary",
    "derive_commit_git_summary",
]
