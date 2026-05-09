"""Unit coverage for first-run readiness checks."""

import json
from datetime import UTC
from datetime import datetime
from pathlib import Path

from glassbox.core import RepositoryIndexFreshness
from glassbox.core.models import RepositoryIndexSnapshot
from glassbox.runtime.readiness import build_first_run_readiness_report
from glassbox.runtime.repository_index import build_and_write_repository_index
from glassbox.runtime.repository_index import write_repository_index


def test_first_run_readiness_reports_healthy_workspace(tmp_path: Path) -> None:
    static_root = _write_spa_build(tmp_path / "static_next")
    _seed_repository(tmp_path)
    _seed_eval_profiles(tmp_path)
    build_and_write_repository_index(tmp_path)

    report = build_first_run_readiness_report(
        tmp_path,
        model_name="local-test-model",
        environ={},
        static_root=static_root,
    )

    assert report.status == "ready"
    assert report.summary_counts["fail"] == 0
    assert report.summary_counts["warning"] == 0
    assert _check_status(report, "provider-configuration") == "pass"
    assert _check_status(report, "dashboard-static-assets") == "pass"
    assert _check_status(report, "repository-index") == "pass"
    assert "command recipe" in _check(report, "repository-index").detail
    assert "release surface" in _check(report, "repository-index").detail
    assert _check_status(report, "eval-profile-availability") == "pass"
    assert _check_status(report, "package-build-posture") == "pass"
    profile_check = _check(report, "workspace-profile-defaults")
    assert profile_check.status == "pass"
    assert "No glassbox.profile.json found" in profile_check.detail
    assert "review `docs/workspace-profiles.md` profile templates" in (
        profile_check.next_actions
    )


def test_first_run_readiness_warns_for_partial_workspace_profile(
    tmp_path: Path,
) -> None:
    static_root = _write_spa_build(tmp_path / "static_next")
    _seed_repository(tmp_path)
    _seed_eval_profiles(tmp_path)
    build_and_write_repository_index(tmp_path)
    _write_workspace_profile(
        tmp_path,
        {
            "profile_version": 1,
            "runtime": {"model_name": "local-test-model"},
        },
    )

    report = build_first_run_readiness_report(
        tmp_path,
        model_name="local-test-model",
        environ={},
        static_root=static_root,
    )
    profile_check = _check(report, "workspace-profile-defaults")

    assert report.status == "needs_attention"
    assert profile_check.status == "warning"
    assert "runtime.approval_mode" in profile_check.detail
    assert "runtime.autonomy_mode" in profile_check.detail
    assert "verification.eval_profile" in profile_check.detail
    assert "review `docs/workspace-profiles.md` profile templates" in (
        profile_check.next_actions
    )


def test_first_run_readiness_blocks_invalid_workspace_profile(
    tmp_path: Path,
) -> None:
    static_root = _write_spa_build(tmp_path / "static_next")
    _seed_repository(tmp_path)
    _seed_eval_profiles(tmp_path)
    build_and_write_repository_index(tmp_path)
    _write_workspace_profile(
        tmp_path,
        {
            "profile_version": 1,
            "runtime": {"provider_api_key": "secret"},
        },
    )

    report = build_first_run_readiness_report(
        tmp_path,
        model_name=None,
        environ={},
        static_root=static_root,
    )
    profile_check = _check(report, "workspace-profile-defaults")
    provider_check = _check(report, "provider-configuration")

    assert report.status == "blocked"
    assert profile_check.status == "fail"
    assert "Workspace profile is invalid" in profile_check.detail
    assert "review `docs/workspace-profiles.md` profile templates" in (
        profile_check.next_actions
    )
    assert provider_check.status == "fail"
    assert "invalid_workspace_profile" in provider_check.detail


def test_first_run_readiness_warns_for_missing_live_provider(
    tmp_path: Path,
) -> None:
    static_root = _write_spa_build(tmp_path / "static_next")
    _seed_repository(tmp_path)
    _seed_eval_profiles(tmp_path)
    build_and_write_repository_index(tmp_path)

    report = build_first_run_readiness_report(
        tmp_path,
        model_name="openai:gpt-5.4",
        environ={},
        static_root=static_root,
    )
    provider_check = _check(report, "provider-configuration")

    assert report.status == "needs_attention"
    assert provider_check.status == "warning"
    assert "local fallback remains available" in provider_check.detail
    assert (
        "`glassbox provider diagnostics --cwd . --model-name openai:gpt-5.4`"
        in provider_check.next_actions
    )
    assert any("OPENAI_API_KEY" in action for action in provider_check.next_actions)


def test_first_run_readiness_warns_for_missing_dashboard_assets(
    tmp_path: Path,
) -> None:
    _seed_repository(tmp_path)
    _seed_eval_profiles(tmp_path)
    build_and_write_repository_index(tmp_path)

    report = build_first_run_readiness_report(
        tmp_path,
        model_name="local-test-model",
        environ={},
        static_root=tmp_path / "missing-static-next",
    )
    dashboard_check = _check(report, "dashboard-static-assets")

    assert report.status == "needs_attention"
    assert dashboard_check.status == "warning"
    assert "missing SPA shell" in dashboard_check.detail
    assert "`pnpm --dir frontend build`" in dashboard_check.next_actions
    assert "`glassbox readiness check --cwd .`" in dashboard_check.next_actions


def test_first_run_readiness_warns_for_stale_repository_index(
    tmp_path: Path,
) -> None:
    static_root = _write_spa_build(tmp_path / "static_next")
    _seed_repository(tmp_path)
    _seed_eval_profiles(tmp_path)
    build_and_write_repository_index(tmp_path)
    (tmp_path / "src" / "sample.py").write_text(
        "class UsefulThing:\n    pass\n\ndef changed() -> None:\n    pass\n",
        encoding="utf-8",
    )

    report = build_first_run_readiness_report(
        tmp_path,
        model_name="local-test-model",
        environ={},
        static_root=static_root,
    )
    index_check = _check(report, "repository-index")

    assert report.status == "needs_attention"
    assert index_check.status == "warning"
    assert "Repository index is stale" in index_check.detail
    assert "`glassbox repo index status --cwd .`" in index_check.next_actions
    assert "`glassbox repo index build --cwd .`" in index_check.next_actions
    assert "`glassbox readiness check --cwd .`" in index_check.next_actions


def test_first_run_readiness_blocks_unwritable_state(tmp_path: Path) -> None:
    static_root = _write_spa_build(tmp_path / "static_next")
    _seed_repository(tmp_path)
    _seed_eval_profiles(tmp_path)
    (tmp_path / ".glassbox").write_text("not a directory\n", encoding="utf-8")

    report = build_first_run_readiness_report(
        tmp_path,
        model_name="local-test-model",
        environ={},
        static_root=static_root,
    )

    assert report.status == "blocked"
    assert _check_status(report, "writable-state") == "fail"
    assert _check_status(report, "database-bootstrap") == "fail"


def test_first_run_readiness_does_not_create_missing_workspace(
    tmp_path: Path,
) -> None:
    static_root = _write_spa_build(tmp_path / "static_next")
    missing_workspace = tmp_path / "missing"

    report = build_first_run_readiness_report(
        missing_workspace,
        model_name="local-test-model",
        environ={},
        static_root=static_root,
    )

    assert report.status == "blocked"
    assert missing_workspace.exists() is False
    assert _check_status(report, "workspace-path") == "fail"
    assert _check_status(report, "writable-state") == "fail"
    assert _check_status(report, "database-bootstrap") == "fail"


def test_first_run_readiness_blocks_failed_repository_index(
    tmp_path: Path,
) -> None:
    static_root = _write_spa_build(tmp_path / "static_next")
    _seed_repository(tmp_path)
    _seed_eval_profiles(tmp_path)
    write_repository_index(
        tmp_path,
        RepositoryIndexSnapshot(
            workspace_root=tmp_path,
            status=RepositoryIndexFreshness.FAILED,
            built_at=datetime.now(UTC),
            failure_reason="parser crash",
        ),
    )

    report = build_first_run_readiness_report(
        tmp_path,
        model_name="local-test-model",
        environ={},
        static_root=static_root,
    )
    index_check = _check(report, "repository-index")

    assert report.status == "blocked"
    assert index_check.status == "fail"
    assert "parser crash" in index_check.detail
    assert "`glassbox repo index status --cwd . --json`" in index_check.next_actions
    assert "`glassbox repo index build --cwd .`" in index_check.next_actions


def test_first_run_readiness_warns_for_missing_eval_profiles(
    tmp_path: Path,
) -> None:
    static_root = _write_spa_build(tmp_path / "static_next")
    _seed_repository(tmp_path)
    build_and_write_repository_index(tmp_path)

    report = build_first_run_readiness_report(
        tmp_path,
        model_name="local-test-model",
        environ={},
        static_root=static_root,
    )
    eval_check = _check(report, "eval-profile-availability")

    assert report.status == "needs_attention"
    assert eval_check.status == "warning"
    assert "Eval profile manifest is not ready" in eval_check.detail
    assert (
        "`glassbox eval profile list --cwd .` after adding evals/profiles.json"
        in eval_check.next_actions
    )


def test_first_run_readiness_warns_for_missing_project_metadata(
    tmp_path: Path,
) -> None:
    static_root = _write_spa_build(tmp_path / "static_next")
    (tmp_path / "README.md").write_text("# Fixture\n", encoding="utf-8")
    _seed_eval_profiles(tmp_path)
    build_and_write_repository_index(tmp_path)

    report = build_first_run_readiness_report(
        tmp_path,
        model_name="local-test-model",
        environ={},
        static_root=static_root,
    )
    package_check = _check(report, "package-build-posture")

    assert report.status == "needs_attention"
    assert package_check.status == "warning"
    assert "no pyproject.toml was found" in package_check.detail
    assert (
        "`glassbox readiness check --cwd PATH` from a repository root"
        in package_check.next_actions
    )


def _check(report, check_id: str):
    return next(check for check in report.checks if check.check_id == check_id)


def _check_status(report, check_id: str) -> str:
    return _check(report, check_id).status


def _write_spa_build(root: Path) -> Path:
    chunk_dir = root / "_next" / "static" / "chunks"
    chunk_dir.mkdir(parents=True)
    (root / "index.html").write_text(
        "<!doctype html><html><head>"
        '<script src="/app/_next/static/chunks/app.js"></script>'
        "</head><body><main>Glassbox Operator Console</main></body></html>",
        encoding="utf-8",
    )
    (chunk_dir / "app.js").write_text("console.log('glassbox');", encoding="utf-8")
    return root


def _seed_repository(root: Path) -> None:
    (root / "src").mkdir()
    (root / "README.md").write_text("# Fixture\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\n',
        encoding="utf-8",
    )
    (root / "src" / "sample.py").write_text(
        "class UsefulThing:\n    pass\n",
        encoding="utf-8",
    )


def _seed_eval_profiles(root: Path) -> None:
    evals_dir = root / "evals"
    evals_dir.mkdir()
    (evals_dir / "profiles.json").write_text(
        """{
  "manifest_version": 1,
  "profiles": [
    {
      "profile_id": "commit-smoke",
      "title": "Commit smoke",
      "verification_stage": "commit-time"
    }
  ]
}
""",
        encoding="utf-8",
    )


def _write_workspace_profile(root: Path, payload: dict[str, object]) -> None:
    (root / "glassbox.profile.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
