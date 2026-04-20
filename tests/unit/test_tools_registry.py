"""Unit tests for the typed tool registry."""

import pytest
from pydantic import BaseModel

from glassbox.tools import (
    ToolRegistry,
    ToolRiskLevel,
    ToolSpec,
    ToolStreamingMode,
)


class ReadFileArgs(BaseModel):
    path: str


class ReadFileResult(BaseModel):
    content: str


class SearchFilesArgs(BaseModel):
    query: str


class SearchFilesResult(BaseModel):
    matches: list[str]


class ReadFileTool:
    spec = ToolSpec(
        name="read_file",
        description="Read a file from the workspace.",
        input_model=ReadFileArgs,
        output_model=ReadFileResult,
        risk_level=ToolRiskLevel.READ_ONLY,
    )

    async def execute(self, arguments: ReadFileArgs) -> ReadFileResult:
        return ReadFileResult(content=arguments.path)


class SearchFilesTool:
    spec = ToolSpec(
        name="search_files",
        description="Search workspace files for matching text.",
        input_model=SearchFilesArgs,
        output_model=SearchFilesResult,
        risk_level=ToolRiskLevel.READ_ONLY,
        streaming_mode=ToolStreamingMode.TEXT,
    )

    async def execute(self, arguments: SearchFilesArgs) -> SearchFilesResult:
        return SearchFilesResult(matches=[arguments.query])


def test_tool_registry_orders_registered_tools_and_exports_model_schemas() -> None:
    registry = ToolRegistry([SearchFilesTool(), ReadFileTool()])

    assert [tool.spec.name for tool in registry.list_tools()] == [
        "read_file",
        "search_files",
    ]
    assert (
        registry.require("search_files").spec.streaming_mode is ToolStreamingMode.TEXT
    )
    assert registry.require("read_file").spec.output_model is ReadFileResult

    schemas = registry.list_schemas()

    assert [schema.name for schema in schemas] == ["read_file", "search_files"]
    assert schemas[0].parameters_json_schema["properties"] == {
        "path": {"title": "Path", "type": "string"}
    }
    assert schemas[1].parameters_json_schema["required"] == ["query"]


def test_tool_registry_rejects_duplicate_tool_names() -> None:
    registry = ToolRegistry([ReadFileTool()])

    with pytest.raises(ValueError, match="duplicate tool name: read_file"):
        registry.register(ReadFileTool())


def test_tool_spec_rejects_blank_name_and_description() -> None:
    with pytest.raises(ValueError, match="tool name must not be blank"):
        ToolSpec(
            name=" ",
            description="Read a file.",
            input_model=ReadFileArgs,
            output_model=ReadFileResult,
            risk_level=ToolRiskLevel.READ_ONLY,
        )

    with pytest.raises(ValueError, match="tool description must not be blank"):
        ToolSpec(
            name="read_file",
            description=" ",
            input_model=ReadFileArgs,
            output_model=ReadFileResult,
            risk_level=ToolRiskLevel.READ_ONLY,
        )
