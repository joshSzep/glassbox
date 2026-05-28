"""V17 release-gate deterministic stage construction."""

from pathlib import Path

from scripts import v14_release_gate_helpers as v14_helpers
from scripts import v17_release_gate_stage_groups as stage_groups
from scripts.validate_v6_release_gate import GateStage

V17_LOCAL_HANDOFF_CASES = stage_groups.V17_LOCAL_HANDOFF_CASES


def build_gate_stages(evidence_dir: Path | None = None) -> list[GateStage]:
    """Return the deterministic blocking stages for the v17 gate."""

    resolved_evidence_dir = evidence_dir or Path(".glassbox/releases/v17-gate")
    eval_output_dir = v14_helpers.eval_evidence_dir(resolved_evidence_dir)
    return [
        *stage_groups.inherited_v16_stages(resolved_evidence_dir),
        *stage_groups.handoff_eval_stages(eval_output_dir),
        *stage_groups.handoff_smoke_stages(),
        *stage_groups.cli_api_stages(),
        *stage_groups.frontend_stages(),
        *stage_groups.package_stages(),
        *stage_groups.docs_stages(),
    ]
