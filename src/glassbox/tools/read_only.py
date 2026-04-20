"""Read-only filesystem tools scoped to a workspace root."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from glassbox.tools.registry import ToolRegistry, ToolRiskLevel, ToolSpec


class ListDirArgs(BaseModel):
    """Arguments for listing one directory inside the workspace."""

    model_config = ConfigDict(extra="forbid")

    path: str = "."
    limit: int = Field(default=100, ge=1, le=500)


class DirectoryEntry(BaseModel):
    """Structured description of one directory child entry."""

    model_config = ConfigDict(extra="forbid")

    name: str
    path: str
    entry_type: str


class ListDirResult(BaseModel):
    """Structured result for one directory listing."""

    model_config = ConfigDict(extra="forbid")

    path: str
    entries: list[DirectoryEntry]
    truncated: bool = False


class ReadFileArgs(BaseModel):
    """Arguments for reading one text file inside the workspace."""

    model_config = ConfigDict(extra="forbid")

    path: str
    start_line: int = Field(default=1, ge=1)
    end_line: int | None = Field(default=None, ge=1)


class ReadFileResult(BaseModel):
    """Structured text slice returned from one file read."""

    model_config = ConfigDict(extra="forbid")

    path: str
    start_line: int
    end_line: int
    content: str


class SearchFilesArgs(BaseModel):
    """Arguments for searching workspace text files."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)
    path: str = "."
    limit: int = Field(default=20, ge=1, le=200)


class SearchMatch(BaseModel):
    """One text search match inside a workspace file."""

    model_config = ConfigDict(extra="forbid")

    path: str
    line_number: int
    line_text: str


class SearchFilesResult(BaseModel):
    """Structured search result for workspace text files."""

    model_config = ConfigDict(extra="forbid")

    query: str
    matches: list[SearchMatch]
    truncated: bool = False


class ListDirTool:
    """List direct children of a directory inside the workspace."""

    spec = ToolSpec(
        name="list_dir",
        description="List directory contents inside the workspace.",
        input_model=ListDirArgs,
        output_model=ListDirResult,
        risk_level=ToolRiskLevel.READ_ONLY,
        path_argument_names=("path",),
    )

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root.resolve(strict=False)

    async def execute(self, arguments: ListDirArgs) -> ListDirResult:
        directory_path = _resolve_workspace_path(
            self._workspace_root,
            arguments.path,
        )
        if not directory_path.exists():
            raise ValueError(f"directory does not exist: {arguments.path}")
        if not directory_path.is_dir():
            raise ValueError(f"path is not a directory: {arguments.path}")

        child_paths = sorted(directory_path.iterdir(), key=lambda path: path.name)
        entries = [
            DirectoryEntry(
                name=child_path.name,
                path=_relative_workspace_path(self._workspace_root, child_path),
                entry_type="dir" if child_path.is_dir() else "file",
            )
            for child_path in child_paths[: arguments.limit]
        ]
        return ListDirResult(
            path=_relative_workspace_path(self._workspace_root, directory_path),
            entries=entries,
            truncated=len(child_paths) > arguments.limit,
        )


class ReadFileTool:
    """Read one text file inside the workspace."""

    spec = ToolSpec(
        name="read_file",
        description="Read text from a file inside the workspace.",
        input_model=ReadFileArgs,
        output_model=ReadFileResult,
        risk_level=ToolRiskLevel.READ_ONLY,
        path_argument_names=("path",),
    )

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root.resolve(strict=False)

    async def execute(self, arguments: ReadFileArgs) -> ReadFileResult:
        file_path = _resolve_workspace_path(self._workspace_root, arguments.path)
        if not file_path.exists():
            raise ValueError(f"file does not exist: {arguments.path}")
        if not file_path.is_file():
            raise ValueError(f"path is not a file: {arguments.path}")

        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError as exc:
            raise ValueError(f"file is not valid utf-8 text: {arguments.path}") from exc

        end_line = arguments.end_line or len(lines)
        if end_line < arguments.start_line:
            raise ValueError("end_line must be greater than or equal to start_line")

        selected_lines = lines[arguments.start_line - 1 : end_line]
        return ReadFileResult(
            path=_relative_workspace_path(self._workspace_root, file_path),
            start_line=arguments.start_line,
            end_line=arguments.start_line + len(selected_lines) - 1
            if selected_lines
            else arguments.start_line - 1,
            content="\n".join(selected_lines),
        )


class SearchFilesTool:
    """Search workspace text files for a plain-text query."""

    spec = ToolSpec(
        name="search_files",
        description="Search workspace text files for matching text.",
        input_model=SearchFilesArgs,
        output_model=SearchFilesResult,
        risk_level=ToolRiskLevel.READ_ONLY,
        path_argument_names=("path",),
    )

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root.resolve(strict=False)

    async def execute(self, arguments: SearchFilesArgs) -> SearchFilesResult:
        search_root = _resolve_workspace_path(self._workspace_root, arguments.path)
        if not search_root.exists():
            raise ValueError(f"search path does not exist: {arguments.path}")

        candidate_files = (
            [search_root]
            if search_root.is_file()
            else sorted(path for path in search_root.rglob("*") if path.is_file())
        )

        matches: list[SearchMatch] = []
        truncated = False
        query_text = arguments.query.lower()

        for file_path in candidate_files:
            try:
                file_lines = file_path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue

            for line_number, line_text in enumerate(file_lines, start=1):
                if query_text not in line_text.lower():
                    continue
                matches.append(
                    SearchMatch(
                        path=_relative_workspace_path(self._workspace_root, file_path),
                        line_number=line_number,
                        line_text=line_text,
                    )
                )
                if len(matches) >= arguments.limit:
                    truncated = True
                    return SearchFilesResult(
                        query=arguments.query,
                        matches=matches,
                        truncated=truncated,
                    )

        return SearchFilesResult(
            query=arguments.query,
            matches=matches,
            truncated=truncated,
        )


def build_read_only_tool_registry(workspace_root: Path) -> ToolRegistry:
    """Build the initial safe read-only tool registry for one workspace."""

    return ToolRegistry(
        [
            ListDirTool(workspace_root),
            ReadFileTool(workspace_root),
            SearchFilesTool(workspace_root),
        ]
    )


def _resolve_workspace_path(workspace_root: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    resolved_path = (
        candidate.resolve(strict=False)
        if candidate.is_absolute()
        else (workspace_root / candidate).resolve(strict=False)
    )
    try:
        resolved_path.relative_to(workspace_root)
    except ValueError as exc:
        raise ValueError(f"path is outside workspace: {raw_path}") from exc
    return resolved_path


def _relative_workspace_path(workspace_root: Path, path: Path) -> str:
    relative_path = path.relative_to(workspace_root)
    return "." if relative_path == Path() else relative_path.as_posix()
