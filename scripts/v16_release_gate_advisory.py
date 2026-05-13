"""V16 release-gate advisory evidence helpers."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts import validate_v15_release_gate as v15_gate

PROVIDER_ADVISORY_LABEL = "v16 advisory provider evidence"
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
        label="v16 advisory dashboard browser evidence",
        reason=(
            "operator-flow cockpit browser evidence remains advisory and is not "
            "deterministic release authority"
        ),
        directory_name="browser",
        docs_path="docs/v16-flow-cockpit-evidence.md",
        latest_status="recorded",
        dry_run_summary="recorded from retained summary",
    ),
    AdvisoryEvidenceRow(
        label="v16 advisory accessibility evidence",
        reason=(
            "keyboard, focus, responsive, and accessibility-adjacent notes remain "
            "advisory beside fixture-backed checks"
        ),
        directory_name="accessibility",
        docs_path="docs/v16-flow-cockpit-evidence.md",
        latest_status="recorded",
        dry_run_summary="recorded from retained summary",
    ),
    AdvisoryEvidenceRow(
        label="v16 dogfooding evidence",
        reason=(
            "operator-flow dogfooding is recorded by GBX-1682 and remains advisory "
            "beside deterministic gate evidence"
        ),
        directory_name="dogfooding",
        docs_path="docs/v16-dogfooding-summary.md",
        latest_status="recorded",
        dry_run_summary="recorded GBX-1682 advisory summary",
    ),
    AdvisoryEvidenceRow(
        label="v16 manual release evidence",
        reason=(
            "manual release-candidate evidence is recorded in the v16 guide "
            "and remains non-blocking beside deterministic gate evidence"
        ),
        directory_name="manual",
        docs_path="docs/v16-release-candidate.md",
        latest_status="recorded",
        dry_run_summary="recorded v16 release-candidate guide",
    ),
)


def record_provider_evidence(
    summary: dict[str, Any],
    evidence_dir: Path,
    *,
    include: bool,
    dry_run: bool,
) -> None:
    v15_gate._record_v15_provider_evidence(  # noqa: SLF001
        summary,
        evidence_dir,
        include=include,
        dry_run=dry_run,
    )
    if summary["advisory"]:
        latest = summary["advisory"][-1]
        if latest.get("label") == "v15 advisory provider evidence":
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
