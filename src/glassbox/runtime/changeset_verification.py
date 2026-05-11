"""Changeset verification preview and evidence recording service."""

import asyncio
import json
import shlex
from pathlib import Path
from typing import cast

from glassbox.core import ArtifactId
from glassbox.core import ChangesetId
from glassbox.core import ChangesetInventoryFreshness
from glassbox.core import ChangesetInventoryRecord
from glassbox.core import ChangesetRecord
from glassbox.core import ChangesetVerificationPostureUpdated
from glassbox.core import EventEnvelope
from glassbox.core import SessionId
from glassbox.core import TaskId
from glassbox.core import TaskVerificationCompleted
from glassbox.core import TaskVerificationFailed
from glassbox.core import TaskVerificationId
from glassbox.core import TaskVerificationLedgerRecord
from glassbox.core import TaskVerificationPlanned
from glassbox.core import TaskVerificationResidualRiskAccepted
from glassbox.core import TaskVerificationRetried
from glassbox.core import TaskVerificationSkipped
from glassbox.core import TaskVerificationStarted
from glassbox.core import TaskVerificationStatus
from glassbox.core import TaskVerificationStreamed
from glassbox.core import ToolAttemptHeartbeat
from glassbox.core import ToolAttemptId
from glassbox.core import ToolAttemptRetryClassification
from glassbox.core import ToolAttemptStatus
from glassbox.core import ToolCallId
from glassbox.core import TurnId
from glassbox.core import VerificationCheckKind
from glassbox.core import VerificationFailureCategory
from glassbox.core import VerificationFailureDigest
from glassbox.core import VerificationPlanEntry
from glassbox.core import VerificationPlanLifecycleState
from glassbox.core import VerificationPlanSource
from glassbox.core import new_tool_attempt_id
from glassbox.core import new_tool_call_id
from glassbox.core import new_turn_id
from glassbox.core.events import ToolOutputStream
from glassbox.runtime.change_inventory import ChangeInventoryArtifact
from glassbox.runtime.changeset_detail import manual_evidence_for_preview
from glassbox.runtime.changeset_detail import review_response_summary_for_preview
from glassbox.runtime.changeset_inventory_status import inventory_status
from glassbox.runtime.changeset_models import ChangesetVerificationEvidenceRecordResult
from glassbox.runtime.changeset_models import ChangesetVerificationPlanDispositionResult
from glassbox.runtime.changeset_models import ChangesetVerificationPlanExecutionResult
from glassbox.runtime.changeset_models import ChangesetVerificationPlanPreview
from glassbox.runtime.changeset_models import PathVerificationPlanPreview
from glassbox.runtime.changeset_repository_contracts import ChangesetRepository
from glassbox.runtime.changeset_topology import derive_changeset_topology_impacts
from glassbox.runtime.changeset_verification_preview import artifact_ids_from_readiness
from glassbox.runtime.changeset_verification_preview import eval_profile_ids_for_preview
from glassbox.runtime.changeset_verification_preview import inventory_paths_for_preview
from glassbox.runtime.changeset_verification_preview import preview_commands
from glassbox.runtime.changeset_verification_preview import recipe_previews
from glassbox.runtime.changeset_verification_preview import recommendation_for_preview
from glassbox.runtime.changeset_verification_preview import release_surface_previews
from glassbox.runtime.changeset_verification_preview import (
    review_loop_verification_summary,
)
from glassbox.runtime.changeset_verification_preview import stale_evidence_previews
from glassbox.runtime.changeset_verification_preview import target_previews
from glassbox.runtime.changeset_verification_readiness import (
    derive_changeset_verification_readiness,
)
from glassbox.runtime.command_evidence import capture_command_environment
from glassbox.runtime.command_evidence import classify_command_purpose
from glassbox.runtime.verification import classify_verification_failure
from glassbox.runtime.verification_plan_builder import build_verification_plan_entries
from glassbox.runtime.workspace_profile import load_workspace_profile
from glassbox.services import ArtifactRepository
from glassbox.tools.command import RunCommandArgs
from glassbox.tools.command import RunCommandTool
from glassbox.tools.policy_command_risk import blocked_command_risk


class ChangesetVerificationService:
    """Preview and record changeset verification posture from retained evidence."""

    def __init__(
        self,
        repository: ChangesetRepository,
        artifact_repository: ArtifactRepository | None = None,
    ) -> None:
        self._repository = repository
        self._artifact_repository = artifact_repository

    def preview_plan(
        self,
        changeset_id: ChangesetId,
        workspace_root: Path,
    ) -> ChangesetVerificationPlanPreview:
        changeset = self._require_changeset(changeset_id)
        inventory_record = self._repository.get_changeset_inventory(
            changeset.session_id,
            changeset.changeset_id,
        )
        inventory, inventory_limitations = self._load_inventory_artifact(
            changeset.session_id,
            inventory_record,
        )
        status = inventory_status(
            changeset,
            inventory_record,
            workspace_root=workspace_root,
        )
        changed_paths = inventory_paths_for_preview(inventory)
        recommendation, recommendation_limitations = recommendation_for_preview(
            workspace_root,
            changed_paths,
        )
        topology_impacts, topology_limitations = derive_changeset_topology_impacts(
            workspace_root=workspace_root,
            changed_paths=changed_paths,
        )
        limitations = [
            *inventory_limitations,
            *recommendation_limitations,
            *topology_limitations,
            *(
                [status.reason]
                if status.reason is not None
                and status.freshness != ChangesetInventoryFreshness.FRESH
                else []
            ),
        ]
        ledger = self._task_ledger_for_changeset(changeset)
        inventory_freshness = status.freshness
        readiness = derive_changeset_verification_readiness(
            inventory=inventory,
            inventory_freshness=inventory_freshness,
            inventory_sequence=(
                inventory_record.last_sequence if inventory_record is not None else None
            ),
            task_ledger=ledger,
            eval_recommendation=recommendation,
            workspace_profile=load_workspace_profile(workspace_root),
        )
        retained_artifact_ids = artifact_ids_from_readiness(readiness)
        response_summary = review_response_summary_for_preview(
            self._repository,
            changeset,
            workspace_root=workspace_root,
        )
        manual_evidence = manual_evidence_for_preview(self._repository, changeset)
        review_loop_summary = review_loop_verification_summary(
            changeset=changeset,
            response_summary=response_summary,
            manual_evidence=manual_evidence,
            readiness=readiness,
            topology_impacts=topology_impacts,
        )
        plan_entries, skipped_checks = build_verification_plan_entries(
            changed_paths=changed_paths,
            readiness=readiness,
            recommendation=recommendation,
        )
        return ChangesetVerificationPlanPreview(
            changeset_id=changeset.changeset_id,
            session_id=changeset.session_id,
            inventory_artifact_id=(
                inventory_record.artifact_id if inventory_record is not None else None
            ),
            inventory_freshness=inventory_freshness,
            changed_paths=changed_paths,
            plan_entries=plan_entries,
            skipped_checks=skipped_checks,
            recommended_commands=preview_commands(
                readiness,
                recommendation,
            ),
            eval_profiles=eval_profile_ids_for_preview(recommendation),
            recipes=recipe_previews(recommendation),
            recommended_targets=target_previews(recommendation),
            release_surfaces=release_surface_previews(recommendation),
            stale_evidence=stale_evidence_previews(readiness),
            topology_impacts=topology_impacts,
            review_loop_summary=review_loop_summary,
            reason_groups=(
                recommendation.reason_groups if recommendation is not None else []
            ),
            expected_scope=changed_paths,
            retained_artifact_ids=retained_artifact_ids,
            readiness=readiness,
            limitations=limitations,
            safe_next_actions=list(
                dict.fromkeys(
                    [
                        *readiness.safe_next_actions,
                        *review_loop_summary.safe_next_actions,
                    ]
                )
            ),
            non_claims=[
                *readiness.non_claims,
                *review_loop_summary.non_claims,
                "verification plan preview does not run commands",
                (
                    "publish, deploy, push, and upload commands are not "
                    "recommended as verification"
                ),
            ],
        )

    def preview_paths(
        self,
        workspace_root: Path,
        changed_paths: list[str],
    ) -> PathVerificationPlanPreview:
        normalized_paths = list(dict.fromkeys(path for path in changed_paths if path))
        recommendation, recommendation_limitations = recommendation_for_preview(
            workspace_root,
            normalized_paths,
        )
        plan_entries, skipped_checks = build_verification_plan_entries(
            changed_paths=normalized_paths,
            recommendation=recommendation,
        )
        recommended_commands = (
            list(recommendation.suggested_commands)
            if recommendation is not None
            else []
        )
        safe_next_actions = list(
            dict.fromkeys(
                [
                    *recommended_commands,
                    "glassbox changeset verification-plan CHANGESET_ID --cwd .",
                ]
            )
        )
        return PathVerificationPlanPreview(
            workspace_root=str(workspace_root),
            changed_paths=normalized_paths,
            plan_entries=plan_entries,
            skipped_checks=skipped_checks,
            recommended_commands=recommended_commands,
            eval_profiles=eval_profile_ids_for_preview(recommendation),
            recipes=recipe_previews(recommendation),
            recommended_targets=target_previews(recommendation),
            release_surfaces=release_surface_previews(recommendation),
            reason_groups=(
                recommendation.reason_groups if recommendation is not None else []
            ),
            limitations=recommendation_limitations,
            safe_next_actions=safe_next_actions,
            non_claims=[
                "path verification plan preview does not run commands",
                "path preview is not persisted changeset evidence",
                "manual-only entries are advisory and are not passes",
            ],
        )

    def record_existing_evidence(
        self,
        changeset_id: ChangesetId,
        workspace_root: Path,
        *,
        task_id: TaskId | None = None,
        verification_id: TaskVerificationId | None = None,
    ) -> ChangesetVerificationEvidenceRecordResult:
        changeset = self._require_changeset(changeset_id)
        resolved_task_id = task_id or changeset.task_id
        if resolved_task_id is None:
            raise ValueError(
                "task_id is required when the changeset is not task-backed"
            )
        ledger = self._repository.list_task_verification_ledger(
            changeset.session_id,
            resolved_task_id,
        )
        if verification_id is not None:
            ledger = [
                entry for entry in ledger if entry.verification_id == verification_id
            ]
        if not ledger:
            raise ValueError("no retained task verification evidence matched")
        inventory_record = self._repository.get_changeset_inventory(
            changeset.session_id,
            changeset.changeset_id,
        )
        inventory, _limitations = self._load_inventory_artifact(
            changeset.session_id,
            inventory_record,
        )
        status = inventory_status(
            changeset,
            inventory_record,
            workspace_root=workspace_root,
        )
        recommendation, _limitations = recommendation_for_preview(
            workspace_root,
            inventory_paths_for_preview(inventory),
        )
        readiness = derive_changeset_verification_readiness(
            inventory=inventory,
            inventory_freshness=status.freshness,
            inventory_sequence=(
                inventory_record.last_sequence if inventory_record is not None else None
            ),
            task_ledger=ledger,
            eval_recommendation=recommendation,
            workspace_profile=load_workspace_profile(workspace_root),
        )
        selected = sorted(ledger, key=lambda entry: entry.last_sequence)
        primary = selected[-1]
        retained_artifact_ids = artifact_ids_from_readiness(readiness)
        stored = self._repository.append_events(
            [
                EventEnvelope(
                    session_id=changeset.session_id,
                    sequence=0,
                    payload=ChangesetVerificationPostureUpdated(
                        changeset_id=changeset.changeset_id,
                        state=readiness.state,
                        summary=readiness.summary,
                        verification_id=primary.verification_id,
                        artifact_id=primary.latest_artifact_id
                        or primary.latest_failed_artifact_id,
                        task_id=resolved_task_id,
                        stale_count=readiness.stale_count,
                        missing_count=readiness.missing_count,
                        failed_count=readiness.failed_count,
                        accepted_risk_count=readiness.accepted_risk_count,
                    ),
                )
            ]
        )
        return ChangesetVerificationEvidenceRecordResult(
            changeset_id=changeset.changeset_id,
            session_id=changeset.session_id,
            selected_verification_ids=[entry.verification_id for entry in selected],
            retained_artifact_ids=retained_artifact_ids,
            readiness=readiness,
            event=stored[0],
        )

    def select_plan_entry(
        self,
        changeset_id: ChangesetId,
        workspace_root: Path,
        *,
        verification_id: TaskVerificationId,
    ) -> ChangesetVerificationPlanDispositionResult:
        changeset, task_id, entry = self._plan_disposition_context(
            changeset_id,
            workspace_root,
            verification_id=verification_id,
        )
        selected = entry.model_copy(
            update={"lifecycle_state": VerificationPlanLifecycleState.SELECTED}
        )
        events = self._repository.append_events(
            [
                EventEnvelope(
                    session_id=changeset.session_id,
                    sequence=0,
                    payload=TaskVerificationPlanned(
                        task_id=task_id,
                        verification=selected,
                    ),
                )
            ]
        )
        return self._disposition_result(
            changeset,
            task_id=task_id,
            action="selected",
            entry=selected,
            events=events,
        )

    def skip_plan_entry(
        self,
        changeset_id: ChangesetId,
        workspace_root: Path,
        *,
        verification_id: TaskVerificationId,
        reason: str,
    ) -> ChangesetVerificationPlanDispositionResult:
        changeset, task_id, entry = self._plan_disposition_context(
            changeset_id,
            workspace_root,
            verification_id=verification_id,
        )
        skipped = entry.model_copy(
            update={"lifecycle_state": VerificationPlanLifecycleState.SKIPPED}
        )
        events = self._repository.append_events(
            [
                EventEnvelope(
                    session_id=changeset.session_id,
                    sequence=0,
                    payload=TaskVerificationPlanned(
                        task_id=task_id,
                        verification=skipped,
                    ),
                ),
                EventEnvelope(
                    session_id=changeset.session_id,
                    sequence=0,
                    payload=TaskVerificationSkipped(
                        task_id=task_id,
                        verification_id=verification_id,
                        reason=reason,
                    ),
                ),
            ]
        )
        return self._disposition_result(
            changeset,
            task_id=task_id,
            action="skipped",
            entry=skipped,
            events=events,
        )

    def accept_plan_entry_risk(
        self,
        changeset_id: ChangesetId,
        workspace_root: Path,
        *,
        verification_id: TaskVerificationId,
        reason: str,
        residual_risks: list[str],
        accepted_by: str = "operator",
    ) -> ChangesetVerificationPlanDispositionResult:
        changeset, task_id, entry = self._plan_disposition_context(
            changeset_id,
            workspace_root,
            verification_id=verification_id,
        )
        accepted = entry.model_copy(
            update={"lifecycle_state": VerificationPlanLifecycleState.ACCEPTED_RISK}
        )
        events = self._repository.append_events(
            [
                EventEnvelope(
                    session_id=changeset.session_id,
                    sequence=0,
                    payload=TaskVerificationPlanned(
                        task_id=task_id,
                        verification=accepted,
                    ),
                ),
                EventEnvelope(
                    session_id=changeset.session_id,
                    sequence=0,
                    payload=TaskVerificationResidualRiskAccepted(
                        task_id=task_id,
                        verification_id=verification_id,
                        accepted_by=accepted_by,
                        reason=reason,
                        residual_risks=residual_risks,
                    ),
                ),
            ]
        )
        return self._disposition_result(
            changeset,
            task_id=task_id,
            action="accepted-risk",
            entry=accepted,
            events=events,
        )

    def supersede_plan_entry(
        self,
        changeset_id: ChangesetId,
        workspace_root: Path,
        *,
        verification_id: TaskVerificationId,
        replacement_verification_id: TaskVerificationId,
        reason: str,
    ) -> ChangesetVerificationPlanDispositionResult:
        changeset, task_id, entry = self._plan_disposition_context(
            changeset_id,
            workspace_root,
            verification_id=verification_id,
        )
        replacement_entry = self._plan_entry(
            self.preview_plan(changeset_id, workspace_root),
            replacement_verification_id,
        )
        replacement = (
            replacement_entry.model_copy(
                update={"lifecycle_state": VerificationPlanLifecycleState.SELECTED}
            )
            if replacement_entry.command or replacement_entry.command_recipe is not None
            else replacement_entry
        )
        superseded = entry.model_copy(
            update={
                "lifecycle_state": VerificationPlanLifecycleState.SUPERSEDED,
                "superseded_by_verification_id": replacement_verification_id,
            }
        )
        events = self._repository.append_events(
            [
                EventEnvelope(
                    session_id=changeset.session_id,
                    sequence=0,
                    payload=TaskVerificationPlanned(
                        task_id=task_id,
                        verification=superseded,
                    ),
                ),
                EventEnvelope(
                    session_id=changeset.session_id,
                    sequence=0,
                    payload=TaskVerificationRetried(
                        task_id=task_id,
                        verification_id=verification_id,
                        next_verification_id=replacement_verification_id,
                        attempt=1,
                        reason=reason,
                    ),
                ),
                EventEnvelope(
                    session_id=changeset.session_id,
                    sequence=0,
                    payload=TaskVerificationPlanned(
                        task_id=task_id,
                        verification=replacement,
                    ),
                ),
            ]
        )
        return self._disposition_result(
            changeset,
            task_id=task_id,
            action="superseded",
            entry=superseded,
            events=events,
            replacement_verification_id=replacement_verification_id,
        )

    def run_selected_plan_entry(
        self,
        changeset_id: ChangesetId,
        workspace_root: Path,
        *,
        verification_id: TaskVerificationId,
        confirmed: bool = False,
    ) -> ChangesetVerificationPlanExecutionResult:
        if not confirmed:
            raise ValueError("verification command execution requires --confirm")
        changeset = self._require_changeset(changeset_id)
        if changeset.task_id is None:
            raise ValueError(
                "verification command execution requires a task-backed changeset"
            )
        ledger_entry = self._selected_ledger_entry(changeset, verification_id)
        entry = self._entry_from_ledger_record(ledger_entry)
        if not entry.command:
            raise ValueError("selected verification entry does not have a command")

        command = shlex.join(entry.command)
        risk = blocked_command_risk(command)
        if risk is not None:
            failure = VerificationFailureDigest(
                category=VerificationFailureCategory.POLICY,
                summary=risk.reason,
            )
            tool_attempt_id = new_tool_attempt_id()
            tool_call_id = new_tool_call_id()
            turn_id = new_turn_id()
            events = self._repository.append_events(
                [
                    EventEnvelope(
                        session_id=changeset.session_id,
                        sequence=0,
                        payload=self._tool_attempt_heartbeat(
                            entry,
                            command=command,
                            status=ToolAttemptStatus.FAILED,
                            tool_attempt_id=tool_attempt_id,
                            tool_call_id=tool_call_id,
                            turn_id=turn_id,
                            task_id=changeset.task_id,
                            message=risk.reason,
                            retry_policy_reason=risk.source_label,
                        ),
                    ),
                    EventEnvelope(
                        session_id=changeset.session_id,
                        sequence=0,
                        payload=TaskVerificationFailed(
                            task_id=changeset.task_id,
                            verification_id=verification_id,
                            failure=failure,
                        ),
                    ),
                ]
            )
            return self._execution_result(
                changeset,
                entry=entry,
                status="policy_blocked",
                events=events,
            )

        events, exit_code, timed_out, artifact_id = asyncio.run(
            self._execute_selected_entry(
                changeset,
                entry,
                workspace_root=workspace_root,
                command=command,
            )
        )
        status = (
            "passed"
            if exit_code in entry.expected_exit_codes and not timed_out
            else "failed"
        )
        if timed_out:
            status = "timed_out"
        return self._execution_result(
            changeset,
            entry=entry,
            status=status,
            events=events,
            exit_code=exit_code,
            timed_out=timed_out,
            output_artifact_id=artifact_id,
        )

    async def _execute_selected_entry(
        self,
        changeset: ChangesetRecord,
        entry: VerificationPlanEntry,
        *,
        workspace_root: Path,
        command: str,
    ) -> tuple[list[EventEnvelope], int | None, bool, ArtifactId | None]:
        task_id = changeset.task_id
        if task_id is None:
            raise ValueError("verification command execution requires task id")
        tool_attempt_id = new_tool_attempt_id()
        tool_call_id = new_tool_call_id()
        turn_id = new_turn_id()
        output_chunks: list[str] = []
        pending_events: list[EventEnvelope] = [
            EventEnvelope(
                session_id=changeset.session_id,
                sequence=0,
                payload=self._tool_attempt_heartbeat(
                    entry,
                    command=command,
                    status=ToolAttemptStatus.STARTED,
                    tool_attempt_id=tool_attempt_id,
                    tool_call_id=tool_call_id,
                    turn_id=turn_id,
                    task_id=task_id,
                    message="verification command selected",
                ),
            ),
            EventEnvelope(
                session_id=changeset.session_id,
                sequence=0,
                payload=TaskVerificationStarted(
                    task_id=task_id,
                    verification_id=entry.verification_id,
                    check_name=entry.check_name,
                ),
            ),
            EventEnvelope(
                session_id=changeset.session_id,
                sequence=0,
                payload=self._tool_attempt_heartbeat(
                    entry,
                    command=command,
                    status=ToolAttemptStatus.RUNNING,
                    tool_attempt_id=tool_attempt_id,
                    tool_call_id=tool_call_id,
                    turn_id=turn_id,
                    task_id=task_id,
                    message="verification command running",
                ),
            ),
        ]

        def on_chunk(stream: str, chunk: str) -> None:
            output_chunks.append(chunk)
            pending_events.append(
                EventEnvelope(
                    session_id=changeset.session_id,
                    sequence=0,
                    payload=TaskVerificationStreamed(
                        task_id=task_id,
                        verification_id=entry.verification_id,
                        stream=cast(ToolOutputStream, stream),
                        chunk_summary=chunk.strip()[:2000] or f"{stream} output",
                    ),
                )
            )

        result = await RunCommandTool(workspace_root).execute_streaming(
            RunCommandArgs(
                command=command,
                timeout=min(entry.timeout_seconds, 300),
            ),
            on_chunk,
        )
        output = "\n".join(part for part in [result.stdout, result.stderr] if part)
        if not output and output_chunks:
            output = "\n".join(output_chunks)
        artifact = (
            self._artifact_repository.write_text_artifact(
                changeset.session_id,
                output or f"{entry.check_name} produced no output\n",
                suffix=".verification-output.txt",
            )
            if self._artifact_repository is not None
            else None
        )
        artifact_id = artifact.artifact_id if artifact is not None else None
        passed = result.exit_code in entry.expected_exit_codes and not result.timed_out
        if passed:
            pending_events.append(
                EventEnvelope(
                    session_id=changeset.session_id,
                    sequence=0,
                    payload=TaskVerificationCompleted(
                        task_id=task_id,
                        verification_id=entry.verification_id,
                        status=TaskVerificationStatus.PASSED,
                        summary=f"{entry.check_name} passed",
                        artifact_id=artifact_id,
                    ),
                )
            )
        else:
            failure = classify_verification_failure(
                output,
                exit_code=result.exit_code,
                timed_out=result.timed_out,
            )
            if artifact_id is not None:
                failure = failure.model_copy(update={"artifact_id": artifact_id})
            pending_events.append(
                EventEnvelope(
                    session_id=changeset.session_id,
                    sequence=0,
                    payload=TaskVerificationFailed(
                        task_id=task_id,
                        verification_id=entry.verification_id,
                        failure=failure,
                    ),
                )
            )
        pending_events.append(
            EventEnvelope(
                session_id=changeset.session_id,
                sequence=0,
                payload=self._tool_attempt_heartbeat(
                    entry,
                    command=command,
                    status=(
                        ToolAttemptStatus.SUCCEEDED
                        if passed
                        else ToolAttemptStatus.FAILED
                    ),
                    tool_attempt_id=tool_attempt_id,
                    tool_call_id=tool_call_id,
                    turn_id=turn_id,
                    task_id=task_id,
                    message=(
                        "verification command passed"
                        if passed
                        else "verification command failed"
                    ),
                    output_artifact_id=artifact_id,
                ),
            )
        )
        stored = self._repository.append_events(pending_events)
        return stored, result.exit_code, result.timed_out, artifact_id

    def _task_ledger_for_changeset(
        self,
        changeset: ChangesetRecord,
    ) -> list[TaskVerificationLedgerRecord]:
        if changeset.task_id is None:
            return []
        return self._repository.list_task_verification_ledger(
            changeset.session_id,
            changeset.task_id,
        )

    def _plan_disposition_context(
        self,
        changeset_id: ChangesetId,
        workspace_root: Path,
        *,
        verification_id: TaskVerificationId,
    ) -> tuple[ChangesetRecord, TaskId, VerificationPlanEntry]:
        changeset = self._require_changeset(changeset_id)
        if changeset.task_id is None:
            raise ValueError(
                "verification plan decisions require a task-backed changeset"
            )
        preview = self.preview_plan(changeset_id, workspace_root)
        return (
            changeset,
            changeset.task_id,
            self._plan_entry(preview, verification_id),
        )

    def _selected_ledger_entry(
        self,
        changeset: ChangesetRecord,
        verification_id: TaskVerificationId,
    ) -> TaskVerificationLedgerRecord:
        if changeset.task_id is None:
            raise ValueError("verification command execution requires task id")
        for entry in self._repository.list_task_verification_ledger(
            changeset.session_id,
            changeset.task_id,
        ):
            if entry.verification_id == verification_id:
                if entry.status not in {
                    TaskVerificationStatus.PLANNED,
                    TaskVerificationStatus.FAILED,
                }:
                    raise ValueError(
                        "verification entry must be selected or failed before "
                        "it can run"
                    )
                return entry
        raise ValueError("verification_id has not been selected for this changeset")

    def _entry_from_ledger_record(
        self,
        record: TaskVerificationLedgerRecord,
    ) -> VerificationPlanEntry:
        return VerificationPlanEntry(
            verification_id=record.verification_id,
            check_name=record.check_name,
            kind=record.kind or VerificationCheckKind.COMMAND,
            command=[str(part) for part in record.command],
            source=record.source or VerificationPlanSource.OPERATOR,
            rationale="Selected verification plan entry retained in the ledger.",
            blocking=record.blocking,
            changed_paths=list(record.changed_paths),
            eval_case_id=record.eval_case_id,
            eval_profile_id=record.eval_profile_id,
        )

    def _tool_attempt_heartbeat(
        self,
        entry: VerificationPlanEntry,
        *,
        command: str,
        status: ToolAttemptStatus,
        tool_attempt_id: ToolAttemptId,
        tool_call_id: ToolCallId,
        turn_id: TurnId,
        task_id: TaskId,
        message: str,
        output_artifact_id: ArtifactId | None = None,
        retry_policy_reason: str | None = None,
    ) -> ToolAttemptHeartbeat:
        command_assessment = classify_command_purpose(command)
        retry_classification = ToolAttemptRetryClassification.UNKNOWN
        retry_requires_approval = entry.execution_requires_approval
        retry_reason = "retry requires operator inspection and explicit confirmation"
        safe_to_retry = status == ToolAttemptStatus.FAILED
        if status in {ToolAttemptStatus.STARTED, ToolAttemptStatus.RUNNING}:
            retry_classification = ToolAttemptRetryClassification.ALREADY_RUNNING
            retry_requires_approval = False
            retry_reason = "verification command is already running"
            safe_to_retry = False
        elif status == ToolAttemptStatus.SUCCEEDED:
            retry_classification = ToolAttemptRetryClassification.UNSAFE_TO_RETRY
            retry_requires_approval = False
            retry_reason = (
                "successful verification should not be retried without a new "
                "selected verification reason"
            )
            safe_to_retry = False
        elif status == ToolAttemptStatus.FAILED:
            retry_classification = ToolAttemptRetryClassification.RETRYABLE
        return ToolAttemptHeartbeat(
            tool_attempt_id=tool_attempt_id,
            status=status,
            turn_id=turn_id,
            tool_call_id=tool_call_id,
            task_id=task_id,
            tool_name="run_command",
            message=message,
            output_artifact_id=output_artifact_id,
            safe_to_retry=safe_to_retry,
            command_purpose=command_assessment.purpose,
            command_review_relevance=command_assessment.review_relevance,
            command_supports_verification=command_assessment.supports_verification,
            command_purpose_reason=command_assessment.reason,
            command_environment=capture_command_environment(
                command=command,
                assessment=command_assessment,
            ),
            retry_classification=retry_classification,
            retry_requires_approval=retry_requires_approval,
            retry_reason=retry_reason,
            retry_policy_reason=retry_policy_reason,
        )

    def _execution_result(
        self,
        changeset: ChangesetRecord,
        *,
        entry: VerificationPlanEntry,
        status: str,
        events: list[EventEnvelope],
        exit_code: int | None = None,
        timed_out: bool = False,
        output_artifact_id: ArtifactId | None = None,
    ) -> ChangesetVerificationPlanExecutionResult:
        if changeset.task_id is None:
            raise ValueError("verification command execution requires task id")
        return ChangesetVerificationPlanExecutionResult(
            changeset_id=changeset.changeset_id,
            session_id=changeset.session_id,
            task_id=changeset.task_id,
            verification_id=entry.verification_id,
            check_name=entry.check_name,
            status=status,
            command=entry.command,
            exit_code=exit_code,
            timed_out=timed_out,
            output_artifact_id=output_artifact_id,
            events=events,
            safe_next_actions=[
                (
                    "glassbox changeset verification-plan "
                    f"{changeset.changeset_id} --cwd ."
                ),
                f"glassbox changeset show {changeset.changeset_id} --cwd .",
            ],
            non_claims=[
                "verification-run only runs explicitly selected local commands",
                "passing verification is local evidence, not reviewer approval",
                "publication remains outside verification plan execution",
            ],
        )

    def _plan_entry(
        self,
        preview: ChangesetVerificationPlanPreview,
        verification_id: TaskVerificationId,
    ) -> VerificationPlanEntry:
        for entry in preview.plan_entries:
            if entry.verification_id == verification_id:
                return entry
        raise ValueError("verification_id is not present in the current plan preview")

    def _disposition_result(
        self,
        changeset: ChangesetRecord,
        *,
        task_id: TaskId,
        action: str,
        entry: VerificationPlanEntry,
        events: list[EventEnvelope],
        replacement_verification_id: TaskVerificationId | None = None,
    ) -> ChangesetVerificationPlanDispositionResult:
        return ChangesetVerificationPlanDispositionResult(
            changeset_id=changeset.changeset_id,
            session_id=changeset.session_id,
            task_id=task_id,
            action=action,
            verification_id=entry.verification_id,
            replacement_verification_id=replacement_verification_id,
            events=events,
            entry=entry,
            safe_next_actions=[
                (
                    "glassbox changeset verification-plan "
                    f"{changeset.changeset_id} --cwd ."
                ),
                f"glassbox changeset show {changeset.changeset_id} --cwd .",
            ],
            non_claims=[
                "verification plan decisions do not run commands",
                "selected checks are not passed until retained evidence says so",
                "accepted risk is local evidence, not release approval",
            ],
        )

    def _load_inventory_artifact(
        self,
        session_id: SessionId,
        inventory_record: ChangesetInventoryRecord | None,
    ) -> tuple[ChangeInventoryArtifact | None, list[str]]:
        if inventory_record is None:
            return None, ["no structured change inventory is attached yet"]
        if self._artifact_repository is None:
            return None, ["artifact repository is unavailable"]
        try:
            content = self._artifact_repository.read_text_artifact(
                _changeset_inventory_artifact_path(
                    session_id,
                    inventory_record.artifact_id,
                )
            )
            return ChangeInventoryArtifact.model_validate_json(content), []
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return None, [f"change inventory artifact could not be read: {exc}"]

    def _require_changeset(self, changeset_id: ChangesetId) -> ChangesetRecord:
        changeset = self._repository.get_changeset(changeset_id)
        if changeset is None:
            raise ValueError(f"unknown changeset: {changeset_id}")
        return changeset


def _changeset_inventory_artifact_path(
    session_id: SessionId,
    artifact_id: ArtifactId,
) -> Path:
    return (
        Path(".glassbox")
        / "sessions"
        / str(session_id)
        / "artifacts"
        / f"{artifact_id}.changeset-inventory.json"
    )


__all__ = ["ChangesetVerificationService"]
