"""Read-only test discovery and target-selection tools."""

import ast
from collections.abc import Iterable
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core.types import RepositoryIndexEntityKind
from glassbox.runtime.repository_index import RepositoryIndexNotFoundError
from glassbox.runtime.repository_index import load_repository_index
from glassbox.tools.registry import ToolRiskLevel
from glassbox.tools.registry import ToolSpec

_EXCLUDED_NAMES = {
    ".git",
    ".glassbox",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "out",
}
_PYTEST_MARKER_CONFIGS = {"pytest.ini", "tox.ini", "setup.cfg", "pyproject.toml"}


class TestFramework(StrEnum):
    """Supported test framework classifications."""

    PYTEST = "pytest"
    UNKNOWN = "unknown"


class TestTargetConfidence(StrEnum):
    """Confidence levels for recommended test targets."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TestDiscoveryArgs(BaseModel):
    """Arguments for read-only test discovery."""

    model_config = ConfigDict(extra="forbid")

    paths: list[str] = Field(
        default_factory=list,
        description="Optional workspace-relative paths to inspect.",
        max_length=100,
    )
    include_symbols: bool = Field(
        default=True,
        description="Parse Python test files for test functions, classes, and markers.",
    )
    max_files: int = Field(
        default=200,
        ge=1,
        le=1000,
        description="Maximum test files to report.",
    )


class TestFileDiscovery(BaseModel):
    """Structured summary for one discovered test file."""

    model_config = ConfigDict(extra="forbid")

    path: str
    framework: TestFramework = TestFramework.UNKNOWN
    test_functions: list[str] = Field(default_factory=list)
    test_classes: list[str] = Field(default_factory=list)
    markers: list[str] = Field(default_factory=list)
    owner_hints: list[str] = Field(default_factory=list)


class TestDiscoveryResult(BaseModel):
    """Read-only test discovery result."""

    model_config = ConfigDict(extra="forbid")

    framework: TestFramework = TestFramework.UNKNOWN
    test_files: list[TestFileDiscovery] = Field(default_factory=list)
    truncated: bool = False
    repository_index_status: str = "missing"
    warnings: list[str] = Field(default_factory=list)


class TestTargetSelectionArgs(BaseModel):
    """Arguments for selecting likely tests for changed paths or task context."""

    model_config = ConfigDict(extra="forbid")

    changed_paths: list[str] = Field(
        default_factory=list,
        description="Workspace-relative changed source or test paths.",
        max_length=200,
    )
    task_context: str | None = Field(
        default=None,
        max_length=1000,
        description="Optional short task context used only for confidence notes.",
    )
    max_targets: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum candidate test targets to return.",
    )


class TestTargetCandidate(BaseModel):
    """One advisory test target recommendation."""

    model_config = ConfigDict(extra="forbid")

    path: str
    framework: TestFramework
    confidence: TestTargetConfidence
    reasons: list[str] = Field(default_factory=list)
    matched_changed_paths: list[str] = Field(default_factory=list)
    command: list[str] = Field(default_factory=list)


class TestTargetSelectionResult(BaseModel):
    """Structured advisory test target selection result."""

    model_config = ConfigDict(extra="forbid")

    candidates: list[TestTargetCandidate] = Field(default_factory=list)
    repository_index_status: str = "missing"
    warnings: list[str] = Field(default_factory=list)


class TestDiscoveryTool:
    """Discover tests without executing them."""

    spec = ToolSpec(
        name="test_discovery",
        description=(
            "List test files and, for Python pytest files, test functions, "
            "classes, markers, and repository-index owner hints without running tests."
        ),
        input_model=TestDiscoveryArgs,
        output_model=TestDiscoveryResult,
        risk_level=ToolRiskLevel.READ_ONLY,
        path_argument_names=("paths",),
    )

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root.resolve(strict=False)

    async def execute(self, arguments: TestDiscoveryArgs) -> TestDiscoveryResult:
        return discover_tests(self._workspace_root, arguments)


class TestTargetSelectionTool:
    """Select likely tests for changed paths without running them."""

    spec = ToolSpec(
        name="test_target_selection",
        description=(
            "Recommend focused test targets for changed paths or task context. "
            "Recommendations are advisory and do not execute tests."
        ),
        input_model=TestTargetSelectionArgs,
        output_model=TestTargetSelectionResult,
        risk_level=ToolRiskLevel.READ_ONLY,
        path_argument_names=("changed_paths",),
    )

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root.resolve(strict=False)

    async def execute(
        self,
        arguments: TestTargetSelectionArgs,
    ) -> TestTargetSelectionResult:
        return select_test_targets(self._workspace_root, arguments)


def discover_tests(
    workspace_root: Path,
    arguments: TestDiscoveryArgs | None = None,
) -> TestDiscoveryResult:
    """Discover pytest-like test files without executing them."""

    args = arguments or TestDiscoveryArgs()
    root = workspace_root.resolve(strict=False)
    path_filters = _normalize_workspace_paths(root, args.paths)
    index_status, owner_hints = _load_index_test_hints(root)
    candidate_files = list(_iter_candidate_test_files(root, path_filters))
    truncated = len(candidate_files) > args.max_files
    bounded_files = candidate_files[: args.max_files]
    test_files = [
        _discover_test_file(root, path, args.include_symbols, owner_hints)
        for path in bounded_files
    ]
    framework = (
        TestFramework.PYTEST
        if test_files
        or any((root / config).exists() for config in _PYTEST_MARKER_CONFIGS)
        else TestFramework.UNKNOWN
    )
    warnings = []
    if not test_files:
        warnings.append("no pytest-style test files discovered")
    if truncated:
        warnings.append(f"test discovery truncated at {args.max_files} files")
    return TestDiscoveryResult(
        framework=framework,
        test_files=test_files,
        truncated=truncated,
        repository_index_status=index_status,
        warnings=warnings,
    )


def select_test_targets(
    workspace_root: Path,
    arguments: TestTargetSelectionArgs,
) -> TestTargetSelectionResult:
    """Recommend focused test targets for changed paths without execution."""

    root = workspace_root.resolve(strict=False)
    changed_paths = _normalize_workspace_paths(root, arguments.changed_paths)
    discovery = discover_tests(root, TestDiscoveryArgs(max_files=1000))
    candidates: dict[str, TestTargetCandidate] = {}

    for changed_path in changed_paths:
        if _is_test_file(Path(changed_path)):
            _merge_candidate(
                candidates,
                TestTargetCandidate(
                    path=changed_path,
                    framework=TestFramework.PYTEST,
                    confidence=TestTargetConfidence.HIGH,
                    reasons=["changed path is itself a pytest-style test file"],
                    matched_changed_paths=[changed_path],
                    command=["pytest", changed_path],
                ),
            )
            continue

        for test_file in discovery.test_files:
            confidence, reasons = _target_confidence_for_change(
                changed_path,
                test_file.path,
            )
            if confidence is None:
                continue
            _merge_candidate(
                candidates,
                TestTargetCandidate(
                    path=test_file.path,
                    framework=test_file.framework,
                    confidence=confidence,
                    reasons=reasons,
                    matched_changed_paths=[changed_path],
                    command=["pytest", test_file.path],
                ),
            )

    if not candidates and arguments.task_context:
        for test_file in discovery.test_files[: arguments.max_targets]:
            _merge_candidate(
                candidates,
                TestTargetCandidate(
                    path=test_file.path,
                    framework=test_file.framework,
                    confidence=TestTargetConfidence.LOW,
                    reasons=["task context supplied but no changed-path match found"],
                    command=["pytest", test_file.path],
                ),
            )

    ordered = sorted(
        candidates.values(),
        key=lambda candidate: (
            _confidence_sort_key(candidate.confidence),
            candidate.path,
        ),
    )[: arguments.max_targets]
    warnings = list(discovery.warnings)
    if changed_paths and not ordered:
        warnings.append("no focused test targets matched changed paths")
    return TestTargetSelectionResult(
        candidates=ordered,
        repository_index_status=discovery.repository_index_status,
        warnings=warnings,
    )


def _discover_test_file(
    root: Path,
    path: Path,
    include_symbols: bool,
    owner_hints: dict[str, list[str]],
) -> TestFileDiscovery:
    relative = path.relative_to(root).as_posix()
    functions: list[str] = []
    classes: list[str] = []
    markers: list[str] = []
    if include_symbols and path.suffix == ".py":
        functions, classes, markers = _parse_pytest_symbols(path)
    return TestFileDiscovery(
        path=relative,
        framework=TestFramework.PYTEST
        if path.suffix == ".py"
        else TestFramework.UNKNOWN,
        test_functions=functions,
        test_classes=classes,
        markers=markers,
        owner_hints=owner_hints.get(relative, []),
    )


def _parse_pytest_symbols(path: Path) -> tuple[list[str], list[str], list[str]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except OSError, SyntaxError, UnicodeDecodeError:
        return [], [], []

    functions: list[str] = []
    classes: list[str] = []
    markers: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test_"):
                functions.append(node.name)
                markers.update(_decorator_markers(node.decorator_list))
        elif isinstance(node, ast.ClassDef):
            if node.name.startswith("Test"):
                classes.append(node.name)
                markers.update(_decorator_markers(node.decorator_list))
    return sorted(functions), sorted(classes), sorted(markers)


def _decorator_markers(decorators: list[ast.expr]) -> set[str]:
    markers: set[str] = set()
    for decorator in decorators:
        dotted = _decorator_name(decorator)
        if dotted is None:
            continue
        if dotted.startswith("pytest.mark."):
            markers.add(dotted.removeprefix("pytest.mark.").split(".", maxsplit=1)[0])
    return markers


def _decorator_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _decorator_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


def _iter_candidate_test_files(root: Path, path_filters: list[str]) -> Iterable[Path]:
    roots = [root / path for path in path_filters] if path_filters else [root]
    for search_root in roots:
        if search_root.is_file():
            if _is_test_file(search_root.relative_to(root)):
                yield search_root
            continue
        if not search_root.exists():
            continue
        for path in sorted(search_root.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(root)
            if _is_excluded(relative):
                continue
            if _is_test_file(relative):
                yield path


def _normalize_workspace_paths(workspace_root: Path, raw_paths: list[str]) -> list[str]:
    normalized: list[str] = []
    for raw_path in raw_paths:
        candidate = Path(raw_path)
        resolved = (
            candidate.resolve(strict=False)
            if candidate.is_absolute()
            else (workspace_root / candidate).resolve(strict=False)
        )
        try:
            relative = resolved.relative_to(workspace_root)
        except ValueError as exc:
            raise ValueError(f"path is outside workspace: {raw_path}") from exc
        normalized.append("." if relative == Path() else relative.as_posix())
    return normalized


def _load_index_test_hints(workspace_root: Path) -> tuple[str, dict[str, list[str]]]:
    try:
        snapshot = load_repository_index(workspace_root)
    except RepositoryIndexNotFoundError:
        return "missing", {}
    hints: dict[str, list[str]] = {}
    for entry in snapshot.entries:
        if entry.kind != RepositoryIndexEntityKind.TEST or entry.path is None:
            continue
        path = entry.path.as_posix()
        hint = entry.summary or entry.name
        hints.setdefault(path, []).append(hint)
    return snapshot.status.value, hints


def _target_confidence_for_change(
    changed_path: str,
    test_path: str,
) -> tuple[TestTargetConfidence | None, list[str]]:
    changed = Path(changed_path)
    test = Path(test_path)
    changed_stem = changed.stem.removeprefix("test_").removesuffix("_test")
    test_stem = test.stem.removeprefix("test_").removesuffix("_test")
    reasons: list[str] = []

    if changed_stem and changed_stem == test_stem:
        reasons.append(f"test filename matches changed module stem '{changed_stem}'")
        return TestTargetConfidence.HIGH, reasons

    changed_parts = set(changed.with_suffix("").parts)
    test_parts = set(test.with_suffix("").parts)
    shared_parts = sorted((changed_parts & test_parts) - {"src", "tests", "test"})
    if shared_parts:
        reasons.append(f"shared path components: {', '.join(shared_parts)}")
        return TestTargetConfidence.MEDIUM, reasons

    if changed.suffix == ".py" and test.parts and test.parts[0] == "tests":
        reasons.append("pytest file in repository may cover Python source change")
        return TestTargetConfidence.LOW, reasons

    return None, []


def _merge_candidate(
    candidates: dict[str, TestTargetCandidate],
    candidate: TestTargetCandidate,
) -> None:
    existing = candidates.get(candidate.path)
    if existing is None:
        candidates[candidate.path] = candidate
        return

    confidence = (
        candidate.confidence
        if _confidence_sort_key(candidate.confidence)
        < _confidence_sort_key(existing.confidence)
        else existing.confidence
    )
    candidates[candidate.path] = TestTargetCandidate(
        path=candidate.path,
        framework=candidate.framework,
        confidence=confidence,
        reasons=sorted({*existing.reasons, *candidate.reasons}),
        matched_changed_paths=sorted(
            {*existing.matched_changed_paths, *candidate.matched_changed_paths}
        ),
        command=candidate.command,
    )


def _confidence_sort_key(confidence: TestTargetConfidence) -> int:
    return {
        TestTargetConfidence.HIGH: 0,
        TestTargetConfidence.MEDIUM: 1,
        TestTargetConfidence.LOW: 2,
    }[confidence]


def _is_test_file(relative: Path) -> bool:
    name = relative.name
    return relative.suffix == ".py" and (
        name.startswith("test_")
        or name.endswith("_test.py")
        or "tests" in relative.parts
    )


def _is_excluded(relative: Path) -> bool:
    return any(part in _EXCLUDED_NAMES for part in relative.parts)
