"""Deterministic provider failure fixtures for advisory recovery behavior."""

import json
import os
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core.models import ProviderRecoveryRecord
from glassbox.core.types import AutonomyMode
from glassbox.llm import ModelProviderConfig
from glassbox.llm import PydanticAIModelAdapter
from glassbox.runtime.provider_canary_models import PROVIDER_CANARY_SCHEMA_VERSION
from glassbox.runtime.provider_canary_scenarios import DEFAULT_PROVIDER_CANARY_SCENARIOS
from glassbox.runtime.provider_capability_matrix import ProviderCapabilityResult
from glassbox.runtime.provider_capability_matrix import build_provider_capability_matrix
from glassbox.runtime.provider_diagnostics import build_provider_diagnostics_report
from glassbox.runtime.provider_recommendations import ProviderRecommendation
from glassbox.runtime.provider_recommendations import ProviderTaskKind
from glassbox.runtime.provider_recommendations import recommend_provider
from glassbox.runtime.provider_recovery import ProviderFailureRecoveryDecision
from glassbox.runtime.provider_recovery import classify_provider_failure

FIXTURE_NOW = datetime(2026, 4, 30, 12, 0, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class ProviderFailureFixture:
    """One deterministic provider failure scenario."""

    fixture_id: str
    description: str
    model_name: str
    task_kind: ProviderTaskKind
    autonomy_mode: AutonomyMode
    error_message: str | None = None
    attempt: int = 1
    max_attempts: int = 3
    stale_canary: bool = False
    configure_credentials: bool = True


class ProviderFailureFixtureResult(BaseModel):
    """Reviewable output from one provider failure fixture."""

    model_config = ConfigDict(extra="forbid")

    fixture_id: str
    description: str
    advisory: bool = True
    deterministic_release_blocking: bool = False
    recovery_history: list[ProviderRecoveryRecord] = Field(default_factory=list)
    recommendation: ProviderRecommendation
    retained_artifacts: list[str] = Field(default_factory=list)


_FIXTURES: tuple[ProviderFailureFixture, ...] = (
    ProviderFailureFixture(
        fixture_id="retryable-provider-error",
        description="Transient provider timeout schedules a bounded retry.",
        model_name="openai:gpt-5.4",
        task_kind=ProviderTaskKind.CODING,
        autonomy_mode=AutonomyMode.TEST_DRIVEN,
        error_message="provider timeout while completing response",
        attempt=1,
        max_attempts=3,
    ),
    ProviderFailureFixture(
        fixture_id="non-retryable-provider-error",
        description="Bad provider request stops for checkpoint inspection.",
        model_name="openai:gpt-5.4",
        task_kind=ProviderTaskKind.CODING,
        autonomy_mode=AutonomyMode.TEST_DRIVEN,
        error_message="provider bad request rejected the selected model",
        attempt=1,
        max_attempts=3,
    ),
    ProviderFailureFixture(
        fixture_id="lost-stream",
        description="Lost stream after retry budget is treated as blocked.",
        model_name="openai:gpt-5.4",
        task_kind=ProviderTaskKind.BACKGROUND,
        autonomy_mode=AutonomyMode.AUTONOMOUS_LOCAL,
        error_message="lost stream after connection reset",
        attempt=3,
        max_attempts=3,
    ),
    ProviderFailureFixture(
        fixture_id="malformed-tool-call",
        description="Malformed provider tool call requires checkpoint inspection.",
        model_name="openai:gpt-5.4",
        task_kind=ProviderTaskKind.VERIFICATION,
        autonomy_mode=AutonomyMode.TEST_DRIVEN,
        error_message="malformed tool call arguments from provider response",
        attempt=1,
        max_attempts=1,
    ),
    ProviderFailureFixture(
        fixture_id="stale-canary-evidence",
        description="Stale retained canary evidence recommends evidence refresh.",
        model_name="openai:gpt-5.4",
        task_kind=ProviderTaskKind.RELEASE,
        autonomy_mode=AutonomyMode.RELEASE_CANDIDATE,
        stale_canary=True,
    ),
    ProviderFailureFixture(
        fixture_id="model-fallback-recommendation",
        description="Unsupported provider model recommends explicit local fallback.",
        model_name="other:model",
        task_kind=ProviderTaskKind.INSPECTION,
        autonomy_mode=AutonomyMode.INSPECT,
        configure_credentials=False,
    ),
)


def provider_failure_fixture_ids() -> list[str]:
    """Return fixture IDs in stable review order."""

    return [fixture.fixture_id for fixture in _FIXTURES]


def provider_failure_fixture_specs() -> list[ProviderFailureFixture]:
    """Return all deterministic provider failure fixture specs."""

    return list(_FIXTURES)


def run_provider_failure_fixture(
    workspace_root: Path,
    fixture_id: str,
) -> ProviderFailureFixtureResult:
    """Run one deterministic provider failure fixture without live credentials."""

    fixture = _fixture_by_id(fixture_id)
    workspace_root.mkdir(parents=True, exist_ok=True)
    retained_artifacts: list[str] = []
    if fixture.configure_credentials:
        _write_fixture_credentials(workspace_root)
    if fixture.stale_canary:
        retained_artifacts.append(_write_stale_canary_summary(workspace_root, fixture))

    recovery_history: list[ProviderRecoveryRecord] = []
    if fixture.error_message is not None:
        decision = _classify_fixture_error(fixture)
        recovery_history.append(_recovery_record_for(fixture, decision))

    recommendation = recommend_provider(
        workspace_root,
        task_kind=fixture.task_kind,
        autonomy_mode=fixture.autonomy_mode,
        model_name=fixture.model_name,
        provider_recovery_history=recovery_history,
    )
    return ProviderFailureFixtureResult(
        fixture_id=fixture.fixture_id,
        description=fixture.description,
        recovery_history=recovery_history,
        recommendation=recommendation,
        retained_artifacts=retained_artifacts,
    )


def _fixture_by_id(fixture_id: str) -> ProviderFailureFixture:
    for fixture in _FIXTURES:
        if fixture.fixture_id == fixture_id:
            return fixture
    available = ", ".join(provider_failure_fixture_ids())
    raise ValueError(
        f"unknown provider failure fixture {fixture_id!r}; choose {available}"
    )


def _classify_fixture_error(
    fixture: ProviderFailureFixture,
) -> ProviderFailureRecoveryDecision:
    if fixture.error_message is None:
        raise ValueError(f"fixture {fixture.fixture_id} does not define an error")
    adapter = PydanticAIModelAdapter(
        ModelProviderConfig(
            provider=fixture.model_name.partition(":")[0],
            model_name=fixture.model_name,
        )
    )
    decision = classify_provider_failure(
        RuntimeError(fixture.error_message),
        model_adapter=adapter,
        attempt=fixture.attempt,
        max_attempts=fixture.max_attempts,
        now=FIXTURE_NOW,
    )
    if decision is None:
        raise AssertionError(f"fixture {fixture.fixture_id} did not classify")
    return decision


def _recovery_record_for(
    fixture: ProviderFailureFixture,
    decision: ProviderFailureRecoveryDecision,
) -> ProviderRecoveryRecord:
    return ProviderRecoveryRecord(
        session_id=UUID("00000000-0000-4000-8000-000000001140"),
        turn_id=UUID(f"00000000-0000-4000-8000-{_fixture_suffix(fixture):012d}"),
        provider=decision.provider,
        model_name=decision.model_name,
        failure_kind=decision.failure_kind,
        action=decision.action,
        reason=decision.reason,
        retryable=decision.retryable,
        safe_to_continue=decision.safe_to_continue,
        degraded=decision.degraded,
        operator_next_action=decision.operator_next_action,
        attempt=decision.attempt,
        max_attempts=decision.max_attempts,
        backoff_seconds=decision.backoff_seconds,
        next_retry_at=decision.next_retry_at,
        created_at=FIXTURE_NOW,
        last_sequence=_fixture_suffix(fixture),
    )


def _fixture_suffix(fixture: ProviderFailureFixture) -> int:
    return provider_failure_fixture_ids().index(fixture.fixture_id) + 1140


def _write_fixture_credentials(workspace_root: Path) -> None:
    env_path = workspace_root / ".env"
    if not env_path.exists():
        env_path.write_text("OPENAI_API_KEY=fixture-openai\n", encoding="utf-8")


def _write_stale_canary_summary(
    workspace_root: Path,
    fixture: ProviderFailureFixture,
) -> str:
    output_dir = workspace_root / ".glassbox" / "provider-canary"
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "provider-canary-summary.json"
    report = build_provider_diagnostics_report(
        workspace_root,
        explicit_model_name=fixture.model_name,
        environ={"OPENAI_API_KEY": "fixture-openai"},
    )
    results: dict[str, ProviderCapabilityResult] = {
        scenario_id: "passed" for scenario_id in DEFAULT_PROVIDER_CANARY_SCENARIOS
    }
    matrix = build_provider_capability_matrix(
        report,
        scenario_ids=DEFAULT_PROVIDER_CANARY_SCENARIOS,
        results=results,
    )
    summary_path.write_text(
        json.dumps(
            {
                "schema_version": PROVIDER_CANARY_SCHEMA_VERSION,
                "generated_at": FIXTURE_NOW.isoformat(),
                "advisory": True,
                "provider": report.selected_provider,
                "model_name": fixture.model_name,
                "diagnostics_state": report.state,
                "output_path": str(summary_path),
                "scenario_definitions": [],
                "scenarios": [
                    {
                        "scenario_id": scenario_id,
                        "outcome": result,
                        "detail": "fixture retained advisory evidence",
                        "automation_status": "automated",
                    }
                    for scenario_id, result in results.items()
                ],
                "capability_matrix": matrix.model_dump(mode="json"),
                "skipped_reason": None,
                "next_actions": [],
            }
        ),
        encoding="utf-8",
    )
    old_mtime = 1_700_000_000
    os.utime(summary_path, (old_mtime, old_mtime))
    return str(summary_path)


__all__ = [
    "ProviderFailureFixture",
    "ProviderFailureFixtureResult",
    "provider_failure_fixture_ids",
    "provider_failure_fixture_specs",
    "run_provider_failure_fixture",
]
