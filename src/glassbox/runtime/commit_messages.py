"""Deterministic commit message suggestions for changesets."""

from collections.abc import Sequence
from pathlib import Path
from textwrap import shorten

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core import ChangesetId
from glassbox.core import ChangesetRecord
from glassbox.core import SessionId
from glassbox.core import TaskRecord
from glassbox.runtime.changesets import ChangesetQueryService
from glassbox.runtime.changesets import ChangesetRepository
from glassbox.runtime.changesets import ChangesetVerificationPlanPreview
from glassbox.runtime.changesets import ChangesetVerificationService
from glassbox.runtime.commit_readiness import ChangesetCommitReadinessService
from glassbox.runtime.commit_readiness import CommitReadinessAssessment
from glassbox.services import ArtifactRepository

COMMIT_MESSAGE_SUGGESTION_KIND = "changeset_commit_message_suggestion"
COMMIT_MESSAGE_SUGGESTION_VERSION = 1


class CommitMessageEvidenceLine(BaseModel):
    """One retained-evidence line used to draft the message."""

    model_config = ConfigDict(extra="forbid")

    kind: str = Field(min_length=1, max_length=100)
    summary: str = Field(min_length=1, max_length=1000)
    references: list[str] = Field(default_factory=list, max_length=20)


class CommitMessageSuggestion(BaseModel):
    """Commit message draft labeled as a non-mutating suggestion."""

    model_config = ConfigDict(extra="forbid")

    suggestion_kind: str = COMMIT_MESSAGE_SUGGESTION_KIND
    schema_version: int = COMMIT_MESSAGE_SUGGESTION_VERSION
    suggestion_label: str = "suggestion_only_not_committed"
    changeset_id: ChangesetId
    session_id: SessionId
    style: str = "plain"
    subject: str = Field(min_length=1, max_length=200)
    body: list[str] = Field(default_factory=list)
    message: str = Field(min_length=1, max_length=4000)
    deterministic: bool = True
    commit_readiness_state: str
    evidence: list[CommitMessageEvidenceLine] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list, max_length=20)
    non_claims: list[str] = Field(default_factory=list, max_length=20)


class ChangesetCommitMessageSuggestionService:
    """Draft commit messages from retained changeset evidence."""

    def __init__(
        self,
        repository: ChangesetRepository,
        artifact_repository: ArtifactRepository | None = None,
    ) -> None:
        self._repository = repository
        self._artifact_repository = artifact_repository

    async def suggest(
        self,
        changeset_id: ChangesetId,
        workspace_root: Path,
        *,
        style: str = "plain",
    ) -> CommitMessageSuggestion:
        """Build one deterministic commit message suggestion."""

        if style not in {"plain", "conventional"}:
            raise ValueError("style must be plain or conventional")
        detail = ChangesetQueryService(self._repository).get_detail(
            changeset_id,
            workspace_root=workspace_root,
        )
        verification_plan = ChangesetVerificationService(
            self._repository,
            self._artifact_repository,
        ).preview_plan(changeset_id, workspace_root)
        commit_readiness = await ChangesetCommitReadinessService(
            self._repository,
            self._artifact_repository,
        ).preview(changeset_id, workspace_root)
        task = (
            self._repository.get_task(detail.changeset.task_id)
            if detail.changeset.task_id is not None
            else None
        )
        return build_commit_message_suggestion(
            changeset=detail.changeset,
            task=task,
            verification_plan=verification_plan,
            commit_readiness=commit_readiness,
            changed_paths=verification_plan.changed_paths,
            style=style,
        )


def build_commit_message_suggestion(
    *,
    changeset: ChangesetRecord,
    task: TaskRecord | None,
    verification_plan: ChangesetVerificationPlanPreview,
    commit_readiness: CommitReadinessAssessment,
    changed_paths: Sequence[str],
    style: str = "plain",
) -> CommitMessageSuggestion:
    """Build a deterministic commit message suggestion from evidence."""

    subject = _subject(changeset, changed_paths=changed_paths, style=style)
    evidence = _evidence_lines(
        changeset=changeset,
        task=task,
        verification_plan=verification_plan,
        commit_readiness=commit_readiness,
        changed_paths=changed_paths,
    )
    body = [line.summary for line in evidence]
    limitations = _limitations(changeset, task, changed_paths)
    message = "\n\n".join(
        [
            subject,
            "\n".join(f"- {line}" for line in body),
        ]
    )
    return CommitMessageSuggestion(
        changeset_id=changeset.changeset_id,
        session_id=changeset.session_id,
        style=style,
        subject=subject,
        body=body,
        message=message,
        commit_readiness_state=commit_readiness.state.value,
        evidence=evidence,
        limitations=limitations,
        non_claims=[
            "commit message is a deterministic suggestion, not a commit action",
            "operator should edit the message before committing",
            "message does not include raw diffs, file contents, or command output",
            "facts absent from changeset evidence are not invented",
        ],
    )


def _subject(
    changeset: ChangesetRecord,
    *,
    changed_paths: Sequence[str],
    style: str,
) -> str:
    objective = " ".join(changeset.objective.strip().split())
    if not objective:
        objective = changeset.summary or "Update changeset evidence"
    base = _strip_terminal_punctuation(shorten(objective, width=72, placeholder="..."))
    if style == "conventional":
        return f"{_conventional_type(changed_paths)}: {base}"
    return base


def _evidence_lines(
    *,
    changeset: ChangesetRecord,
    task: TaskRecord | None,
    verification_plan: ChangesetVerificationPlanPreview,
    commit_readiness: CommitReadinessAssessment,
    changed_paths: Sequence[str],
) -> list[CommitMessageEvidenceLine]:
    lines = [
        CommitMessageEvidenceLine(
            kind="changeset",
            summary=f"Changeset: {changeset.changeset_id}",
        ),
        CommitMessageEvidenceLine(
            kind="changed_paths",
            summary=_changed_paths_summary(changed_paths),
            references=list(changed_paths[:20]),
        ),
        CommitMessageEvidenceLine(
            kind="verification",
            summary=(
                f"Verification: {verification_plan.readiness.state.value} - "
                f"{verification_plan.readiness.summary}"
            ),
        ),
        CommitMessageEvidenceLine(
            kind="commit_readiness",
            summary=(
                f"Commit readiness: {commit_readiness.state.value} - "
                f"{commit_readiness.reason}"
            ),
        ),
        CommitMessageEvidenceLine(
            kind="risk",
            summary=(
                f"Risk: {changeset.risk_level.value}; "
                f"{changeset.unresolved_risk_count} unresolved, "
                f"{changeset.accepted_risk_count} accepted"
            ),
        ),
    ]
    if task is not None:
        lines.insert(
            1,
            CommitMessageEvidenceLine(
                kind="task",
                summary=f"Task: {task.title} ({task.status.value})",
                references=[str(task.task_id)],
            ),
        )
    elif changeset.task_id is not None:
        lines.insert(
            1,
            CommitMessageEvidenceLine(
                kind="task",
                summary=f"Task: {changeset.task_id}",
                references=[str(changeset.task_id)],
            ),
        )
    return lines


def _changed_paths_summary(changed_paths: Sequence[str]) -> str:
    if not changed_paths:
        return "Changed paths: none recorded"
    shown = ", ".join(changed_paths[:5])
    suffix = "" if len(changed_paths) <= 5 else f", +{len(changed_paths) - 5} more"
    return f"Changed paths: {len(changed_paths)} ({shown}{suffix})"


def _limitations(
    changeset: ChangesetRecord,
    task: TaskRecord | None,
    changed_paths: Sequence[str],
) -> list[str]:
    limitations: list[str] = []
    if task is None and changeset.task_id is not None:
        limitations.append("task record could not be loaded; only task ID is included")
    if not changed_paths:
        limitations.append("changed-path inventory is missing or empty")
    if changeset.summary is None:
        limitations.append("changeset has no separate summary field")
    return limitations


def _conventional_type(changed_paths: Sequence[str]) -> str:
    paths = list(changed_paths)
    if paths and all(
        path.startswith("docs/") or path.endswith(".md") for path in paths
    ):
        return "docs"
    if paths and all(
        path.startswith("tests/")
        or "/tests/" in path
        or path.endswith((".test.ts", ".test.tsx", "_test.py"))
        for path in paths
    ):
        return "test"
    return "chore"


def _strip_terminal_punctuation(value: str) -> str:
    return value.rstrip(".:;")


__all__ = [
    "COMMIT_MESSAGE_SUGGESTION_KIND",
    "COMMIT_MESSAGE_SUGGESTION_VERSION",
    "ChangesetCommitMessageSuggestionService",
    "CommitMessageEvidenceLine",
    "CommitMessageSuggestion",
    "build_commit_message_suggestion",
]
