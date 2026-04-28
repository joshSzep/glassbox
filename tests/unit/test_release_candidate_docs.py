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
