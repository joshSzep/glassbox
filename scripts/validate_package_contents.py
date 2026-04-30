"""Validate built Glassbox wheel and sdist contents."""

from __future__ import annotations

import argparse
import sys
import tarfile
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = REPO_ROOT / "dist"

WHEEL_REQUIRED_FILES = (
    "glassbox/__init__.py",
    "glassbox/cli/__init__.py",
    "glassbox/cli/autonomy_commands.py",
    "glassbox/cli/branch_search_commands.py",
    "glassbox/cli/chat_startup.py",
    "glassbox/cli/command_guide.py",
    "glassbox/cli/job_commands.py",
    "glassbox/cli/memory_commands.py",
    "glassbox/cli/observability_commands.py",
    "glassbox/cli/provider_commands.py",
    "glassbox/cli/readiness_commands.py",
    "glassbox/cli/repository_commands.py",
    "glassbox/cli/replay_eval_commands.py",
    "glassbox/cli/task_commands.py",
    "glassbox/runtime/autonomy.py",
    "glassbox/runtime/background_jobs.py",
    "glassbox/runtime/branch_search.py",
    "glassbox/runtime/eval_profile_models.py",
    "glassbox/runtime/eval_recommendations.py",
    "glassbox/runtime/evals.py",
    "glassbox/runtime/observability.py",
    "glassbox/runtime/provider_canary.py",
    "glassbox/runtime/provider_diagnostics.py",
    "glassbox/runtime/provider_recommendations.py",
    "glassbox/runtime/readiness.py",
    "glassbox/runtime/repository_index.py",
    "glassbox/runtime/task_plan_capture.py",
    "glassbox/runtime/task_queries.py",
    "glassbox/runtime/verification.py",
    "glassbox/runtime/workspace_memory_capture.py",
    "glassbox/web/app.py",
    "glassbox/web/static_next/index.html",
)
WHEEL_REQUIRED_PREFIXES = ("glassbox/web/static_next/_next/",)
SDIST_REQUIRED_SUFFIXES = (
    "README.md",
    "LICENSE",
    "pyproject.toml",
    "docs/getting-started.md",
    "docs/operator-quickstart.md",
    "docs/daily-workflow-quickstart.md",
    "docs/providers.md",
    "docs/release-packaging.md",
    "docs/version-release-policy.md",
    "docs/dashboard-cockpit-contract.md",
    "docs/dogfooding.md",
    "docs/v9-command-surface-review.md",
    "docs/v9-dogfooding-summary.md",
    "docs/v9-eval-promotion-plan.md",
    "docs/v9-public-baseline.md",
    "docs/v9-release-candidate.md",
    "docs/v9-release-gate.md",
    "docs/v9-vocabulary.md",
    "docs/v7-release-candidate.md",
    "docs/v7-release-gate.md",
    "docs/manual-v7-release-validation.md",
    "docs/manual-v8-release-validation.md",
    "docs/manual-v9-release-validation.md",
    "docs/workspace-profiles.md",
    "docs/manual-qa-evidence-v7.md",
    "docs/manual-qa-evidence-v8.md",
    "docs/manual-qa-evidence-v9.md",
    "docs/autonomy-console.md",
    "docs/background-autonomy-release-smoke-v8.md",
    "docs/branch-search.md",
    "docs/recovery-maintenance-review-v8.md",
    "docs/repository-intelligence-index.md",
    "docs/task-plans.md",
    "docs/tasks-v8.md",
    "docs/tasks-v9.md",
    "docs/v8-auditable-autonomy-contract.md",
    "docs/v8-autonomy-baseline-inventory.md",
    "docs/v8-release-candidate.md",
    "docs/v8-release-gate.md",
    "docs/verification-loops.md",
    "docs/workspace-memory.md",
    "evals/profiles.json",
    "evals/coverage.json",
    "evals/impact.json",
    "evals/cases/autonomy.budget-exhaustion.json",
    "evals/cases/branch-search.candidate-comparison.json",
    "evals/cases/context.compaction-provenance.json",
    "evals/cases/long-run.cockpit-summary.json",
    "evals/cases/long-run.recovery-boundaries.json",
    "evals/cases/memory.context-drift.json",
    "evals/cases/repository-index.context-drift.json",
    "evals/cases/task-plan.proposal-capture.json",
    "evals/cases/task.continuation-blocked.json",
    "evals/cases/tool-attempt.partial-retry.json",
    "evals/cases/verification.failure.json",
    "evals/cases/verification.stale-cockpit.json",
    "evals/cases/verification.success.json",
    "evals/bundles/autonomy.budget-exhaustion.json",
    "evals/bundles/branch-search.candidate-comparison.json",
    "evals/bundles/context.compaction-provenance.json",
    "evals/bundles/long-run.cockpit-summary.json",
    "evals/bundles/long-run.recovery-boundaries.json",
    "evals/bundles/memory.context-drift.json",
    "evals/bundles/repository-index.context-drift.json",
    "evals/bundles/task-plan.proposal-capture.json",
    "evals/bundles/task.continuation-blocked.json",
    "evals/bundles/tool-attempt.partial-retry.json",
    "evals/bundles/verification.failure.json",
    "evals/bundles/verification.stale-cockpit.json",
    "evals/bundles/verification.success.json",
    "frontend/generated/openapi.json",
    "frontend/generated/api-types.ts",
    "scripts/background_autonomy_smoke.py",
    "scripts/validate_frontend_release_assets.py",
    "scripts/validate_installed_wheel_smoke.py",
    "scripts/validate_package_contents.py",
    "scripts/validate_v8_release_gate.py",
    "scripts/validate_v9_release_gate.py",
    "src/glassbox/cli/autonomy_commands.py",
    "src/glassbox/cli/branch_search_commands.py",
    "src/glassbox/cli/chat_startup.py",
    "src/glassbox/cli/command_guide.py",
    "src/glassbox/cli/job_commands.py",
    "src/glassbox/cli/memory_commands.py",
    "src/glassbox/cli/observability_commands.py",
    "src/glassbox/cli/provider_commands.py",
    "src/glassbox/cli/readiness_commands.py",
    "src/glassbox/cli/repository_commands.py",
    "src/glassbox/cli/replay_eval_commands.py",
    "src/glassbox/cli/task_commands.py",
    "src/glassbox/runtime/autonomy.py",
    "src/glassbox/runtime/background_jobs.py",
    "src/glassbox/runtime/branch_search.py",
    "src/glassbox/runtime/eval_profile_models.py",
    "src/glassbox/runtime/eval_recommendations.py",
    "src/glassbox/runtime/evals.py",
    "src/glassbox/runtime/observability.py",
    "src/glassbox/runtime/provider_canary.py",
    "src/glassbox/runtime/provider_diagnostics.py",
    "src/glassbox/runtime/provider_recommendations.py",
    "src/glassbox/runtime/readiness.py",
    "src/glassbox/runtime/repository_index.py",
    "src/glassbox/runtime/task_plan_capture.py",
    "src/glassbox/runtime/task_queries.py",
    "src/glassbox/runtime/verification.py",
    "src/glassbox/runtime/workspace_memory_capture.py",
    "src/glassbox/web/static_next/index.html",
)
SDIST_REQUIRED_PREFIXES = ("src/glassbox/web/static_next/_next/",)


def validate_distribution_contents(dist_dir: Path = DIST_DIR) -> list[str]:
    """Return package content problems for the newest wheel and sdist."""

    problems: list[str] = []
    wheel_path = _latest_file(dist_dir, "glassbox-*.whl")
    sdist_path = _latest_file(dist_dir, "glassbox-*.tar.gz")
    if wheel_path is None:
        problems.append(f"missing built wheel in {dist_dir}")
    else:
        problems.extend(validate_wheel_contents(wheel_path))
    if sdist_path is None:
        problems.append(f"missing built sdist in {dist_dir}")
    else:
        problems.extend(validate_sdist_contents(sdist_path))
    return problems


def validate_wheel_contents(wheel_path: Path) -> list[str]:
    """Return content problems for one built wheel."""

    problems: list[str] = []
    with zipfile.ZipFile(wheel_path) as wheel:
        names = set(wheel.namelist())
        for required_file in WHEEL_REQUIRED_FILES:
            if required_file not in names:
                problems.append(f"wheel missing required file: {required_file}")
        for required_prefix in WHEEL_REQUIRED_PREFIXES:
            if not _has_file_with_prefix(names, required_prefix):
                problems.append(f"wheel missing required file under: {required_prefix}")

        metadata_name = _single_matching_name(names, ".dist-info/METADATA")
        entry_points_name = _single_matching_name(names, ".dist-info/entry_points.txt")
        if metadata_name is None:
            problems.append("wheel missing dist-info METADATA")
        else:
            metadata = wheel.read(metadata_name).decode("utf-8", errors="replace")
            if "Requires-Dist: textual" not in metadata:
                problems.append("wheel metadata missing textual runtime dependency")
            if ">=6" not in metadata or "<7" not in metadata:
                problems.append("wheel metadata missing textual >=6,<7 bounds")
        if entry_points_name is None:
            problems.append("wheel missing console script entry_points.txt")
        else:
            entry_points = wheel.read(entry_points_name).decode(
                "utf-8",
                errors="replace",
            )
            if "glassbox = glassbox.cli:main" not in entry_points:
                problems.append("wheel missing glassbox console script entrypoint")
    return problems


def validate_sdist_contents(sdist_path: Path) -> list[str]:
    """Return content problems for one built source distribution."""

    problems: list[str] = []
    with tarfile.open(sdist_path, mode="r:gz") as sdist:
        names = {member.name for member in sdist.getmembers() if member.isfile()}
    for required_suffix in SDIST_REQUIRED_SUFFIXES:
        if not _has_file_with_suffix(names, required_suffix):
            problems.append(f"sdist missing required file: {required_suffix}")
    for required_prefix in SDIST_REQUIRED_PREFIXES:
        if not _has_file_containing_prefix(names, required_prefix):
            problems.append(f"sdist missing required file under: {required_prefix}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate built Glassbox wheel and sdist contents."
    )
    parser.add_argument(
        "--dist-dir",
        type=Path,
        default=DIST_DIR,
        help="directory containing built distribution artifacts",
    )
    args = parser.parse_args(argv)

    problems = validate_distribution_contents(args.dist_dir.resolve())
    if problems:
        print("Package content validation failed:", file=sys.stderr)
        for problem in problems:
            print(f"- {problem}", file=sys.stderr)
        return 1

    print("Built wheel and sdist contain required Glassbox release files.")
    return 0


def _latest_file(directory: Path, pattern: str) -> Path | None:
    paths = sorted(directory.glob(pattern), key=lambda path: path.stat().st_mtime)
    if not paths:
        return None
    return paths[-1]


def _has_file_with_prefix(names: set[str], prefix: str) -> bool:
    return any(name.startswith(prefix) and not name.endswith("/") for name in names)


def _has_file_with_suffix(names: set[str], suffix: str) -> bool:
    return any(name == suffix or name.endswith(f"/{suffix}") for name in names)


def _has_file_containing_prefix(names: set[str], prefix: str) -> bool:
    return any(f"/{prefix}" in name and not name.endswith("/") for name in names)


def _single_matching_name(names: set[str], suffix: str) -> str | None:
    matches = sorted(name for name in names if name.endswith(suffix))
    return matches[0] if matches else None


if __name__ == "__main__":
    raise SystemExit(main())
