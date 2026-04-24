"""Integration tests for the initial read-only workspace tools."""

import asyncio
from pathlib import Path

import pytest

from glassbox.tools import ListDirArgs
from glassbox.tools import ReadFileArgs
from glassbox.tools import SearchFilesArgs
from glassbox.tools import build_read_only_tool_registry


def test_read_only_tools_execute_against_workspace(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text(
        "print('glassbox')\nprint('repo')\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text(
        "Glassbox CLI\nWorkspace tools\n",
        encoding="utf-8",
    )
    registry = build_read_only_tool_registry(tmp_path)

    async def scenario() -> None:
        list_result = await registry.require("list_dir").execute(ListDirArgs(path="."))
        read_result = await registry.require("read_file").execute(
            ReadFileArgs(path="src/app.py", start_line=1, end_line=1)
        )
        search_result = await registry.require("search_files").execute(
            SearchFilesArgs(query="glassbox")
        )

        assert [entry.path for entry in list_result.entries] == ["README.md", "src"]
        assert read_result.content == "print('glassbox')"
        assert read_result.end_line == 1
        assert [(match.path, match.line_number) for match in search_result.matches] == [
            ("README.md", 1),
            ("src/app.py", 1),
        ]

    asyncio.run(scenario())


def test_read_only_tools_reject_out_of_scope_paths(tmp_path: Path) -> None:
    (tmp_path / "safe.txt").write_text("hello\n", encoding="utf-8")
    registry = build_read_only_tool_registry(tmp_path)

    async def scenario() -> None:
        with pytest.raises(ValueError, match="outside workspace"):
            await registry.require("list_dir").execute(ListDirArgs(path="../"))

        with pytest.raises(ValueError, match="outside workspace"):
            await registry.require("read_file").execute(
                ReadFileArgs(path="../secret.txt")
            )

        with pytest.raises(ValueError, match="outside workspace"):
            await registry.require("search_files").execute(
                SearchFilesArgs(query="hello", path="../")
            )

    asyncio.run(scenario())
