"""V14 release-gate advisory evidence helpers."""

import subprocess
from pathlib import Path
from typing import Any

from scripts import v11_release_gate_helpers as gate_helpers
from scripts.validate_v6_release_gate import REPO_ROOT
from scripts.validate_v11_release_gate import load_provider_canary_evidence


def record_v14_provider_evidence(
    summary: dict[str, Any],
    evidence_dir: Path,
    *,
    include: bool,
    dry_run: bool,
) -> None:
    gate_helpers.record_v11_provider_evidence(
        summary,
        evidence_dir,
        include=include,
        dry_run=dry_run,
        run_command=lambda command: subprocess.run(
            command,
            cwd=REPO_ROOT,
            check=False,
        ),
        load_evidence=lambda summary_path: load_provider_canary_evidence(
            REPO_ROOT,
            summary_path=summary_path,
        ),
    )
    if summary["advisory"]:
        latest = summary["advisory"][-1]
        if latest.get("label") == "v11 advisory provider evidence":
            latest["label"] = "v14 advisory provider evidence"


def record_v14_advisory_ux_evidence(
    summary: dict[str, Any],
    evidence_dir: Path,
) -> None:
    advisory_entries = [
        (
            "v14 advisory dashboard evidence",
            "fresh dashboard/browser walkthrough retained from GBX-1451; "
            "advisory only and not deterministic release authority",
            "browser",
            "docs/v14-advisory-dashboard-evidence.md",
            ".glassbox/releases/v14-advisory-review-evidence/browser/summary.json",
        ),
        (
            "v14 advisory accessibility evidence",
            "fresh keyboard/focus/responsive pairing retained from GBX-1452; "
            "not certification or WCAG conformance",
            "accessibility",
            "docs/v14-advisory-accessibility-evidence.md",
            ".glassbox/releases/v14-advisory-review-evidence/accessibility/summary.json",
        ),
    ]
    for label, reason, directory_name, docs_path, retained_summary in advisory_entries:
        summary["advisory"].append(
            {
                "label": label,
                "status": "recorded",
                "reason": reason,
                "blocking": False,
                "freshness_status": "retained",
                "latest_status": "recorded",
                "evidence_dir": str(evidence_dir / directory_name),
                "retained_summary": retained_summary,
                "docs": docs_path,
                "required_for_release": False,
            }
        )
