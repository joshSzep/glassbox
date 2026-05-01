"""Knowledge-posture status formatting helpers for the CLI."""

from glassbox.runtime.knowledge_posture import KnowledgeCueProvenance


def format_knowledge_provenance(provenance: KnowledgeCueProvenance) -> str:
    parts = [provenance.label, provenance.source_kind]
    if provenance.source_id is not None:
        parts.append(f"id {provenance.source_id}")
    if provenance.session_id is not None:
        parts.append(f"session {provenance.session_id}")
    if provenance.source_start_sequence is not None:
        end_sequence = (
            provenance.source_end_sequence or provenance.source_start_sequence
        )
        parts.append(f"events {provenance.source_start_sequence}-{end_sequence}")
    if provenance.artifact_id is not None:
        parts.append(f"artifact {provenance.artifact_id}")
    if provenance.path is not None:
        parts.append(provenance.path)
    if provenance.timestamp is not None:
        parts.append(provenance.timestamp)
    if provenance.freshness is not None:
        parts.append(f"freshness {provenance.freshness}")
    return "; ".join(parts)


__all__ = ["format_knowledge_provenance"]
