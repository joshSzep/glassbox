"""Provider-canary retained evidence loading and freshness derivation."""

import json
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

from glassbox.runtime.provider_canary_models import EVIDENCE_STALE_AFTER_SECONDS
from glassbox.runtime.provider_canary_models import ProviderCanaryEvidenceStatus
from glassbox.runtime.provider_canary_models import ProviderCanaryEvidenceSummary
from glassbox.runtime.provider_canary_models import ProviderCanaryFreshnessStatus
from glassbox.runtime.provider_canary_models import ProviderCanarySummary
from glassbox.runtime.provider_canary_reporting import count_provider_canary_outcomes
from glassbox.runtime.provider_canary_scenarios import DEFAULT_PROVIDER_CANARY_SCENARIOS
from glassbox.runtime.provider_diagnostics import build_provider_diagnostics_report


def load_provider_canary_evidence(
    workspace_root: Path,
    *,
    summary_path: Path | None = None,
    expected_model_name: str | None = None,
) -> ProviderCanaryEvidenceSummary:
    """Load a compact advisory summary for retained provider-canary evidence."""

    summaries = _provider_canary_summary_paths(workspace_root, summary_path)
    if not summaries:
        return ProviderCanaryEvidenceSummary(
            summary_count=0,
            latest_status="missing",
            freshness_status="missing",
            configured_model_name=_configured_model_name(
                workspace_root,
                expected_model_name=expected_model_name,
            ),
            next_actions=[
                f"glassbox provider canary run --cwd {workspace_root}",
            ],
        )

    latest_path = summaries[0]
    payload = _load_summary_payload(latest_path)
    try:
        summary = ProviderCanarySummary.model_validate(payload)
    except ValueError as exc:
        return _legacy_or_invalid_provider_canary_evidence(
            latest_path,
            payload,
            summary_count=len(summaries),
            workspace_root=workspace_root,
            error=exc,
            expected_model_name=expected_model_name,
        )
    outcome_counts = count_provider_canary_outcomes(summary.scenarios)
    latest_status = _evidence_status(outcome_counts)
    stale = _is_stale(latest_path)
    configured_model_name = _configured_model_name(
        workspace_root,
        expected_model_name=expected_model_name,
    )
    identity_matches_current_config = _identity_matches_current_config(
        retained_model_name=summary.model_name,
        configured_model_name=configured_model_name,
    )
    missing_scenarios = _missing_scenarios(summary)
    freshness_status = _freshness_status(
        latest_status=latest_status,
        stale=stale,
        diagnostics_state=summary.diagnostics_state,
        provider=summary.provider,
    )
    next_actions = [f"inspect provider canary evidence {latest_path}"]
    if stale:
        next_actions.append(f"glassbox provider canary run --cwd {workspace_root}")
    if identity_matches_current_config is False:
        next_actions.append(
            "rerun provider canary evidence for the currently configured model"
        )
    if missing_scenarios:
        next_actions.append(
            "rerun provider canary evidence to cover missing scenarios: "
            + ", ".join(missing_scenarios)
        )
    if latest_status in {"failed", "warning", "skipped"}:
        next_actions.extend(summary.next_actions)

    return ProviderCanaryEvidenceSummary(
        summary_count=len(summaries),
        latest_summary_path=str(latest_path),
        latest_generated_at=summary.generated_at,
        latest_status=latest_status,
        freshness_status=freshness_status,
        schema_version=summary.schema_version,
        provider=summary.provider,
        model_name=summary.model_name,
        configured_model_name=configured_model_name,
        identity_matches_current_config=identity_matches_current_config,
        diagnostics_state=summary.diagnostics_state,
        scenario_count=len(summary.scenarios),
        matrix_entry_count=len(summary.capability_matrix.entries),
        missing_scenarios=missing_scenarios,
        passed_count=outcome_counts["passed"],
        skipped_count=outcome_counts["skipped"],
        warning_count=outcome_counts["warning"],
        failed_count=outcome_counts["failed"],
        stale=stale,
        next_actions=next_actions,
    )


def _legacy_or_invalid_provider_canary_evidence(
    latest_path: Path,
    payload: dict[str, Any],
    *,
    summary_count: int,
    workspace_root: Path,
    error: ValueError,
    expected_model_name: str | None,
) -> ProviderCanaryEvidenceSummary:
    scenarios = payload.get("scenarios")
    scenario_count = len(scenarios) if isinstance(scenarios, list) else 0
    matrix_payload = payload.get("capability_matrix")
    matrix_entries = (
        matrix_payload.get("entries") if isinstance(matrix_payload, dict) else None
    )
    matrix_entry_count = len(matrix_entries) if isinstance(matrix_entries, list) else 0
    return ProviderCanaryEvidenceSummary(
        summary_count=summary_count,
        latest_summary_path=str(latest_path),
        latest_generated_at=_payload_str(payload.get("generated_at")),
        latest_status="warning",
        freshness_status="incompatible",
        schema_version=_payload_str(payload.get("schema_version")),
        provider=_payload_str(payload.get("provider")),
        model_name=_payload_str(payload.get("model_name")),
        configured_model_name=_configured_model_name(
            workspace_root,
            expected_model_name=expected_model_name,
        ),
        diagnostics_state=_payload_str(payload.get("diagnostics_state")),
        scenario_count=scenario_count,
        matrix_entry_count=matrix_entry_count,
        missing_scenarios=list(DEFAULT_PROVIDER_CANARY_SCENARIOS),
        warning_count=1,
        stale=True,
        next_actions=[
            f"inspect provider canary evidence {latest_path}",
            f"glassbox provider canary run --cwd {workspace_root}",
            "retained provider canary evidence is stale or incompatible: "
            f"{type(error).__name__}",
        ],
    )


def _provider_canary_summary_paths(
    workspace_root: Path,
    summary_path: Path | None,
) -> list[Path]:
    if summary_path is not None:
        resolved = (
            summary_path
            if summary_path.is_absolute()
            else workspace_root / summary_path
        )
        return [resolved] if resolved.exists() else []
    evidence_root = workspace_root / ".glassbox"
    if not evidence_root.exists():
        return []
    return sorted(
        evidence_root.glob("**/provider-canary-summary.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def _load_summary_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _evidence_status(
    outcome_counts,
) -> ProviderCanaryEvidenceStatus:
    if outcome_counts["failed"] > 0:
        return "failed"
    if outcome_counts["warning"] > 0:
        return "warning"
    if outcome_counts["skipped"] > 0:
        return "skipped" if outcome_counts["passed"] == 0 else "warning"
    return "passed"


def _freshness_status(
    *,
    latest_status: ProviderCanaryEvidenceStatus,
    stale: bool,
    diagnostics_state: str,
    provider: str,
) -> ProviderCanaryFreshnessStatus:
    if stale:
        return "stale"
    if latest_status == "failed":
        return "failed"
    if latest_status == "warning":
        return "warning"
    if latest_status == "skipped" and (
        diagnostics_state in {"missing_credentials", "local_fallback"}
        or provider == "local"
    ):
        return "credentialless"
    if latest_status == "skipped":
        return "warning"
    return "fresh"


def _is_stale(path: Path) -> bool:
    age_seconds = datetime.now(UTC).timestamp() - path.stat().st_mtime
    return age_seconds > EVIDENCE_STALE_AFTER_SECONDS


def _configured_model_name(
    workspace_root: Path,
    *,
    expected_model_name: str | None,
) -> str | None:
    if expected_model_name is not None:
        return expected_model_name
    if not (workspace_root / "glassbox.profile.json").exists():
        return None
    try:
        return build_provider_diagnostics_report(workspace_root).selected_model_name
    except ValueError:
        return None


def _identity_matches_current_config(
    *,
    retained_model_name: str,
    configured_model_name: str | None,
) -> bool | None:
    if configured_model_name is None:
        return None
    return retained_model_name == configured_model_name


def _missing_scenarios(summary: ProviderCanarySummary) -> list[str]:
    observed = {entry.scenario_id for entry in summary.capability_matrix.entries}
    return [
        scenario_id
        for scenario_id in DEFAULT_PROVIDER_CANARY_SCENARIOS
        if scenario_id not in observed
    ]


def _payload_str(value: object) -> str | None:
    return value if isinstance(value, str) else None
