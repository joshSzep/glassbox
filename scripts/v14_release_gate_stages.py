"""V14 release-gate deterministic stage construction."""

from pathlib import Path

from scripts import v11_release_gate_helpers as gate_helpers
from scripts import v13_release_gate_helpers as v13_helpers
from scripts.validate_v6_release_gate import GateStage

V14_MATURITY_CASES = (
    "changeset.lifecycle-rich-evidence",
    "changeset.response-linked-fixup-inventory",
    "changeset.skipped-advisory-evidence-posture",
)


def build_gate_stages(evidence_dir: Path | None = None) -> list[GateStage]:
    """Return the deterministic blocking stages for the v14 gate."""

    resolved_evidence_dir = evidence_dir or Path(".glassbox/releases/v14-gate")
    eval_output_dir = eval_evidence_dir(resolved_evidence_dir)
    return [
        *v13_helpers.build_gate_stages(resolved_evidence_dir),
        GateStage(
            "v14 deterministic eval release report",
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
                str(eval_output_dir / "v14-release-signoff"),
                "--cwd",
                ".",
            ),
        ),
        GateStage(
            "v14 review-loop maturity profile",
            (
                "uv",
                "run",
                "glassbox",
                "eval",
                "run",
                "--profile",
                "release-candidate",
                "--output-dir",
                str(eval_output_dir / "v14-review-loop-maturity-release"),
                "--refresh-output-dir",
                "--cwd",
                ".",
            ),
        ),
        GateStage(
            "v14 review-loop maturity eval smoke",
            (
                "uv",
                "run",
                "glassbox",
                "eval",
                "run",
                *V14_MATURITY_CASES,
                "--output-dir",
                str(eval_output_dir / "v14-review-loop-maturity-smoke"),
                "--refresh-output-dir",
                "--cwd",
                ".",
            ),
        ),
        GateStage(
            "v14 review-loop CLI API coverage",
            (
                "uv",
                "run",
                "pytest",
                "tests/integration/test_cli_interactive_commands.py",
                "tests/integration/test_cli_tui_review_commands.py",
                "tests/integration/test_web_changeset_routes.py",
                "-k",
                "review or feedback or evidence or accessibility",
            ),
        ),
        GateStage(
            "v14 dashboard maturity frontend coverage",
            (
                "pnpm",
                "--dir",
                "frontend",
                "test",
                "--",
                "changeset-console.test.tsx",
                "operator-actions.component.test.tsx",
            ),
        ),
        GateStage(
            "v14 eval coverage audit",
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


def eval_evidence_dir(evidence_dir: Path) -> Path:
    return gate_helpers.eval_evidence_dir(evidence_dir)
