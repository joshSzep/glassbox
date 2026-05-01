"""Deterministic context compaction service.

This module remains the stable compatibility facade for CLI, web, and runtime
callers. Range planning, artifact assembly, freshness assessment, and mutation
operations live in focused helpers.
"""

from glassbox.runtime.context_compaction import CONTEXT_COMPACTION_ARTIFACT_KIND
from glassbox.runtime.context_compaction import CONTEXT_COMPACTION_SOURCE_REFERENCE_CAP
from glassbox.runtime.context_compaction_freshness import (
    assessed_context_compaction_record,
)
from glassbox.runtime.context_compaction_freshness import (
    latest_material_source_sequence,
)
from glassbox.runtime.context_compaction_mutations import (
    create_deterministic_context_compaction,
)
from glassbox.runtime.context_compaction_mutations import invalidate_context_compaction
from glassbox.runtime.context_compaction_mutations import refresh_context_compaction
from glassbox.runtime.context_compaction_range import ContextCompactionRangeError
from glassbox.runtime.context_compaction_range import ContextCompactionSuggestedRange

__all__ = [
    "CONTEXT_COMPACTION_ARTIFACT_KIND",
    "CONTEXT_COMPACTION_SOURCE_REFERENCE_CAP",
    "ContextCompactionRangeError",
    "ContextCompactionSuggestedRange",
    "assessed_context_compaction_record",
    "create_deterministic_context_compaction",
    "invalidate_context_compaction",
    "latest_material_source_sequence",
    "refresh_context_compaction",
]
