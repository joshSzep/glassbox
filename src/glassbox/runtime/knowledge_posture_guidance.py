"""Safe inspection command guidance for knowledge posture cues."""

from collections.abc import Iterable

from glassbox.runtime.knowledge_posture_models import KnowledgePostureCue
from glassbox.runtime.observability_models import RepositoryIndexObservability
from glassbox.runtime.observability_models import VerificationObservability
from glassbox.runtime.observability_models import WorkspaceMemoryObservability
from glassbox.runtime.provider_canary_models import ProviderCanaryEvidenceSummary


def memory_inspection_commands(memory: WorkspaceMemoryObservability) -> list[str]:
    return ["glassbox memory list --cwd .", *memory.next_actions]


def repository_index_inspection_commands(
    repository_index: RepositoryIndexObservability,
) -> list[str]:
    return ["glassbox repo index status --cwd .", *repository_index.next_actions]


def checkpoint_inspection_commands() -> list[str]:
    return ["glassbox session status SESSION_ID --cwd ."]


def compaction_inspection_commands() -> list[str]:
    return ["glassbox session compactions SESSION_ID --cwd ."]


def verification_inspection_commands(
    verification: VerificationObservability,
) -> list[str]:
    return ["glassbox eval audit --cwd .", *verification.next_actions]


def provider_evidence_inspection_commands(
    provider_canary: ProviderCanaryEvidenceSummary,
) -> list[str]:
    return [
        "glassbox provider canary evidence --cwd .",
        *provider_canary.next_actions,
    ]


def next_actions_from_cues(cues: Iterable[KnowledgePostureCue]) -> list[str]:
    return _dedupe(command for cue in cues for command in cue.inspect_commands[:2])


def _dedupe(commands: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for command in commands:
        if command in seen:
            continue
        seen.add(command)
        deduped.append(command)
    return deduped


__all__ = [
    "checkpoint_inspection_commands",
    "compaction_inspection_commands",
    "memory_inspection_commands",
    "next_actions_from_cues",
    "provider_evidence_inspection_commands",
    "repository_index_inspection_commands",
    "verification_inspection_commands",
]
