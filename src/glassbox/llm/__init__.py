"""LLM integration package for Glassbox."""

from glassbox.llm.adapters import (
    ModelAdapter,
    ModelAdapterStreamEvent,
    ModelFinalResult,
    ModelProviderConfig,
    ModelTextDelta,
    ModelToolCall,
    ModelToolCallDelta,
    PreparedModelTurn,
    PydanticAIModelAdapter,
    PydanticAIStreamTranslator,
)
from glassbox.llm.prompts import (
    build_approval_policy_prompt_fragment,
    build_memory_notes_prompt_fragment,
    build_output_style_prompt_fragment,
    build_repo_context_prompt_fragment,
    build_runtime_prompt_fragment,
    build_system_prompt,
    build_tool_usage_prompt_fragment,
)

__all__ = [
    "ModelAdapter",
    "ModelAdapterStreamEvent",
    "ModelFinalResult",
    "ModelProviderConfig",
    "ModelTextDelta",
    "ModelToolCall",
    "ModelToolCallDelta",
    "PreparedModelTurn",
    "PydanticAIModelAdapter",
    "PydanticAIStreamTranslator",
    "build_approval_policy_prompt_fragment",
    "build_memory_notes_prompt_fragment",
    "build_output_style_prompt_fragment",
    "build_repo_context_prompt_fragment",
    "build_runtime_prompt_fragment",
    "build_system_prompt",
    "build_tool_usage_prompt_fragment",
]
