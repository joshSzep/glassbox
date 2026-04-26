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
