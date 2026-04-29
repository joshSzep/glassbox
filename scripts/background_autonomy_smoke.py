"""Run deterministic background autonomy smoke scenarios for v8."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Any
from typing import cast

SCRIPT_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_REPO_ROOT))

from glassbox.core import AutonomyMode  # noqa: E402
from glassbox.core import BackgroundJobFailureKind  # noqa: E402
from glassbox.core import BackgroundJobKind  # noqa: E402
from glassbox.core import BackgroundJobState  # noqa: E402
from glassbox.core import EventEnvelope  # noqa: E402
from glassbox.core import SessionStarted  # noqa: E402
from glassbox.core import TaskCreated  # noqa: E402
from glassbox.core import TaskPlanProposed  # noqa: E402
from glassbox.core import TaskPlanSnapshot  # noqa: E402
from glassbox.core import TaskStepProposal  # noqa: E402
from glassbox.core import new_session_id  # noqa: E402
from glassbox.core import new_task_id  # noqa: E402
from glassbox.core import new_task_step_id  # noqa: E402
from glassbox.runtime.background_jobs import (  # noqa: E402
    run_background_job_worker_once,
)
from glassbox.runtime.background_jobs import (  # noqa: E402
    run_background_job_worker_once_async,
)
from glassbox.runtime.bootstrap import open_runtime_context  # noqa: E402
from glassbox.runtime.task_queries import TaskPlanRepository  # noqa: E402

DEFAULT_EVIDENCE_ROOT = SCRIPT_REPO_ROOT / ".glassbox" / "releases"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run deterministic v8 background autonomy release smoke.",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        help="isolated workspace to use; defaults inside the evidence directory",
    )
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        help="directory for retained smoke evidence",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="write the planned scenario list without running the smoke",
    )
    parser.add_argument("--json", action="store_true", help="print summary JSON")
    args = parser.parse_args(argv)

    evidence_dir = _resolve_evidence_dir(args.evidence_dir)
    workspace = (args.workspace or evidence_dir / "workspace").resolve()
    summary = _new_summary(evidence_dir, workspace, dry_run=args.dry_run)

    if args.dry_run:
        summary["status"] = "dry_run"
        summary["scenarios"] = _planned_scenarios()
        _write_summary(evidence_dir, summary)
        _print_summary(summary, as_json=args.json)
        return 0

    try:
        workspace.mkdir(parents=True, exist_ok=True)
        summary["scenarios"] = _run_smoke(workspace)
        summary["status"] = "passed"
    except Exception as exc:  # pragma: no cover - exercised by release operators
        summary["status"] = "failed"
        summary["error"] = f"{type(exc).__name__}: {exc}"
        _write_summary(evidence_dir, summary)
        _print_summary(summary, as_json=args.json)
        return 1

    _write_summary(evidence_dir, summary)
    _print_summary(summary, as_json=args.json)
    return 0


def _run_smoke(workspace: Path) -> list[dict[str, Any]]:
    db_path = workspace / ".glassbox" / "background-autonomy-smoke.sqlite3"
    with open_runtime_context(workspace, db_path=db_path) as runtime_context:
        repository = runtime_context.repositories.sessions
        scenarios = [
            _smoke_read_only_completion(runtime_context),
            _smoke_cancellation(runtime_context),
            _smoke_failure_retry_and_abandon(runtime_context, workspace),
            _smoke_stale_claim_recovery(runtime_context),
            asyncio.run(_smoke_task_continuation_pause(runtime_context)),
        ]
        jobs = repository.list_background_jobs(limit=100)
    return [
        *scenarios,
        {
            "name": "retained_projection_snapshot",
            "status": "passed",
            "job_count": len(jobs),
            "states": [job.state.value for job in jobs],
        },
    ]


def _smoke_read_only_completion(runtime_context) -> dict[str, Any]:
    repository = runtime_context.repositories.sessions
    session_id = _start_session(runtime_context, "read-only completion")
    job = repository.enqueue_background_job(
        session_id,
        kind=BackgroundJobKind.READ_ONLY_MAINTENANCE,
        job_type="projection-health-refresh",
        title="Smoke projection health refresh",
    )
    tick = run_background_job_worker_once(runtime_context, worker_id="smoke-read-only")
    updated = repository.get_background_job(job.job_id)
    if updated is None:
        raise RuntimeError("read-only job disappeared")
    _expect(
        updated.state == BackgroundJobState.COMPLETED, "read-only job did not complete"
    )
    return {
        "name": "read_only_completion",
        "status": "passed",
        "job_id": str(job.job_id),
        "claimed_count": tick.claimed_count,
        "completed_count": tick.completed_count,
    }


def _smoke_cancellation(runtime_context) -> dict[str, Any]:
    repository = runtime_context.repositories.sessions
    session_id = _start_session(runtime_context, "cancellation")
    job = repository.enqueue_background_job(
        session_id,
        kind=BackgroundJobKind.READ_ONLY_MAINTENANCE,
        job_type="artifact-pressure-scan",
        title="Smoke cancellable artifact scan",
    )
    repository.cancel_background_job(job.job_id, reason="release smoke cancellation")
    tick = run_background_job_worker_once(runtime_context, worker_id="smoke-cancel")
    updated = repository.get_background_job(job.job_id)
    if updated is None:
        raise RuntimeError("cancelled job disappeared")
    _expect(updated.state == BackgroundJobState.CANCELLED, "job was not cancelled")
    return {
        "name": "cancellation_acknowledgement",
        "status": "passed",
        "job_id": str(job.job_id),
        "cancelled_count": tick.cancelled_count,
    }


def _smoke_failure_retry_and_abandon(
    runtime_context,
    workspace: Path,
) -> dict[str, Any]:
    repository = runtime_context.repositories.sessions
    session_id = _start_session(runtime_context, "failure retry abandon")
    job = repository.enqueue_background_job(
        session_id,
        kind=BackgroundJobKind.READ_ONLY_MAINTENANCE,
        job_type="unsupported-smoke-job",
        title="Smoke unsupported job failure",
    )
    tick = run_background_job_worker_once(runtime_context, worker_id="smoke-failure")
    failed = repository.get_background_job(job.job_id)
    if failed is None:
        raise RuntimeError("failed job disappeared")
    _expect(failed.state == BackgroundJobState.FAILED, "job did not fail")
    _expect(
        failed.failure_kind == BackgroundJobFailureKind.TOOL_ERROR, "wrong failure kind"
    )
    _expect(failed.retryable, "read-only failure was not retryable")
    failure_artifact_path = failed.failure_artifact_path
    if failure_artifact_path is None:
        raise RuntimeError("failure artifact was missing")
    _expect(
        (workspace / failure_artifact_path).is_file(),
        "failure artifact missing on disk",
    )

    retried = repository.retry_background_job(
        job.job_id,
        requested_by="release-smoke",
        reason="verify retry event-safe boundary",
    )
    _expect(retried.state == BackgroundJobState.QUEUED, "retry did not requeue job")
    abandoned = repository.abandon_background_job(
        job.job_id,
        abandoned_by="release-smoke",
        reason="release smoke completed retry evidence",
    )
    _expect(
        abandoned.state == BackgroundJobState.ABANDONED, "abandon did not terminate job"
    )
    return {
        "name": "failure_retry_and_abandon",
        "status": "passed",
        "job_id": str(job.job_id),
        "failed_count": tick.failed_count,
        "failure_artifact_path": failure_artifact_path,
    }


def _smoke_stale_claim_recovery(runtime_context) -> dict[str, Any]:
    repository = runtime_context.repositories.sessions
    session_id = _start_session(runtime_context, "stale claim")
    now = datetime(2026, 4, 29, 12, tzinfo=UTC)
    job = repository.enqueue_background_job(
        session_id,
        kind=BackgroundJobKind.READ_ONLY_MAINTENANCE,
        job_type="provider-evidence-freshness-scan",
        title="Smoke stale provider evidence scan",
    )
    repository.claim_background_job(
        job.job_id,
        worker_id="smoke-old-worker",
        claim_token="expired-claim",
        lease_expires_at=now - timedelta(seconds=1),
        now=now,
    )
    tick = run_background_job_worker_once(
        runtime_context,
        worker_id="smoke-recovery",
        now=now,
    )
    updated = repository.get_background_job(job.job_id)
    if updated is None:
        raise RuntimeError("stale job disappeared")
    _expect(updated.state == BackgroundJobState.STALE, "stale claim was not recorded")
    return {
        "name": "stale_owner_cleanup",
        "status": "passed",
        "job_id": str(job.job_id),
        "recovered_stale_count": tick.recovered_stale_count,
    }


async def _smoke_task_continuation_pause(runtime_context) -> dict[str, Any]:
    repository = runtime_context.repositories.sessions
    session_id = _start_session(runtime_context, "task continuation")
    task_id = new_task_id()
    step_id = new_task_step_id()
    repository.append_events(
        [
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=TaskCreated(
                    task_id=task_id,
                    title="Smoke continuation task",
                    goal="Pause at the explicit budget boundary",
                ),
            ),
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=TaskPlanProposed(
                    task_id=task_id,
                    plan=TaskPlanSnapshot(
                        task_id=task_id,
                        title="Smoke continuation task",
                        goal="Pause at the explicit budget boundary",
                        steps=[
                            TaskStepProposal(
                                step_id=step_id,
                                title="Attempt one background step",
                                order=0,
                            )
                        ],
                    ),
                ),
            ),
        ]
    )
    job = repository.enqueue_background_job(
        session_id,
        kind=BackgroundJobKind.MUTATING_CONTINUATION,
        job_type="task-continuation-step",
        title="Smoke task continuation",
        task_id=task_id,
    )
    tick = await run_background_job_worker_once_async(
        runtime_context,
        worker_id="smoke-continuation",
    )
    updated = repository.get_background_job(job.job_id)
    task_repository = cast(TaskPlanRepository, repository)
    task = task_repository.get_task(task_id)
    if updated is None:
        raise RuntimeError("continuation job disappeared")
    _expect(
        updated.state == BackgroundJobState.COMPLETED, "continuation job did not finish"
    )
    if task is None:
        raise RuntimeError("task projection missing")
    _expect(task.status.value == "paused", "task did not pause at budget boundary")
    return {
        "name": "task_continuation_budget_pause",
        "status": "passed",
        "job_id": str(job.job_id),
        "claimed_count": tick.claimed_count,
        "completed_count": tick.completed_count,
        "task_id": str(task_id),
    }


def _start_session(runtime_context, label: str):
    session_id = new_session_id()
    runtime_context.repositories.sessions.append_event(
        EventEnvelope(
            session_id=session_id,
            sequence=0,
            payload=SessionStarted(
                cwd=str(runtime_context.infrastructure.artifacts_root),
                model_name="smoke:model",
                approval_mode="confirm",
                autonomy_mode=AutonomyMode.MANUAL,
                branch_label=label,
            ),
        )
    )
    return session_id


def _planned_scenarios() -> list[dict[str, str]]:
    return [
        {"name": "read_only_completion", "status": "planned"},
        {"name": "cancellation_acknowledgement", "status": "planned"},
        {"name": "failure_retry_and_abandon", "status": "planned"},
        {"name": "stale_owner_cleanup", "status": "planned"},
        {"name": "task_continuation_budget_pause", "status": "planned"},
    ]


def _new_summary(
    evidence_dir: Path, workspace: Path, *, dry_run: bool
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": "running",
        "created_at": _now_iso(),
        "evidence_dir": str(evidence_dir),
        "workspace_root": str(workspace),
        "dry_run": dry_run,
        "release_gate_recommendation": {
            "stage": "v8 background job smoke",
            "command": "uv run python scripts/background_autonomy_smoke.py",
            "blocking": True,
            "provider_credentials_required": False,
        },
        "scenarios": [],
    }


def _resolve_evidence_dir(path: Path | None) -> Path:
    if path is not None:
        evidence_dir = path
    else:
        evidence_dir = DEFAULT_EVIDENCE_ROOT / _timestamp() / "background-jobs"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    return evidence_dir.resolve()


def _write_summary(evidence_dir: Path, summary: dict[str, Any]) -> None:
    summary["completed_at"] = _now_iso()
    (evidence_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _print_summary(summary: dict[str, Any], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(summary, indent=2, sort_keys=True))
        return
    print(f"Background autonomy smoke: {summary['status']}")
    print(f"Evidence: {summary['evidence_dir']}")
    for scenario in summary["scenarios"]:
        print(f"- {scenario['name']}: {scenario['status']}")


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
