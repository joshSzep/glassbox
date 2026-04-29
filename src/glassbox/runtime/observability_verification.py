"""Retained eval-summary observability collector."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from glassbox.runtime.observability_models import VerificationObservability


@dataclass(frozen=True, slots=True)
class RetainedEvalSummary:
    path: Path
    payload: dict[str, Any]


def build_verification_observability(workspace_root: Path) -> VerificationObservability:
    summaries = _retained_eval_summaries(workspace_root)
    if not summaries:
        return VerificationObservability(
            summary_count=0,
            next_actions=["glassbox eval run"],
        )

    latest_summary = summaries[0]
    latest_path = latest_summary.path
    payload = latest_summary.payload
    latest_exit_code = _optional_int(payload.get("exit_code"))
    latest_profile_id = _optional_str(payload.get("profile_id"))
    latest_suite_status = "passed" if latest_exit_code == 0 else "failed"
    next_actions = [f"inspect eval summary {latest_path}"]
    if latest_exit_code not in (None, 0):
        next_actions.append(f"glassbox eval report {latest_profile_id or 'PROFILE_ID'}")

    return VerificationObservability(
        summary_count=len(summaries),
        latest_summary_path=str(latest_path),
        latest_suite_status=latest_suite_status,
        latest_exit_code=latest_exit_code,
        latest_profile_id=latest_profile_id,
        latest_selected_case_count=_optional_int(payload.get("selected_case_count")),
        latest_passed_case_count=_optional_int(payload.get("passed_case_count")),
        latest_failed_case_count=_optional_int(payload.get("failed_case_count")),
        next_actions=next_actions,
    )


def _retained_eval_summaries(workspace_root: Path) -> list[RetainedEvalSummary]:
    summary_paths = sorted(
        (workspace_root / ".glassbox" / "evals").glob("**/summary.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return [
        RetainedEvalSummary(path=path, payload=_load_json_object(path))
        for path in summary_paths
    ]


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) else None


def _optional_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


__all__ = ["build_verification_observability"]
