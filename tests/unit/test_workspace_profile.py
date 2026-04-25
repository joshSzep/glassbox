"""Unit tests for repository-owned workspace profile defaults."""

import json
from pathlib import Path

import pytest

from glassbox.runtime.workspace_profile import DEFAULT_APPROVAL_MODE
from glassbox.runtime.workspace_profile import DEFAULT_MODEL_NAME
from glassbox.runtime.workspace_profile import load_workspace_profile
from glassbox.runtime.workspace_profile import resolve_eval_profile_default
from glassbox.runtime.workspace_profile import resolve_session_start_defaults
from glassbox.runtime.workspace_profile import workspace_profile_path


def test_load_workspace_profile_allows_missing_file(tmp_path: Path) -> None:
    assert load_workspace_profile(tmp_path) is None


def test_load_workspace_profile_parses_runtime_and_verification_defaults(
    tmp_path: Path,
) -> None:
    _write_workspace_profile(
        tmp_path,
        {
            "profile_version": 1,
            "runtime": {
                "model_name": "anthropic:claude-sonnet-4",
                "approval_mode": "review",
            },
            "verification": {"eval_profile": "commit-smoke"},
        },
    )

    profile = load_workspace_profile(tmp_path)

    assert profile is not None
    assert profile.runtime.model_name == "anthropic:claude-sonnet-4"
    assert profile.runtime.approval_mode == "review"
    assert profile.verification.eval_profile == "commit-smoke"


def test_resolve_session_start_defaults_uses_profile_before_built_ins(
    tmp_path: Path,
) -> None:
    _write_workspace_profile(
        tmp_path,
        {
            "profile_version": 1,
            "runtime": {
                "model_name": "openai:gpt-4.1",
                "approval_mode": "on-request",
            },
        },
    )

    defaults = resolve_session_start_defaults(
        tmp_path,
        explicit_model_name=None,
        explicit_approval_mode=None,
    )

    assert defaults.model_name == "openai:gpt-4.1"
    assert defaults.model_name_source == "workspace-profile"
    assert defaults.approval_mode == "on-request"
    assert defaults.approval_mode_source == "workspace-profile"


def test_resolve_session_start_defaults_keeps_explicit_cli_flags_first(
    tmp_path: Path,
) -> None:
    _write_workspace_profile(
        tmp_path,
        {
            "profile_version": 1,
            "runtime": {
                "model_name": "anthropic:claude-sonnet-4",
                "approval_mode": "never",
            },
        },
    )

    defaults = resolve_session_start_defaults(
        tmp_path,
        explicit_model_name="openai:gpt-5.4",
        explicit_approval_mode="confirm",
    )

    assert defaults.model_name == "openai:gpt-5.4"
    assert defaults.model_name_source == "cli"
    assert defaults.approval_mode == "confirm"
    assert defaults.approval_mode_source == "cli"


def test_resolve_session_start_defaults_falls_back_to_built_ins(
    tmp_path: Path,
) -> None:
    defaults = resolve_session_start_defaults(
        tmp_path,
        explicit_model_name=None,
        explicit_approval_mode=None,
    )

    assert defaults.model_name == DEFAULT_MODEL_NAME
    assert defaults.model_name_source == "built-in"
    assert defaults.approval_mode == DEFAULT_APPROVAL_MODE
    assert defaults.approval_mode_source == "built-in"


def test_resolve_eval_profile_default_uses_profile_when_cli_absent(
    tmp_path: Path,
) -> None:
    _write_workspace_profile(
        tmp_path,
        {
            "profile_version": 1,
            "verification": {"eval_profile": "commit-smoke"},
        },
    )

    default = resolve_eval_profile_default(tmp_path, explicit_profile=None)

    assert default.profile_id == "commit-smoke"
    assert default.source == "workspace-profile"


def test_resolve_eval_profile_default_keeps_explicit_cli_profile(
    tmp_path: Path,
) -> None:
    _write_workspace_profile(
        tmp_path,
        {
            "profile_version": 1,
            "verification": {"eval_profile": "commit-smoke"},
        },
    )

    default = resolve_eval_profile_default(tmp_path, explicit_profile="release")

    assert default.profile_id == "release"
    assert default.source == "cli"


@pytest.mark.parametrize(
    "payload",
    [
        {"profile_version": 999},
        {"profile_version": 1, "runtime": {"approval_mode": "always"}},
        {"profile_version": 1, "runtime": {"provider_api_key": "secret"}},
    ],
)
def test_load_workspace_profile_rejects_invalid_configuration(
    tmp_path: Path,
    payload: dict[str, object],
) -> None:
    _write_workspace_profile(tmp_path, payload)

    with pytest.raises(ValueError, match="invalid workspace profile"):
        load_workspace_profile(tmp_path)


def _write_workspace_profile(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = workspace_profile_path(tmp_path)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path
