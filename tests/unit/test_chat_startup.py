"""Unit coverage for interactive chat startup summaries."""

from pathlib import Path
from uuid import UUID

from glassbox.cli.chat_startup import chat_startup_summary_lines
from glassbox.core import SessionConfig
from glassbox.core.types import AutonomyMode
from glassbox.runtime.autonomy import default_budget_for_autonomy_mode
from glassbox.runtime.provider_diagnostics import build_provider_diagnostics_report

SESSION_ID = UUID("00000000-0000-4000-8000-000000000123")


def test_chat_startup_summary_names_core_runtime_context(tmp_path: Path) -> None:
    config = _session_config(tmp_path, model_name="local-test-model")
    lines = chat_startup_summary_lines(
        session_id=SESSION_ID,
        config=config,
        database_path=tmp_path / ".glassbox" / "glassbox.sqlite3",
        dashboard_url="http://127.0.0.1:8765",
        dashboard_disabled=False,
        dashboard_asset_problems=[],
        provider_report=build_provider_diagnostics_report(
            tmp_path,
            explicit_model_name="local-test-model",
            environ={},
        ),
        include_prompt_suggestions=True,
    )

    assert lines[0] == "Glassbox chat ready"
    assert f"Session: {SESSION_ID}" in lines
    assert "Model: local-test-model" in lines
    assert any(line.startswith("Approval: confirm:") for line in lines)
    assert any(line.startswith("Autonomy: manual; budget manual") for line in lines)
    assert f"Workspace: {tmp_path}" in lines
    assert f"Database: {tmp_path / '.glassbox' / 'glassbox.sqlite3'}" in lines
    assert f"Dashboard: http://127.0.0.1:8765?session={SESSION_ID}" in lines
    assert "Provider: local ready (local-test-model)" in lines
    assert "Prompt ideas:" in lines


def test_chat_startup_summary_explains_dashboard_disabled(
    tmp_path: Path,
) -> None:
    config = _session_config(tmp_path, model_name="local-test-model")
    lines = chat_startup_summary_lines(
        session_id=SESSION_ID,
        config=config,
        database_path=tmp_path / ".glassbox" / "glassbox.sqlite3",
        dashboard_url=None,
        dashboard_disabled=True,
        dashboard_asset_problems=[],
        provider_report=build_provider_diagnostics_report(
            tmp_path,
            explicit_model_name="local-test-model",
            environ={},
        ),
        include_prompt_suggestions=False,
    )

    assert (
        "Dashboard: disabled by --no-dashboard; omit it to launch the cockpit" in lines
    )
    assert "Prompt ideas:" not in lines


def test_chat_startup_summary_explains_dashboard_asset_warning(
    tmp_path: Path,
) -> None:
    config = _session_config(tmp_path, model_name="local-test-model")
    lines = chat_startup_summary_lines(
        session_id=SESSION_ID,
        config=config,
        database_path=tmp_path / ".glassbox" / "glassbox.sqlite3",
        dashboard_url="http://127.0.0.1:8765",
        dashboard_disabled=False,
        dashboard_asset_problems=["missing SPA shell: static_next/index.html"],
        provider_report=build_provider_diagnostics_report(
            tmp_path,
            explicit_model_name="local-test-model",
            environ={},
        ),
        include_prompt_suggestions=False,
    )

    assert any("asset warning: missing SPA shell" in line for line in lines)


def test_chat_startup_summary_explains_provider_local_fallback(
    tmp_path: Path,
) -> None:
    config = _session_config(tmp_path, model_name="openai:gpt-5.4")
    lines = chat_startup_summary_lines(
        session_id=SESSION_ID,
        config=config,
        database_path=tmp_path / ".glassbox" / "glassbox.sqlite3",
        dashboard_url=None,
        dashboard_disabled=False,
        dashboard_asset_problems=[],
        provider_report=build_provider_diagnostics_report(
            tmp_path,
            explicit_model_name="openai:gpt-5.4",
            environ={},
        ),
        include_prompt_suggestions=False,
    )

    assert any(
        line.startswith("Provider: local fallback for openai:gpt-5.4") for line in lines
    )
    assert any("OPENAI_API_KEY" in line for line in lines)


def _session_config(tmp_path: Path, *, model_name: str) -> SessionConfig:
    autonomy_mode = AutonomyMode.MANUAL
    return SessionConfig(
        model_name=model_name,
        cwd=tmp_path,
        approval_mode="confirm",
        autonomy_mode=autonomy_mode,
        autonomy_budget=default_budget_for_autonomy_mode(autonomy_mode),
        autonomy_budget_preset=autonomy_mode.value,
    )
