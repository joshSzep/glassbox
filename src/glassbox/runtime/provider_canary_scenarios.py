"""Provider-canary scenario definitions and selection helpers."""

from glassbox.runtime.provider_canary_models import ProviderCanaryScenarioDefinition

DEFAULT_PROVIDER_CANARY_SCENARIOS = (
    "streaming-text",
    "tool-call",
    "approval",
    "ask-user",
    "cancellation",
    "dashboard",
    "daemon-attach",
    "malformed-tool-call",
    "long-context-continuity",
    "retry-behavior",
    "rate-limit-handling",
    "tool-call-streaming",
    "cancellation-during-retry",
    "multi-step-plan-following",
    "verification-loop-interaction",
)

PROVIDER_CANARY_SCENARIO_DEFINITIONS = {
    "streaming-text": ProviderCanaryScenarioDefinition(
        scenario_id="streaming-text",
        automation_status="automated",
        timeout_seconds=60.0,
        description=(
            "Run a short provider-backed text turn and verify model and "
            "assistant event evidence."
        ),
        prompt="Reply with a short provider canary acknowledgement.",
    ),
    "tool-call": ProviderCanaryScenarioDefinition(
        scenario_id="tool-call",
        automation_status="preflight_only",
        timeout_seconds=60.0,
        description=(
            "Preflight provider/tool-call readiness before workflow-specific "
            "live automation is available."
        ),
    ),
    "approval": ProviderCanaryScenarioDefinition(
        scenario_id="approval",
        automation_status="preflight_only",
        timeout_seconds=60.0,
        description="Preflight provider behavior for approval-gated tool workflows.",
    ),
    "ask-user": ProviderCanaryScenarioDefinition(
        scenario_id="ask-user",
        automation_status="preflight_only",
        timeout_seconds=60.0,
        description=(
            "Preflight provider behavior for ask-user suspension and resume workflows."
        ),
    ),
    "cancellation": ProviderCanaryScenarioDefinition(
        scenario_id="cancellation",
        automation_status="preflight_only",
        timeout_seconds=30.0,
        description=(
            "Preflight provider behavior for cancellation-sensitive workflow runs."
        ),
    ),
    "dashboard": ProviderCanaryScenarioDefinition(
        scenario_id="dashboard",
        automation_status="preflight_only",
        timeout_seconds=30.0,
        description="Preflight dashboard compatibility for retained provider evidence.",
    ),
    "daemon-attach": ProviderCanaryScenarioDefinition(
        scenario_id="daemon-attach",
        automation_status="preflight_only",
        timeout_seconds=30.0,
        description=(
            "Preflight daemon attach compatibility for provider-backed sessions."
        ),
    ),
    "malformed-tool-call": ProviderCanaryScenarioDefinition(
        scenario_id="malformed-tool-call",
        automation_status="preflight_only",
        timeout_seconds=30.0,
        description=(
            "Preflight provider/tool adapter behavior for malformed or "
            "schema-invalid tool calls."
        ),
    ),
    "long-context-continuity": ProviderCanaryScenarioDefinition(
        scenario_id="long-context-continuity",
        automation_status="preflight_only",
        timeout_seconds=60.0,
        description=(
            "Preflight provider suitability for long-context continuity across "
            "multi-step local work."
        ),
    ),
    "retry-behavior": ProviderCanaryScenarioDefinition(
        scenario_id="retry-behavior",
        automation_status="preflight_only",
        timeout_seconds=60.0,
        description="Preflight provider retry posture for transient failures.",
    ),
    "rate-limit-handling": ProviderCanaryScenarioDefinition(
        scenario_id="rate-limit-handling",
        automation_status="preflight_only",
        timeout_seconds=60.0,
        description="Preflight provider behavior expectations around rate limits.",
    ),
    "tool-call-streaming": ProviderCanaryScenarioDefinition(
        scenario_id="tool-call-streaming",
        automation_status="preflight_only",
        timeout_seconds=60.0,
        description="Preflight streaming behavior while tool calls are emitted.",
    ),
    "cancellation-during-retry": ProviderCanaryScenarioDefinition(
        scenario_id="cancellation-during-retry",
        automation_status="preflight_only",
        timeout_seconds=60.0,
        description="Preflight cancellation behavior while retry handling is active.",
    ),
    "multi-step-plan-following": ProviderCanaryScenarioDefinition(
        scenario_id="multi-step-plan-following",
        automation_status="preflight_only",
        timeout_seconds=60.0,
        description="Preflight provider suitability for following bounded task plans.",
    ),
    "verification-loop-interaction": ProviderCanaryScenarioDefinition(
        scenario_id="verification-loop-interaction",
        automation_status="preflight_only",
        timeout_seconds=60.0,
        description=(
            "Preflight provider suitability for verify-repair loop interaction."
        ),
    ),
}


def selected_provider_canary_scenarios(scenarios: list[str] | None) -> list[str]:
    """Return explicitly selected scenarios or the full advisory default set."""

    return scenarios or list(DEFAULT_PROVIDER_CANARY_SCENARIOS)


def provider_canary_definition_for(
    scenario_id: str,
) -> ProviderCanaryScenarioDefinition:
    """Return known scenario metadata or a skipped advisory placeholder."""

    return PROVIDER_CANARY_SCENARIO_DEFINITIONS.get(
        scenario_id,
        ProviderCanaryScenarioDefinition(
            scenario_id=scenario_id,
            automation_status="preflight_only",
            timeout_seconds=30.0,
            description=(
                "Unknown scenario retained as a skipped advisory preflight row."
            ),
        ),
    )
