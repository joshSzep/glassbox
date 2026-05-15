"""HTTP integration tests for changeset dashboard APIs."""

import asyncio
import sqlite3
import subprocess
from pathlib import Path

import httpx

from glassbox.core import CommandEnvironmentSummary
from glassbox.core import CommandPurpose
from glassbox.core import CommandReviewRelevance
from glassbox.core import CommandToolchainVersion
from glassbox.core import EventEnvelope
from glassbox.core import SessionStarted
from glassbox.core import TaskCreated
from glassbox.core import TaskPlanStatus
from glassbox.core import TaskStatusChanged
from glassbox.core import TaskVerificationCompleted
from glassbox.core import TaskVerificationPlanned
from glassbox.core import TaskVerificationStatus
from glassbox.core import ToolAttemptHeartbeat
from glassbox.core import ToolAttemptStatus
from glassbox.core import VerificationCheckKind
from glassbox.core import VerificationPlanEntry
from glassbox.core import VerificationPlanSource
from glassbox.core import new_artifact_id
from glassbox.core import new_session_id
from glassbox.core import new_task_id
from glassbox.core import new_task_verification_id
from glassbox.core import new_tool_attempt_id
from glassbox.core import new_turn_id
from glassbox.runtime.bootstrap import _build_runtime_context  # noqa: PLC2701
from glassbox.store import SQLiteSessionRepository
from glassbox.store.sqlite import initialize_database
from glassbox.store.sqlite import open_database
from glassbox.web import create_app


def test_changeset_routes_create_list_show_refresh_and_archive(tmp_path: Path) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            _init_git_repo(tmp_path)
            app = _make_app(tmp_path, connection)
            session_id = new_session_id()
            task_id = new_task_id()
            repository = SQLiteSessionRepository(connection)
            repository.append_events(
                [
                    EventEnvelope(
                        session_id=session_id,
                        sequence=0,
                        payload=SessionStarted(
                            cwd=str(tmp_path),
                            model_name="openai:gpt-5.4",
                            approval_mode="confirm",
                        ),
                    ),
                    EventEnvelope(
                        session_id=session_id,
                        sequence=0,
                        payload=TaskCreated(
                            task_id=task_id,
                            title="API changeset task",
                            goal="Review API changeset verification",
                        ),
                    ),
                    EventEnvelope(
                        session_id=session_id,
                        sequence=0,
                        payload=TaskStatusChanged(
                            task_id=task_id,
                            status=TaskPlanStatus.COMPLETED,
                        ),
                    ),
                ]
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                create_response = await client.post(
                    "/changesets",
                    json={
                        "source_kind": "task",
                        "task_id": str(task_id),
                        "objective": "Review session evidence",
                    },
                )
                changeset_id = create_response.json()["changeset_id"]
                feedback_add_response = await client.post(
                    f"/changesets/{changeset_id}/feedback",
                    json={
                        "feedback_kind": "reviewer_question",
                        "summary": "Does the API expose feedback scopes?",
                        "provenance": "reviewer",
                        "reviewer_label": "reviewer-api",
                        "file_path": "app.py",
                        "line_start": 1,
                    },
                )
                feedback_id = feedback_add_response.json()["feedback"]["feedback_id"]
                manual_evidence_response = await client.post(
                    f"/changesets/{changeset_id}/manual-evidence",
                    json={
                        "evidence_kind": "external_check",
                        "summary": "external CI reported green",
                        "source_label": "external-ci",
                        "feedback_id": feedback_id,
                        "freshness": "current",
                    },
                )
                browser_evidence_response = await client.post(
                    f"/changesets/{changeset_id}/browser-evidence",
                    json={
                        "capture_kind": "dashboard_walkthrough",
                        "summary": "dashboard showed feedback and manual evidence",
                        "source_label": "dashboard-local",
                        "route_label": "/console/changesets",
                        "environment": "local-dev",
                        "browser": "chromium",
                        "viewport_width": 1440,
                        "viewport_height": 900,
                        "observed_at": "2026-05-01T12:30:00",
                        "input_method": "keyboard",
                        "console_checked": True,
                        "screenshot_path_hint": (
                            ".glassbox/evidence/changeset/dashboard.png"
                        ),
                        "screenshot_width": 1440,
                        "screenshot_height": 900,
                        "skipped_cases": ["mobile viewport"],
                        "limitations": ["local dashboard fixture only"],
                        "feedback_id": feedback_id,
                        "freshness": "needs_inspection",
                    },
                )
                accessibility_evidence_response = await client.post(
                    f"/changesets/{changeset_id}/accessibility-evidence",
                    json={
                        "observation_kind": "focus_order_issue",
                        "summary": "focus leaves the feedback dialog",
                        "source_label": "keyboard-review",
                        "environment": "local-dev",
                        "observed_issue": "Tab moved focus behind the dialog.",
                        "tool": "manual keyboard",
                        "route_label": "/console/changesets",
                        "reviewer_label": "reviewer-a",
                        "severity": "high",
                        "disposition": "paired_with_feedback",
                        "follow_up": "Keep feedback open until focus is fixed.",
                        "paired_tool_output_label": "playwright keyboard smoke",
                        "skipped_cases": ["screen reader pairing"],
                        "feedback_id": feedback_id,
                        "freshness": "needs_inspection",
                    },
                )
                manual_evidence_list_response = await client.get(
                    "/changesets/manual-evidence",
                    params={
                        "changeset_id": changeset_id,
                        "include_rejected": True,
                    },
                )
                feedback_list_response = await client.get(
                    "/changesets/feedback",
                    params={"changeset_id": changeset_id},
                )
                feedback_detail_response = await client.get(
                    f"/changesets/feedback/{feedback_id}"
                )
                feedback_resolve_response = await client.post(
                    f"/changesets/feedback/{feedback_id}/resolve",
                    json={
                        "summary": "API exposes feedback detail and scopes.",
                        "residual_risk": "Reviewer approval is not implied.",
                    },
                )
                feedback_reopen_response = await client.post(
                    f"/changesets/feedback/{feedback_id}/reopen",
                    json={"reason": "Need dashboard read copy."},
                )
                feedback_accept_response = await client.post(
                    f"/changesets/feedback/{feedback_id}/accept-risk",
                    json={
                        "risk_summary": "Dashboard mutation waits for later UX work.",
                        "reason": "Read surfaces are sufficient for this slice.",
                    },
                )
                list_response = await client.get("/changesets")
                detail_response = await client.get(f"/changesets/{changeset_id}")
                (tmp_path / "app.py").write_text(
                    "print('changed')\n",
                    encoding="utf-8",
                )
                refresh_response = await client.post(
                    f"/changesets/{changeset_id}/refresh",
                    json={"actor": "qa"},
                )
                feedback_fixup_response = await client.post(
                    f"/changesets/feedback/{feedback_id}/fixup",
                    json={
                        "from_workspace": False,
                        "paths": ["app.py"],
                        "source_summary": "API recorded response-linked path inventory",
                        "actor": "qa",
                    },
                )
                plan_response = await client.get(
                    f"/changesets/{changeset_id}/verification-plan"
                )
                verification_command = plan_response.json()["recommended_commands"][0]
                verification_id = new_task_verification_id()
                artifact_id = new_artifact_id()
                repository.append_events(
                    _verification_events(
                        session_id,
                        task_id,
                        verification_id,
                        command=verification_command.split(),
                        artifact_id=artifact_id,
                    )
                )
                tool_attempt_id = new_tool_attempt_id()
                repository.append_events(
                    [
                        EventEnvelope(
                            session_id=session_id,
                            sequence=0,
                            payload=ToolAttemptHeartbeat(
                                tool_attempt_id=tool_attempt_id,
                                status=ToolAttemptStatus.FAILED,
                                turn_id=new_turn_id(),
                                tool_name="run_command",
                                task_id=task_id,
                                message="pytest failed before the selected rerun",
                                output_artifact_id=artifact_id,
                                command_purpose=CommandPurpose.TEST,
                                command_review_relevance=(
                                    CommandReviewRelevance.VERIFICATION
                                ),
                                command_supports_verification=True,
                                command_purpose_reason=(
                                    "test command can support verification evidence"
                                ),
                                command_environment=CommandEnvironmentSummary(
                                    capture_scope="verification_or_local_artifact",
                                    command_purpose=CommandPurpose.TEST,
                                    platform="Darwin",
                                    python_version="3.13.0",
                                    toolchains=[
                                        CommandToolchainVersion(
                                            name="pytest",
                                            version="8.0",
                                            available=True,
                                            source="executable",
                                        )
                                    ],
                                    redaction_notes=["raw environment is not stored"],
                                ),
                            ),
                        )
                    ]
                )
                record_response = await client.post(
                    f"/changesets/{changeset_id}/record-verification",
                    json={"verification_id": str(verification_id)},
                )
                brief_response = await client.post(
                    f"/changesets/{changeset_id}/brief",
                    json={"actor": "qa", "include_markdown": True},
                )
                commit_message_response = await client.get(
                    f"/changesets/{changeset_id}/commit-message"
                )
                commit_readiness_response = await client.get(
                    f"/changesets/{changeset_id}/commit-readiness"
                )
                handoff_readiness_response = await client.get(
                    f"/changesets/{changeset_id}/handoff-readiness"
                )
                graph_response = await client.get(
                    f"/changesets/{changeset_id}/evidence-graph"
                )
                graph_summary_response = await client.get(
                    f"/changesets/{changeset_id}/evidence-graph/summary"
                )
                claim_id = f"claim:changeset:{changeset_id}:review-posture"
                claim_response = await client.get(
                    f"/changesets/{changeset_id}/evidence-graph/claims/{claim_id}"
                )
                feedback_node_id = f"review-feedback:{feedback_id}"
                node_response = await client.get(
                    f"/changesets/{changeset_id}/evidence-graph/nodes/"
                    f"{feedback_node_id}"
                )
                neighborhood_response = await client.get(
                    f"/changesets/{changeset_id}/evidence-graph/neighborhood",
                    params={"node_id": claim_id, "depth": 1},
                )
                reviewer_safe_graph_response = await client.get(
                    f"/changesets/{changeset_id}/evidence-graph",
                    params={"reviewer_safe": True},
                )
                (tmp_path / "app.py").write_text(
                    "print('changed again')\n",
                    encoding="utf-8",
                )
                stale_response = await client.get(f"/changesets/{changeset_id}")
                feedback_archive_response = await client.post(
                    f"/changesets/feedback/{feedback_id}/archive",
                    json={"actor": "qa", "reason": "superseded local record"},
                )
                archive_response = await client.post(
                    f"/changesets/{changeset_id}/archive",
                    json={"actor": "qa", "reason": "superseded"},
                )

            assert create_response.status_code == 200
            assert create_response.json()["session_id"] == str(session_id)
            assert feedback_add_response.status_code == 200
            assert feedback_add_response.json()["feedback"]["summary"] == (
                "Does the API expose feedback scopes?"
            )
            assert feedback_add_response.json()["scopes"][0]["file_path"] == "app.py"
            assert "not approval" in " ".join(
                feedback_add_response.json()["non_claims"]
            )
            assert manual_evidence_response.status_code == 200
            assert (
                manual_evidence_response.json()["evidence"]["summary"]
                == "external CI reported green"
            )
            assert (
                manual_evidence_response.json()["evidence"]["target_kind"] == "feedback"
            )
            assert "not retained command evidence" in " ".join(
                manual_evidence_response.json()["non_claims"]
            )
            assert browser_evidence_response.status_code == 200
            assert (
                browser_evidence_response.json()["evidence"]["evidence_kind"]
                == "browser_observation"
            )
            assert (
                browser_evidence_response.json()["evidence"]["target_kind"]
                == "feedback"
            )
            assert (
                "not deterministic release authority"
                in browser_evidence_response.json()["evidence"]["non_claims"]
            )
            assert accessibility_evidence_response.status_code == 200
            assert (
                accessibility_evidence_response.json()["evidence"]["evidence_kind"]
                == "accessibility_note"
            )
            assert (
                "severity: high"
                in accessibility_evidence_response.json()["evidence"]["limitations"]
            )
            assert (
                "not accessibility certification"
                in accessibility_evidence_response.json()["evidence"]["non_claims"]
            )
            assert manual_evidence_list_response.status_code == 200
            assert {
                item["evidence_kind"]
                for item in manual_evidence_list_response.json()["items"]
            } == {"accessibility_note", "browser_observation", "external_check"}
            assert feedback_list_response.status_code == 200
            assert (
                feedback_list_response.json()["items"][0]["feedback_id"] == feedback_id
            )
            assert (
                feedback_list_response.json()["response_summary"][
                    "total_feedback_count"
                ]
                == 1
            )
            assert (
                feedback_list_response.json()["response_summary"]["items"][0][
                    "response_state"
                ]
                == "planned"
            )
            assert feedback_detail_response.status_code == 200
            assert feedback_detail_response.json()["scopes"][0]["scope_kind"] == "file"
            assert (
                feedback_detail_response.json()["response_status"]["response_state"]
                == "planned"
            )
            assert feedback_resolve_response.status_code == 200
            assert (
                feedback_resolve_response.json()["feedback"]["disposition"]
                == "resolved_locally"
            )
            assert (
                feedback_resolve_response.json()["feedback"]["residual_risk"]
                == "Reviewer approval is not implied."
            )
            assert feedback_reopen_response.status_code == 200
            assert feedback_reopen_response.json()["feedback"]["disposition"] == "open"
            assert feedback_reopen_response.json()["feedback"]["reopened_count"] == 1
            assert feedback_accept_response.status_code == 200
            assert (
                feedback_accept_response.json()["feedback"]["disposition"]
                == "accepted_with_risk"
            )
            assert list_response.status_code == 200
            assert list_response.json()["items"][0]["changeset_id"] == changeset_id
            assert detail_response.status_code == 200
            assert detail_response.json()["sources"][0]["source_kind"] == "task"
            assert (
                detail_response.json()["review_feedback"][0]["feedback_id"]
                == feedback_id
            )
            assert {
                item["evidence_kind"]
                for item in detail_response.json()["manual_evidence"]
            } == {"accessibility_note", "browser_observation", "external_check"}
            assert (
                detail_response.json()["review_response_summary"]["accepted_risk_count"]
                == 1
            )
            assert (
                "glassbox changeset show"
                in detail_response.json()["safe_next_actions"][0]
            )
            assert refresh_response.status_code == 200
            assert refresh_response.json()["status"] == "refreshed"
            assert (
                refresh_response.json()["detail"]["inventory"]["freshness"] == "fresh"
            )
            assert feedback_fixup_response.status_code == 200
            assert feedback_fixup_response.json()["feedback_id"] == feedback_id
            assert feedback_fixup_response.json()["changed_path_count"] == 1
            assert (
                feedback_fixup_response.json()["response_status"][
                    "fixup_inventory_count"
                ]
                == 1
            )
            assert "not reviewer acceptance" in " ".join(
                feedback_fixup_response.json()["non_claims"]
            )
            assert plan_response.status_code == 200
            assert plan_response.json()["expected_scope"] == ["app.py"]
            assert plan_response.json()["plan_summary"]["total_count"] >= 1
            assert plan_response.json()["plan_summary"]["proposed_count"] >= 1
            assert plan_response.json()["review_loop_summary"]["feedback_count"] == 1
            assert (
                plan_response.json()["review_loop_summary"]["manual_evidence_count"]
                == 3
            )
            assert (
                plan_response.json()["review_loop_summary"]["browser_evidence_count"]
                == 1
            )
            assert (
                plan_response.json()["review_loop_summary"][
                    "skipped_live_evidence_count"
                ]
                == 0
            )
            assert record_response.status_code == 200
            assert record_response.json()["readiness"]["state"] == "passed"
            assert record_response.json()["retained_artifact_ids"] == [str(artifact_id)]
            assert brief_response.status_code == 200
            assert (
                brief_response.json()["brief"]["artifact_kind"]
                == "changeset_review_brief"
            )
            assert "limitation_summary" in brief_response.json()
            assert brief_response.json()["markdown"].startswith("# Review Brief:")
            assert (
                brief_response.json()["detail"]["command_evidence"]["failed_count"] == 1
            )
            assert (
                brief_response.json()["detail"]["verification_plan_summary"][
                    "passed_count"
                ]
                == 1
            )
            assert brief_response.json()["detail"]["command_evidence"]["items"][0][
                "tool_attempt_id"
            ] == str(tool_attempt_id)
            assert "Command Evidence" in brief_response.json()["markdown"]
            assert (
                brief_response.json()["detail"]["changeset"][
                    "latest_review_brief_artifact_id"
                ]
                == brief_response.json()["artifact_id"]
            )
            assert (
                brief_response.json()["detail"]["readiness"][0]["readiness_kind"]
                == "review"
            )
            assert brief_response.json()["detail"]["readiness"][0]["state"] == "ready"
            assert commit_message_response.status_code == 200
            assert (
                commit_message_response.json()["suggestion_label"]
                == "suggestion_only_not_committed"
            )
            assert (
                commit_message_response.json()["subject"] == "Review session evidence"
            )
            assert "Commit readiness:" in commit_message_response.json()["message"]
            assert commit_readiness_response.status_code == 200
            assert commit_readiness_response.json()["readiness_kind"] == "commit"
            assert commit_readiness_response.json()["review_feedback_count"] == 1
            assert commit_readiness_response.json()["manual_evidence_count"] == 3
            assert commit_readiness_response.json()["local_only_evidence_count"] == 3
            assert commit_readiness_response.json()["accepted_risk_count"] >= 1
            assert "does not stage" in " ".join(
                commit_readiness_response.json()["non_claims"]
            )
            assert handoff_readiness_response.status_code == 200
            assert handoff_readiness_response.json()["readiness_kind"] == "handoff"
            assert handoff_readiness_response.json()["state"] == "unresolved_risk"
            assert (
                handoff_readiness_response.json()["shared_readiness"]["source"]["kind"]
                == "changeset"
            )
            assert (
                handoff_readiness_response.json()["evidence"]["manual_evidence_count"]
                == 3
            )
            assert (
                handoff_readiness_response.json()["verification_plan_summary"][
                    "passed_count"
                ]
                == 1
            )
            assert "not publication" in " ".join(
                handoff_readiness_response.json()["non_claims"]
            )
            assert graph_response.status_code == 200
            graph = graph_response.json()
            assert graph["target"]["kind"] == "changeset"
            assert graph["target"]["target_id"] == changeset_id
            assert graph["claims"][0]["claim_id"] == claim_id
            assert graph["claims"][0]["state"] == "accepted_with_risk"
            assert any(
                node["node_id"] == feedback_node_id
                and node["kind"] == "review_feedback"
                for node in graph["nodes"]
            )
            assert graph_summary_response.status_code == 200
            assert graph_summary_response.json()["claim_count"] == 1
            assert graph_summary_response.json()["accepted_risk_claim_count"] == 1
            assert claim_response.status_code == 200
            assert claim_response.json()["claim_id"] == claim_id
            assert claim_response.json()["state"] == "accepted_with_risk"
            assert node_response.status_code == 200
            assert node_response.json()["node_id"] == feedback_node_id
            assert neighborhood_response.status_code == 200
            neighborhood_node_ids = {
                node["node_id"] for node in neighborhood_response.json()["nodes"]
            }
            assert claim_id in neighborhood_node_ids
            assert feedback_node_id in neighborhood_node_ids
            assert reviewer_safe_graph_response.status_code == 200
            assert all(
                node["visibility"] == "reviewer_safe"
                for node in reviewer_safe_graph_response.json()["nodes"]
            )
            assert stale_response.status_code == 200
            assert stale_response.json()["inventory_status"]["stale"] is True
            assert stale_response.json()["inventory"]["freshness"] == "stale"
            assert stale_response.json()["verification_posture"]["state"] == "passed"
            assert feedback_archive_response.status_code == 200
            assert (
                feedback_archive_response.json()["feedback"]["disposition"]
                == "archived"
            )
            assert archive_response.status_code == 200
            assert (
                archive_response.json()["detail"]["changeset"]["status"] == "archived"
            )
        finally:
            connection.close()

    asyncio.run(scenario())


def test_changeset_routes_record_skipped_live_evidence_without_placeholders(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        connection = _open_initialized_db(tmp_path)
        try:
            _init_git_repo(tmp_path)
            app = _make_app(tmp_path, connection)
            session_id = new_session_id()
            task_id = new_task_id()
            repository = SQLiteSessionRepository(connection)
            repository.append_events(
                [
                    EventEnvelope(
                        session_id=session_id,
                        sequence=0,
                        payload=SessionStarted(
                            cwd=str(tmp_path),
                            model_name="openai:gpt-5.4",
                            approval_mode="confirm",
                        ),
                    ),
                    EventEnvelope(
                        session_id=session_id,
                        sequence=0,
                        payload=TaskCreated(
                            task_id=task_id,
                            title="API skipped evidence task",
                            goal="Record skipped advisory evidence",
                        ),
                    ),
                    EventEnvelope(
                        session_id=session_id,
                        sequence=0,
                        payload=TaskStatusChanged(
                            task_id=task_id,
                            status=TaskPlanStatus.COMPLETED,
                        ),
                    ),
                ]
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                create_response = await client.post(
                    "/changesets",
                    json={
                        "source_kind": "task",
                        "task_id": str(task_id),
                        "objective": "Skipped evidence API support",
                    },
                )
                changeset_id = create_response.json()["changeset_id"]
                skipped_browser_response = await client.post(
                    f"/changesets/{changeset_id}/browser-evidence",
                    json={
                        "capture_state": "not_run",
                        "capture_kind": "dashboard_walkthrough",
                        "summary": "dashboard walkthrough intentionally skipped",
                        "source_label": "dashboard-local",
                        "skip_reason": "local dashboard server was not started",
                        "skipped_cases": ["unknown viewport"],
                        "freshness": "needs_inspection",
                    },
                )
                contradictory_browser_response = await client.post(
                    f"/changesets/{changeset_id}/browser-evidence",
                    json={
                        "capture_state": "not_run",
                        "capture_kind": "browser_check",
                        "summary": "contradictory skipped browser evidence",
                        "source_label": "local-browser",
                        "skip_reason": "browser was not opened",
                        "console_checked": True,
                    },
                )
                skipped_accessibility_response = await client.post(
                    f"/changesets/{changeset_id}/accessibility-evidence",
                    json={
                        "capture_state": "not_applicable",
                        "observation_kind": "screen_reader_note",
                        "summary": (
                            "screen reader pass not applicable to backend-only change"
                        ),
                        "source_label": "accessibility-review",
                        "skip_reason": "no user-facing route changed",
                        "skipped_cases": ["screen reader pass"],
                    },
                )
                contradictory_accessibility_response = await client.post(
                    f"/changesets/{changeset_id}/accessibility-evidence",
                    json={
                        "capture_state": "not_applicable",
                        "observation_kind": "keyboard_pass",
                        "summary": "contradictory skipped accessibility evidence",
                        "source_label": "keyboard-review",
                        "skip_reason": "keyboard pass was not run",
                        "observed_issue": "Tab order looked correct.",
                    },
                )
                evidence_list_response = await client.get(
                    "/changesets/manual-evidence",
                    params={"changeset_id": changeset_id},
                )
                plan_response = await client.get(
                    f"/changesets/{changeset_id}/verification-plan"
                )
                handoff_response = await client.get(
                    f"/changesets/{changeset_id}/handoff-readiness"
                )

            assert create_response.status_code == 200
            assert skipped_browser_response.status_code == 200
            browser_payload = skipped_browser_response.json()
            assert (
                "capture state: not_run" in browser_payload["evidence"]["limitations"]
            )
            assert (
                "skipped browser/dashboard evidence is not a pass"
                in browser_payload["evidence"]["non_claims"]
            )
            assert contradictory_browser_response.status_code == 422
            assert (
                "cannot claim console was checked"
                in (contradictory_browser_response.json()["detail"])
            )
            assert skipped_accessibility_response.status_code == 200
            accessibility_payload = skipped_accessibility_response.json()
            assert (
                "capture state: not_applicable"
                in accessibility_payload["evidence"]["limitations"]
            )
            assert (
                "skipped accessibility evidence is not a pass"
                in accessibility_payload["evidence"]["non_claims"]
            )
            assert contradictory_accessibility_response.status_code == 422
            assert (
                "cannot include an observed issue"
                in (contradictory_accessibility_response.json()["detail"])
            )
            assert evidence_list_response.status_code == 200
            assert [
                item["evidence_kind"] for item in evidence_list_response.json()["items"]
            ] == ["accessibility_note", "browser_observation"]
            assert plan_response.status_code == 200
            assert (
                plan_response.json()["review_loop_summary"][
                    "skipped_live_evidence_count"
                ]
                == 2
            )
            assert (
                plan_response.json()["review_loop_summary"][
                    "skipped_browser_evidence_count"
                ]
                == 1
            )
            assert (
                plan_response.json()["review_loop_summary"][
                    "skipped_accessibility_evidence_count"
                ]
                == 1
            )
            assert handoff_response.status_code == 200
            assert (
                handoff_response.json()["evidence"]["skipped_live_evidence_count"] == 2
            )
            assert any(
                signal["signal_id"] == "skipped-live-evidence"
                for signal in handoff_response.json()["signals"]
            )
        finally:
            connection.close()

    asyncio.run(scenario())


def _init_git_repo(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    (tmp_path / "app.py").write_text("print('base')\n", encoding="utf-8")
    subprocess.run(["git", "add", "app.py"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )


def _open_initialized_db(tmp_path: Path) -> sqlite3.Connection:
    connection = open_database(tmp_path / ".glassbox" / "glassbox.sqlite3")
    initialize_database(connection)
    return connection


def _make_app(tmp_path: Path, connection: sqlite3.Connection):
    runtime_context = _build_runtime_context(connection, tmp_path)
    return create_app(runtime_context)


def _verification_events(
    session_id,
    task_id,
    verification_id,
    *,
    command: list[str],
    artifact_id,
) -> list[EventEnvelope]:
    return [
        EventEnvelope(
            session_id=session_id,
            sequence=0,
            payload=TaskVerificationPlanned(
                task_id=task_id,
                verification=VerificationPlanEntry(
                    verification_id=verification_id,
                    check_name="changeset api verification",
                    kind=VerificationCheckKind.COMMAND,
                    command=command,
                    source=VerificationPlanSource.EVAL_RECOMMENDATION,
                    rationale="operator selected API plan command",
                    changed_paths=[Path("app.py")],
                ),
            ),
        ),
        EventEnvelope(
            session_id=session_id,
            sequence=0,
            payload=TaskVerificationCompleted(
                task_id=task_id,
                verification_id=verification_id,
                status=TaskVerificationStatus.PASSED,
                summary="selected verification passed",
                artifact_id=artifact_id,
            ),
        ),
    ]
