"""Unit coverage for first-run readiness checks."""

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


def test_first_run_readiness_warns_for_missing_live_provider(
    tmp_path: Path,
) -> None:
    static_root = _write_spa_build(tmp_path / "static_next")
    _seed_repository(tmp_path)
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
    assert "OPENAI_API_KEY" in provider_check.next_actions[0]


def test_first_run_readiness_warns_for_missing_dashboard_assets(
    tmp_path: Path,
) -> None:
    _seed_repository(tmp_path)
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


def test_first_run_readiness_warns_for_stale_repository_index(
    tmp_path: Path,
) -> None:
    static_root = _write_spa_build(tmp_path / "static_next")
    _seed_repository(tmp_path)
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
    assert "`glassbox repo index build --cwd .`" in index_check.next_actions


def test_first_run_readiness_blocks_unwritable_state(tmp_path: Path) -> None:
    static_root = _write_spa_build(tmp_path / "static_next")
    _seed_repository(tmp_path)
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
