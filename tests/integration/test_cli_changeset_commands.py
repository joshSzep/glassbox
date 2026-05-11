"""CLI coverage for changeset inspection commands."""

import json
import subprocess
from pathlib import Path

from glassbox.cli import main
from glassbox.core import EventEnvelope
from glassbox.core import SessionStarted
from glassbox.core import TaskCreated
from glassbox.core import TaskPlanStatus
from glassbox.core import TaskStatusChanged
from glassbox.core import TaskVerificationCompleted
from glassbox.core import TaskVerificationPlanned
from glassbox.core import TaskVerificationStatus
from glassbox.core import VerificationCheckKind
from glassbox.core import VerificationPlanEntry
from glassbox.core import VerificationPlanSource
from glassbox.core import new_artifact_id
from glassbox.core import new_session_id
from glassbox.core import new_task_id
from glassbox.core import new_task_verification_id
from glassbox.store import SQLiteSessionRepository
from glassbox.store import initialize_database
from glassbox.store import open_database


def test_changeset_create_list_show_refresh_and_archive(
    tmp_path: Path,
    capsys,
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    session_id = new_session_id()
    task_id = new_task_id()
    _init_git_repo(tmp_path)
    _seed_task(db_path, tmp_path, session_id, task_id)

    create_exit = main(
        [
            "changeset",
            "create",
            "--from",
            "task",
            "--task",
            str(task_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    created = json.loads(capsys.readouterr().out)
    changeset_id = created["changeset_id"]
    feedback_add_exit = main(
        [
            "changeset",
            "feedback",
            "add",
            changeset_id,
            "--kind",
            "requested_change",
            "--summary",
            "Clarify the review-feedback list output",
            "--body",
            "Keep the feedback entry local and bounded.",
            "--provenance",
            "reviewer",
            "--reviewer-label",
            "reviewer-1",
            "--file",
            "app.py",
            "--line-start",
            "1",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    feedback_added = json.loads(capsys.readouterr().out)
    feedback_id = feedback_added["feedback"]["feedback_id"]
    evidence_attach_exit = main(
        [
            "changeset",
            "evidence",
            "attach",
            changeset_id,
            "--kind",
            "external_check",
            "--summary",
            "external CI reported green",
            "--source-label",
            "external-ci",
            "--feedback",
            feedback_id,
            "--freshness",
            "current",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    evidence_attached = json.loads(capsys.readouterr().out)
    evidence_browser_exit = main(
        [
            "changeset",
            "evidence",
            "browser",
            changeset_id,
            "--summary",
            "dashboard rendered feedback with manual evidence",
            "--source-label",
            "dashboard-local",
            "--route",
            "/console/changesets",
            "--environment",
            "local-dev",
            "--browser",
            "chromium",
            "--viewport",
            "1440x900",
            "--observed-at",
            "2026-05-01T12:30:00",
            "--input-method",
            "keyboard",
            "--console-checked",
            "--screenshot-file",
            ".glassbox/evidence/changeset/dashboard.png",
            "--screenshot-width",
            "1440",
            "--screenshot-height",
            "900",
            "--skipped-case",
            "mobile viewport",
            "--limitation",
            "local dashboard fixture only",
            "--feedback",
            feedback_id,
            "--freshness",
            "needs_inspection",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    evidence_browser = json.loads(capsys.readouterr().out)
    evidence_accessibility_exit = main(
        [
            "changeset",
            "evidence",
            "accessibility",
            changeset_id,
            "--kind",
            "focus_order_issue",
            "--summary",
            "focus leaves the feedback dialog",
            "--source-label",
            "keyboard-review",
            "--environment",
            "local-dev",
            "--tool",
            "manual keyboard",
            "--route",
            "/console/changesets",
            "--reviewer-label",
            "reviewer-a",
            "--observed-issue",
            "Tab moved focus behind the dialog.",
            "--severity",
            "high",
            "--disposition",
            "paired_with_feedback",
            "--follow-up",
            "Keep feedback open until focus order is fixed.",
            "--paired-tool-output-label",
            "playwright keyboard smoke",
            "--skipped-case",
            "screen reader pairing",
            "--feedback",
            feedback_id,
            "--freshness",
            "needs_inspection",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    evidence_accessibility = json.loads(capsys.readouterr().out)
    evidence_list_exit = main(
        [
            "changeset",
            "evidence",
            "list",
            "--changeset",
            changeset_id,
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    evidence_list_output = capsys.readouterr().out
    feedback_list_exit = main(
        [
            "changeset",
            "feedback",
            "list",
            "--changeset",
            changeset_id,
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    feedback_list_output = capsys.readouterr().out
    feedback_show_exit = main(
        [
            "changeset",
            "feedback",
            "show",
            feedback_id,
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    feedback_detail = json.loads(capsys.readouterr().out)
    feedback_status_exit = main(
        [
            "changeset",
            "feedback",
            "status",
            changeset_id,
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    feedback_status = json.loads(capsys.readouterr().out)
    feedback_resolve_exit = main(
        [
            "changeset",
            "feedback",
            "resolve",
            feedback_id,
            "--summary",
            "List output now includes feedback summary and safe next actions.",
            "--residual-risk",
            "Reviewer acceptance is not implied.",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    feedback_resolved = json.loads(capsys.readouterr().out)
    feedback_reopen_exit = main(
        [
            "changeset",
            "feedback",
            "reopen",
            feedback_id,
            "--reason",
            "Need a dashboard read surface too.",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    feedback_reopened = json.loads(capsys.readouterr().out)
    feedback_accept_exit = main(
        [
            "changeset",
            "feedback",
            "accept-risk",
            feedback_id,
            "--risk-summary",
            "Dashboard is read-only for this task.",
            "--reason",
            "CLI and API own feedback mutation until later UX work.",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    feedback_accepted = json.loads(capsys.readouterr().out)

    list_exit = main(
        [
            "changeset",
            "list",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    list_output = capsys.readouterr().out

    show_exit = main(
        [
            "changeset",
            "show",
            changeset_id,
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    detail = json.loads(capsys.readouterr().out)

    (tmp_path / "app.py").write_text("print('changed')\n", encoding="utf-8")

    refresh_exit = main(
        [
            "changeset",
            "refresh",
            changeset_id,
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
        ]
    )
    refresh_output = capsys.readouterr().out
    plan_exit = main(
        [
            "changeset",
            "verification-plan",
            changeset_id,
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    plan = json.loads(capsys.readouterr().out)
    verification_command = plan["recommended_commands"][0]
    verification_id = new_task_verification_id()
    artifact_id = new_artifact_id()
    _seed_verification(
        db_path,
        session_id,
        task_id,
        verification_id,
        command=verification_command.split(),
        artifact_id=artifact_id,
    )
    record_exit = main(
        [
            "changeset",
            "record-verification",
            changeset_id,
            "--verification",
            str(verification_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    recorded = json.loads(capsys.readouterr().out)
    fixup_exit = main(
        [
            "changeset",
            "feedback",
            "fixup",
            feedback_id,
            "--source-summary",
            "operator recorded bounded fixup inventory from CLI",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    fixup_output = capsys.readouterr()
    assert fixup_exit == 0, fixup_output.err
    fixup = json.loads(fixup_output.out)
    brief_exit = main(
        [
            "changeset",
            "brief",
            changeset_id,
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    brief = json.loads(capsys.readouterr().out)
    brief_show_exit = main(
        [
            "changeset",
            "show",
            changeset_id,
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    brief_detail = json.loads(capsys.readouterr().out)
    commit_message_exit = main(
        [
            "changeset",
            "commit-message",
            changeset_id,
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    commit_message = json.loads(capsys.readouterr().out)
    precommit_summary_path = tmp_path / ".glassbox" / "precommit-summary.json"
    precommit_summary_path.write_text(
        json.dumps(
            {
                "status": "passed",
                "profile_id": "commit-smoke",
                "passed": 3,
                "failed": 0,
                "total": 3,
            }
        ),
        encoding="utf-8",
    )
    precommit_exit = main(
        [
            "changeset",
            "record-precommit",
            changeset_id,
            "--summary",
            str(precommit_summary_path),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    precommit = json.loads(capsys.readouterr().out)
    commit_prep_exit = main(
        [
            "changeset",
            "commit-prep",
            changeset_id,
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    commit_prep = json.loads(capsys.readouterr().out)
    handoff_exit = main(
        [
            "changeset",
            "handoff-readiness",
            changeset_id,
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    handoff = json.loads(capsys.readouterr().out)
    graph_summary_exit = main(
        [
            "changeset",
            "evidence-graph",
            changeset_id,
            "--summary",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    graph_summary = json.loads(capsys.readouterr().out)
    claim_id = f"claim:changeset:{changeset_id}:review-posture"
    graph_claim_exit = main(
        [
            "changeset",
            "evidence-graph",
            changeset_id,
            "--claim-id",
            claim_id,
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    graph_claim = json.loads(capsys.readouterr().out)
    graph_neighborhood_exit = main(
        [
            "changeset",
            "evidence-graph",
            changeset_id,
            "--node-id",
            claim_id,
            "--depth",
            "1",
            "--reviewer-safe",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    graph_neighborhood = json.loads(capsys.readouterr().out)
    export_path = tmp_path / "changeset-export.json"
    export_exit = main(
        [
            "changeset",
            "export",
            changeset_id,
            str(export_path),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    exported = json.loads(capsys.readouterr().out)
    export_payload = json.loads(export_path.read_text(encoding="utf-8"))
    (tmp_path / "app.py").write_text("print('changed again')\n", encoding="utf-8")

    stale_show_exit = main(
        [
            "changeset",
            "show",
            changeset_id,
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    stale_detail = json.loads(capsys.readouterr().out)
    feedback_archive_exit = main(
        [
            "changeset",
            "feedback",
            "archive",
            feedback_id,
            "--reason",
            "Superseded by resolved local response evidence.",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    feedback_archived = json.loads(capsys.readouterr().out)

    archive_exit = main(
        [
            "changeset",
            "archive",
            changeset_id,
            "--reason",
            "superseded",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    archived = json.loads(capsys.readouterr().out)

    assert create_exit == 0
    assert created["session_id"] == str(session_id)
    assert feedback_add_exit == 0
    assert feedback_added["feedback"]["summary"] == (
        "Clarify the review-feedback list output"
    )
    assert feedback_added["scopes"][0]["file_path"] == "app.py"
    assert "not approval" in " ".join(feedback_added["non_claims"])
    assert evidence_attach_exit == 0
    assert evidence_attached["evidence"]["target_kind"] == "feedback"
    assert evidence_attached["evidence"]["summary"] == "external CI reported green"
    assert evidence_attached["artifact_id"] is not None
    assert "not retained command evidence" in " ".join(evidence_attached["non_claims"])
    assert evidence_browser_exit == 0
    assert evidence_browser["evidence"]["evidence_kind"] == "browser_observation"
    assert evidence_browser["evidence"]["target_kind"] == "feedback"
    assert evidence_browser["evidence"]["freshness"] == "needs_inspection"
    assert "not deterministic release authority" in " ".join(
        evidence_browser["evidence"]["non_claims"]
    )
    assert "browser/dashboard evidence is advisory" in " ".join(
        evidence_browser["non_claims"]
    )
    assert evidence_accessibility_exit == 0
    assert evidence_accessibility["evidence"]["evidence_kind"] == "accessibility_note"
    assert "severity: high" in evidence_accessibility["evidence"]["limitations"]
    assert "not accessibility certification" in " ".join(
        evidence_accessibility["evidence"]["non_claims"]
    )
    assert evidence_list_exit == 0
    assert "Manual evidence: 3" in evidence_list_output
    assert "external CI reported green" in evidence_list_output
    assert "dashboard rendered feedback with manual evidence" in evidence_list_output
    assert "focus leaves the feedback dialog" in evidence_list_output
    assert feedback_list_exit == 0
    assert "Review feedback: 1" in feedback_list_output
    assert "Clarify the review-feedback list output" in feedback_list_output
    assert feedback_show_exit == 0
    assert feedback_detail["feedback"]["feedback_kind"] == "requested_change"
    assert feedback_detail["scopes"][0]["scope_kind"] == "file"
    assert feedback_detail["response_status"]["response_state"] == "planned"
    assert feedback_detail["response_status"]["fixup_inventory_count"] == 0
    assert feedback_status_exit == 0
    assert feedback_status["total_feedback_count"] == 1
    assert feedback_status["unresolved_count"] == 1
    assert feedback_status["items"][0]["response_state"] == "planned"
    assert feedback_resolve_exit == 0
    assert feedback_resolved["feedback"]["disposition"] == "resolved_locally"
    assert feedback_resolved["feedback"]["residual_risk"] == (
        "Reviewer acceptance is not implied."
    )
    assert feedback_reopen_exit == 0
    assert feedback_reopened["feedback"]["disposition"] == "open"
    assert feedback_reopened["feedback"]["reopened_count"] == 1
    assert feedback_accept_exit == 0
    assert feedback_accepted["feedback"]["disposition"] == "accepted_with_risk"
    assert list_exit == 0
    assert "Changesets: 1" in list_output
    assert show_exit == 0
    assert detail["changeset"]["task_id"] == str(task_id)
    assert detail["review_feedback"][0]["feedback_id"] == feedback_id
    assert {item["evidence_kind"] for item in detail["manual_evidence"]} == {
        "accessibility_note",
        "browser_observation",
        "external_check",
    }
    assert detail["review_response_summary"]["total_feedback_count"] == 1
    assert detail["review_response_summary"]["accepted_risk_count"] == 1
    assert detail["sources"][0]["source_kind"] == "task"
    assert "glassbox changeset refresh" in detail["safe_next_actions"][1]
    assert detail["next_action_records"][0]["target"]["kind"] == "changeset"
    assert detail["next_action_records"][0]["command"]["display"].startswith(
        "glassbox changeset show"
    )
    assert refresh_exit == 0
    assert "Refreshed change inventory" in refresh_output
    assert plan_exit == 0
    assert plan["expected_scope"] == ["app.py"]
    assert plan["readiness"]["state"] == "missing"
    assert plan["review_loop_summary"]["feedback_count"] == 1
    assert plan["review_loop_summary"]["manual_evidence_count"] == 3
    assert plan["review_loop_summary"]["browser_evidence_count"] == 1
    assert plan["review_loop_summary"]["accessibility_evidence_count"] == 1
    assert (
        "manual evidence suggests context only"
        in plan["review_loop_summary"]["non_claims"][0]
    )
    assert record_exit == 0
    assert recorded["readiness"]["state"] == "passed"
    assert recorded["retained_artifact_ids"] == [str(artifact_id)]
    assert fixup_exit == 0
    assert fixup["feedback_id"] == feedback_id
    assert fixup["changeset_id"] == changeset_id
    assert fixup["inventory"]["changed_path_count"] >= 1
    assert fixup["inventory"]["matched_scope_path_count"] >= 1
    assert fixup["response_status"]["fixup_inventory_count"] == 1
    assert "not reviewer acceptance" in " ".join(fixup["non_claims"])
    assert any("feedback show" in action for action in fixup["safe_next_actions"])
    assert brief_exit == 0
    assert brief["brief"]["artifact_kind"] == "changeset_review_brief"
    assert brief["brief"]["verification"]["body"].startswith("Readiness is passed")
    assert brief["limitation_summary"] is None
    assert brief["brief"]["limitation_summary"] is None
    assert brief["event"]["payload"]["event_type"] == "ChangesetReviewBriefCreated"
    assert brief["readiness_event"]["payload"]["state"] == "ready"
    assert Path(tmp_path / brief["artifact_path"]).exists()
    assert brief_show_exit == 0
    assert (
        brief_detail["changeset"]["latest_review_brief_artifact_id"]
        == (brief["artifact_id"])
    )
    assert (
        brief_detail["review_response_summary"]["items"][0]["fixup_inventory_count"]
        == 1
    )
    assert brief_detail["review_briefs"][0]["artifact_id"] == brief["artifact_id"]
    assert brief_detail["readiness"][0]["readiness_kind"] == "review"
    assert commit_message_exit == 0
    assert commit_message["suggestion_label"] == "suggestion_only_not_committed"
    assert commit_message["subject"] == "Review task: Add changeset command"
    assert "Commit readiness:" in commit_message["message"]
    assert commit_message["deterministic"] is True
    assert precommit_exit == 0
    assert precommit["evidence"]["artifact_kind"] == "changeset_precommit_evidence"
    assert precommit["evidence"]["state"] == "passed"
    assert precommit["readiness_event"]["payload"]["readiness_kind"] == "commit"
    assert precommit["readiness_event"]["payload"]["state"] == "ready"
    assert Path(tmp_path / precommit["artifact_path"]).exists()
    assert any(
        signal["signal_id"] == "retained-precommit-evidence"
        for signal in precommit["commit_readiness"]["signals"]
    )
    assert commit_prep_exit == 0
    assert commit_prep["commit_message"]["suggestion_label"] == (
        "suggestion_only_not_committed"
    )
    assert "did not stage" in commit_prep["safe_copy"]
    assert commit_prep["commit_readiness"]["state"] in {
        "dirty_untracked_risk",
        "ready",
        "stale_inventory",
    }
    assert commit_prep["commit_readiness"]["review_feedback_count"] == 1
    assert commit_prep["commit_readiness"]["manual_evidence_count"] == 3
    assert commit_prep["commit_readiness"]["local_only_evidence_count"] == 3
    assert commit_prep["commit_readiness"]["accepted_risk_count"] >= 1
    assert commit_prep["handoff_readiness"]["readiness_kind"] == "handoff"
    assert "not reviewer approval" in commit_prep["commit_message"]["message"]
    assert handoff_exit == 0
    assert handoff["readiness_kind"] == "handoff"
    assert handoff["state"] == "unresolved_risk"
    assert handoff["evidence"]["accepted_risk_count"] == 1
    assert handoff["evidence"]["manual_evidence_count"] == 3
    assert "not publication" in " ".join(handoff["non_claims"])
    assert any("changeset show" in action for action in handoff["safe_next_actions"])
    assert handoff["next_action_records"][0]["target"]["kind"] == "changeset"
    assert handoff["next_action_records"][0]["command"]["display"].startswith(
        "glassbox changeset show"
    )
    assert graph_summary_exit == 0
    assert graph_summary["target_kind"] == "changeset"
    assert graph_summary["target_id"] == changeset_id
    assert graph_summary["claim_count"] == 1
    assert graph_summary["accepted_risk_claim_count"] == 1
    assert graph_claim_exit == 0
    assert graph_claim["claim_id"] == claim_id
    assert graph_claim["state"] == "accepted_with_risk"
    assert graph_claim["supporting_edge_ids"]
    assert graph_neighborhood_exit == 0
    assert {node["node_id"] for node in graph_neighborhood["nodes"]} >= {claim_id}
    assert all(
        node["visibility"] == "reviewer_safe" for node in graph_neighborhood["nodes"]
    )
    assert export_exit == 0
    assert exported["status"] == "exported"
    assert export_payload["export_kind"] == "changeset_review_export"
    assert export_payload["changeset"]["changeset_id"] == changeset_id
    assert export_payload["review_brief"]["artifact_id"] == brief["artifact_id"]
    assert export_payload["review_brief"]["schema_version"] == 2
    assert export_payload["review_brief"]["limitation_summary"] is None
    assert export_payload["review_brief"]["review_feedback"] is not None
    assert export_payload["review_brief"]["manual_evidence"] is not None
    assert export_payload["review_brief"]["publication_boundary"] is not None
    assert export_payload["review_feedback"]["total_count"] == 1
    assert export_payload["review_responses"]["accepted_risk_count"] == 1
    assert export_payload["manual_evidence"]["total_count"] == 3
    assert export_payload["live_review_evidence"]["browser_evidence_count"] == 1
    assert export_payload["live_review_evidence"]["accessibility_evidence_count"] == 1
    assert "raw screenshots" in " ".join(export_payload["redaction_report"])
    assert "not reviewer approval" in " ".join(export_payload["non_claims"])
    assert (
        "raw .glassbox database state is not included"
        in (export_payload["redaction_report"])
    )
    artifact_kinds = {
        reference["artifact_kind"]
        for reference in export_payload["artifact_references"]
    }
    assert "manual_evidence" in artifact_kinds
    assert export_payload["artifact_references"][0]["local_only"] is True
    assert stale_show_exit == 0
    assert stale_detail["inventory"]["freshness"] == "stale"
    assert stale_detail["verification_posture"]["state"] == "passed"
    assert stale_detail["verification_plan"]["readiness"]["state"] == "stale"
    assert stale_detail["inventory_status"]["stale"] is True
    assert "source digest changed" in stale_detail["inventory_status"]["reason"]
    assert feedback_archive_exit == 0
    assert feedback_archived["feedback"]["disposition"] == "archived"
    assert feedback_archived["feedback"]["archived_reason"] == (
        "Superseded by resolved local response evidence."
    )
    assert archive_exit == 0
    assert archived["payload"]["event_type"] == "ChangesetArchived"


def test_changeset_verification_plan_accepts_path_preview(
    tmp_path: Path,
    capsys,
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    exit_code = main(
        [
            "changeset",
            "verification-plan",
            "--path",
            "frontend/app/changesets/page.tsx",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["changed_paths"] == ["frontend/app/changesets/page.tsx"]
    assert payload["plan_entries"]
    assert any(
        entry["lifecycle_state"] == "manual-only"
        and entry["manual_evidence_required"] is True
        for entry in payload["plan_entries"]
    )
    assert "not persisted changeset evidence" in " ".join(payload["non_claims"])


def test_changeset_verification_plan_records_operator_dispositions(
    tmp_path: Path,
    capsys,
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    session_id = new_session_id()
    task_id = new_task_id()
    _init_git_repo(tmp_path)
    _seed_task(db_path, tmp_path, session_id, task_id)

    create_exit = main(
        [
            "changeset",
            "create",
            "--from",
            "task",
            "--task",
            str(task_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    changeset_id = json.loads(capsys.readouterr().out)["changeset_id"]
    (tmp_path / "app.py").write_text("print('changed')\n", encoding="utf-8")
    refresh_exit = main(
        [
            "changeset",
            "refresh",
            changeset_id,
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    capsys.readouterr()
    plan_exit = main(
        [
            "changeset",
            "verification-plan",
            changeset_id,
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    plan = json.loads(capsys.readouterr().out)
    command_entry = next(entry for entry in plan["plan_entries"] if entry["command"])
    manual_entry = next(
        entry
        for entry in plan["plan_entries"]
        if entry["manual_evidence_required"] is True
    )

    select_exit = main(
        [
            "changeset",
            "verification-select",
            changeset_id,
            "--verification",
            command_entry["verification_id"],
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    select_output = capsys.readouterr()
    assert select_exit == 0, select_output.err
    selected = json.loads(select_output.out)
    skip_exit = main(
        [
            "changeset",
            "verification-skip",
            changeset_id,
            "--verification",
            command_entry["verification_id"],
            "--reason",
            "covered by external retained evidence",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    skipped = json.loads(capsys.readouterr().out)
    risk_exit = main(
        [
            "changeset",
            "verification-accept-risk",
            changeset_id,
            "--verification",
            command_entry["verification_id"],
            "--reason",
            "small docs-only residual risk",
            "--risk",
            "no fresh command run",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    accepted = json.loads(capsys.readouterr().out)
    supersede_exit = main(
        [
            "changeset",
            "verification-supersede",
            changeset_id,
            "--verification",
            command_entry["verification_id"],
            "--replacement",
            manual_entry["verification_id"],
            "--reason",
            "manual evidence replaces stale command plan",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    supersede_output = capsys.readouterr()
    assert supersede_exit == 0, supersede_output.err
    superseded = json.loads(supersede_output.out)

    assert create_exit == 0
    assert refresh_exit == 0
    assert plan_exit == 0
    assert select_exit == 0
    assert selected["action"] == "selected"
    assert selected["events"][0]["payload"]["event_type"] == "TaskVerificationPlanned"
    assert skip_exit == 0
    assert skipped["action"] == "skipped"
    assert len(skipped["events"]) == 2
    assert risk_exit == 0
    assert accepted["action"] == "accepted-risk"
    assert accepted["events"][1]["payload"]["residual_risks"] == [
        "no fresh command run"
    ]
    assert supersede_exit == 0
    assert superseded["action"] == "superseded"
    assert superseded["replacement_verification_id"] == manual_entry["verification_id"]
    assert "not release approval" in " ".join(accepted["non_claims"])


def test_changeset_evidence_records_skipped_live_evidence_without_placeholders(
    tmp_path: Path,
    capsys,
) -> None:
    db_path = tmp_path / ".glassbox" / "glassbox.sqlite3"
    session_id = new_session_id()
    task_id = new_task_id()
    _init_git_repo(tmp_path)
    _seed_task(db_path, tmp_path, session_id, task_id)

    create_exit = main(
        [
            "changeset",
            "create",
            "--from",
            "task",
            "--task",
            str(task_id),
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    changeset_id = json.loads(capsys.readouterr().out)["changeset_id"]
    dashboard_exit = main(
        [
            "changeset",
            "evidence",
            "dashboard",
            changeset_id,
            "--summary",
            "dashboard walkthrough intentionally skipped",
            "--source-label",
            "dashboard-local",
            "--capture-state",
            "not_run",
            "--skip-reason",
            "local dashboard server was not started",
            "--skipped-case",
            "unknown viewport",
            "--freshness",
            "needs_inspection",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    dashboard = json.loads(capsys.readouterr().out)
    contradiction_exit = main(
        [
            "changeset",
            "evidence",
            "browser",
            changeset_id,
            "--summary",
            "contradictory skipped browser evidence",
            "--source-label",
            "local-browser",
            "--capture-state",
            "not_run",
            "--skip-reason",
            "browser was not opened",
            "--console-checked",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    contradiction_error = capsys.readouterr().err
    accessibility_exit = main(
        [
            "changeset",
            "evidence",
            "accessibility",
            changeset_id,
            "--kind",
            "screen_reader_note",
            "--summary",
            "screen reader pass not applicable to this backend-only change",
            "--source-label",
            "accessibility-review",
            "--capture-state",
            "not_applicable",
            "--skip-reason",
            "no user-facing route changed",
            "--skipped-case",
            "screen reader pass",
            "--cwd",
            str(tmp_path),
            "--db-path",
            str(db_path),
            "--json",
        ]
    )
    accessibility = json.loads(capsys.readouterr().out)

    assert create_exit == 0
    assert dashboard_exit == 0
    assert dashboard["evidence"]["evidence_kind"] == "browser_observation"
    assert "capture state: not_run" in dashboard["evidence"]["limitations"]
    assert (
        "skip reason: local dashboard server was not started"
        in (dashboard["evidence"]["limitations"])
    )
    assert (
        "skipped browser/dashboard evidence is not a pass"
        in (dashboard["evidence"]["non_claims"])
    )
    assert "browser/dashboard evidence is advisory" in " ".join(dashboard["non_claims"])
    assert any(
        "browser/dashboard route" in action for action in dashboard["safe_next_actions"]
    )
    assert contradiction_exit == 1
    assert "cannot claim console was checked" in contradiction_error
    assert accessibility_exit == 0
    assert accessibility["evidence"]["evidence_kind"] == "accessibility_note"
    assert "capture state: not_applicable" in accessibility["evidence"]["limitations"]
    assert (
        "skip reason: no user-facing route changed"
        in (accessibility["evidence"]["limitations"])
    )
    assert (
        "skipped accessibility evidence is not a pass"
        in (accessibility["evidence"]["non_claims"])
    )


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


def _seed_task(db_path: Path, tmp_path: Path, session_id, task_id) -> None:
    connection = open_database(db_path)
    try:
        initialize_database(connection)
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
                        title="Add changeset command",
                        goal="Expose changeset surfaces",
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
    finally:
        connection.close()


def _seed_verification(
    db_path: Path,
    session_id,
    task_id,
    verification_id,
    *,
    command: list[str],
    artifact_id,
) -> None:
    connection = open_database(db_path)
    try:
        repository = SQLiteSessionRepository(connection)
        repository.append_events(
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TaskVerificationPlanned(
                        task_id=task_id,
                        verification=VerificationPlanEntry(
                            verification_id=verification_id,
                            check_name="changeset verification",
                            kind=VerificationCheckKind.COMMAND,
                            command=command,
                            source=VerificationPlanSource.EVAL_RECOMMENDATION,
                            rationale="operator selected changeset plan command",
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
        )
    finally:
        connection.close()
