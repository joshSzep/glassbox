"""Ownership hint discovery for repository intelligence layouts."""

from pathlib import Path

from glassbox.core.models import RepositoryIndexProvenance
from glassbox.core.models import RepositoryIntelligenceOwnershipHint
from glassbox.core.models import RepositoryIntelligenceSubsystem
from glassbox.core.types import RepositoryIndexSourceType
from glassbox.core.types import RepositoryIntelligenceConfidence


def discover_codeowners_ownership_hints(
    root: Path,
) -> list[RepositoryIntelligenceOwnershipHint]:
    """Discover advisory ownership hints from CODEOWNERS-style metadata."""

    codeowners = _first_existing_path(root, [".github/CODEOWNERS", "CODEOWNERS"])
    if codeowners is None:
        return []
    hints: list[RepositoryIntelligenceOwnershipHint] = []
    try:
        lines = (root / codeowners).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for index, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        scope = _codeowners_scope(parts[0])
        owners = " ".join(parts[1:])
        hints.append(
            RepositoryIntelligenceOwnershipHint(
                hint_id=f"owner:codeowners:{index}",
                owner_label=owners,
                scope_paths=[scope],
                confidence=RepositoryIntelligenceConfidence.HIGH,
                provenance=[
                    RepositoryIndexProvenance(
                        source_type=RepositoryIndexSourceType.MANIFEST,
                        path=codeowners,
                        line_start=index,
                        line_end=index,
                    )
                ],
                limitations=[
                    "CODEOWNERS-style hints are advisory repository metadata, "
                    "not access-control authority."
                ],
            )
        )
    return hints


def discover_subsystem_owner_hints(
    root: Path,
    subsystems: list[RepositoryIntelligenceSubsystem],
) -> list[RepositoryIntelligenceOwnershipHint]:
    """Discover advisory owner labels from inferred subsystems."""

    del root
    hints: list[RepositoryIntelligenceOwnershipHint] = []
    for subsystem in subsystems:
        hints.append(
            RepositoryIntelligenceOwnershipHint(
                hint_id=f"owner:{subsystem.subsystem_id}",
                owner_label=f"{subsystem.name} subsystem maintainers",
                scope_paths=subsystem.scope_paths,
                subsystem=subsystem.subsystem_id,
                confidence=RepositoryIntelligenceConfidence.LOW,
                provenance=[
                    RepositoryIndexProvenance(
                        source_type=RepositoryIndexSourceType.FILE_SYSTEM,
                        path=subsystem.scope_paths[0],
                        note="Inferred from repository subsystem path conventions.",
                    )
                ],
                limitations=[
                    "Inferred owner hint names a local subsystem, not a person "
                    "or required reviewer."
                ],
            )
        )
    return hints


def _codeowners_scope(pattern: str) -> Path:
    cleaned = pattern.lstrip("/")
    prefix = cleaned.split("*", 1)[0].rstrip("/")
    if not prefix:
        return Path(".")
    path = Path(prefix)
    if path.suffix:
        return path.parent if path.parent != Path(".") else path
    return path


def _first_existing_path(root: Path, candidates: list[str]) -> Path | None:
    for candidate in candidates:
        relative = Path(candidate)
        if (root / relative).exists():
            return relative
    return None


__all__ = [
    "discover_codeowners_ownership_hints",
    "discover_subsystem_owner_hints",
]
