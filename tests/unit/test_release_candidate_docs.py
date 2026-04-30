"""Release-candidate documentation guardrails."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


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
        "pre-1.0",
        "`uv run glassbox command tree`",
        "`session`, `task`, `branch-search`, `memory`, `repo index`, `replay`, `eval`",
        "provider recommendations",
        "evidence is the release authority; live-provider evidence is advisory",
        "GBX-912 owns the next version identifier",
    ):
        assert required_text in content


def test_docs_hub_links_to_v9_public_baseline() -> None:
    docs_readme = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    assert "v9-public-baseline.md" in docs_readme
