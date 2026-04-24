"""Lightweight architectural guardrails for refactor-sensitive boundaries."""

import ast
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src" / "glassbox"

PYTHON_DIRECTION_RULES: tuple[tuple[Path, tuple[str, ...], str], ...] = (
    (
        SRC_ROOT / "store",
        ("glassbox.runtime", "glassbox.cli", "glassbox.web"),
        "store modules must not depend on runtime, cli, or web packages",
    ),
    (
        SRC_ROOT / "services",
        (
            "glassbox.store",
            "glassbox.runtime",
            "glassbox.cli",
            "glassbox.web",
        ),
        (
            "services modules must stay free of concrete store, runtime, cli, "
            "and web imports"
        ),
    ),
)

PYTHON_IMPORT_RULES: tuple[tuple[Path, tuple[str, ...], str], ...] = (
    (
        SRC_ROOT / "cli",
        ("glassbox.store.sqlite", "glassbox.store._sqlite"),
        "cli modules must not depend directly on raw sqlite helpers",
    ),
    (
        SRC_ROOT / "web" / "routes",
        (
            "glassbox.store.sqlite",
            "glassbox.store._sqlite",
            "glassbox.store.repositories",
        ),
        (
            "web routes must not depend directly on raw store helpers or "
            "repository implementations"
        ),
    ),
)

PYTHON_FACADE_RULES: tuple[
    tuple[Path, tuple[str, ...], int, str],
    ...,
] = (
    (
        SRC_ROOT / "runtime" / "__init__.py",
        (
            "glassbox.runtime",
            "glassbox.runtime.bootstrap",
            "glassbox.runtime.bus",
            "glassbox.runtime.context",
        ),
        60,
        "runtime package root should stay a thin curated surface",
    ),
    (
        SRC_ROOT / "store" / "sqlite.py",
        ("glassbox.store._sqlite_",),
        100,
        "store.sqlite should stay a thin facade over internal sqlite modules",
    ),
    (
        SRC_ROOT / "runtime" / "eval_summary.py",
        (
            "glassbox.runtime.eval_summary_annotations",
            "glassbox.runtime.eval_summary_models",
            "glassbox.runtime.eval_summary_release",
            "glassbox.runtime.eval_summary_suite",
        ),
        80,
        "eval_summary should stay a thin facade over split reporting modules",
    ),
    (
        SRC_ROOT / "runtime" / "replay.py",
        (
            "glassbox.core.ids",
            "pathlib",
            "glassbox.runtime.replay_models",
            "glassbox.runtime.replay_orchestrator",
            "glassbox.runtime.replay_triage",
            "glassbox.services",
        ),
        240,
        (
            "replay.py should remain bounded and delegate specialized work "
            "to split replay modules"
        ),
    ),
)

JAVASCRIPT_FACADE_RULES: tuple[
    tuple[Path, tuple[str, ...], tuple[str, ...], int, str],
    ...,
] = (
    (
        SRC_ROOT / "web" / "static" / "state.js",
        (
            "./state-core.js",
            "./state-snapshot.js",
            "./state-stream.js",
            "./state-interaction.js",
            "./state-events.js",
        ),
        (
            "./state-core.js",
            "./state-snapshot.js",
            "./state-stream.js",
            "./state-interaction.js",
            "./state-events.js",
        ),
        200,
        "state.js should stay a thin facade over the split reducer modules",
    ),
    (
        SRC_ROOT / "web" / "static" / "render.js",
        (
            "./render-session-panes.js",
            "./render-activity-panes.js",
            "./render-action-panes.js",
            "./render-diagnostics-panes.js",
        ),
        (
            "./render-session-panes.js",
            "./render-activity-panes.js",
            "./render-action-panes.js",
            "./render-diagnostics-panes.js",
        ),
        90,
        "render.js should stay a thin facade over split pane renderers",
    ),
    (
        SRC_ROOT / "web" / "static" / "dashboard.js",
        (
            "./state.js",
            "./dashboard-controller.js",
            "./dashboard-dom.js",
            "./dashboard-transport.js",
        ),
        (
            "./dashboard-controller.js",
            "./dashboard-dom.js",
            "./dashboard-transport.js",
        ),
        110,
        (
            "dashboard.js should stay a thin browser entry facade over split "
            "transport, dom, and controller modules"
        ),
    ),
)


def test_dependency_direction_rules_hold_for_refactor_boundaries() -> None:
    violations: list[str] = []

    for directory, forbidden_prefixes, message in PYTHON_DIRECTION_RULES:
        for file_path in sorted(directory.rglob("*.py")):
            for module in _python_import_modules(file_path):
                if _matches_any_prefix(module, forbidden_prefixes):
                    violations.append(_format_violation(file_path, message, module))

    for directory, forbidden_prefixes, message in PYTHON_IMPORT_RULES:
        for file_path in sorted(directory.rglob("*.py")):
            if file_path.name == "__init__.py":
                continue
            for module in _python_import_modules(file_path):
                if _matches_any_prefix(module, forbidden_prefixes):
                    violations.append(_format_violation(file_path, message, module))

    assert violations == []


def test_python_modules_do_not_enable_future_annotations() -> None:
    violations: list[str] = []

    for root in (REPO_ROOT / "src", REPO_ROOT / "tests"):
        for file_path in sorted(root.rglob("*.py")):
            if "annotations" in _python_future_features(file_path):
                violations.append(
                    _format_violation(
                        file_path,
                        "python 3.14 modules should not use future annotations",
                        "from __future__ import annotations",
                    )
                )

    assert violations == []


def test_python_public_facades_stay_thin_and_delegate_to_owned_modules() -> None:
    violations: list[str] = []

    for file_path, allowed_prefixes, max_lines, message in PYTHON_FACADE_RULES:
        modules = _python_import_modules(file_path)
        disallowed = [
            module
            for module in modules
            if module != "__future__"
            and not _matches_any_prefix(module, allowed_prefixes)
        ]
        if disallowed:
            violations.append(
                _format_violation(
                    file_path,
                    message,
                    f"unexpected imports {disallowed}",
                )
            )
        line_count = _line_count(file_path)
        if line_count > max_lines:
            violations.append(
                _format_violation(
                    file_path,
                    message,
                    f"{line_count} lines exceeds {max_lines}",
                )
            )

    assert violations == []


def test_browser_public_facades_stay_thin_and_delegate_to_split_modules() -> None:
    violations: list[str] = []

    for (
        file_path,
        allowed_edges,
        required_edges,
        max_lines,
        message,
    ) in JAVASCRIPT_FACADE_RULES:
        edges = _javascript_module_edges(file_path)
        disallowed = sorted(edge for edge in edges if edge not in allowed_edges)
        if disallowed:
            violations.append(
                _format_violation(
                    file_path,
                    message,
                    f"unexpected imports {disallowed}",
                )
            )
        missing = sorted(edge for edge in required_edges if edge not in edges)
        if missing:
            violations.append(
                _format_violation(
                    file_path,
                    message,
                    f"missing imports {missing}",
                )
            )
        line_count = _line_count(file_path)
        if line_count > max_lines:
            violations.append(
                _format_violation(
                    file_path,
                    message,
                    f"{line_count} lines exceeds {max_lines}",
                )
            )

    assert violations == []


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


def _javascript_module_edges(file_path: Path) -> set[str]:
    content = file_path.read_text(encoding="utf-8")
    edges: set[str] = set()
    for statement in content.split(";"):
        stripped = statement.strip()
        from_match = re.search(r"\bfrom\s+[\"']([^\"']+)[\"']", stripped)
        if from_match is not None:
            edges.add(from_match.group(1))
            continue
        import_match = re.search(r"^import\s+[\"']([^\"']+)[\"']", stripped)
        if import_match is not None:
            edges.add(import_match.group(1))
    return edges


def _line_count(file_path: Path) -> int:
    return len(file_path.read_text(encoding="utf-8").splitlines())


def _format_violation(file_path: Path, message: str, detail: str) -> str:
    return f"{file_path.relative_to(REPO_ROOT)}: {message}: {detail}"


def _matches_any_prefix(module: str, prefixes: tuple[str, ...]) -> bool:
    return any(module == prefix or module.startswith(prefix) for prefix in prefixes)
