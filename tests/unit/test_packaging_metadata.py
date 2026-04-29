"""Packaging metadata tests for installed Glassbox distributions."""

import io
import tarfile
import tomllib
import zipfile
from pathlib import Path

from scripts.validate_package_contents import validate_distribution_contents
from scripts.validate_package_contents import validate_sdist_contents
from scripts.validate_package_contents import validate_wheel_contents

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def _pyproject() -> dict:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def test_project_metadata_includes_terminal_runtime_dependencies() -> None:
    project = _pyproject()["project"]

    assert project["scripts"]["glassbox"] == "glassbox.cli:main"
    assert "textual>=6,<7" in project["dependencies"]
    assert all(
        "node" not in dependency.lower() for dependency in project["dependencies"]
    )
    assert all(
        "pnpm" not in dependency.lower() for dependency in project["dependencies"]
    )


def test_build_targets_package_dashboard_static_assets() -> None:
    hatch_config = _pyproject()["tool"]["hatch"]["build"]["targets"]

    assert "src/glassbox/web/static_next/**" in hatch_config["wheel"]["artifacts"]
    assert "src/glassbox/web/static_next/**" in hatch_config["sdist"]["artifacts"]
    assert "src/glassbox" in hatch_config["wheel"]["packages"]
    assert "/evals" in hatch_config["sdist"]["include"]
    assert "/frontend/generated" in hatch_config["sdist"]["include"]
    assert "/scripts" in hatch_config["sdist"]["include"]


def test_distribution_content_validator_accepts_complete_wheel_and_sdist(
    tmp_path: Path,
) -> None:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    wheel_path = dist_dir / "glassbox-0.1.0-py3-none-any.whl"
    sdist_path = dist_dir / "glassbox-0.1.0.tar.gz"
    _write_wheel(wheel_path)
    _write_sdist(sdist_path)

    assert validate_distribution_contents(dist_dir) == []


def test_wheel_content_validator_reports_missing_metadata_and_assets(
    tmp_path: Path,
) -> None:
    wheel_path = tmp_path / "glassbox-0.1.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel_path, mode="w") as wheel:
        wheel.writestr("glassbox/__init__.py", "")
        wheel.writestr("glassbox/cli/__init__.py", "")
        wheel.writestr("glassbox/web/app.py", "")

    problems = validate_wheel_contents(wheel_path)

    assert (
        "wheel missing required file: glassbox/web/static_next/index.html" in problems
    )
    assert "wheel missing required file: glassbox/cli/task_commands.py" in problems
    assert "wheel missing required file: glassbox/runtime/task_queries.py" in problems
    assert (
        "wheel missing required file under: glassbox/web/static_next/_next/" in problems
    )
    assert "wheel missing dist-info METADATA" in problems
    assert "wheel missing console script entry_points.txt" in problems


def test_sdist_content_validator_reports_missing_docs_and_static_assets(
    tmp_path: Path,
) -> None:
    sdist_path = tmp_path / "glassbox-0.1.0.tar.gz"
    _write_sdist(sdist_path, include_static_assets=False, include_docs=False)

    problems = validate_sdist_contents(sdist_path)

    assert "sdist missing required file: docs/release-packaging.md" in problems
    assert "sdist missing required file: docs/getting-started.md" in problems
    assert "sdist missing required file: docs/providers.md" in problems
    assert "sdist missing required file: docs/workspace-profiles.md" in problems
    assert "sdist missing required file: docs/manual-qa-evidence-v7.md" in problems
    assert (
        "sdist missing required file: docs/v8-auditable-autonomy-contract.md"
        in problems
    )
    assert "sdist missing required file: docs/v8-release-gate.md" in problems
    assert "sdist missing required file: evals/profiles.json" in problems
    assert "sdist missing required file: frontend/generated/openapi.json" in problems
    assert (
        "sdist missing required file: scripts/validate_v8_release_gate.py" in problems
    )
    assert (
        "sdist missing required file: docs/manual-v7-release-validation.md" in problems
    )
    assert "sdist missing required file: docs/v7-release-candidate.md" in problems
    assert "sdist missing required file: docs/v7-release-gate.md" in problems
    assert (
        "sdist missing required file: src/glassbox/web/static_next/index.html"
        in problems
    )
    assert (
        "sdist missing required file under: src/glassbox/web/static_next/_next/"
        in problems
    )


def _write_wheel(path: Path) -> None:
    with zipfile.ZipFile(path, mode="w") as wheel:
        wheel.writestr("glassbox/__init__.py", "")
        wheel.writestr("glassbox/cli/__init__.py", "")
        wheel.writestr("glassbox/cli/autonomy_commands.py", "")
        wheel.writestr("glassbox/cli/branch_search_commands.py", "")
        wheel.writestr("glassbox/cli/job_commands.py", "")
        wheel.writestr("glassbox/cli/memory_commands.py", "")
        wheel.writestr("glassbox/cli/observability_commands.py", "")
        wheel.writestr("glassbox/cli/repository_commands.py", "")
        wheel.writestr("glassbox/cli/task_commands.py", "")
        wheel.writestr("glassbox/runtime/autonomy.py", "")
        wheel.writestr("glassbox/runtime/background_jobs.py", "")
        wheel.writestr("glassbox/runtime/branch_search.py", "")
        wheel.writestr("glassbox/runtime/observability.py", "")
        wheel.writestr("glassbox/runtime/repository_index.py", "")
        wheel.writestr("glassbox/runtime/task_plan_capture.py", "")
        wheel.writestr("glassbox/runtime/task_queries.py", "")
        wheel.writestr("glassbox/runtime/verification.py", "")
        wheel.writestr("glassbox/runtime/workspace_memory_capture.py", "")
        wheel.writestr("glassbox/web/app.py", "")
        wheel.writestr("glassbox/web/static_next/index.html", "<html></html>")
        wheel.writestr("glassbox/web/static_next/_next/static/chunks/app.js", "")
        wheel.writestr(
            "glassbox-0.1.0.dist-info/METADATA",
            "Name: glassbox\nRequires-Dist: textual<7,>=6\n",
        )
        wheel.writestr(
            "glassbox-0.1.0.dist-info/entry_points.txt",
            "[console_scripts]\nglassbox = glassbox.cli:main\n",
        )


def _write_sdist(
    path: Path,
    *,
    include_static_assets: bool = True,
    include_docs: bool = True,
) -> None:
    with tarfile.open(path, mode="w:gz") as sdist:
        _add_tar_text(sdist, "glassbox-0.1.0/README.md", "# Glassbox\n")
        _add_tar_text(sdist, "glassbox-0.1.0/LICENSE", "license\n")
        _add_tar_text(sdist, "glassbox-0.1.0/pyproject.toml", "[project]\n")
        if include_docs:
            _add_tar_text(
                sdist,
                "glassbox-0.1.0/docs/getting-started.md",
                "# Getting Started\n",
            )
            _add_tar_text(
                sdist,
                "glassbox-0.1.0/docs/providers.md",
                "# Provider Setup\n",
            )
            _add_tar_text(
                sdist,
                "glassbox-0.1.0/docs/release-packaging.md",
                "# Release Packaging\n",
            )
            _add_tar_text(
                sdist,
                "glassbox-0.1.0/docs/v7-release-candidate.md",
                "# v7 Release Candidate\n",
            )
            _add_tar_text(
                sdist,
                "glassbox-0.1.0/docs/v7-release-gate.md",
                "# v7 Release Gate\n",
            )
            _add_tar_text(
                sdist,
                "glassbox-0.1.0/docs/manual-v7-release-validation.md",
                "# v7 Manual Release Validation\n",
            )
            _add_tar_text(
                sdist,
                "glassbox-0.1.0/docs/workspace-profiles.md",
                "# Workspace Profiles\n",
            )
            _add_tar_text(
                sdist,
                "glassbox-0.1.0/docs/manual-qa-evidence-v7.md",
                "# v7 Manual QA Evidence Archive\n",
            )
            for doc_path in (
                "docs/autonomy-console.md",
                "docs/background-autonomy-release-smoke-v8.md",
                "docs/branch-search.md",
                "docs/recovery-maintenance-review-v8.md",
                "docs/repository-intelligence-index.md",
                "docs/task-plans.md",
                "docs/tasks-v8.md",
                "docs/v8-auditable-autonomy-contract.md",
                "docs/v8-autonomy-baseline-inventory.md",
                "docs/v8-release-gate.md",
                "docs/verification-loops.md",
                "docs/workspace-memory.md",
            ):
                _add_tar_text(sdist, f"glassbox-0.1.0/{doc_path}", "# v8\n")
            for eval_path in (
                "evals/profiles.json",
                "evals/coverage.json",
                "evals/impact.json",
                "evals/cases/autonomy.budget-exhaustion.json",
                "evals/cases/branch-search.candidate-comparison.json",
                "evals/cases/memory.context-drift.json",
                "evals/cases/repository-index.context-drift.json",
                "evals/cases/task-plan.proposal-capture.json",
                "evals/cases/task.continuation-blocked.json",
                "evals/cases/verification.failure.json",
                "evals/cases/verification.success.json",
                "evals/bundles/autonomy.budget-exhaustion.json",
                "evals/bundles/branch-search.candidate-comparison.json",
                "evals/bundles/memory.context-drift.json",
                "evals/bundles/repository-index.context-drift.json",
                "evals/bundles/task-plan.proposal-capture.json",
                "evals/bundles/task.continuation-blocked.json",
                "evals/bundles/verification.failure.json",
                "evals/bundles/verification.success.json",
            ):
                _add_tar_text(sdist, f"glassbox-0.1.0/{eval_path}", "{}\n")
            _add_tar_text(
                sdist,
                "glassbox-0.1.0/frontend/generated/openapi.json",
                "{}\n",
            )
            _add_tar_text(
                sdist,
                "glassbox-0.1.0/frontend/generated/api-types.ts",
                "export type Api = unknown;\n",
            )
            for script_path in (
                "scripts/background_autonomy_smoke.py",
                "scripts/validate_installed_wheel_smoke.py",
                "scripts/validate_package_contents.py",
                "scripts/validate_v8_release_gate.py",
            ):
                _add_tar_text(sdist, f"glassbox-0.1.0/{script_path}", "\n")
            for source_path in (
                "src/glassbox/cli/autonomy_commands.py",
                "src/glassbox/cli/branch_search_commands.py",
                "src/glassbox/cli/job_commands.py",
                "src/glassbox/cli/memory_commands.py",
                "src/glassbox/cli/observability_commands.py",
                "src/glassbox/cli/repository_commands.py",
                "src/glassbox/cli/task_commands.py",
                "src/glassbox/runtime/autonomy.py",
                "src/glassbox/runtime/background_jobs.py",
                "src/glassbox/runtime/branch_search.py",
                "src/glassbox/runtime/observability.py",
                "src/glassbox/runtime/repository_index.py",
                "src/glassbox/runtime/task_plan_capture.py",
                "src/glassbox/runtime/task_queries.py",
                "src/glassbox/runtime/verification.py",
                "src/glassbox/runtime/workspace_memory_capture.py",
            ):
                _add_tar_text(sdist, f"glassbox-0.1.0/{source_path}", "\n")
        if include_static_assets:
            _add_tar_text(
                sdist,
                "glassbox-0.1.0/src/glassbox/web/static_next/index.html",
                "<html></html>",
            )
            _add_tar_text(
                sdist,
                "glassbox-0.1.0/src/glassbox/web/static_next/_next/static/chunks/app.js",
                "console.log('glassbox');\n",
            )


def _add_tar_text(sdist: tarfile.TarFile, name: str, content: str) -> None:
    encoded = content.encode("utf-8")
    info = tarfile.TarInfo(name)
    info.size = len(encoded)
    sdist.addfile(info, io.BytesIO(encoded))
