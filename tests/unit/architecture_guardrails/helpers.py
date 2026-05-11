"""Shared helpers for architecture guardrail tests."""

import ast
import re
from pathlib import Path

from tests.unit.architecture_guardrails.rules import REPO_ROOT


def _python_import_modules(file_path: Path) -> list[str]:
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
            continue
        if isinstance(node, ast.ImportFrom):
            if node.level:
                modules.append("." * node.level + (node.module or ""))
                continue
            if node.module is not None:
                modules.append(node.module)
    return sorted(set(modules))


def _python_import_violations(
    directory: Path,
    forbidden_prefixes: tuple[str, ...],
    message: str,
    *,
    skip_package_init: bool = False,
) -> list[str]:
    violations: list[str] = []

    file_paths = [directory] if directory.is_file() else sorted(directory.rglob("*.py"))
    for file_path in file_paths:
        if skip_package_init and file_path.name == "__init__.py":
            continue
        for module in _python_import_modules(file_path):
            if _matches_any_prefix(module, forbidden_prefixes):
                violations.append(_format_violation(file_path, message, module))

    return violations


def _frontend_import_modules(file_path: Path) -> list[str]:
    source = file_path.read_text(encoding="utf-8")
    modules: list[str] = []
    for match in re.finditer(
        r"""^\s*import(?:\s+type)?(?:\s+[\s\S]*?\s+from)?\s+["']([^"']+)["']""",
        source,
        re.MULTILINE,
    ):
        modules.append(match.group(1))
    return sorted(set(modules))


def _frontend_import_violations(
    directory: Path,
    forbidden_prefixes: tuple[str, ...],
    message: str,
) -> list[str]:
    violations: list[str] = []

    file_paths = [directory] if directory.is_file() else sorted(directory.rglob("*"))
    for file_path in file_paths:
        if file_path.suffix not in {".ts", ".tsx"}:
            continue
        for module in _frontend_import_modules(file_path):
            if _matches_any_prefix(module, forbidden_prefixes):
                violations.append(_format_violation(file_path, message, module))

    return violations


def _python_future_features(file_path: Path) -> set[str]:
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    features: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and node.level == 0
            and node.module == "__future__"
        ):
            features.update(alias.name for alias in node.names)
    return features


def _line_count(file_path: Path) -> int:
    return len(file_path.read_text(encoding="utf-8").splitlines())


def _line_count_violations(rules: tuple[tuple[Path, int, str], ...]) -> list[str]:
    violations: list[str] = []

    for file_path, max_lines, message in rules:
        line_count = _line_count(file_path)
        if line_count > max_lines:
            violations.append(
                _format_violation(
                    file_path,
                    message,
                    f"{line_count} lines exceeds {max_lines}",
                )
            )

    return violations


def _format_violation(file_path: Path, message: str, detail: str) -> str:
    try:
        display_path = file_path.relative_to(REPO_ROOT)
    except ValueError:
        display_path = file_path
    return f"{display_path}: {message}: {detail}"


def _matches_any_prefix(module: str, prefixes: tuple[str, ...]) -> bool:
    return any(module == prefix or module.startswith(prefix) for prefix in prefixes)
