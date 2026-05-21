"""V17 release-gate advisory evidence helpers."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts import v16_release_gate_helpers as v16_helpers

PROVIDER_ADVISORY_LABEL = "v17 advisory provider evidence"
PROVIDER_CANARY_DRY_RUN_COMMAND = (
    "uv run glassbox provider canary run --cwd . "
    "--output-dir <evidence>/provider-canary --json"
)
PROVIDER_CANARY_SKIPPED_DRY_RUN = f"- {PROVIDER_ADVISORY_LABEL}: skipped by default"


@dataclass(frozen=True)
class AdvisoryEvidenceRow:
    label: str
    reason: str
    directory_name: str
    docs_path: str
    latest_status: str
    dry_run_summary: str


ADVISORY_EVIDENCE_ROWS = (
    AdvisoryEvidenceRow(
        label="v17 advisory dashboard browser evidence",
        reason=(
            "local handoff cockpit browser evidence remains advisory beside "
            "deterministic API, frontend, and eval checks"
        ),
        directory_name="browser",
        docs_path="docs/local-handoff.md",
        latest_status="planned",
        dry_run_summary="planned; not deterministic release authority",
    ),
    AdvisoryEvidenceRow(
        label="v17 advisory accessibility evidence",
        reason=(
            "keyboard, focus, responsive, and accessibility notes remain advisory "
            "unless fixture-backed coverage promotes a narrow contract"
        ),
        directory_name="accessibility",
        docs_path="docs/local-handoff.md",
        latest_status="planned",
        dry_run_summary="planned; not deterministic release authority",
    ),
    AdvisoryEvidenceRow(
        label="v17 dogfooding evidence",
        reason=(
            "local handoff dogfooding is useful release confidence but is not a "
            "blocking deterministic gate stage"
        ),
        directory_name="dogfooding",
        docs_path="docs/tasks-v17.md",
        latest_status="planned",
        dry_run_summary="planned for v17 dogfooding",
    ),
    AdvisoryEvidenceRow(
        label="v17 manual release evidence",
        reason=(
            "manual handoff review remains human custody evidence beside tests, "
            "evals, package checks, and release gates"
        ),
        directory_name="manual",
        docs_path="docs/v17-local-handoff-contract.md",
        latest_status="planned",
        dry_run_summary="planned release-candidate review",
    ),
)


def record_provider_evidence(
    summary: dict[str, Any],
    evidence_dir: Path,
    *,
    include: bool,
    dry_run: bool,
) -> None:
    v16_helpers.record_provider_evidence(
        summary,
        evidence_dir,
        include=include,
        dry_run=dry_run,
    )
    if summary["advisory"]:
        latest = summary["advisory"][-1]
        if latest.get("label") == "v16 advisory provider evidence":
            latest["label"] = PROVIDER_ADVISORY_LABEL


def record_advisory_evidence(summary: dict[str, Any], evidence_dir: Path) -> None:
    for row in ADVISORY_EVIDENCE_ROWS:
        summary["advisory"].append(advisory_summary_row(row, evidence_dir))


def advisory_summary_row(
    row: AdvisoryEvidenceRow,
    evidence_dir: Path,
) -> dict[str, Any]:
    return {
        "label": row.label,
        "status": row.latest_status,
        "reason": row.reason,
        "blocking": False,
        "freshness_status": row.latest_status,
        "latest_status": row.latest_status,
        "evidence_dir": str(evidence_dir / row.directory_name),
        "docs": row.docs_path,
        "required_for_release": False,
    }


def provider_dry_run_line(*, include_provider_canaries: bool) -> str:
    if include_provider_canaries:
        return f"- {PROVIDER_ADVISORY_LABEL}: {PROVIDER_CANARY_DRY_RUN_COMMAND}"
    return PROVIDER_CANARY_SKIPPED_DRY_RUN


def advisory_dry_run_lines() -> list[str]:
    return [f"- {row.label}: {row.dry_run_summary}" for row in ADVISORY_EVIDENCE_ROWS]
