"""Run the v16 operator-flow release gate scaffold."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

SCRIPT_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_REPO_ROOT))

from scripts import v16_release_gate_helpers as v16_helpers  # noqa: E402
from scripts.release_gate_models import MilestoneReleaseGate  # noqa: E402
from scripts.release_gate_runner import run_release_gate  # noqa: E402
from scripts.validate_v6_release_gate import GateStage  # noqa: E402

V16_OPERATOR_FLOW_CASES = v16_helpers.V16_OPERATOR_FLOW_CASES
V16_RELEASE_GATE = MilestoneReleaseGate(
    label="V16",
    description="Run the Glassbox v16 operator-flow release gate.",
    build_gate_stages=v16_helpers.build_gate_stages,
    resolve_evidence_dir=v16_helpers.resolve_evidence_dir,
    new_evidence_summary=v16_helpers.new_evidence_summary,
    print_dry_run=v16_helpers.print_dry_run,
    record_planned_stages=v16_helpers.record_planned_stages,
    record_installed_wheel_plan=v16_helpers.record_installed_wheel_plan,
    record_provider_evidence=v16_helpers.record_provider_evidence,
    record_advisory_evidence=v16_helpers.record_advisory_evidence,
    finish_summary=v16_helpers.finish_summary,
    write_evidence_summary=v16_helpers.write_evidence_summary,
    print_summary=v16_helpers.print_summary,
)


def build_gate_stages(evidence_dir: Path | None = None) -> list[GateStage]:
    """Return the deterministic blocking stages for the v16 gate."""

    return v16_helpers.build_gate_stages(evidence_dir)


def main(argv: Sequence[str] | None = None) -> int:
    return run_release_gate(V16_RELEASE_GATE, argv)


if __name__ == "__main__":
    raise SystemExit(main())
