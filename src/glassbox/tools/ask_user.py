"""Ask user tool: suspends a turn to collect operator input."""

from pathlib import Path

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.tools.patch import build_patch_tool_registry
from glassbox.tools.registry import ToolRegistry
from glassbox.tools.registry import ToolRiskLevel
from glassbox.tools.registry import ToolSpec

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class AskUserArgs(BaseModel):
    """Arguments for asking the operator a question."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(
        min_length=1,
        description="The question to present to the operator.",
    )


class AskUserResult(BaseModel):
    """Result returned to the model after the operator answers."""

    model_config = ConfigDict(extra="forbid")

    answer: str = Field(description="The operator's answer to the question.")


# ---------------------------------------------------------------------------
# Tool
# ---------------------------------------------------------------------------


class AskUserTool:
    """Suspend a turn and surface a question to the operator for input.

    Execution of this tool is intercepted by the turn engine before reaching
    ``execute()``.  The engine emits a ``UserQuestionAsked`` event and suspends
    the turn; ``execute()`` exists only to satisfy the Tool protocol and should
    never be called directly.
    """

    spec = ToolSpec(
        name="ask_user",
        description=(
            "Pause the current turn and ask the operator a question. "
            "The turn resumes automatically once the operator provides an answer."
        ),
        input_model=AskUserArgs,
        output_model=AskUserResult,
        risk_level=ToolRiskLevel.READ_ONLY,
    )

    def __init__(self, workspace_root: Path) -> None:  # noqa: ARG002
        pass

    async def execute(
        self, arguments: AskUserArgs
    ) -> AskUserResult:  # pragma: no cover
        """Not called directly; the turn engine intercepts this tool."""
        raise NotImplementedError(
            "ask_user execution must be intercepted by the turn engine"
        )


# ---------------------------------------------------------------------------
# Registry builder
# ---------------------------------------------------------------------------


def build_ask_user_tool_registry(workspace_root: Path) -> ToolRegistry:
    """Build a tool registry with all tools including the ask_user tool."""

    registry = build_patch_tool_registry(workspace_root)
    registry.register(AskUserTool(workspace_root))
    return registry
