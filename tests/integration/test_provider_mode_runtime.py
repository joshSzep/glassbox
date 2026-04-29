"""Integration tests for provider-mode runtime execution without network access."""

import asyncio
import json
import sqlite3
from pathlib import Path

from pydantic_ai.messages import ModelRequest
from pydantic_ai.messages import ModelResponse
from pydantic_ai.messages import TextContent
from pydantic_ai.messages import TextPart
from pydantic_ai.messages import UserPromptPart
from pydantic_ai.models.function import FunctionModel

from glassbox.cli import main
from glassbox.core import SessionConfig
from glassbox.core.events import AssistantMessageCompleted
from glassbox.core.events import AssistantMessageDelta
from glassbox.core.events import ModelCallStarted
from glassbox.llm import PydanticAIModelExecutor
from glassbox.runtime import bootstrap as runtime_bootstrap
from glassbox.runtime.provider_canary import run_provider_canary_sync
from glassbox.store import initialize_database
from glassbox.store import open_database

AGENTIC_CANARY_SCENARIOS = [
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
]


def _open_initialized_database(tmp_path: Path) -> sqlite3.Connection:
    connection = open_database(tmp_path / "glassbox.sqlite3")
    initialize_database(connection)
    return connection


def test_provider_mode_streaming_turn_executes_without_network(
    tmp_path: Path,
    monkeypatch,
) -> None:
    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        (tmp_path / ".env").write_text("OPENAI_API_KEY=dotenv-openai\n")

        def fake_build_openai_model_executor(
            model_name: str,
            *,
            api_key: str | None = None,
            base_url: str | None = None,
        ) -> PydanticAIModelExecutor:
            assert model_name == "gpt-5.4"
            assert api_key == "dotenv-openai"
            assert base_url is None
            return PydanticAIModelExecutor(
                FunctionModel(
                    function=_provider_function_model_response,
                    stream_function=_provider_stream_function_model_response,
                    model_name=f"openai:{model_name}",
                )
            )

        monkeypatch.setattr(
            runtime_bootstrap,
            "build_openai_model_executor",
            fake_build_openai_model_executor,
        )

        try:
            runtime_context = runtime_bootstrap._build_runtime_context(
                connection,
                tmp_path,
            )
            service = runtime_context.services.session_service
            repository = runtime_context.repositories.sessions
            state = await service.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            await service.submit_user_message(state.session_id, "Inspect the repo")

            events = repository.read_session_events(state.session_id)
            transcript = repository.list_transcript_messages(state.session_id)
        finally:
            connection.close()

        model_started = [
            event.payload
            for event in events
            if isinstance(event.payload, ModelCallStarted)
        ]
        deltas = [
            event.payload
            for event in events
            if isinstance(event.payload, AssistantMessageDelta)
        ]
        completed = [
            event.payload
            for event in events
            if isinstance(event.payload, AssistantMessageCompleted)
        ]

        assert model_started[-1].provider == "openai"
        assert model_started[-1].model_name == "gpt-5.4"
        assert [delta.delta for delta in deltas] == ["Provider stream ", "complete."]
        assert completed[-1].parts[0].text == "Provider stream complete."
        assert transcript[-1].parts[0].text == "Provider stream complete."

    asyncio.run(scenario())


def test_provider_mode_non_streaming_turn_falls_back_without_network(
    tmp_path: Path,
    monkeypatch,
) -> None:
    async def scenario() -> None:
        connection = _open_initialized_database(tmp_path)
        (tmp_path / ".env").write_text("OPENAI_API_KEY=dotenv-openai\n")

        def fake_build_openai_model_executor(
            model_name: str,
            *,
            api_key: str | None = None,
            base_url: str | None = None,
        ) -> PydanticAIModelExecutor:
            assert model_name == "gpt-5.4"
            assert api_key == "dotenv-openai"
            assert base_url is None
            return PydanticAIModelExecutor(
                FunctionModel(
                    function=_provider_non_streaming_model_response,
                    model_name=f"openai:{model_name}",
                )
            )

        monkeypatch.setattr(
            runtime_bootstrap,
            "build_openai_model_executor",
            fake_build_openai_model_executor,
        )

        try:
            runtime_context = runtime_bootstrap._build_runtime_context(
                connection,
                tmp_path,
            )
            service = runtime_context.services.session_service
            repository = runtime_context.repositories.sessions
            state = await service.start_session(
                SessionConfig(
                    model_name="openai:gpt-5.4",
                    cwd=tmp_path,
                    approval_mode="confirm",
                )
            )
            await service.submit_user_message(state.session_id, "Inspect the repo")

            events = repository.read_session_events(state.session_id)
            transcript = repository.list_transcript_messages(state.session_id)
        finally:
            connection.close()

        model_started = [
            event.payload
            for event in events
            if isinstance(event.payload, ModelCallStarted)
        ]
        deltas = [
            event.payload
            for event in events
            if isinstance(event.payload, AssistantMessageDelta)
        ]
        completed = [
            event.payload
            for event in events
            if isinstance(event.payload, AssistantMessageCompleted)
        ]

        assert model_started[-1].provider == "openai"
        assert model_started[-1].model_name == "gpt-5.4"
        assert deltas == []
        assert completed[-1].parts[0].text == "Provider fallback complete."
        assert transcript[-1].parts[0].text == "Provider fallback complete."

    asyncio.run(scenario())


def test_provider_diagnostics_cli_reports_redacted_configuration(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    (tmp_path / ".env").write_text(
        "OPENAI_API_KEY=super-secret-openai\nOPENAI_BASE_URL=https://api.example\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "provider",
            "diagnostics",
            "--cwd",
            str(tmp_path),
            "--model-name",
            "openai:gpt-5.4",
            "--json",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["state"] == "ready"
    assert payload["selected_provider"] == "openai"
    assert payload["runtime_mode"] == "openai"
    assert "super-secret-openai" not in captured.out
    assert payload["diagnostics"][0]["api_key_present"] is True
    assert payload["diagnostics"][0]["api_key_source"] == "dotenv"
    assert payload["capability_preflight"]["credential_source"] == "dotenv"
    assert payload["capability_preflight"]["base_url_posture"] == "custom"
    assert payload["capability_preflight"]["scenario_preflight"][0]["status"] == (
        "ready"
    )
    assert "super-secret-openai" not in str(payload["capability_preflight"])


def test_provider_diagnostics_cli_prints_capability_preflight(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "secret-anthropic")
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)

    exit_code = main(
        [
            "provider",
            "diagnostics",
            "--cwd",
            str(tmp_path),
            "--model-name",
            "anthropic:claude-sonnet-4",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Capability preflight:" in captured.out
    assert "provider=anthropic" in captured.out
    assert "credential_source=process-env" in captured.out
    assert "streaming=supported" in captured.out
    assert "tool-call: not_automated" in captured.out
    assert "secret-anthropic" not in captured.out


def test_provider_canary_cli_writes_skipped_summary_without_credentials(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    output_dir = tmp_path / "canary-output"

    exit_code = main(
        [
            "provider",
            "canary",
            "run",
            "--cwd",
            str(tmp_path),
            "--model-name",
            "openai:gpt-5.4",
            "--scenario",
            "streaming-text",
            "--scenario",
            "approval",
            "--output-dir",
            str(output_dir),
            "--json",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    summary_path = output_dir / "provider-canary-summary.json"
    retained = json.loads(summary_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert payload["advisory"] is True
    assert payload["provider"] == "openai"
    assert payload["diagnostics_state"] == "local_fallback"
    assert [scenario["scenario_id"] for scenario in payload["scenarios"]] == [
        "streaming-text",
        "approval",
    ]
    matrix_scenarios = [
        entry["scenario_id"] for entry in payload["capability_matrix"]["entries"]
    ]
    assert matrix_scenarios == [
        "streaming-text",
        "approval",
    ]
    assert payload["capability_matrix"]["deterministic_release_blocking"] is False
    assert payload["capability_matrix"]["entries"][0]["redaction_status"] == "redacted"
    assert {scenario["outcome"] for scenario in payload["scenarios"]} == {"skipped"}
    assert retained == payload
    assert "API_KEY" in payload["next_actions"][0]


def test_provider_canary_cli_redacts_configured_secrets_in_summary(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    (tmp_path / ".env").write_text(
        "OPENAI_BASE_URL=https://api.example\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "canary-output"

    exit_code = main(
        [
            "provider",
            "canary",
            "run",
            "--cwd",
            str(tmp_path),
            "--model-name",
            "openai:gpt-5.4",
            "--output-dir",
            str(output_dir),
            "--json",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    retained = (output_dir / "provider-canary-summary.json").read_text(encoding="utf-8")

    assert exit_code == 0
    assert payload["diagnostics_state"] == "missing_credentials"
    assert payload["skipped_reason"] == "missing OPENAI_API_KEY"
    assert "https://api.example" not in captured.out
    assert "https://api.example" not in retained


def test_provider_canary_runs_default_multi_scenario_with_fake_provider(
    tmp_path: Path,
    monkeypatch,
) -> None:
    (tmp_path / ".env").write_text("OPENAI_API_KEY=dotenv-openai\n")

    def fake_build_openai_model_executor(
        model_name: str,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> PydanticAIModelExecutor:
        assert model_name == "gpt-5.4"
        assert api_key == "dotenv-openai"
        assert base_url is None
        return PydanticAIModelExecutor(
            FunctionModel(
                function=_provider_canary_model_response,
                stream_function=_provider_canary_stream_model_response,
                model_name=f"openai:{model_name}",
            )
        )

    monkeypatch.setattr(
        runtime_bootstrap,
        "build_openai_model_executor",
        fake_build_openai_model_executor,
    )
    output_dir = tmp_path / ".glassbox" / "provider-canary"

    summary = run_provider_canary_sync(
        tmp_path,
        model_name="openai:gpt-5.4",
        output_dir=output_dir,
    )
    retained = json.loads(
        (output_dir / "provider-canary-summary.json").read_text(encoding="utf-8")
    )

    assert [definition.scenario_id for definition in summary.scenario_definitions] == [
        *AGENTIC_CANARY_SCENARIOS
    ]
    outcomes = {
        scenario.scenario_id: scenario.outcome for scenario in summary.scenarios
    }
    assert outcomes["streaming-text"] == "passed"
    assert outcomes["tool-call"] == "skipped"
    assert outcomes["verification-loop-interaction"] == "skipped"
    assert summary.scenarios[0].automation_status == "automated"
    assert summary.scenarios[1].automation_status == "preflight_only"
    matrix_rows = {
        entry.scenario_id: entry for entry in summary.capability_matrix.entries
    }
    assert matrix_rows["streaming-text"].scenario_confidence == "observed"
    assert matrix_rows["tool-call-streaming"].tool_call_reliability == "assumed"
    assert matrix_rows["rate-limit-handling"].retry_posture == "rate_limit_unknown"
    assert retained == summary.model_dump(mode="json")
    assert "dotenv-openai" not in json.dumps(retained)


def test_provider_canary_evidence_cli_and_observability_surface_latest_run(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    output_dir = tmp_path / ".glassbox" / "provider-canary"

    run_exit_code = main(
        [
            "provider",
            "canary",
            "run",
            "--cwd",
            str(tmp_path),
            "--model-name",
            "openai:gpt-5.4",
            "--output-dir",
            str(output_dir),
            "--json",
        ]
    )
    capsys.readouterr()
    assert run_exit_code == 0

    evidence_exit_code = main(
        [
            "provider",
            "canary",
            "evidence",
            "--cwd",
            str(tmp_path),
            "--json",
        ]
    )
    evidence_output = capsys.readouterr()
    evidence_payload = json.loads(evidence_output.out)

    assert evidence_exit_code == 0
    assert evidence_payload["latest_status"] == "skipped"
    assert evidence_payload["summary_count"] == 1
    assert evidence_payload["skipped_count"] == len(AGENTIC_CANARY_SCENARIOS)
    assert evidence_payload["matrix_entry_count"] == len(AGENTIC_CANARY_SCENARIOS)

    observability_exit_code = main(
        [
            "observability",
            "status",
            "--cwd",
            str(tmp_path),
            "--json",
        ]
    )
    observability_output = capsys.readouterr()
    observability_payload = json.loads(observability_output.out)

    assert observability_exit_code == 0
    assert observability_payload["provider_canary"]["latest_status"] == "skipped"
    assert observability_payload["provider_canary"]["summary_count"] == 1


def _provider_function_model_response(messages, _agent_info) -> ModelResponse:
    user_prompt_text = _latest_user_prompt(messages)
    assert user_prompt_text == "Inspect the repo"
    return ModelResponse(parts=[TextPart(content="Provider stream complete.")])


async def _provider_stream_function_model_response(messages, _agent_info):
    _ = _provider_function_model_response(messages, _agent_info)
    yield "Provider stream "
    yield "complete."


def _provider_non_streaming_model_response(messages, _agent_info) -> ModelResponse:
    user_prompt_text = _latest_user_prompt(messages)
    assert user_prompt_text == "Inspect the repo"
    return ModelResponse(parts=[TextPart(content="Provider fallback complete.")])


def _provider_canary_model_response(messages, _agent_info) -> ModelResponse:
    assert _latest_user_prompt(messages) == (
        "Reply with a short provider canary acknowledgement."
    )
    return ModelResponse(parts=[TextPart(content="Provider canary complete.")])


async def _provider_canary_stream_model_response(messages, _agent_info):
    _ = _provider_canary_model_response(messages, _agent_info)
    yield "Provider canary "
    yield "complete."


def _latest_user_prompt(messages) -> str | None:
    for message in reversed(messages):
        if not isinstance(message, ModelRequest):
            continue
        for part in reversed(message.parts):
            if isinstance(part, UserPromptPart):
                if isinstance(part.content, str):
                    return part.content
                return "".join(
                    content.content
                    for content in part.content
                    if isinstance(content, TextContent)
                )
    return None
