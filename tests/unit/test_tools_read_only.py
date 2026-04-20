"""Unit tests for the read-only tool registry helper and models."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from glassbox.tools import (
    DirectoryEntry,
    ListDirResult,
    ReadFileResult,
    SearchFilesResult,
    build_read_only_tool_registry,
)


def test_build_read_only_tool_registry_exposes_expected_tool_names() -> None:
    registry = build_read_only_tool_registry(Path("/tmp/workspace"))

    assert [tool.spec.name for tool in registry.list_tools()] == [
        "list_dir",
        "read_file",
        "search_files",
    ]


def test_read_only_tool_output_models_validate_expected_shapes() -> None:
    list_result = ListDirResult(
        path="src",
        entries=[
            DirectoryEntry(name="glassbox", path="src/glassbox", entry_type="dir")
        ],
    )
    read_result = ReadFileResult(
        path="README.md",
        start_line=1,
        end_line=2,
        content="line 1\nline 2",
    )
    search_result = SearchFilesResult(
        query="glassbox",
        matches=[],
    )

    assert list_result.entries[0].entry_type == "dir"
    assert read_result.end_line == 2
    assert search_result.query == "glassbox"


def test_read_only_tool_output_models_reject_invalid_shapes() -> None:
    with pytest.raises(ValidationError):
        ListDirResult.model_validate(
            {
                "path": "src",
                "entries": [{"name": "glassbox", "path": "src/glassbox"}],
            }
        )

    with pytest.raises(ValidationError):
        ReadFileResult.model_validate(
            {
                "path": "README.md",
                "start_line": 1,
                "end_line": {"line": 2},
                "content": "hello",
            }
        )

    with pytest.raises(ValidationError):
        SearchFilesResult.model_validate(
            {
                "query": "glassbox",
                "matches": [{"path": "a.py"}],
            }
        )
