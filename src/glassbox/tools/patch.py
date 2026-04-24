"""Apply patch tool: controlled, workspace-scoped file edits for Glassbox sessions."""

from __future__ import annotations

import difflib
from pathlib import Path

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.tools.registry import ToolRegistry
from glassbox.tools.registry import ToolRiskLevel
from glassbox.tools.registry import ToolSpec
from glassbox.tools.workflow import build_workflow_tool_registry

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ApplyPatchArgs(BaseModel):
    """Arguments for applying one text replacement to a workspace file.

    When ``old_text`` is an empty string the full file is overwritten with
    ``new_text`` (and the file is created if it does not yet exist).  When
    ``old_text`` is non-empty it must match *exactly once* in the current file
    content; zero or multiple matches are both treated as errors.
    """

    model_config = ConfigDict(extra="forbid")

    path: str = Field(
        description="File path relative to the workspace root.",
        min_length=1,
    )
    old_text: str = Field(
        default="",
        description=(
            "Exact text to find and replace.  "
            "Empty string means overwrite the entire file with new_text."
        ),
    )
    new_text: str = Field(
        default="",
        description="Replacement text.",
    )


class ApplyPatchResult(BaseModel):
    """Structured result from one apply_patch invocation."""

    model_config = ConfigDict(extra="forbid")

    path: str
    success: bool
    diff: str | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Tool
# ---------------------------------------------------------------------------


class ApplyPatchTool:
    """Apply a text replacement patch to a workspace-scoped file."""

    spec = ToolSpec(
        name="apply_patch",
        description=(
            "Edit a file within the workspace by replacing an exact string with "
            "new content.  Set old_text to an empty string to overwrite the "
            "entire file (and create it if it does not exist).  The replacement "
            "must match exactly once; ambiguous or missing matches are rejected."
        ),
        input_model=ApplyPatchArgs,
        output_model=ApplyPatchResult,
        risk_level=ToolRiskLevel.WORKSPACE_WRITE,
        path_argument_names=("path",),
    )

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root.resolve(strict=False)

    async def execute(self, arguments: ApplyPatchArgs) -> ApplyPatchResult:
        """Apply the patch and return a structured result with a diff preview."""

        resolved = _resolve_workspace_path(self._workspace_root, arguments.path)

        # ---- full-overwrite mode ----------------------------------------
        if arguments.old_text == "":
            old_content = (
                resolved.read_text(encoding="utf-8") if resolved.exists() else ""
            )
            new_content = arguments.new_text
            diff = _make_diff(arguments.path, old_content, new_content)
            resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(new_content, encoding="utf-8")
            return ApplyPatchResult(path=arguments.path, success=True, diff=diff)

        # ---- targeted replacement mode -----------------------------------
        if not resolved.exists():
            return ApplyPatchResult(
                path=arguments.path,
                success=False,
                error=f"file not found: {arguments.path}",
            )

        old_content = resolved.read_text(encoding="utf-8")
        count = old_content.count(arguments.old_text)

        if count == 0:
            return ApplyPatchResult(
                path=arguments.path,
                success=False,
                error="old_text not found in file",
            )

        if count > 1:
            return ApplyPatchResult(
                path=arguments.path,
                success=False,
                error=(
                    f"old_text matches {count} locations; "
                    "add more context to make it unambiguous"
                ),
            )

        new_content = old_content.replace(arguments.old_text, arguments.new_text, 1)
        diff = _make_diff(arguments.path, old_content, new_content)
        resolved.write_text(new_content, encoding="utf-8")
        return ApplyPatchResult(path=arguments.path, success=True, diff=diff)


# ---------------------------------------------------------------------------
# Registry builder
# ---------------------------------------------------------------------------


def build_patch_tool_registry(workspace_root: Path) -> ToolRegistry:
    """Build a tool registry with all tools including the apply_patch tool."""

    registry = build_workflow_tool_registry(workspace_root)
    registry.register(ApplyPatchTool(workspace_root))
    return registry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_workspace_path(workspace_root: Path, relative_path: str) -> Path:
    """Resolve relative_path against workspace_root, rejecting escapes."""

    resolved = (workspace_root / relative_path).resolve(strict=False)
    if not resolved.is_relative_to(workspace_root):
        raise ValueError(
            f"path '{relative_path}' is outside workspace '{workspace_root}'"
        )
    return resolved


def _make_diff(path: str, old_content: str, new_content: str) -> str:
    """Return a unified diff string for the before/after file contents."""

    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    diff_lines = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
    )
    return "".join(diff_lines)
