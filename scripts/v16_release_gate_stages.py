"""V16 release-gate deterministic stage construction."""

from pathlib import Path

from scripts import v14_release_gate_helpers as v14_helpers
from scripts import validate_v15_release_gate as v15_gate
from scripts.validate_v6_release_gate import GateStage

V16_OPERATOR_FLOW_CASES = (
    "operator-flow.queue-ranking",
    "operator-flow.evidence-graph-support",
    "operator-flow.verification-plan-lifecycle",
    "operator-flow.skipped-check-posture",
    "operator-flow.changeset-workup-preview",
    "operator-flow.maintenance-cues",
    "operator-flow.reviewer-safe-bundle",
)


def build_gate_stages(evidence_dir: Path | None = None) -> list[GateStage]:
    """Return the deterministic blocking stages for the v16 gate."""

    resolved_evidence_dir = evidence_dir or Path(".glassbox/releases/v16-gate")
    eval_output_dir = v14_helpers.eval_evidence_dir(resolved_evidence_dir)
    return [
        *v15_gate.build_gate_stages(resolved_evidence_dir),
        GateStage(
            "v16 deterministic eval release report",
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
                str(eval_output_dir / "v16-release-signoff"),
                "--cwd",
                ".",
            ),
        ),
        GateStage(
            "v16 operator flow release profile",
            (
                "uv",
                "run",
                "glassbox",
                "eval",
                "run",
                "--profile",
                "release-candidate",
                "--output-dir",
                str(eval_output_dir / "v16-operator-flow-release"),
                "--refresh-output-dir",
                "--cwd",
                ".",
            ),
        ),
        GateStage(
            "v16 operator flow eval smoke",
            (
                "uv",
                "run",
                "glassbox",
                "eval",
                "run",
                *V16_OPERATOR_FLOW_CASES,
                "--output-dir",
                str(eval_output_dir / "v16-operator-flow-smoke"),
                "--refresh-output-dir",
                "--cwd",
                ".",
            ),
        ),
        GateStage(
            "v16 operator queue smoke",
            ("uv", "run", "glassbox", "queue", "list", "--json", "--cwd", "."),
        ),
        GateStage(
            "v16 evidence graph smoke",
            (
                "uv",
                "run",
                "glassbox",
                "changeset",
                "evidence-graph",
                "--help",
            ),
        ),
        GateStage(
            "v16 verification plan smoke",
            (
                "uv",
                "run",
                "glassbox",
                "changeset",
                "verification-plan",
                "--path",
                "docs/tasks-v16.md",
                "--json",
                "--cwd",
                ".",
            ),
        ),
        GateStage(
            "v16 operator flow runtime coverage",
            (
                "uv",
                "run",
                "pytest",
                "tests/unit/test_session_query_derivation.py",
                "tests/unit/test_evidence_graph.py",
                "tests/unit/test_changeset_workup.py",
                "tests/unit/test_changeset_verification_readiness.py",
                "tests/integration/test_performance_budgets.py",
                "tests/unit/test_runtime_eval_coverage.py",
                "-q",
            ),
        ),
        GateStage(
            "v16 operator flow CLI API coverage",
            (
                "uv",
                "run",
                "pytest",
                "tests/integration/test_cli_changeset_commands.py",
                "tests/integration/test_cli_session_commands.py",
                "tests/integration/test_web_changeset_routes.py",
                "tests/integration/test_openapi_schema.py",
                "-q",
            ),
        ),
        GateStage(
            "v16 operator flow frontend smoke",
            (
                "pnpm",
                "--dir",
                "frontend",
                "test",
                "--",
                "--maxWorkers=1",
                "workspace-overview.test.ts",
                "changeset-console.test.tsx",
                "session-inspector.test.ts",
                "generated-api-types.test.ts",
            ),
        ),
        GateStage(
            "v16 package contents validation",
            ("uv", "run", "python", "scripts/validate_package_contents.py"),
        ),
        GateStage(
            "v16 release docs",
            (
                "uv",
                "run",
                "pytest",
                "tests/unit/test_release_candidate_docs.py",
                "-q",
            ),
        ),
        GateStage(
            "v16 eval coverage audit",
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
