from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read_doc(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_v9_dogfooding_protocol_records_evidence_and_redaction_contract() -> None:
    doc = _read_doc("docs/dogfooding.md")

    for phrase in (
        ".glassbox/dogfooding/v9/<pass-id>/",
        "Repository inspection and explanation",
        "Small code edit with verification",
        "Longer task-plan or branch-search workflow",
        "Provider posture",
        "## Redaction Rules",
        "raw provider prompts",
        "Finding Disposition",
        "Accepted residual risk",
        "Post-v9 task",
    ):
        assert phrase in doc


def test_docs_hub_links_v9_dogfooding_protocol() -> None:
    docs_readme = _read_doc("docs/README.md")

    assert "[dogfooding.md](./dogfooding.md)" in docs_readme
    assert "[v9-dogfooding-summary.md](./v9-dogfooding-summary.md)" in docs_readme


def test_v9_dogfooding_summary_records_passes_and_findings() -> None:
    doc = _read_doc("docs/v9-dogfooding-summary.md")

    for phrase in (
        "20260429-0930-repository-inspection",
        "20260429-1100-small-edit-verification",
        "20260429-1400-branch-search-plan",
        "credentialed streaming canary passed",
        "Friction Findings",
        "GBX-982 Triage And Dispositions",
        "Provider canary summary consistency",
        "Branch-search decision copy",
        "GBX-982 fixed the two high-signal low-risk implementation findings",
    ):
        assert phrase in doc
