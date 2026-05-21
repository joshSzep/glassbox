"""V17 release-gate deterministic stage construction."""

from pathlib import Path

from scripts import v14_release_gate_helpers as v14_helpers
from scripts import validate_v16_release_gate as v16_gate
from scripts.validate_v6_release_gate import GateStage

V17_LOCAL_HANDOFF_CASES = (
    "local-handoff.prepare-preview",
    "local-handoff.import-triage",
    "local-handoff.custody-decisions",
    "local-handoff.reviewer-safe-bundle",
)


def build_gate_stages(evidence_dir: Path | None = None) -> list[GateStage]:
    """Return the deterministic blocking stages for the v17 gate."""

    resolved_evidence_dir = evidence_dir or Path(".glassbox/releases/v17-gate")
    eval_output_dir = v14_helpers.eval_evidence_dir(resolved_evidence_dir)
    return [
        *v16_gate.build_gate_stages(resolved_evidence_dir),
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
        ),
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
        ),
        GateStage(
            "v17 package contents validation",
            ("uv", "run", "python", "scripts/validate_package_contents.py"),
        ),
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
