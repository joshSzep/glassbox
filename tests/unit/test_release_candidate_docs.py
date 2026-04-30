"""Release-candidate documentation guardrails."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+\.md)(?:#[^)]+)?\)")


def test_v2_release_candidate_doc_covers_supported_operating_model() -> None:
    content = (REPO_ROOT / "docs" / "v2-release-candidate.md").read_text(
        encoding="utf-8"
    )

    for required_text in (
        "## Release-Readiness Checklist",
        "uv run glassbox command tree",
        "uv run glassbox observability status --json",
        "uv run glassbox performance budgets",
        "uv run pre-commit run --all-files",
        "Manual dashboard smoke",
        "Manual daemon smoke",
        "Deliberate Non-Goals",
    ):
        assert required_text in content


def test_readmes_link_to_v2_release_candidate_guide() -> None:
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    getting_started = (REPO_ROOT / "docs" / "getting-started.md").read_text(
        encoding="utf-8"
    )

    assert "docs/v2-release-candidate.md" in root_readme
    assert "v2-release-candidate.md" in docs_readme
    assert "v2-release-candidate.md" in getting_started


def test_v6_release_candidate_doc_covers_supported_operating_model() -> None:
    content = (REPO_ROOT / "docs" / "v6-release-candidate.md").read_text(
        encoding="utf-8"
    )

    for required_text in (
        "## Supported Operating Model",
        "uv run python scripts/validate_v6_release_gate.py",
        "glassbox session cancel SESSION_ID",
        "glassbox provider canary run",
        "manual-validation.md",
        "## Release-Readiness Checklist",
        "## Known Residual Risks",
        "## Deliberate Non-Goals",
        "## Release Decision",
        "Decision: GO for v6 release candidate.",
        ".glassbox/releases/gbx-704-final-decision/summary.json",
        "Post-v6 follow-up backlog",
    ):
        assert required_text in content


def test_readmes_link_to_v6_release_candidate_guide() -> None:
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    getting_started = (REPO_ROOT / "docs" / "getting-started.md").read_text(
        encoding="utf-8"
    )

    assert "docs/v6-release-candidate.md" in root_readme
    assert "v6-release-candidate.md" in docs_readme
    assert "v6-release-candidate.md" in getting_started


def test_docs_hub_links_to_v6_phase_64_docs() -> None:
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for doc_name in (
        "tasks-v6.md",
        "v6-release-hardening.md",
        "v6-release-inventory.md",
        "v6-release-evidence.md",
    ):
        assert doc_name in docs_readme


def test_v6_phase_64_docs_are_cross_linked() -> None:
    v5_gate = (REPO_ROOT / "docs" / "v5-terminal-release-gate.md").read_text(
        encoding="utf-8"
    )
    release_packaging = (REPO_ROOT / "docs" / "release-packaging.md").read_text(
        encoding="utf-8"
    )
    hardening = (REPO_ROOT / "docs" / "v6-release-hardening.md").read_text(
        encoding="utf-8"
    )
    inventory = (REPO_ROOT / "docs" / "v6-release-inventory.md").read_text(
        encoding="utf-8"
    )
    evidence = (REPO_ROOT / "docs" / "v6-release-evidence.md").read_text(
        encoding="utf-8"
    )

    for content in (v5_gate, release_packaging):
        assert "v6-release-hardening.md" in content
        assert "v6-release-inventory.md" in content
        assert "v6-release-evidence.md" in content

    assert "v6-release-inventory.md" in hardening
    assert "v6-release-evidence.md" in hardening
    assert "v6-release-hardening.md" in inventory
    assert "v6-release-evidence.md" in inventory
    assert "v6-release-hardening.md" in evidence
    assert "v6-release-inventory.md" in evidence


def test_v7_contract_covers_adoption_and_scale_boundary() -> None:
    content = (REPO_ROOT / "docs" / "v7-adoption-scale-contract.md").read_text(
        encoding="utf-8"
    )

    for required_text in (
        "## Scope",
        "## Non-Goals",
        "## Supported Workflow Set",
        "## v6 Follow-Up Mapping",
        "## Evidence Classes",
        "## Release-Readiness Checklist",
        "## Residual Risk Register Shape",
        "## Pass And Fail Policy",
        "Provider canary failures are advisory by default",
        "Deterministic stage failure blocks the v7 release candidate.",
        "tasks-v7.md",
    ):
        assert required_text in content


def test_v7_inventory_covers_scale_verification_and_adoption_gaps() -> None:
    content = (REPO_ROOT / "docs" / "v7-scale-verification-inventory.md").read_text(
        encoding="utf-8"
    )

    for required_text in (
        "## Command Surface Baseline",
        "## Deterministic Eval Portfolio",
        "## Provider Diagnostics And Canary Evidence",
        "## Larger-Session Read Paths",
        "## Daemon, Transport, And Multi-Observer Evidence",
        "## Tool Policy And Approval Governance",
        "## Accessibility Evidence",
        "## Onboarding And Packaging",
        "## Recommended v7 Gate Membership",
        "## Summary Of Weak Or Missing Coverage",
        "approval_flow",
        "ask_user_flow",
        "live-provider-canary",
        "uv run glassbox command tree",
    ):
        assert required_text in content


def test_docs_hub_links_to_v7_phase_71_docs() -> None:
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for doc_name in (
        "tasks-v7.md",
        "v7-adoption-scale-contract.md",
        "v7-scale-verification-inventory.md",
    ):
        assert doc_name in docs_readme


def test_v7_phase_71_docs_are_cross_linked() -> None:
    task_graph = (REPO_ROOT / "docs" / "tasks-v7.md").read_text(encoding="utf-8")
    contract = (REPO_ROOT / "docs" / "v7-adoption-scale-contract.md").read_text(
        encoding="utf-8"
    )
    inventory = (REPO_ROOT / "docs" / "v7-scale-verification-inventory.md").read_text(
        encoding="utf-8"
    )

    assert "v7-adoption-scale-contract.md" in task_graph
    assert "v7-scale-verification-inventory.md" in task_graph
    assert "v7-scale-verification-inventory.md" in contract
    assert "v7-adoption-scale-contract.md" in inventory


def test_v8_contract_covers_auditable_autonomy_boundary() -> None:
    content = (REPO_ROOT / "docs" / "v8-auditable-autonomy-contract.md").read_text(
        encoding="utf-8"
    )

    for required_text in (
        "## Scope",
        "## Non-Goals",
        "## Supported Workflow Set",
        "## Auditable Autonomy Definition",
        "## v7 Follow-Up Mapping",
        "## Evidence Classes",
        "## Release-Readiness Checklist",
        "## Residual Risk Register Shape",
        "## Pass And Fail Policy",
        "Autonomy-boundedness evidence failure blocks",
        "Provider evidence should never be mistaken for deterministic release signoff.",
        "tasks-v8.md",
    ):
        assert required_text in content


def test_v8_inventory_covers_autonomy_baseline_and_gaps() -> None:
    content = (REPO_ROOT / "docs" / "v8-autonomy-baseline-inventory.md").read_text(
        encoding="utf-8"
    )

    for required_text in (
        "## Command Surface Baseline",
        "## Turn Execution, Suspension, And Resumption",
        "## Approval, Command, Policy, And Budget Gates",
        "## Cancellation And Stop Conditions",
        "## Daemon, Ownership, Attach, And Background-Worker Seams",
        "## Runtime Context, Notes, Working Set, And Memory Limits",
        "## Repository Context And Code-Inspection Limits",
        "## Branching, Replay, Eval, And Verification Flows",
        "## Dashboard And Web Control Surfaces",
        "## Provider Diagnostics, Canaries, And Model Readiness",
        "## Conservative Bottlenecks And Safe Loosening Opportunities",
        "## Implementation Surface Classification",
        "## Summary Of Weak Or Missing Coverage",
        "uv run glassbox command tree",
        "src/glassbox/runtime/turn_engine.py",
        "tasks-v8.md",
    ):
        assert required_text in content


def test_docs_hub_links_to_v8_phase_81_docs() -> None:
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for doc_name in (
        "tasks-v8.md",
        "v8-auditable-autonomy-contract.md",
        "v8-autonomy-baseline-inventory.md",
    ):
        assert doc_name in docs_readme


def test_v8_phase_81_docs_are_cross_linked() -> None:
    task_graph = (REPO_ROOT / "docs" / "tasks-v8.md").read_text(encoding="utf-8")
    contract = (REPO_ROOT / "docs" / "v8-auditable-autonomy-contract.md").read_text(
        encoding="utf-8"
    )
    inventory = (REPO_ROOT / "docs" / "v8-autonomy-baseline-inventory.md").read_text(
        encoding="utf-8"
    )

    assert "v8-auditable-autonomy-contract.md" in task_graph
    assert "v8-autonomy-baseline-inventory.md" in task_graph
    assert "v8-autonomy-baseline-inventory.md" in contract
    assert "v8-auditable-autonomy-contract.md" in inventory


def test_v8_release_candidate_doc_covers_supported_operating_model() -> None:
    content = (REPO_ROOT / "docs" / "v8-release-candidate.md").read_text(
        encoding="utf-8"
    )

    for required_text in (
        "## Supported Operating Model",
        "uv run python scripts/validate_v8_release_gate.py",
        ".glassbox/releases/20260429T180807Z-v8-gate/summary.json",
        ".glassbox/evals/20260429T180807Z-v8-gate/autonomy-advisory/",
        "task plans",
        "autonomy budgets",
        "background jobs",
        "workspace memory",
        "repository index",
        "verify-repair loops",
        "branch-search workflows",
        "provider recommendations remain advisory",
        "## Release-Readiness Checklist",
        "## Known Residual Risks",
        "## Deliberate Non-Goals",
        "## Release Decision",
        "Decision: GO for v8 release candidate publication.",
    ):
        assert required_text in content


def test_readmes_link_to_v8_release_candidate_guide() -> None:
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    assert "docs/v8-release-candidate.md" in root_readme
    assert "v8-release-candidate.md" in docs_readme


def test_v9_public_baseline_covers_supported_product_contract() -> None:
    content = (REPO_ROOT / "docs" / "v9-public-baseline.md").read_text(encoding="utf-8")

    for required_text in (
        "## Product Model",
        "## Supported Daily Workflows",
        "## Advisory Workflows",
        "## Release-Evidence Workflows",
        "## v8 Residual-Risk Mapping",
        "## Version Contract",
        "`0.9.0`",
        "`uv run glassbox command tree`",
        "`session`, `task`, `branch-search`, `memory`, `repo index`, `replay`, `eval`",
        "provider recommendations",
        "evidence is the release authority; live-provider evidence is advisory",
        "version-release-policy.md",
    ):
        assert required_text in content


def test_docs_hub_links_to_v9_public_baseline() -> None:
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    assert "v9-public-baseline.md" in docs_readme
    assert "v9-vocabulary.md" in docs_readme
    assert "v9-command-surface-review.md" in docs_readme


def test_v9_vocabulary_covers_command_and_dashboard_language() -> None:
    content = (REPO_ROOT / "docs" / "v9-vocabulary.md").read_text(encoding="utf-8")

    for required_text in (
        "## Core Terms",
        "## Preferred Language",
        "## Command Help Review",
        "## Dashboard Copy Review",
        "## Compatibility Policy",
        "Session",
        "Task",
        "Evidence",
        "Memory",
        "Branch",
        "Verify",
        "Provider",
        "Daemon",
        "Projection",
        "`uv run glassbox command tree`",
        "No command rename is recommended for `GBX-930`",
        "provider evidence is advisory",
    ):
        assert required_text in content


def test_v9_command_surface_review_covers_deemphasis_plan() -> None:
    content = (REPO_ROOT / "docs" / "v9-command-surface-review.md").read_text(
        encoding="utf-8"
    )

    for required_text in (
        "## Classification",
        "### Daily Commands",
        "### Advanced Commands",
        "### Recovery And Internal-Maintenance Commands",
        "### Release-Evidence Commands",
        "## Dashboard Surface Inventory",
        "## Recommendations",
        "## Compatibility Plan",
        "glassbox command guide",
        "glassbox command tree",
        "No command, route, JSON field, event type, or dashboard panel is deprecated",
        "WorkspaceOverview",
        "SessionInspector",
        "TaskAutonomyConsole",
        "KnowledgeAutonomyConsole",
        "BranchSearchConsole",
    ):
        assert required_text in content


def test_v9_dashboard_cockpit_contract_covers_operator_priority_model() -> None:
    content = (REPO_ROOT / "docs" / "dashboard-cockpit-contract.md").read_text(
        encoding="utf-8"
    )

    for required_text in (
        "## Cockpit Surfaces",
        "Workspace overview",
        "Active session",
        "Task queue",
        "Evidence",
        "Memory and repository index",
        "Branches",
        "Recovery cues",
        "## Priority Rules",
        "Pending approval that blocks a live or resumable turn.",
        "Stale repository index",
        "Provider credential, compatibility, freshness, warning",
        "evidence.",
        "## Responsive Expectations",
        "## Keyboard And Accessibility Expectations",
        "## Data Source Map",
        "`GET /sessions/aggregate`",
        "`GET /sessions/{session_id}`",
        "`GET /sessions/{session_id}/events`",
        "`SessionAggregateView`",
        "`WorkspaceRuntimeSummaryView`",
        "`OperatorSessionSummaryView`",
        "`WorkspaceOverview`",
        "`SessionInspector`",
        "`TaskAutonomyConsole`",
        "`KnowledgeAutonomyConsole`",
        "`BranchSearchConsole`",
        "GBX-941",
        "GBX-942",
        "GBX-943",
    ):
        assert required_text in content


def test_v9_eval_promotion_plan_classifies_autonomy_cases() -> None:
    content = (REPO_ROOT / "docs" / "v9-eval-promotion-plan.md").read_text(
        encoding="utf-8"
    )
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    evals_readme = (REPO_ROOT / "evals" / "README.md").read_text(encoding="utf-8")

    for required_text in (
        "## Review Inputs",
        "## Promotion Criteria",
        "## Case Classification",
        "## GBX-951 Follow-Up",
        "uv run glassbox eval run --profile v8-autonomy-advisory --cwd .",
        "uv run glassbox eval audit --cwd .",
        "`GBX-951` updates `evals/profiles.json`",
        "Split before promotion",
        "Keep advisory",
        "Promote to release-candidate",
        "autonomy.budget-exhaustion",
        "verification.success",
        "verification.failure",
        "branch-search.candidate-comparison",
        ".glassbox/evals/gbx-950-promotion-review.md",
    ):
        assert required_text in content

    assert "v9-eval-promotion-plan.md" in docs_readme
    assert "v9-eval-promotion-plan.md" in evals_readme


def test_v9_release_gate_doc_covers_automated_evidence_contract() -> None:
    content = (REPO_ROOT / "docs" / "v9-release-gate.md").read_text(encoding="utf-8")
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for required_text in (
        "uv run python scripts/validate_v9_release_gate.py",
        "v9 first-run readiness smoke",
        "v9 command discovery smoke",
        "v9 provider evidence policy check",
        "v9 provider recommendation release fit",
        "v9 promoted autonomy release profile",
        "v9 deterministic eval release report",
        "adoption_readiness",
        "release_authority",
        "Provider canaries remain advisory by default",
        "Any failed blocking stage fails the v9 release gate.",
    ):
        assert required_text in content

    assert "v9-release-gate.md" in docs_readme


def test_v9_manual_validation_docs_cover_accessibility_and_residual_risks() -> None:
    manual = (REPO_ROOT / "docs" / "manual-v9-release-validation.md").read_text(
        encoding="utf-8"
    )
    archive = (REPO_ROOT / "docs" / "manual-qa-evidence-v9.md").read_text(
        encoding="utf-8"
    )
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for required_text in (
        ".glassbox/releases/gbx-992-manual-evidence/",
        "First-run readiness",
        "Chat startup summary",
        "Dashboard cockpit",
        "Task evidence drill-down",
        "Recovery cues",
        "Provider evidence cues",
        "Package smoke",
        "Named Accessibility Pairings",
        "Non-claims",
        "Browser-rendered dashboard keyboard and mobile evidence is blocked",
        "Provisional go",
    ):
        assert required_text in manual

    for required_text in (
        "## Directory Convention",
        "## Manual Validation Manifest",
        "First-run readiness",
        "Dashboard Cockpit Checklist",
        "Named Accessibility Pairings",
        "## Redaction Rules",
        "## Accessibility Claims Rule",
    ):
        assert required_text in archive

    assert "manual-v9-release-validation.md" in docs_readme
    assert "manual-qa-evidence-v9.md" in docs_readme


def test_v9_release_candidate_doc_covers_decision_and_evidence() -> None:
    content = (REPO_ROOT / "docs" / "v9-release-candidate.md").read_text(
        encoding="utf-8"
    )
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for required_text in (
        "## Release Posture",
        "## Supported Operating Model",
        "## Release-Readiness Checklist",
        "## Current Evidence Summary",
        "## Known Residual Risks",
        "## Deliberate Non-Goals",
        "## Release Decision",
        "uv run python scripts/validate_v9_release_gate.py",
        ".glassbox/releases/gbx-993-v9-release-candidate/",
        ".glassbox/evals/gbx-993-v9-release-candidate/",
        "Provider evidence improves operational confidence",
        "deterministic replay/eval release authority",
        "Browser-rendered dashboard keyboard and mobile evidence was blocked",
        "Decision: GO for v9 release candidate publication.",
        "63` passed stages",
        "No deterministic blocker remains open",
        "manual-v9-release-validation.md",
        "v9-dogfooding-summary.md",
    ):
        assert required_text in content

    assert "docs/v9-release-candidate.md" in root_readme
    assert "v9-release-candidate.md" in docs_readme


def test_v10_long_running_task_contract_covers_product_model() -> None:
    content = (REPO_ROOT / "docs" / "v10-long-running-task-contract.md").read_text(
        encoding="utf-8"
    )

    for required_text in (
        "## Scope",
        "## Non-Goals",
        "## Product Model",
        "## Supported Workflow Set",
        "## Evidence Expectations",
        "## v9 Residual-Risk And Dogfooding Mapping",
        "## Pass And Fail Policy",
        "Event",
        "Checkpoint",
        "Compaction",
        "Attempt",
        "Heartbeat",
        "Verification",
        "Recovery",
        "uv run glassbox command tree",
        "glassbox session resume SESSION_ID",
        "glassbox eval audit",
        "durable-event lifecycle evidence",
        "checkpoint model, projection, API, CLI, export, and resume evidence",
        "compaction artifact, provenance, freshness, and prompt-integration evidence",
        "resumable-tool attempt, heartbeat, partial-output, retry, and recovery",
        "provider failure, model-switch, fallback, and advisory-posture evidence",
        "Provider evidence remains advisory.",
        "tasks-v10.md",
        "## Canonical Event Vocabulary",
        "`LongRunPhaseChanged`",
        "`TaskCheckpointCreated`",
        "`ContextCompactionCreated`",
        "`ToolAttemptHeartbeat`",
        "`RecoveryDecisionRecorded`",
        "`ResumeOutcomeRecorded`",
        "`long_run_events`",
        "## Incomplete-Turn Recovery Semantics",
        "`turn_recovery_posture`",
        "`non_resumable`",
        "Projection rebuilds continue to derive this",
        "posture from canonical events",
        "## SSE Cursor Contract",
        "`glassbox.stream.status`",
        "`history_truncated`",
        "keepalive comments are explicit",
    ):
        assert required_text in content


def test_readmes_link_to_v10_long_running_task_contract() -> None:
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    assert "docs/v10-long-running-task-contract.md" in root_readme
    assert "docs/tasks-v10.md" in root_readme
    assert "v10-long-running-task-contract.md" in docs_readme
    assert "tasks-v10.md" in docs_readme


def test_v10_durability_audit_maps_runtime_recovery_boundaries() -> None:
    content = (REPO_ROOT / "docs" / "v10-durability-audit.md").read_text(
        encoding="utf-8"
    )
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for required_text in (
        "## Classification Legend",
        "## Boundary Map",
        "## Priority Work Queue",
        "## Test Inventory",
        "Turn engine",
        "Model loop",
        "Tool execution output and completion",
        "Approval and ask-user suspension reconstruction",
        "Background job leases, heartbeats, and stale recovery",
        "Daemon ownership",
        "SSE server replay and live stream",
        "Context assembly",
        "SQLite projections",
        "Replay and eval",
        "Dashboard reducers and attention summary",
        "Already durable",
        "Rebuildable projection",
        "Recoverable but weakly surfaced",
        "Process-local",
        "Accepted non-goal",
        "src/glassbox/runtime/turn_engine.py",
        "src/glassbox/runtime/model_loop.py",
        "src/glassbox/runtime/turn_tool_executor.py",
        "src/glassbox/runtime/turn_resumption.py",
        "src/glassbox/runtime/background_jobs.py",
        "src/glassbox/runtime/daemon.py",
        "src/glassbox/web/routes/events.py",
        "frontend/api/sse.ts",
        "frontend/state/session-events.ts",
        "tests/unit/test_turn_resumption.py",
        "process restart after `ModelCallStarted` without `ModelCallCompleted`",
        "deterministic replay/eval cases for all promoted v10 long-run contracts",
    ):
        assert required_text in content

    assert "v10-durability-audit.md" in docs_readme


def test_provider_docs_define_v9_evidence_freshness_contract() -> None:
    content = (REPO_ROOT / "docs" / "providers.md").read_text(encoding="utf-8")
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for required_text in (
        "## Provider Evidence Freshness",
        "`latest_status`",
        "`freshness_status`",
        "`fresh`, `stale`, `incompatible`, `missing`,",
        "`credentialless`, `warning`, or `failed`",
        "provider-evidence-freshness.v1",
        "current provider/model",
        "identity",
        "younger than seven days",
        "Deterministic replay/eval reports remain the blocking release authority",
    ):
        assert required_text in content

    assert "freshness states" in docs_readme


def test_provider_docs_define_v9_recommendation_contract() -> None:
    content = (REPO_ROOT / "docs" / "providers.md").read_text(encoding="utf-8")

    for required_text in (
        "`capability_fit`",
        "`risk_posture`",
        "`evidence_freshness`",
        "`credential_readiness`",
        "`recommended_action`",
        "`failure_posture`",
        "`budget_impact`",
        "Values are:",
        "`switch_provider`",
        "`local_fallback`",
        "replay/eval evidence remains the blocking release boundary",
        "Workflow scenario mapping is deliberately explicit",
        "inspect workflows look for `streaming-text` and `long-context-continuity`",
        "edit-safe workflows look for `streaming-text`, `tool-call`,",
        "test-driven workflows look for `streaming-text`, `tool-call`,",
        "release-candidate workflows look for `streaming-text`, `tool-call`,",
        "background-continuation workflows look for `streaming-text`,",
        "provider/model mismatches lower confidence",
    ):
        assert required_text in content


def test_docs_hub_separates_operator_docs_from_release_evidence() -> None:
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for heading in (
        "## Start Here",
        "## Daily Workflows",
        "## Reference",
        "## Release Evidence",
        "## Implementation History",
    ):
        assert heading in docs_readme

    assert docs_readme.index("## Daily Workflows") < docs_readme.index(
        "## Release Evidence"
    )
    assert "operator-quickstart.md" in docs_readme
    assert "dashboard-cockpit-contract.md" in docs_readme
    assert "v8-release-candidate.md" in docs_readme
    assert "tasks-v9.md" in docs_readme


def test_operator_quickstart_covers_daily_happy_path() -> None:
    content = (REPO_ROOT / "docs" / "operator-quickstart.md").read_text(
        encoding="utf-8"
    )

    for required_text in (
        "## 1. Install",
        "## 2. Configure An Optional Provider",
        "## 3. Start Chat",
        "## 4. Inspect The Dashboard",
        "## 5. Approve, Deny, Or Answer",
        "## 6. Verify Work",
        "uv run glassbox session chat --cwd .",
        "uv run glassbox provider diagnostics --cwd .",
        "uv run glassbox session approve SESSION_ID APPROVAL_ID",
        "uv run glassbox eval recommend PATH",
    ):
        assert required_text in content


def test_root_readme_prioritizes_v9_product_path_before_release_archive() -> None:
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "docs/v9-public-baseline.md" in root_readme
    assert "docs/operator-quickstart.md" in root_readme
    assert root_readme.index("docs/v9-public-baseline.md") < root_readme.index(
        "docs/v8-release-candidate.md"
    )


def test_public_operator_doc_links_resolve() -> None:
    doc_paths = (
        REPO_ROOT / "README.md",
        REPO_ROOT / "docs" / "README.md",
        REPO_ROOT / "docs" / "v9-public-baseline.md",
        REPO_ROOT / "docs" / "v9-vocabulary.md",
        REPO_ROOT / "docs" / "v9-command-surface-review.md",
        REPO_ROOT / "docs" / "dashboard-cockpit-contract.md",
        REPO_ROOT / "docs" / "operator-quickstart.md",
        REPO_ROOT / "docs" / "version-release-policy.md",
    )

    for doc_path in doc_paths:
        content = doc_path.read_text(encoding="utf-8")
        for link in MARKDOWN_LINK.findall(content):
            target = (doc_path.parent / link).resolve()
            assert target.exists(), f"{doc_path.relative_to(REPO_ROOT)} links to {link}"


def test_version_release_policy_covers_metadata_and_release_notes() -> None:
    content = (REPO_ROOT / "docs" / "version-release-policy.md").read_text(
        encoding="utf-8"
    )

    for required_text in (
        "Glassbox v9 uses package version `0.9.0`",
        "`pyproject.toml` is the packaging source",
        "`glassbox.__version__`",
        "glassbox --version",
        "v9.0.0-rc.N",
        "## Release Note Template",
        "Provider evidence: advisory",
    ):
        assert required_text in content
