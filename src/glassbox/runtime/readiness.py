"""First-run readiness checks for local Glassbox workspaces."""

import importlib.util
import sqlite3
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import computed_field

from glassbox.runtime.bootstrap_storage import RuntimeStoragePaths
from glassbox.runtime.bootstrap_storage import open_initialized_runtime_database
from glassbox.runtime.bootstrap_storage import resolve_runtime_storage_paths
from glassbox.runtime.provider_diagnostics import build_provider_diagnostics_report
from glassbox.runtime.repository_index import RepositoryIndexNotFoundError
from glassbox.runtime.repository_index import load_repository_index
from glassbox.runtime.repository_index import repository_index_path
from glassbox.tools import DEFAULT_TOOL_POLICY_PATH
from glassbox.tools import load_tool_policy_manifest
from glassbox.web.app import _STATIC_NEXT_DIR
from glassbox.web.spa_static import validate_spa_static_assets

type ReadinessCheckStatus = Literal["pass", "warning", "fail"]
type FirstRunReadinessStatus = Literal["ready", "needs_attention", "blocked"]


class FirstRunReadinessCheck(BaseModel):
    """One operator-facing first-run readiness check."""

    model_config = ConfigDict(extra="forbid")

    check_id: str
    title: str
    status: ReadinessCheckStatus
    detail: str
    next_actions: list[str] = []
    path: str | None = None


class FirstRunReadinessReport(BaseModel):
    """Aggregated first-run readiness report for a workspace."""

    model_config = ConfigDict(extra="forbid")

    status: FirstRunReadinessStatus
    workspace_root: Path
    database_path: Path
    checks: list[FirstRunReadinessCheck]

    @computed_field
    @property
    def summary_counts(self) -> dict[str, int]:
        return {
            "pass": sum(1 for check in self.checks if check.status == "pass"),
            "warning": sum(1 for check in self.checks if check.status == "warning"),
            "fail": sum(1 for check in self.checks if check.status == "fail"),
        }


def build_first_run_readiness_report(
    workspace_root: Path,
    *,
    db_path: Path | None = None,
    model_name: str | None = None,
    environ: Mapping[str, str] | None = None,
    static_root: Path | None = None,
) -> FirstRunReadinessReport:
    """Build a redacted first-run readiness report for a local workspace."""

    storage_paths = resolve_runtime_storage_paths(workspace_root, db_path=db_path)
    checks = [
        _runtime_dependencies_check(),
        _workspace_path_check(storage_paths.workspace_root),
        _writable_state_check(storage_paths.workspace_root),
        _database_bootstrap_check(storage_paths),
        _provider_configuration_check(
            storage_paths.workspace_root,
            model_name=model_name,
            environ=environ,
        ),
        _dashboard_static_assets_check(static_root or _STATIC_NEXT_DIR),
        _repository_index_check(storage_paths.workspace_root),
        _tool_policy_manifest_check(storage_paths.workspace_root),
    ]
    return FirstRunReadinessReport(
        status=_overall_status(checks),
        workspace_root=storage_paths.workspace_root,
        database_path=storage_paths.database_path,
        checks=checks,
    )


def _runtime_dependencies_check() -> FirstRunReadinessCheck:
    required_modules = ("fastapi", "pydantic", "textual", "uvicorn")
    missing_modules = [
        module
        for module in required_modules
        if importlib.util.find_spec(module) is None
    ]
    if sys.version_info[:2] < (3, 14) or sys.version_info[:2] >= (3, 15):
        return FirstRunReadinessCheck(
            check_id="runtime-dependencies",
            title="Python runtime dependencies",
            status="fail",
            detail=(
                "Glassbox requires Python >=3.14,<3.15; "
                f"current runtime is {sys.version.split()[0]}."
            ),
            next_actions=["run Glassbox through `uv run` from the repository root"],
        )
    if missing_modules:
        return FirstRunReadinessCheck(
            check_id="runtime-dependencies",
            title="Python runtime dependencies",
            status="fail",
            detail=f"Missing importable runtime modules: {', '.join(missing_modules)}.",
            next_actions=["run `uv sync` from the repository root"],
        )
    return FirstRunReadinessCheck(
        check_id="runtime-dependencies",
        title="Python runtime dependencies",
        status="pass",
        detail=f"Python {sys.version.split()[0]} can import required runtime modules.",
    )


def _workspace_path_check(workspace_root: Path) -> FirstRunReadinessCheck:
    if not workspace_root.exists():
        return FirstRunReadinessCheck(
            check_id="workspace-path",
            title="Workspace path",
            status="fail",
            detail=f"Workspace path does not exist: {workspace_root}",
            next_actions=["rerun with `--cwd PATH` pointing at a local checkout"],
            path=str(workspace_root),
        )
    if not workspace_root.is_dir():
        return FirstRunReadinessCheck(
            check_id="workspace-path",
            title="Workspace path",
            status="fail",
            detail=f"Workspace path is not a directory: {workspace_root}",
            next_actions=["rerun with `--cwd PATH` pointing at a local checkout"],
            path=str(workspace_root),
        )
    return FirstRunReadinessCheck(
        check_id="workspace-path",
        title="Workspace path",
        status="pass",
        detail=f"Workspace is a local directory: {workspace_root}",
        path=str(workspace_root),
    )


def _writable_state_check(workspace_root: Path) -> FirstRunReadinessCheck:
    state_dir = workspace_root / ".glassbox"
    if not workspace_root.is_dir():
        return FirstRunReadinessCheck(
            check_id="writable-state",
            title="Writable .glassbox state",
            status="fail",
            detail=(
                "Workspace is not a directory, so state cannot be written: "
                f"{workspace_root}"
            ),
            next_actions=["rerun with `--cwd PATH` pointing at a local checkout"],
            path=str(state_dir),
        )
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        probe_path = state_dir / ".readiness-write-check"
        probe_path.write_text("ok\n", encoding="utf-8")
        probe_path.unlink()
    except OSError as exc:
        return FirstRunReadinessCheck(
            check_id="writable-state",
            title="Writable .glassbox state",
            status="fail",
            detail=f"Unable to write Glassbox state at {state_dir}: {exc}",
            next_actions=[
                "fix workspace permissions or choose a writable `--cwd` before "
                "starting chat"
            ],
            path=str(state_dir),
        )
    return FirstRunReadinessCheck(
        check_id="writable-state",
        title="Writable .glassbox state",
        status="pass",
        detail=f"Workspace state directory is writable: {state_dir}",
        path=str(state_dir),
    )


def _database_bootstrap_check(
    storage_paths: RuntimeStoragePaths,
) -> FirstRunReadinessCheck:
    if not storage_paths.workspace_root.is_dir():
        return FirstRunReadinessCheck(
            check_id="database-bootstrap",
            title="Database bootstrap",
            status="fail",
            detail=(
                "Workspace is not a directory, so the Glassbox SQLite database "
                "cannot be initialized."
            ),
            next_actions=["rerun with `--cwd PATH` pointing at a local checkout"],
            path=str(storage_paths.database_path),
        )
    try:
        connection = open_initialized_runtime_database(storage_paths)
    except (OSError, ValueError, sqlite3.Error) as exc:
        return FirstRunReadinessCheck(
            check_id="database-bootstrap",
            title="Database bootstrap",
            status="fail",
            detail=f"Unable to initialize the Glassbox SQLite database: {exc}",
            next_actions=[
                "fix `.glassbox/` permissions or pass `--db-path` to a writable "
                "SQLite database path"
            ],
            path=str(storage_paths.database_path),
        )
    else:
        connection.close()
    return FirstRunReadinessCheck(
        check_id="database-bootstrap",
        title="Database bootstrap",
        status="pass",
        detail=f"SQLite schema is initialized at {storage_paths.database_path}",
        path=str(storage_paths.database_path),
    )


def _provider_configuration_check(
    workspace_root: Path,
    *,
    model_name: str | None,
    environ: Mapping[str, str] | None,
) -> FirstRunReadinessCheck:
    report = build_provider_diagnostics_report(
        workspace_root,
        explicit_model_name=model_name,
        environ=environ,
    )
    if report.state == "ready":
        return FirstRunReadinessCheck(
            check_id="provider-configuration",
            title="Provider configuration",
            status="pass",
            detail=(
                f"Provider diagnostics are ready for model "
                f"{report.selected_model_name} ({report.runtime_mode})."
            ),
            next_actions=report.onboarding_steps[:1],
        )
    if report.state == "local_fallback":
        return FirstRunReadinessCheck(
            check_id="provider-configuration",
            title="Provider configuration",
            status="warning",
            detail=(
                f"Provider credentials are not configured for "
                f"{report.selected_model_name}; deterministic local fallback remains "
                "available."
            ),
            next_actions=report.next_actions or report.onboarding_steps[:2],
        )
    return FirstRunReadinessCheck(
        check_id="provider-configuration",
        title="Provider configuration",
        status="fail",
        detail=(
            f"Provider diagnostics state is {report.state}: "
            f"{'; '.join(report.problems) or 'configuration is not usable'}"
        ),
        next_actions=report.next_actions,
    )


def _dashboard_static_assets_check(static_root: Path) -> FirstRunReadinessCheck:
    problems = validate_spa_static_assets(static_root)
    if problems:
        return FirstRunReadinessCheck(
            check_id="dashboard-static-assets",
            title="Dashboard static assets",
            status="warning",
            detail=problems[0],
            next_actions=[
                "`pnpm --dir frontend build`",
                "rerun `glassbox readiness check --cwd .`",
            ],
            path=str(static_root),
        )
    return FirstRunReadinessCheck(
        check_id="dashboard-static-assets",
        title="Dashboard static assets",
        status="pass",
        detail=f"Packaged dashboard assets are available at {static_root}",
        path=str(static_root),
    )


def _repository_index_check(workspace_root: Path) -> FirstRunReadinessCheck:
    path = repository_index_path(workspace_root)
    try:
        snapshot = load_repository_index(workspace_root)
    except RepositoryIndexNotFoundError:
        return FirstRunReadinessCheck(
            check_id="repository-index",
            title="Repository index posture",
            status="warning",
            detail=f"Repository index has not been built at {path}.",
            next_actions=["`glassbox repo index build --cwd .`"],
            path=str(path),
        )
    if snapshot.status == "fresh":
        return FirstRunReadinessCheck(
            check_id="repository-index",
            title="Repository index posture",
            status="pass",
            detail=f"Repository index is fresh with {len(snapshot.entries)} entries.",
            path=str(path),
        )
    status = "fail" if snapshot.status == "failed" else "warning"
    next_actions = ["`glassbox repo index build --cwd .`"]
    if snapshot.status == "failed":
        next_actions.insert(0, "`glassbox repo index status --cwd . --json`")
    return FirstRunReadinessCheck(
        check_id="repository-index",
        title="Repository index posture",
        status=status,
        detail=(
            f"Repository index is {snapshot.status.value}"
            + (f": {snapshot.failure_reason}" if snapshot.failure_reason else ".")
        ),
        next_actions=next_actions,
        path=str(path),
    )


def _tool_policy_manifest_check(workspace_root: Path) -> FirstRunReadinessCheck:
    policy_path = (workspace_root / DEFAULT_TOOL_POLICY_PATH).resolve()
    try:
        manifest = load_tool_policy_manifest(workspace_root)
    except ValueError as exc:
        return FirstRunReadinessCheck(
            check_id="tool-policy-manifest",
            title="Tool policy manifest",
            status="fail",
            detail=str(exc),
            next_actions=[
                "fix `glassbox-policy.json` or remove it to use the default "
                "review policy"
            ],
            path=str(policy_path),
        )
    if policy_path.exists():
        detail = (
            f"Loaded policy manifest with {len(manifest.rules)} tool rules and "
            f"{len(manifest.autonomy_rules)} autonomy rules."
        )
    else:
        detail = "No workspace policy manifest found; built-in review defaults apply."
    return FirstRunReadinessCheck(
        check_id="tool-policy-manifest",
        title="Tool policy manifest",
        status="pass",
        detail=detail,
        path=str(policy_path),
    )


def _overall_status(
    checks: list[FirstRunReadinessCheck],
) -> FirstRunReadinessStatus:
    if any(check.status == "fail" for check in checks):
        return "blocked"
    if any(check.status == "warning" for check in checks):
        return "needs_attention"
    return "ready"
