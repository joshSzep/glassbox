"""V16 release-gate advisory evidence helpers."""

from pathlib import Path
from typing import Any

from scripts import validate_v15_release_gate as v15_gate


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
            latest["label"] = "v16 advisory provider evidence"


def record_advisory_evidence(summary: dict[str, Any], evidence_dir: Path) -> None:
    advisory_entries = [
        (
            "v16 advisory dashboard browser evidence",
            "operator-flow cockpit browser evidence remains advisory and is not "
            "deterministic release authority",
            "browser",
            "docs/v16-flow-cockpit-evidence.md",
            "recorded",
        ),
        (
            "v16 advisory accessibility evidence",
            "keyboard, focus, responsive, and accessibility-adjacent notes remain "
            "advisory beside fixture-backed checks",
            "accessibility",
            "docs/v16-flow-cockpit-evidence.md",
            "recorded",
        ),
        (
            "v16 dogfooding evidence",
            "operator-flow dogfooding is recorded by GBX-1682 and remains advisory "
            "beside deterministic gate evidence",
            "dogfooding",
            "docs/v16-dogfooding-summary.md",
            "recorded",
        ),
        (
            "v16 manual release evidence",
            "manual release-candidate evidence is recorded in the v16 guide "
            "and remains non-blocking beside deterministic gate evidence",
            "manual",
            "docs/v16-release-candidate.md",
            "recorded",
        ),
    ]
    for label, reason, directory_name, docs_path, latest_status in advisory_entries:
        summary["advisory"].append(
            {
                "label": label,
                "status": latest_status,
                "reason": reason,
                "blocking": False,
                "freshness_status": latest_status,
                "latest_status": latest_status,
                "evidence_dir": str(evidence_dir / directory_name),
                "docs": docs_path,
                "required_for_release": False,
            }
        )
