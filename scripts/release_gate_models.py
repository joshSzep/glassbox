"""Shared release-gate runner models."""

from __future__ import annotations

from collections.abc import Callable
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Protocol

from scripts.validate_v6_release_gate import GateStage

type EvidenceSummary = dict[str, Any]


class DryRunPrinter(Protocol):
    def __call__(
        self,
        stages: Sequence[GateStage],
        *,
        include_provider_canaries: bool,
    ) -> None: ...


class EvidenceSummaryFactory(Protocol):
    def __call__(
        self,
        evidence_dir: Path,
        *,
        include_provider_canaries: bool,
        dry_run: bool,
    ) -> EvidenceSummary: ...


class ProviderEvidenceRecorder(Protocol):
    def __call__(
        self,
        summary: EvidenceSummary,
        evidence_dir: Path,
        *,
        include: bool,
        dry_run: bool,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class MilestoneReleaseGate:
    """Configuration hooks for one milestone release gate."""

    label: str
    description: str
    build_gate_stages: Callable[[Path | None], list[GateStage]]
    resolve_evidence_dir: Callable[[Path | None], Path]
    new_evidence_summary: EvidenceSummaryFactory
    print_dry_run: DryRunPrinter
    record_planned_stages: Callable[[EvidenceSummary, Sequence[GateStage]], None]
    record_installed_wheel_plan: Callable[[EvidenceSummary], None]
    record_provider_evidence: ProviderEvidenceRecorder
    record_advisory_evidence: Callable[[EvidenceSummary, Path], None]
    finish_summary: Callable[[EvidenceSummary, str], None]
    write_evidence_summary: Callable[[Path, EvidenceSummary], Path]
    print_summary: Callable[[EvidenceSummary], None]
