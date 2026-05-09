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


def test_v11_confidence_adoption_contract_covers_scope_and_residual_risks() -> None:
    content = (REPO_ROOT / "docs" / "v11-confidence-adoption-contract.md").read_text(
        encoding="utf-8"
    )
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for required_text in (
        "## Scope",
        "## Non-Goals",
        "## Supported Workflow Set",
        "## Evidence Expectations",
        "## V10 Residual-Risk Mapping",
        "## Pass And Fail Policy",
        "`0.10.0`",
        "Large full-session compactions",
        "`glassbox eval recommend`",
        "live dashboard",
        "Provider canaries, live browser runs, and accessibility pairings",
        "blocking release authority",
        "Long-running work remains bounded local continuation",
        "tasks-v11.md",
    ):
        assert required_text in content

    assert "docs/v11-confidence-adoption-contract.md" in root_readme
    assert "v11-confidence-adoption-contract.md" in docs_readme


def test_v12_reviewable_change_contract_covers_product_boundary() -> None:
    content = (REPO_ROOT / "docs" / "v12-reviewable-change-contract.md").read_text(
        encoding="utf-8"
    )
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for required_text in (
        "## Scope",
        "## Product Model",
        "## Vocabulary",
        "## Supported Workflow Set",
        "## Evidence Expectations",
        "## Release Authority",
        "## Non-Goals",
        "## Safety Rules",
        "## Command And Dashboard Copy Guidelines",
        "changesets",
        "Change inventory",
        "review briefs",
        "verification readiness",
        "commit readiness",
        "Adopted candidate",
        "Residual risk",
        "Reviewer-safe evidence",
        "Local-only evidence",
        "A **git branch** is repository history.",
        "A **changeset** is reviewable local change evidence.",
        "worktree isolation",
        "branch-search candidate",
        "monorepo topology",
        "command evidence",
        "automatic commits",
        "automatic pushes",
        "automatic pull request creation",
        "automatic branch-search merging",
        "Deterministic replay, eval, package, migration, unit, integration",
        "Do not say Glassbox committed, staged, pushed, opened a PR, merged",
        "tasks-v12.md",
    ):
        assert required_text in content

    assert "docs/v12-reviewable-change-contract.md" in root_readme
    assert "v12-reviewable-change-contract.md" in docs_readme
    assert "docs/tasks-v12.md" in root_readme
    assert "tasks-v12.md" in docs_readme


def test_v13_review_loop_contract_covers_product_boundary() -> None:
    content = (REPO_ROOT / "docs" / "v13-review-loop-contract.md").read_text(
        encoding="utf-8"
    )
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for required_text in (
        "## Scope",
        "## Product Model",
        "## Vocabulary",
        "## Operator Language Boundaries",
        "## Supported Workflow Set",
        "## Evidence Expectations",
        "## Release Authority",
        "## Non-Goals",
        "## Safety Rules",
        "## Command And Dashboard Copy Guidelines",
        "Review feedback",
        "Requested change",
        "Reviewer question",
        "Fixup response",
        "Operator note",
        "Task checkpoint",
        "Changeset risk",
        "Verification evidence",
        "Manual evidence",
        "Browser evidence",
        "Accessibility evidence",
        "Lifecycle brief",
        "Handoff readiness",
        "Publication boundary",
        "Final operator action",
        "manual evidence",
        "browser, dashboard, and accessibility evidence",
        "UX consolidation happens late in v13 after feature dogfooding",
        "automatic review approval",
        "automatic staging",
        "automatic commits",
        "automatic pushes",
        "automatic pull request creation",
        "automatic branch-search merging",
        "Deterministic replay, eval, package, migration, unit, integration",
        "Review feedback is evidence, not approval.",
        "**Operator note** is local context.",
        "**Task checkpoint** is continuation evidence.",
        "**Changeset risk** is readiness evidence.",
        "**Verification evidence** comes from explicit retained checks.",
        "Do not say Glassbox approved, staged, committed, pushed, opened a PR",
        "tasks-v13.md",
    ):
        assert required_text in content

    assert "docs/v13-review-loop-contract.md" in root_readme
    assert "v13-review-loop-contract.md" in docs_readme
    assert "docs/tasks-v13.md" in root_readme
    assert "tasks-v13.md" in docs_readme


def test_v14_review_loop_maturity_contract_covers_product_boundary() -> None:
    content = (REPO_ROOT / "docs" / "v14-review-loop-maturity-contract.md").read_text(
        encoding="utf-8"
    )
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for required_text in (
        "## Scope",
        "## Vocabulary Deltas",
        "## Supported Workflow Set",
        "## Evidence Expectations",
        "## Advisory Evidence Boundaries",
        "## Release Authority",
        "## Safety Rules",
        "## V13 Dogfooding Mapping",
        "## Non-Goals",
        "Response-linked fixup inventory",
        "Skipped advisory evidence",
        "Summarized lifecycle limitations",
        "Fresh advisory UX evidence",
        "rich lifecycle limitations",
        "response-linked fixup inventory",
        "skipped advisory evidence",
        "Deterministic replay, eval, package, migration, unit, integration",
        "Review-loop guidance starts with safe inspection before any mutation.",
        "Do not say Glassbox approved, staged, committed, pushed, opened a PR",
        "v13-review-loop-contract.md",
        "v13-dogfooding-summary.md",
        "tasks-v14.md",
        "automatic review approval",
        "automatic staging",
        "automatic commits",
        "automatic pushes",
        "automatic pull request creation",
        "turning skipped browser or accessibility evidence into passing evidence",
    ):
        assert required_text in content

    assert "docs/v14-review-loop-maturity-contract.md" in root_readme
    assert "v14-review-loop-maturity-contract.md" in docs_readme
    assert "docs/tasks-v14.md" in root_readme
    assert "tasks-v14.md" in docs_readme


def test_v15_repository_intelligence_contract_covers_product_boundary() -> None:
    content = (
        REPO_ROOT / "docs" / "v15-repository-intelligence-contract.md"
    ).read_text(encoding="utf-8")

    for required_text in (
        "## Scope",
        "## Vocabulary",
        "## Supported Workflow Set",
        "## Repository Intelligence Sources",
        "## Memory-To-Repository Intelligence Rules",
        "## Evidence Expectations",
        "## Advisory Boundaries",
        "## Release Authority",
        "## Safety Rules",
        "## Mapping To Existing Contracts",
        "## Non-Goals",
        "repository index snapshots",
        "workspace topology snapshots",
        "eval metadata",
        "command recipes",
        "confirmed active workspace memory",
        "candidate-only, rejected, stale, invalidated, imported-unreviewed",
        "WorkspaceMemoryUsedInContext",
        "dependency manifests",
        "source roots, test roots, docs roots",
        "release-sensitive surfaces",
        "Repository intelligence is local, rebuildable, freshness-aware,",
        "provenance-backed, and advisory by default.",
        "Repository intelligence is advisory by default.",
        "Deterministic replay, eval, package, migration, unit, integration",
        "Memory-derived intelligence must come from confirmed active memory",
        "Prompt use must be bounded, source-labeled, inspectable, and",
        "v8-auditable-autonomy-contract.md",
        "repository-intelligence-index.md",
        "workspace-topology.md",
        "workspace-memory.md",
        "runtime-context.md",
        "hosted code search",
        "external vector-store authority",
        "provider-side hidden memory",
        "automatic owner assignment",
        "automatic commits",
        "automatic pushes",
        "automatic pull request creation",
        "hidden semantic indexing",
        "tasks-v15.md",
    ):
        assert required_text in content


def test_v15_repository_intelligence_audit_maps_current_surfaces() -> None:
    content = (REPO_ROOT / "docs" / "v15-repository-intelligence-audit.md").read_text(
        encoding="utf-8"
    )

    for required_text in (
        "## Summary",
        "## Classification Legend",
        "## Audit Entries",
        "## Signal Inventory",
        "## Test Inventory",
        "## Disposition",
        "Fix now",
        "Document only",
        "Accepted risk",
        "Not v15",
        "Repository Index Builder And Search",
        "Repository Index Freshness And Observability",
        "Workspace Topology",
        "Eval Recommendation Engine",
        "Topology-Derived Verification Recipes",
        "Workspace Memory",
        "Runtime Context And Prompt Use",
        "Changeset Topology And Review Surfaces",
        "CLI Commands",
        "Web API Routes And Types",
        "Dashboard Knowledge And Repository Surfaces",
        "Store And Projection Boundaries",
        "runtime/repository_index*",
        "runtime/workspace_topology.py",
        "runtime/eval_recommendation*",
        "runtime/workspace_memory*",
        "runtime/changeset_topology.py",
        "runtime/context_*",
        "store projections",
        "web routes",
        "frontend knowledge/repository surfaces",
        "Path-to-test",
        "Path-to-eval",
        "Recipe",
        "Topology",
        "Command",
        "Owner",
        "Package",
        "Dependency",
        "Generated path",
        "Policy-sensitive path",
        "Release-sensitive surface",
        "src/glassbox/runtime/repository_index.py:28",
        "src/glassbox/runtime/workspace_topology.py:198",
        "src/glassbox/runtime/eval_recommendation_engine.py:58",
        "src/glassbox/runtime/workspace_memory_capture.py:79",
        "src/glassbox/runtime/changeset_topology.py:35",
        "src/glassbox/runtime/context_builder.py:104",
        "src/glassbox/web/repository_index_routes.py:39",
        "frontend/components/console/knowledge-autonomy/repository.tsx:23",
        "no dedicated v15 repository intelligence console",
        "hosted repository indexing",
        "automatic owner assignment",
    ):
        assert required_text in content


def test_v15_repository_intelligence_docs_are_discoverable() -> None:
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for required_text in (
        "docs/v15-repository-intelligence-contract.md",
        "docs/v15-repository-intelligence-audit.md",
        "docs/tasks-v15.md",
        "v15 planning track is",
        "repository intelligence v2",
    ):
        assert required_text in root_readme

    for required_text in (
        "v15-repository-intelligence-contract.md",
        "v15-repository-intelligence-audit.md",
        "tasks-v15.md",
        "path-to-verification-recommendations.md",
        "## Repository Intelligence Map",
        "repository-intelligence-index.md",
        "workspace-topology.md",
        "workspace-memory.md",
        "replay-evals.md",
        "command-evidence.md",
        "changeset-verification-readiness.md",
        "command recipes remain recommendations, not",
        "planned repository intelligence console",
        "task graph are the active planning",
    ):
        assert required_text in docs_readme


def test_v15_path_to_verification_contract_covers_recommendation_boundary() -> None:
    content = (
        REPO_ROOT / "docs" / "path-to-verification-recommendations.md"
    ).read_text(encoding="utf-8")
    replay_evals = (REPO_ROOT / "docs" / "replay-evals.md").read_text(encoding="utf-8")

    for required_text in (
        "## Inputs",
        "## Output Model",
        "## Evidence Classes",
        "## Confidence",
        "## Freshness And Stale Evidence",
        "## Non-Claims",
        "PathVerificationRecommendationReport",
        "PathVerificationImpact",
        "EvalTestTargetRecommendation",
        "source metadata",
        "profile budget implications",
        "PathVerificationTarget",
        "PathVerificationCommandRecipeTarget",
        "PathVerificationEvalCaseTarget",
        "PathVerificationEvalProfileTarget",
        "PathVerificationSkippedCheck",
        "PathVerificationStaleEvidence",
        "PathVerificationProvenance",
        "deterministic-executable",
        "advisory-command",
        "live-provider-canary",
        "browser-evidence",
        "accessibility-evidence",
        "manual-evidence",
        "fresh",
        "stale",
        "missing",
        "degraded",
        "unknown",
        "Repository intelligence snapshots",
        "workspace topology snapshots",
        "eval metadata",
        "confirmed active workspace memory",
        "command recipes are approved to execute",
        "## Test Target Discovery",
        "test targets separately from advisory command",
        "generated paths warn operators",
        "packages with no discovered test roots",
        "## Eval Scope Enrichment",
        "repository intelligence as an advisory enrichment layer",
        "Stale snapshots keep their provenance",
        "VerificationDriftAssessment.stale_evidence",
        "`.glassbox` artifact churn is ignored",
        "Changeset verification previews expose the same guidance",
        "raw command output",
    ):
        assert required_text in content

    assert "path-to-verification-recommendations.md" in replay_evals


def test_workspace_memory_documents_repository_intelligence_integration() -> None:
    content = (REPO_ROOT / "docs" / "workspace-memory.md").read_text(encoding="utf-8")

    for required_text in (
        "## Repository Intelligence Integration",
        "Confirmed active entries can enrich repository-intelligence snapshots",
        "verified commands and command recipes",
        "generated candidates that have not been confirmed",
        "rejected candidates",
        "stale, invalidated, or pruned entries",
        "imported entries that have not passed the local review posture",
        "`repository_intelligence`",
        "stable command recipes, package conventions, generated-output conventions",
        "snapshot `memory_references`",
        "Memory-derived intelligence does not override stronger deterministic source",
        "WorkspaceMemoryUsedInContext",
        "automatic memory capture",
        "cross-repository memory sync",
        "release authority",
    ):
        assert required_text in content


def test_repository_index_documents_memory_reference_snapshots() -> None:
    content = (REPO_ROOT / "docs" / "repository-intelligence-index.md").read_text(
        encoding="utf-8"
    )

    for required_text in (
        "`memory_references`",
        "confirmed active workspace memory IDs",
        "Stale, invalidated, imported-unreviewed, rejected, pruned, and",
        "Memory references remain",
        "snapshot must cite the memory ID",
    ):
        assert required_text in content


def test_v14_review_loop_maturity_audit_maps_dogfooding_followups() -> None:
    content = (REPO_ROOT / "docs" / "v14-review-loop-maturity-audit.md").read_text(
        encoding="utf-8"
    )
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for required_text in (
        "## Summary",
        "## Classification Legend",
        "## Audit Entries",
        "## Accepted Non-Goals",
        "## Test Inventory",
        "## Disposition",
        "Fix now",
        "Document only",
        "Accepted risk",
        "Not v14",
        "Lifecycle Brief Limitation Handling",
        "Response-Linked Fixup Inventory Paths",
        "Skipped Browser And Dashboard Evidence",
        "Skipped Accessibility Evidence",
        "Command Discovery And In-Session Guidance",
        "Dashboard Review-Loop Surfaces",
        "Release-Gate Advisory Evidence Posture",
        "Stale Dogfooding Provider Prefixes",
        "Fresh Browser And Accessibility Evidence",
        "src/glassbox/runtime/changeset_review_brief_sections.py:716",
        "src/glassbox/runtime/review_fixup_actions.py:44",
        "src/glassbox/cli/parser_changeset_evidence.py:103",
        "scripts/v13_release_gate_helpers.py:168",
        "GBX-1410",
        "GBX-1420",
        "GBX-1430",
        "GBX-1440",
        "GBX-1450",
        "GBX-1460",
        "No audited finding requires hosted review",
    ):
        assert required_text in content

    assert "docs/v14-review-loop-maturity-audit.md" in root_readme
    assert "v14-review-loop-maturity-audit.md" in docs_readme


def test_v14_review_loop_vocabulary_copy_stays_bounded() -> None:
    command_guide = (
        REPO_ROOT / "src" / "glassbox" / "cli" / "command_guide_review.py"
    ).read_text(encoding="utf-8")
    review_responses = (REPO_ROOT / "docs" / "review-responses.md").read_text(
        encoding="utf-8"
    )
    browser_accessibility = (
        REPO_ROOT / "docs" / "browser-accessibility-evidence.md"
    ).read_text(encoding="utf-8")
    daily_workflow = (REPO_ROOT / "docs" / "daily-workflow-quickstart.md").read_text(
        encoding="utf-8"
    )

    for required_text in (
        "response-linked fixup inventory posture",
        "non-approval claims before",
        "recording fixup evidence",
        "Record local response text; attach response-linked fixup",
        "inventory separately before treating the response as ready",
        "Record an explicit skipped dashboard case",
        "viewport or calling it a pass",
    ):
        assert required_text in command_guide

    assert "## Response-Linked Fixup Inventory Rules" in review_responses
    assert "## GBX-1420 Operator UX Contract" in review_responses
    assert "### CLI Contract" in review_responses
    assert "glassbox changeset feedback fixup FEEDBACK_ID --from-workspace --cwd ." in (
        review_responses
    )
    assert "### GBX-1440 Happy Path" in review_responses
    assert "glassbox changeset refresh CHANGESET_ID --cwd ." in review_responses
    assert "neither records reviewer approval" in review_responses
    assert "--all-eligible" in review_responses
    assert "### API, TUI, And Dashboard Contract" in review_responses
    assert "POST /changesets/feedback/{feedback_id}/fixup" in review_responses
    assert "### Error And Safe-Next-Action Language" in review_responses
    assert "workspace diff source digest changed since fixup inventory" in (
        review_responses
    )
    assert "was recorded" in review_responses
    assert "fixup inventory has no path records matching feedback" in review_responses
    assert "scope" in review_responses
    assert "local evidence" in review_responses
    assert "approval or acceptance" in review_responses
    assert "## Skipped Advisory Evidence" in browser_accessibility
    assert "invent a live browser pass" in browser_accessibility
    assert "## Review A Local Change" in daily_workflow
    assert "review-loop maturity" in daily_workflow
    assert "glassbox changeset create --from workspace-diff" in daily_workflow
    assert "feedback fixup FEEDBACK_ID --from-workspace" in daily_workflow
    assert "not review approval" in daily_workflow
    assert "rather than passed" in daily_workflow


def test_review_briefs_document_rich_evidence_overflow_contract() -> None:
    content = (REPO_ROOT / "docs" / "review-briefs.md").read_text(encoding="utf-8")

    for required_text in (
        "## Rich-Evidence Limitation Overflow",
        "`GBX-1410` characterized the v13/v14-start failure mode",
        "more than 20 retained",
        "`GBX-1411` replaces that brittle behavior",
        "`GBX-1412` exposes that compression",
        "`limitation_summary`",
        "dashboard action copy",
        "review export payloads",
        "deduplicate repeated limitations",
        "keep high-severity blockers visible",
        "add an overflow summary",
        "ordering deterministic",
        "brief artifact",
    ):
        assert required_text in content


def test_v13_review_loop_audit_covers_current_boundaries() -> None:
    content = (REPO_ROOT / "docs" / "v13-review-loop-audit.md").read_text(
        encoding="utf-8"
    )
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for required_text in (
        "## Summary",
        "## Classification Legend",
        "## Audit Entries",
        "## Test Inventory",
        "## Disposition",
        "Fixed in v13",
        "Evidence-only in v13",
        "Accepted non-goal",
        "Carried-forward risk",
        "Changeset creation",
        "Review briefs",
        "Verification readiness",
        "Commit preparation",
        "Manual command evidence",
        "Branch-candidate adoption",
        "Topology recommendations",
        "Dashboard review",
        "TUI slash commands",
        "Exports",
        "src/glassbox/core/events.py",
        "src/glassbox/runtime/review_briefs.py",
        "src/glassbox/runtime/changeset_verification_readiness.py",
        "src/glassbox/runtime/commit_readiness.py",
        "src/glassbox/runtime/command_evidence.py",
        "frontend/components/console/changeset-console.tsx",
        "Manual evidence must be labeled manual or external",
        "Automatic merge remains an **accepted non-goal**.",
        "impact-rule coverage remains a carried-forward risk",
        "No product-code change is required by this audit.",
    ):
        assert required_text in content

    assert "v13-review-loop-audit.md" in docs_readme


def test_v13_review_loop_ux_audit_chooses_review_command_shape() -> None:
    content = (REPO_ROOT / "docs" / "v13-review-loop-ux-audit.md").read_text(
        encoding="utf-8"
    )
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for required_text in (
        "## Summary",
        "## Evidence Sources",
        "## Surface Findings",
        "## Command Vocabulary Decision",
        "## Build Order",
        "## Non-Goals",
        "## GBX-1381 Target",
        "Use `/review` as the primary slash command.",
        "`/changeset` should remain a compatibility alias",
        "Review: Create Changeset",
        "Review: Generate Lifecycle Brief",
        "Review: Preview Verification",
        "Review: Inspect Handoff",
        "src/glassbox/cli/tui/commands.py",
        "src/glassbox/cli/interactive_session.py",
        "frontend/components/console/changeset-console.tsx",
        "auto-run verification commands",
        "auto-stage files",
        "auto-commit",
        "auto-push",
        "auto-open pull requests",
        "auto-merge branches",
        "imply reviewer approval",
        "current-session defaulting for changeset creation",
    ):
        assert required_text in content

    assert "docs/v13-review-loop-ux-audit.md" in root_readme
    assert "v13-review-loop-ux-audit.md" in docs_readme


def test_v13_review_brief_lifecycle_contract_covers_non_claims() -> None:
    content = (REPO_ROOT / "docs" / "review-briefs.md").read_text(encoding="utf-8")

    for required_text in (
        "v13 lifecycle briefs",
        "`schema_version`: `2`",
        "## Lifecycle Brief Contract",
        "## Render Targets",
        "lifecycle summary",
        "review feedback",
        "review responses",
        "manual evidence",
        "live review evidence",
        "stale verification",
        "publication boundary",
        "`feedback`",
        "`response`",
        "`manual_evidence`",
        "`browser_evidence`",
        "`dashboard_evidence`",
        "`accessibility_evidence`",
        "`publication_boundary`",
        "Passing verification does not hide unresolved feedback",
        "does not imply the reviewer accepted it",
        "review feedback was approved or accepted by a reviewer",
        "manual evidence is retained command/tool evidence",
        "lifecycle handoff readiness means publication occurred",
        "a commit, push, PR, or merge should happen automatically",
    ):
        assert required_text in content


def test_publication_boundary_contract_covers_final_action_boundary() -> None:
    content = (REPO_ROOT / "docs" / "publication-boundary.md").read_text(
        encoding="utf-8"
    )
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for required_text in (
        "## Scope",
        "## States",
        "## Relationship To Commit Readiness",
        "## Safe Next-Action Policy",
        "## Non-Goals",
        "## Non-Claims",
        "`not-ready`",
        "`needs-review-response`",
        "`needs-verification`",
        "`stale-inventory`",
        "`unresolved-risk`",
        "`handoff-ready`",
        "`commit-prep-ready`",
        "`publication-blocked`",
        "`accepted-with-risk`",
        "Handoff readiness can be blocked by unresolved feedback",
        "Guidance must start with inspection before mutation",
        "automatic staging",
        "automatic committing",
        "automatic pushing",
        "automatic pull request creation",
        "automatic merging",
        "automatic deployment",
        "automatic package publishing",
        "No state means a",
        "pull request, merge, deploy, package upload",
        "release publication happened",
    ):
        assert required_text in content

    assert "docs/publication-boundary.md" in root_readme
    assert "publication-boundary.md" in docs_readme


def test_manual_evidence_contract_covers_attachment_boundaries() -> None:
    content = (REPO_ROOT / "docs" / "manual-evidence.md").read_text(encoding="utf-8")
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for required_text in (
        "## Evidence Kinds",
        "`manual_command`",
        "`external_check`",
        "`reviewer_note`",
        "`screenshot`",
        "`browser_observation`",
        "`accessibility_note`",
        "`local_file_reference`",
        "`sanitized_log`",
        "`operator_assertion`",
        "## Attachment Targets",
        "## Required Fields",
        "## Redaction And Size Rules",
        "## Freshness Rules",
        "## Manual Evidence Versus Command Evidence",
        "## Reviewer-Safe Language",
        "## Redaction Fixture Plan",
        "## Non-Claims",
        "Manual evidence is not verification proof by itself",
        "source label",
        "local-only posture",
        "Do not backfill manual command summaries as retained command evidence",
        "Glassbox ran the command",
        "files were staged, committed, pushed, published, merged, or deployed",
    ):
        assert required_text in content

    assert "docs/manual-evidence.md" in root_readme
    assert "manual-evidence.md" in docs_readme


def test_browser_accessibility_evidence_protocol_bounds_live_claims() -> None:
    content = (REPO_ROOT / "docs" / "browser-accessibility-evidence.md").read_text(
        encoding="utf-8"
    )
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for required_text in (
        "# Browser, Dashboard, And Accessibility Evidence Protocol",
        "## Evidence Kinds",
        "`live_dashboard_walkthrough`",
        "`browser_check`",
        "`screenshot_evidence`",
        "`keyboard_navigation_note`",
        "`responsive_layout_observation`",
        "`accessibility_pairing`",
        "## Required Fields",
        "environment",
        "viewport width and height",
        "date and observation time",
        "skipped cases",
        "limitations",
        "non-claims",
        "## Live Dashboard Walkthrough Protocol",
        "## Browser Check Protocol",
        "## Screenshot Evidence Protocol",
        "## Keyboard Navigation Protocol",
        "## Responsive Layout Protocol",
        "## Accessibility Pairing Protocol",
        "## Advisory Versus Blocking Policy",
        "## Naming And Retention",
        ".glassbox/evidence/<changeset-id>/browser/",
        ".glassbox/evidence/<changeset-id>/dashboard/",
        ".glassbox/evidence/<changeset-id>/accessibility/",
        "## Reviewer-Safe Language",
        "## Non-Claims",
        "Live review evidence is not deterministic release authority",
        "not accessibility certification",
        "advisory by default",
        "deterministic fixture-backed check",
        "must not override failed, missing, or stale deterministic checks",
        "the application is WCAG compliant",
        "files were staged, committed, pushed, published, merged, or deployed",
    ):
        assert required_text in content

    assert "docs/browser-accessibility-evidence.md" in root_readme
    assert "browser-accessibility-evidence.md" in docs_readme


def test_v14_advisory_review_evidence_protocol_is_repeatable() -> None:
    content = (REPO_ROOT / "docs" / "v14-advisory-review-evidence.md").read_text(
        encoding="utf-8"
    )
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for required_text in (
        "# V14 Advisory Review Evidence Protocol",
        "## Scope",
        "## Retained Evidence Location",
        ".glassbox/releases/v14-advisory-review-evidence/",
        "## Scenario List",
        "Dashboard changeset detail",
        "Feedback status",
        "Skipped evidence display",
        "Fixup inventory action state",
        "Handoff readiness",
        "## Browser Evidence Fields",
        "viewport width, height, and orientation",
        "console status",
        "## Accessibility Pairing Fields",
        "keyboard path checked",
        "screen-reader certified",
        "## Manual Run Steps",
        "The protocol can be run manually even if Playwright is unavailable.",
        "## Skipped-Case Template",
        "Capture state: not_run | not_applicable",
        "## Non-Claim Template",
        "skipped browser, dashboard, or accessibility evidence is not a pass",
        "response-linked fixup inventory is not reviewer approval",
        "Glassbox did not stage, commit, push, open a PR, merge, deploy, or publish",
        "## Summary Shape",
        "## Release Boundary",
        "does not become a release gate",
        "fixture-backed contract and pass/fail policy",
    ):
        assert required_text in content

    assert "docs/v14-advisory-review-evidence.md" in root_readme
    assert "v14-advisory-review-evidence.md" in docs_readme


def test_v14_advisory_dashboard_evidence_summary_is_bounded() -> None:
    content = (REPO_ROOT / "docs" / "v14-advisory-dashboard-evidence.md").read_text(
        encoding="utf-8"
    )
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for required_text in (
        "# V14 Advisory Dashboard Evidence Summary",
        "GBX-1451",
        ".glassbox/releases/v14-advisory-review-evidence/browser/",
        "## Observed Coverage",
        "Dashboard changeset detail",
        "Feedback status",
        "Skipped evidence display",
        "Fixup inventory action state",
        "Handoff readiness",
        "## Browser Evidence",
        "/app/changesets/changeset-1",
        "local static server for the production frontend build",
        "Chromium through Playwright",
        "Viewport: 1440x900 landscape",
        "Console status: checked, no browser console errors or page errors observed",
        "## Skipped Coverage",
        "Mobile dashboard viewport",
        "Accessibility pairing",
        "Live backend dogfooding changeset attachment",
        "## Findings",
        "EMFILE",
        "## Non-Claims",
        "advisory evidence is not deterministic release authority",
        "skipped browser, dashboard, or accessibility evidence is not a pass",
        "response-linked fixup inventory is not reviewer approval",
        "Glassbox did not stage, commit, push, open a PR, merge, deploy, or publish",
    ):
        assert required_text in content

    assert "docs/v14-advisory-dashboard-evidence.md" in root_readme
    assert "v14-advisory-dashboard-evidence.md" in docs_readme


def test_v14_advisory_accessibility_evidence_summary_is_bounded() -> None:
    content = (REPO_ROOT / "docs" / "v14-advisory-accessibility-evidence.md").read_text(
        encoding="utf-8"
    )
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for required_text in (
        "# V14 Advisory Accessibility Evidence Summary",
        "GBX-1452",
        ".glassbox/releases/v14-advisory-review-evidence/accessibility/",
        "## Observed Coverage",
        "Keyboard path",
        "Focus affordance",
        "Responsive layout",
        "Advisory copy",
        "## Accessibility Evidence Fields",
        "/app/changesets/changeset-1",
        "local static server for the production frontend build",
        "Chromium through Playwright",
        "1440x900 landscape and 390x844 portrait",
        "Keyboard path checked",
        "Focus-visible observation",
        "Console status: checked, no browser console errors or page errors observed",
        "## Skipped Coverage",
        "Screen-reader pairing",
        "Automated contrast tooling",
        "Complete tab-order audit",
        "Live backend dogfooding changeset attachment",
        "## Findings",
        "## Non-Claims",
        "accessibility evidence is not certification or WCAG conformance",
        "no screen-reader behavior was certified",
        "automated contrast tooling was not run",
        "this pass is not a complete tab-order audit",
        "advisory evidence is not deterministic release authority",
        "Glassbox did not stage, commit, push, open a PR, merge, deploy, or publish",
    ):
        assert required_text in content

    assert "docs/v14-advisory-accessibility-evidence.md" in root_readme
    assert "v14-advisory-accessibility-evidence.md" in docs_readme


def test_v12_change_lifecycle_audit_covers_current_boundaries() -> None:
    content = (REPO_ROOT / "docs" / "v12-change-lifecycle-audit.md").read_text(
        encoding="utf-8"
    )
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for required_text in (
        "## Summary",
        "## Classification Legend",
        "## Audit Entries",
        "## Test Inventory",
        "## Disposition",
        "Workspace diff summary",
        "Git status",
        "Branch search",
        "Task checkpoints",
        "Verification recommendations and ledger",
        "Handoff summaries",
        "Tool output artifacts",
        "Command execution and policy",
        "Dashboard review surfaces",
        "Export and redaction",
        "Fixed in v12",
        "Evidence-only in v12",
        "Accepted non-goal",
        "src/glassbox/tools/workflow.py#L253",
        "src/glassbox/runtime/session_export_package.py#L88",
        "tests/integration/test_workflow_tools.py#L84",
        "No product-code change is required by this audit.",
    ):
        assert required_text in content

    assert "v12-change-lifecycle-audit.md" in docs_readme


def test_v12_release_gate_documents_reviewable_change_evidence() -> None:
    content = (REPO_ROOT / "docs" / "v12-release-gate.md").read_text(encoding="utf-8")
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for required_text in (
        "## Automated Stages",
        "## Evidence Summary",
        "## Pass And Fail Policy",
        "scripts/validate_v12_release_gate.py",
        "v12 deterministic eval release report",
        "v12 reviewable-change release profile",
        "v12 changeset lifecycle smoke",
        "v12 eval coverage audit",
        "changeset.reviewable-lifecycle",
        "changeset.branch-candidate-adoption",
        "package contents",
        "installed-wheel smoke",
        "advisory",
        "summary.json",
        "live pull request creation",
    ):
        assert required_text in content

    assert "docs/v12-release-gate.md" in root_readme
    assert "v12-release-gate.md" in docs_readme


def test_v13_release_gate_documents_review_loop_evidence() -> None:
    content = (REPO_ROOT / "docs" / "v13-release-gate.md").read_text(encoding="utf-8")
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for required_text in (
        "## Automated Stages",
        "## Evidence Summary",
        "## Pass And Fail Policy",
        "scripts/validate_v13_release_gate.py",
        "v13 deterministic eval release report",
        "v13 review-loop release profile",
        "v13 review-loop eval smoke",
        "v13 review-loop command coverage",
        "v13 eval coverage audit",
        "changeset.review-loop-lifecycle",
        "changeset.in-session-review-ux",
        "package contents",
        "installed-wheel smoke",
        "advisory browser evidence",
        "advisory accessibility evidence",
        "summary.json",
        "live pull request creation",
    ):
        assert required_text in content

    assert "docs/v13-release-gate.md" in root_readme
    assert "v13-release-gate.md" in docs_readme


def test_v13_dogfooding_summary_records_review_loop_passes() -> None:
    content = (REPO_ROOT / "docs" / "v13-dogfooding-summary.md").read_text(
        encoding="utf-8"
    )
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for required_text in (
        "## Passes",
        "## Findings",
        "## Disposition",
        ".glassbox/releases/gbx-1392-dogfooding/",
        "Dogfooding session seed",
        "Review feedback creation",
        "Manual evidence redaction",
        "Dashboard advisory evidence",
        "Accessibility advisory evidence",
        "Lifecycle brief generation",
        "Handoff readiness",
        "Feedback response",
        "Docs-only validation",
        "dogfood:local",
        "absolute-path",
        "response-linked fixup inventory",
        "artifact schema cap of 20 items",
        "no staging, commit, push, pull request, merge, deploy, or publication",
    ):
        assert required_text in content

    assert "docs/v13-dogfooding-summary.md" in root_readme
    assert "v13-dogfooding-summary.md" in docs_readme


def test_v14_dogfooding_summary_records_maturity_passes() -> None:
    content = (REPO_ROOT / "docs" / "v14-dogfooding-summary.md").read_text(
        encoding="utf-8"
    )
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for required_text in (
        "## Passes",
        "## Findings",
        "## Disposition",
        ".glassbox/releases/gbx-1462-v14-dogfooding/",
        "Command discovery with runtime flags",
        "Command discovery supported shape",
        "Changeset create without session",
        "Response-linked fixup inventory",
        "Skipped dashboard evidence",
        "Skipped browser evidence",
        "Skipped accessibility evidence",
        "Lifecycle brief generation",
        "Verification preview",
        "Handoff readiness",
        "rich-evidence limitations summarized",
        "14 additional retained limitation(s)",
        "--from-workspace",
        "--session is required for --from workspace-diff",
        "skipped accessibility evidence",
        "no review approval, staging, commit, push, pull request, merge",
        "GBX-1451",
        "GBX-1452",
    ):
        assert required_text in content

    assert "docs/v14-dogfooding-summary.md" in root_readme
    assert "v14-dogfooding-summary.md" in docs_readme


def test_v14_release_candidate_guide_covers_maturity_model() -> None:
    content = (REPO_ROOT / "docs" / "v14-release-candidate.md").read_text(
        encoding="utf-8"
    )
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for required_text in (
        "## Release Posture",
        "## Supported Operating Model",
        "## Current Evidence Summary",
        "## Known Residual Risks",
        "## Release Decision",
        "Decision: GO for v14 release candidate publication.",
        ".glassbox/releases/gbx-1463-v14-release-candidate/",
        ".glassbox/evals/gbx-1463-v14-release-candidate/",
        ".glassbox/releases/gbx-1462-v14-dogfooding/",
        ".glassbox/releases/v14-advisory-review-evidence/",
        "91\n  passing blocking stages",
        "| Automated v14 gate | passed |",
        "| Package and installed smoke | passed |",
        "25 selected",
        "changeset.lifecycle-rich-evidence",
        "changeset.response-linked-fixup-inventory",
        "changeset.skipped-advisory-evidence-posture",
        "68 planned blocking stages",
        "response-linked fixup inventory",
        "skipped advisory evidence",
        "rich lifecycle briefs",
        "20-item artifact cap",
        "command-discovery friction",
        "GBX-1451",
        "GBX-1452",
        "0.10.0",
        "automatic pull request creation",
        "No deterministic blocker remains open",
    ):
        assert required_text in content

    assert "docs/v14-release-candidate.md" in root_readme
    assert "v14-release-candidate.md" in docs_readme


def test_v13_release_candidate_guide_covers_review_loop_model() -> None:
    content = (REPO_ROOT / "docs" / "v13-release-candidate.md").read_text(
        encoding="utf-8"
    )
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for required_text in (
        "## Release Posture",
        "## Supported Operating Model",
        "## Current Evidence Summary",
        "## Known Residual Risks",
        "## Release Decision",
        "Decision: GO for v13 release candidate publication.",
        ".glassbox/releases/gbx-1393-v13-release-candidate/",
        ".glassbox/evals/gbx-1393-v13-release-candidate/",
        ".glassbox/releases/gbx-1392-dogfooding/",
        "85 blocking",
        "three advisory evidence items were explicitly skipped",
        "changeset.review-loop-lifecycle",
        "changeset.in-session-review-ux",
        "39/39 capabilities covered",
        "22/22",
        "response-linked fixup inventory",
        "20-item limitation cap",
        "manual evidence",
        "browser/dashboard evidence",
        "accessibility evidence",
        "No deterministic blocker remains open",
        "automatic pull request creation",
    ):
        assert required_text in content

    assert "docs/v13-release-candidate.md" in root_readme
    assert "v13-release-candidate.md" in docs_readme


def test_v12_dogfooding_summary_records_real_reviewable_change_passes() -> None:
    content = (REPO_ROOT / "docs" / "v12-dogfooding-summary.md").read_text(
        encoding="utf-8"
    )
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for required_text in (
        "## Passes",
        "## Findings",
        "## Disposition",
        ".glassbox/releases/gbx-1292-dogfooding/",
        "Changeset from real workspace diff",
        "Review brief for local change",
        "Commit preparation with stale or missing verification",
        "Branch-candidate adoption into changeset",
        "Topology-aware recommendations for mixed change",
        "changeset refresh",
        "changeset brief",
        "changeset verification-plan",
        "changeset commit-prep",
        "dirty_untracked_risk",
        "src/glassbox/runtime/changesets.py",
        "no retained command",
        "no merge, commit, push",
    ):
        assert required_text in content

    assert "docs/v12-dogfooding-summary.md" in root_readme
    assert "v12-dogfooding-summary.md" in docs_readme


def test_v12_release_candidate_guide_covers_supported_reviewable_change_model() -> None:
    content = (REPO_ROOT / "docs" / "v12-release-candidate.md").read_text(
        encoding="utf-8"
    )
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for required_text in (
        "## Release Posture",
        "## Supported Operating Model",
        "## Primary Operator Flows",
        "## Release-Readiness Checklist",
        "## Current Evidence Summary",
        "## Known Residual Risks",
        "## Deliberate Non-Goals",
        "## Release Decision",
        "Decision: GO for v12 release candidate publication.",
        "scripts/validate_v12_release_gate.py",
        ".glassbox/releases/gbx-1293-v12-release-candidate/",
        ".glassbox/evals/gbx-1293-v12-release-candidate/",
        "changeset.reviewable-lifecycle",
        "changeset.branch-candidate-adoption",
        "80",
        "advisory provider evidence",
        "hosted code review",
        "automatic pull request creation",
        "src/glassbox/runtime/changesets.py",
        "v12-dogfooding-summary.md",
        "command-evidence.md",
    ):
        assert required_text in content

    assert "docs/v12-release-candidate.md" in root_readme
    assert "v12-release-candidate.md" in docs_readme


def test_v12_worktree_isolation_contract_covers_safety_boundary() -> None:
    content = (REPO_ROOT / "docs" / "worktree-isolation.md").read_text(encoding="utf-8")
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    branch_search = (REPO_ROOT / "docs" / "branch-search.md").read_text(
        encoding="utf-8"
    )

    for required_text in (
        "## Scope",
        "## Worktree Custody Model",
        "## Naming",
        "## Creation Rules",
        "## Cleanup Rules",
        "## Candidate Adoption Boundary",
        "## Reviewer And Export Posture",
        "## Git Fixture Design Notes",
        "temporary local git worktrees",
        "candidate branch name",
        "cleanup confirmation",
        "custody evidence",
        "automatic merge, rebase, cherry-pick",
        "automatic staging, committing, pushing",
        "remote or multi-user locking",
        "explicit destructive confirmation",
        "git worktree list --porcelain",
        "source changeset or branch-search candidate",
        "worktree paths as local-only evidence",
    ):
        assert required_text in content

    assert "worktree-isolation.md" in docs_readme
    assert "worktree-isolation.md" in branch_search


def test_v11_residual_risk_audit_covers_current_source_and_evidence() -> None:
    content = (REPO_ROOT / "docs" / "v11-residual-risk-audit.md").read_text(
        encoding="utf-8"
    )
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for required_text in (
        "## Summary",
        "## Detailed Audit",
        "### Compaction Cap Handling",
        "### Historical Checkpoint Absence",
        "### Release-Path Recommendation Gap",
        "### Live Cockpit Evidence",
        "### Accessibility Evidence",
        "### Provider Matrix Partialness",
        "### Bounded Autonomy Non-Goals",
        "### Broad Command-Surface Friction",
        "Fixed in v11",
        "Evidence-only in v11",
        "Accepted non-goal",
        "src/glassbox/runtime/context_compaction.py:83",
        "src/glassbox/runtime/session_query_service.py:140",
        "evals/impact.json:253",
        "frontend/tests/task-autonomy-console.test.tsx:93",
        "src/glassbox/runtime/provider_canary_scenarios.py:5",
        "tests/integration/test_cli_eval_commands.py:642",
    ):
        assert required_text in content

    assert "v11-residual-risk-audit.md" in docs_readme


def test_v11_live_cockpit_evidence_protocol_covers_scenarios_and_non_claims() -> None:
    content = (REPO_ROOT / "docs" / "live-cockpit-evidence-v11.md").read_text(
        encoding="utf-8"
    )
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for required_text in (
        "## Purpose",
        "## Evidence Directory Convention",
        ".glassbox/releases/YYYYMMDDTHHMMSSZ-v11-live-cockpit/",
        "## Scenario Matrix",
        "Active turn",
        "Pending approval",
        "Pending question",
        "Stale tool attempt",
        "Stale verification",
        "Compaction freshness",
        "Provider warning",
        "Daemon interruption",
        "Stream reconnect",
        "Historical snapshot",
        "## Automated Evidence",
        "## Manual Evidence",
        "## Non-Claims",
        "formal accessibility certification",
        "provider reliability or provider release authority",
        "deterministic cockpit evidence",
        "## Release Summary Template",
        "## GBX-1131 Evidence Summary",
        ".glassbox/releases/gbx-1131-live-cockpit/",
        "Stream degradation and reconnect",
        "duplicate React key warning",
        "v11-confidence-adoption-contract.md",
        "long-run-cockpit-contract.md",
    ):
        assert required_text in content

    assert "live-cockpit-evidence-v11.md" in docs_readme


def test_v11_accessibility_review_records_named_pairings_and_non_claims() -> None:
    content = (REPO_ROOT / "docs" / "accessibility-review-v11.md").read_text(
        encoding="utf-8"
    )
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for required_text in (
        "## Environment",
        "## Named Pairings",
        "Terminal keyboard pairing",
        "Terminal plain-mode pairing",
        "Dashboard keyboard pairing",
        "macOS VoiceOver",
        "Not executed",
        "54 passed",
        "5 passed",
        "4 passed",
        "## Supported Claims",
        "## Non-Claims And Follow-Ups",
        "not formal WCAG, VPAT, or screen-reader certification",
        "live-cockpit-evidence-v11.md",
        "terminal-accessibility-review-v7.md",
        "dashboard-accessibility-review-v8.md",
    ):
        assert required_text in content

    assert "accessibility-review-v11.md" in docs_readme


def test_v11_dashboard_performance_doc_records_large_session_measurement() -> None:
    content = (REPO_ROOT / "docs" / "dashboard-performance-v11.md").read_text(
        encoding="utf-8"
    )
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for required_text in (
        "## Scope",
        "## Measurement Summary",
        "54 passed",
        "2 passed",
        "## Coverage Map",
        "Aggregate load",
        "Selected-session load",
        "SSE reducer cost",
        "Long timeline rendering",
        "Detail-page pagination",
        "Browser long-session route",
        "No blocking large-session dashboard performance issue",
        "GBX-1131",
        "long-run-cockpit-contract.md",
    ):
        assert required_text in content

    assert "dashboard-performance-v11.md" in docs_readme


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


def test_v10_refactor_docs_describe_final_module_shape() -> None:
    architecture = (REPO_ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    boundaries = (REPO_ROOT / "docs" / "refactor-boundaries.md").read_text(
        encoding="utf-8"
    )
    roadmap = (REPO_ROOT / "docs" / "refactor-v10.md").read_text(encoding="utf-8")

    for required_text in (
        "### V10 Second-Order Ownership",
        "provider_canary_*.py",
        "provider_recommendation_*.py",
        "task_query_*.py",
        "policy_*.py",
        "sqlite_schema_*.py",
        "session_route_*.py",
        "task_route_*.py",
        "session_api_*.py",
        "task-autonomy/",
        "workspace-console/",
        "*-analysis.ts",
    ):
        assert required_text in architecture

    for required_text in (
        "The v10 second-order boundary map is implemented through Phase 64",
        "### V10 Accepted Compatibility Shims",
        "compatibility facade over queue, inspector, action, evidence",
        "FastAPI declaration surfaces over HTTP-local query/action helpers",
        "`web/session_api.py`: response-model compatibility facade",
        "`tools/policy.py`: policy-engine public facade",
        "`core/events.py`, `core/models.py`, and `core/__init__.py`",
        "focused `task_query_*` modules",
        "focused `sqlite_schema_*` modules",
    ):
        assert required_text in boundaries

    assert "GBX-R350: Update Architecture Docs For The V10 Refactor Shape" in roadmap
    assert (
        "GBX-R351: Close Out V10 Refactor Guardrails And Focused Validation" in roadmap
    )
    assert "Accepted compatibility shims and intended owners are listed" in roadmap
    assert "pnpm --dir frontend typecheck" in roadmap
    assert "pnpm --dir frontend lint" in roadmap
    assert "pnpm --dir frontend test" in roadmap


def test_v11_refactor_docs_describe_final_module_shape() -> None:
    architecture = (REPO_ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    boundaries = (REPO_ROOT / "docs" / "refactor-boundaries.md").read_text(
        encoding="utf-8"
    )
    roadmap = (REPO_ROOT / "docs" / "refactor-v11.md").read_text(encoding="utf-8")

    for required_text in (
        "### V11 Confidence-Surface Ownership",
        "eval_recommendation_*.py",
        "knowledge_posture*.py",
        "branch_decision_*.py",
        "session_export*.py",
        "session_import*.py",
        "tool_attempt_recovery*.py",
        "sqlite_projection_*.py",
    ):
        assert required_text in architecture

    for required_text in (
        "The v11 confidence-surface refactor map is implemented through Phase 75",
        "## V11 Closeout Validation Commands",
        "uv run pytest tests/unit/test_architecture_guardrails.py",
        "pnpm --dir frontend typecheck",
        "uv run python scripts/validate_v11_release_gate.py --dry-run",
        "`sqlite_projection_background_jobs.py`",
    ):
        assert required_text in boundaries

    assert "GBX-R460: Update Architecture Docs For The V11 Refactor Shape" in roadmap
    assert (
        "GBX-R461: Close Out V11 Refactor Guardrails And Focused Validation" in roadmap
    )
    assert "Accepted compatibility shims and intended owners are listed" in roadmap
    assert "uv run pytest tests/unit/test_architecture_guardrails.py" in roadmap
    assert "pnpm --dir frontend lint" in roadmap
    assert "pnpm --dir frontend test" in roadmap


def test_v13_refactor_docs_describe_final_module_shape() -> None:
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    architecture = (REPO_ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    boundaries = (REPO_ROOT / "docs" / "refactor-boundaries.md").read_text(
        encoding="utf-8"
    )
    roadmap = (REPO_ROOT / "docs" / "refactor-v13.md").read_text(encoding="utf-8")

    for required_text in (
        "## Current Post-v13 Review-Loop Refactor Shape",
        "The completed post-v13 refactor keeps the current behavior",
        "`frontend/stores/changeset-store.ts` remains the dashboard store facade",
        "`scripts/v13_release_gate_helpers.py`",
    ):
        assert required_text in architecture

    for required_text in (
        "The post-v13 review-loop boundary map is implemented through Phase 87",
        "### V13 Accepted Compatibility Shims",
        "`frontend/components/console/changeset-console.tsx` delegates",
        "`frontend/stores/changeset-store.ts` delegates API actions",
        "`scripts/validate_v13_release_gate.py` delegates v13 release-gate",
    ):
        assert required_text in boundaries

    for required_text in (
        "GBX-R570: Extract V13 Release-Gate Helper Owners",
        "GBX-R571: Refresh Refactor Documentation And Package Metadata Expectations",
        "scripts/v13_release_gate_helpers.py",
        "uv run python scripts/validate_package_contents.py",
    ):
        assert required_text in roadmap

    assert "docs/refactor-v13.md" in root_readme
    assert "refactor-v13.md" in docs_readme


def test_v14_refactor_docs_define_next_boundary_map() -> None:
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    architecture = (REPO_ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    boundaries = (REPO_ROOT / "docs" / "refactor-boundaries.md").read_text(
        encoding="utf-8"
    )
    roadmap = (REPO_ROOT / "docs" / "refactor-v14.md").read_text(encoding="utf-8")

    for required_text in (
        "## Current Post-v14 Review-Loop Maturity Refactor Shape",
        "`runtime/changeset_review_brief_sections.py` remains the lifecycle brief",
        "`runtime/review_responses.py` remains the review response facade",
        "`scripts/v14_release_gate_helpers.py`",
    ):
        assert required_text in architecture

    for required_text in (
        "The post-v14 review-loop maturity boundary map starts",
        "#### Post-V14 Review-Loop Maturity Runtime Sub-Boundaries",
        "#### Post-V14 Terminal Review-Loop Sub-Boundaries",
        "### Post-V14 Accepted Compatibility Shims",
        "`frontend/stores/changeset-store-actions.ts`: store action facade",
    ):
        assert required_text in boundaries

    for required_text in (
        "GBX-R600: Define Post-V14 Refactor Boundary Map",
        "- Status: `DONE`",
        "GBX-R601: Characterize Current V14 Review-Loop Maturity Behavior",
        "GBX-R602: Add Post-V14 Facade Guardrails After First Extraction",
    ):
        assert required_text in roadmap

    assert "docs/refactor-v14.md" in root_readme
    assert "refactor-v14.md" in docs_readme


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


def test_interactive_workflows_cover_tui_review_loop_shortcuts() -> None:
    content = (REPO_ROOT / "docs" / "interactive-workflows.md").read_text(
        encoding="utf-8"
    )

    for required_text in (
        "### In-Session Review Loop",
        "`/changeset` is a compatibility alias",
        "/review create",
        "/review status",
        "/review refresh",
        "/review brief",
        "/review verify",
        "/review handoff",
        "/review feedback",
        "/review dashboard",
        "current workspace",
        "diff and anchors it to the active chat session",
        "active chat session",
        "do not auto-run tests",
        "stage files, commit, push, open pull requests",
        "Plain mode also supports the same review-loop",
    ):
        assert required_text in content


def test_root_readme_prioritizes_current_product_path_before_release_archive() -> None:
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "docs/v10-long-running-task-contract.md" in root_readme
    assert "docs/v11-confidence-adoption-contract.md" in root_readme
    assert "docs/operator-quickstart.md" in root_readme
    assert root_readme.index(
        "docs/v10-long-running-task-contract.md"
    ) < root_readme.index("docs/v8-release-candidate.md")


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
        "Glassbox v11 uses package version `0.10.0`",
        "v10 names the supported product capability",
        "v11 names the confidence, adoption, and release-evidence milestone",
        "`pyproject.toml` is the packaging source",
        "`glassbox.__version__`",
        "glassbox --version",
        "v11-0.10.0-rc.N",
        "## Release Note Template",
        "Provider evidence: advisory",
    ):
        assert required_text in content
