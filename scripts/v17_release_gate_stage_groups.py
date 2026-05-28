"""V17 release-gate stage groups by evidence family."""

from pathlib import Path

from scripts import validate_v16_release_gate as v16_gate
from scripts.validate_v6_release_gate import GateStage

V17_LOCAL_HANDOFF_CASES = (
    "local-handoff.prepare-preview",
    "local-handoff.import-triage",
    "local-handoff.custody-decisions",
    "local-handoff.reviewer-safe-bundle",
)

INSTALLED_SMOKE_STAGE_LABELS = ("installed wheel smoke",)


def inherited_v16_stages(evidence_dir: Path) -> list[GateStage]:
    """Return deterministic release stages inherited from v16."""

    return v16_gate.build_gate_stages(evidence_dir)


def handoff_eval_stages(eval_output_dir: Path) -> list[GateStage]:
    """Return deterministic eval stages for v17 local handoff."""

    return [
        GateStage(
            "v17 deterministic eval release report",
            (
                "uv",
                "run",
                "glassbox",
                "eval",
                "report",
                "commit-smoke",
                "push-confirmation",
                "release-candidate",
                "--output-dir",
                str(eval_output_dir / "v17-release-signoff"),
                "--cwd",
                ".",
            ),
        ),
        GateStage(
            "v17 local handoff release profile",
            (
                "uv",
                "run",
                "glassbox",
                "eval",
                "run",
                "--profile",
                "release-candidate",
                "--output-dir",
                str(eval_output_dir / "v17-local-handoff-release"),
                "--refresh-output-dir",
                "--cwd",
                ".",
            ),
        ),
        GateStage(
            "v17 local handoff eval smoke",
            (
                "uv",
                "run",
                "glassbox",
                "eval",
                "run",
                *V17_LOCAL_HANDOFF_CASES,
                "--output-dir",
                str(eval_output_dir / "v17-local-handoff-smoke"),
                "--refresh-output-dir",
                "--cwd",
                ".",
            ),
        ),
    ]


def handoff_smoke_stages() -> list[GateStage]:
    """Return focused runtime handoff smoke stages."""

    return [
        GateStage(
            "v17 handoff package smoke",
            ("uv", "run", "glassbox", "handoff", "inspect", "--help"),
        ),
        GateStage(
            "v17 redaction preview smoke",
            (
                "uv",
                "run",
                "pytest",
                "tests/unit/test_handoff_redaction_preview.py",
                "tests/unit/test_session_export_redaction.py",
                "-q",
            ),
        ),
        GateStage(
            "v17 import triage smoke",
            (
                "uv",
                "run",
                "pytest",
                "tests/unit/test_handoff_import_triage.py",
                "tests/unit/test_handoff_guidance.py",
                "-q",
            ),
        ),
        GateStage(
            "v17 custody smoke",
            (
                "uv",
                "run",
                "pytest",
                "tests/unit/test_handoff_decisions.py",
                "tests/integration/test_handoff_projection.py",
                "-q",
            ),
        ),
    ]


def cli_api_stages() -> list[GateStage]:
    """Return CLI and API coverage stages for v17 local handoff."""

    return [
        GateStage(
            "v17 local handoff CLI API coverage",
            (
                "uv",
                "run",
                "pytest",
                "tests/integration/test_cli_handoff_commands.py",
                "tests/integration/test_web_handoff_routes.py",
                "tests/integration/test_openapi_schema.py",
                "-q",
            ),
        )
    ]


def frontend_stages() -> list[GateStage]:
    """Return frontend handoff smoke stages."""

    return [
        GateStage(
            "v17 local handoff frontend smoke",
            (
                "pnpm",
                "--dir",
                "frontend",
                "test",
                "--",
                "--maxWorkers=1",
                "handoff-cockpit.test.tsx",
                "generated-api-types.test.ts",
            ),
        )
    ]


def package_stages() -> list[GateStage]:
    """Return package validation stages for v17 local handoff."""

    return [
        GateStage(
            "v17 package contents validation",
            ("uv", "run", "python", "scripts/validate_package_contents.py"),
        )
    ]


def docs_stages() -> list[GateStage]:
    """Return docs and eval-audit stages for v17 signoff."""

    return [
        GateStage(
            "v17 release docs",
            (
                "uv",
                "run",
                "pytest",
                "tests/unit/test_release_candidate_docs.py",
                "-q",
            ),
        ),
        GateStage(
            "v17 eval coverage audit",
            (
                "uv",
                "run",
                "glassbox",
                "eval",
                "audit",
                "--profile",
                "release-candidate",
                "--cwd",
                ".",
            ),
        ),
    ]


def installed_smoke_stage_labels() -> tuple[str, ...]:
    """Return installed-smoke labels recorded by the shared gate runner."""

    return INSTALLED_SMOKE_STAGE_LABELS
