"""Lightweight architectural guardrails for refactor-sensitive boundaries."""

import ast
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src" / "glassbox"
FRONTEND_ROOT = REPO_ROOT / "frontend"

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
        ("glassbox.store.sqlite",),
        "cli modules must not depend directly on raw sqlite helpers",
    ),
    (
        SRC_ROOT / "web" / "routes",
        (
            "glassbox.store.sqlite",
            "glassbox.store.repositories",
        ),
        (
            "web routes must not depend directly on raw store helpers or "
            "repository implementations"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "background_jobs.py",
        (
            "glassbox.cli.tui",
            "glassbox.store.sqlite",
            "glassbox.web",
        ),
        (
            "post-v8 runtime autonomy modules should use service/query seams "
            "instead of TUI, raw sqlite, or HTTP route imports"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "workspace_memory_capture.py",
        (
            "glassbox.cli.tui",
            "glassbox.store.sqlite",
            "glassbox.web",
        ),
        (
            "post-v8 runtime autonomy modules should use service/query seams "
            "instead of TUI, raw sqlite, or HTTP route imports"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "observability.py",
        (
            "glassbox.cli.tui",
            "glassbox.store.sqlite",
            "glassbox.web",
        ),
        (
            "post-v8 runtime autonomy modules should use service/query seams "
            "instead of TUI, raw sqlite, or HTTP route imports"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "repository_index.py",
        (
            "glassbox.cli.tui",
            "glassbox.store.sqlite",
            "glassbox.web",
        ),
        (
            "post-v8 runtime autonomy modules should use service/query seams "
            "instead of TUI, raw sqlite, or HTTP route imports"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "provider_diagnostics.py",
        (
            "glassbox.cli.tui",
            "glassbox.store.sqlite",
            "glassbox.web",
        ),
        (
            "post-v8 runtime autonomy modules should use service/query seams "
            "instead of TUI, raw sqlite, or HTTP route imports"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "provider_canary.py",
        (
            "glassbox.cli.tui",
            "glassbox.store.sqlite",
            "glassbox.web",
        ),
        (
            "post-v8 runtime autonomy modules should use service/query seams "
            "instead of TUI, raw sqlite, or HTTP route imports"
        ),
    ),
    (
        SRC_ROOT / "cli" / "tui",
        (
            "glassbox.runtime.background_jobs",
            "glassbox.store",
            "glassbox.web",
        ),
        (
            "TUI state and widgets should consume events, snapshots, and "
            "CLI-local state instead of store, web, or worker orchestration"
        ),
    ),
)

FRONTEND_IMPORT_RULES: tuple[tuple[Path, tuple[str, ...], str], ...] = (
    (
        FRONTEND_ROOT / "stores",
        (
            "@/app",
            "@/components",
            "@/pages",
            "next/",
            "react",
            "src/glassbox",
        ),
        (
            "frontend stores should stay framework-light and must not import "
            "React components, Next server modules, or backend source"
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
        ("glassbox.store.sqlite_",),
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
        SRC_ROOT / "runtime" / "evals.py",
        (
            "glassbox.runtime.eval_case_models",
            "glassbox.runtime.eval_constants",
            "glassbox.runtime.eval_discovery",
            "glassbox.runtime.eval_profile_models",
            "glassbox.runtime.eval_selection",
        ),
        90,
        "evals should stay a thin facade over split eval modules",
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

FRONTEND_FACADE_RULES: tuple[tuple[Path, int, str], ...] = (
    (
        FRONTEND_ROOT / "stores" / "dashboard-stores.ts",
        1600,
        (
            "dashboard-stores.ts should remain a reviewable compatibility "
            "surface while domain stores split underneath it"
        ),
    ),
)


def test_dependency_direction_rules_hold_for_refactor_boundaries() -> None:
    violations: list[str] = []

    for directory, forbidden_prefixes, message in PYTHON_DIRECTION_RULES:
        violations.extend(
            _python_import_violations(directory, forbidden_prefixes, message)
        )

    for directory, forbidden_prefixes, message in PYTHON_IMPORT_RULES:
        violations.extend(
            _python_import_violations(
                directory,
                forbidden_prefixes,
                message,
                skip_package_init=True,
            )
        )

    assert violations == []


def test_frontend_store_boundaries_stay_framework_light() -> None:
    violations: list[str] = []

    for directory, forbidden_prefixes, message in FRONTEND_IMPORT_RULES:
        violations.extend(
            _frontend_import_violations(directory, forbidden_prefixes, message)
        )

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


def test_frontend_public_store_surfaces_stay_reviewable() -> None:
    violations: list[str] = []

    for file_path, max_lines, message in FRONTEND_FACADE_RULES:
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


def test_post_v8_python_guardrail_messages_point_to_owned_boundaries(
    tmp_path: Path,
) -> None:
    runtime_file = tmp_path / "collector.py"
    runtime_file.write_text(
        "from glassbox.web.routes.sessions import router\n",
        encoding="utf-8",
    )

    violations = _python_import_violations(
        tmp_path,
        ("glassbox.web",),
        (
            "post-v8 runtime autonomy modules should use service/query seams "
            "instead of TUI, raw sqlite, or HTTP route imports"
        ),
    )

    assert violations == [
        (
            f"{runtime_file}: post-v8 runtime autonomy "
            "modules should use service/query seams instead of TUI, raw sqlite, "
            "or HTTP route imports: glassbox.web.routes.sessions"
        )
    ]


def test_frontend_store_guardrail_messages_point_to_domain_store_splits(
    tmp_path: Path,
) -> None:
    store_file = tmp_path / "session-store.ts"
    store_file.write_text(
        'import { SessionInspector } from "@/components/console/session-inspector";\n',
        encoding="utf-8",
    )

    violations = _frontend_import_violations(
        tmp_path,
        ("@/components",),
        (
            "frontend stores should stay framework-light and must not import "
            "React components, Next server modules, or backend source"
        ),
    )

    assert violations == [
        (
            f"{store_file}: frontend stores should stay "
            "framework-light and must not import React components, Next server "
            "modules, or backend source: @/components/console/session-inspector"
        )
    ]


def test_spa_source_replaces_legacy_static_dashboard() -> None:
    legacy_static_dir = SRC_ROOT / "web" / "static"
    assert not any(legacy_static_dir.rglob("*"))
    assert (REPO_ROOT / "frontend" / "app" / "page.tsx").is_file()
    assert (REPO_ROOT / "frontend" / "components" / "console").is_dir()


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

    for file_path in sorted(directory.rglob("*")):
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


def _format_violation(file_path: Path, message: str, detail: str) -> str:
    try:
        display_path = file_path.relative_to(REPO_ROOT)
    except ValueError:
        display_path = file_path
    return f"{display_path}: {message}: {detail}"


def _matches_any_prefix(module: str, prefixes: tuple[str, ...]) -> bool:
    return any(module == prefix or module.startswith(prefix) for prefix in prefixes)
