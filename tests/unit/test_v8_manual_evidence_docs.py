from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read_doc(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_v8_manual_release_validation_records_required_evidence() -> None:
    doc = _read_doc("docs/manual-v8-release-validation.md")

    for phrase in (
        "GBX-894",
        "Terminal task planning",
        "Dashboard plan inspection",
        "Background continuation",
        "Budget exhaustion",
        "Memory confirmation/invalidation",
        "Repository index rebuild",
        "Verify-repair loop",
        "Branch-search comparison",
        "Provider recommendation",
        "Package smoke",
        "EMFILE",
        "screen-reader claim",
        "Provisional go",
    ):
        assert phrase in doc


def test_v8_manual_template_records_pairings_and_redaction_rules() -> None:
    doc = _read_doc("docs/manual-qa-evidence-v8.md")

    for phrase in (
        ".glassbox/releases/YYYYMMDDTHHMMSSZ-v8-gate/",
        "manual-validation.md",
        "Named Accessibility Pairings",
        "Redaction Rules",
        "Accessibility Claims Rule",
        "Provider Review",
        "Package Smoke",
    ):
        assert phrase in doc


def test_docs_readme_links_v8_manual_evidence() -> None:
    readme = _read_doc("docs/README.md")

    assert "[manual-qa-evidence-v8.md]" in readme
    assert "[manual-v8-release-validation.md]" in readme
