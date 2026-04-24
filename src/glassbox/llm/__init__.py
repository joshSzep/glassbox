"""LLM integration package for Glassbox."""

from glassbox.llm.adapters import ModelAdapter
from glassbox.llm.adapters import ModelAdapterStreamEvent
from glassbox.llm.adapters import ModelFinalResult
from glassbox.llm.adapters import ModelProviderConfig
from glassbox.llm.adapters import ModelTextDelta
from glassbox.llm.adapters import ModelToolCall
from glassbox.llm.adapters import ModelToolCallDelta
from glassbox.llm.adapters import PreparedModelTurn
from glassbox.llm.adapters import PydanticAIModelAdapter
from glassbox.llm.adapters import PydanticAIStreamTranslator
from glassbox.llm.executor import ModelExecutionResult
from glassbox.llm.executor import ModelExecutor
from glassbox.llm.executor import PydanticAIModelExecutor
from glassbox.llm.executor import build_anthropic_model_executor
from glassbox.llm.executor import build_local_text_model_executor
from glassbox.llm.executor import build_openai_model_executor
from glassbox.llm.prompts import build_approval_policy_prompt_fragment
from glassbox.llm.prompts import build_artifact_backed_context_prompt_fragment
from glassbox.llm.prompts import build_memory_notes_prompt_fragment
from glassbox.llm.prompts import build_output_style_prompt_fragment
from glassbox.llm.prompts import build_repo_context_prompt_fragment
from glassbox.llm.prompts import build_runtime_prompt_fragment
from glassbox.llm.prompts import build_system_prompt
from glassbox.llm.prompts import build_tool_usage_prompt_fragment
from glassbox.llm.prompts import build_working_set_prompt_fragment

__all__ = [
    "ModelAdapter",
    "ModelAdapterStreamEvent",
    "ModelExecutionResult",
    "ModelExecutor",
    "ModelFinalResult",
    "ModelProviderConfig",
    "ModelTextDelta",
    "ModelToolCall",
    "ModelToolCallDelta",
    "PydanticAIModelExecutor",
    "PreparedModelTurn",
    "PydanticAIModelAdapter",
    "PydanticAIStreamTranslator",
    "build_approval_policy_prompt_fragment",
    "build_artifact_backed_context_prompt_fragment",
    "build_anthropic_model_executor",
    "build_local_text_model_executor",
    "build_memory_notes_prompt_fragment",
    "build_openai_model_executor",
    "build_output_style_prompt_fragment",
    "build_repo_context_prompt_fragment",
    "build_runtime_prompt_fragment",
    "build_system_prompt",
    "build_tool_usage_prompt_fragment",
    "build_working_set_prompt_fragment",
]
