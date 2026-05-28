"""Backend import-direction and Python syntax guardrails."""

from tests.unit.architecture_guardrails.helpers import _format_violation
from tests.unit.architecture_guardrails.helpers import _python_future_features
from tests.unit.architecture_guardrails.helpers import _python_import_violations
from tests.unit.architecture_guardrails.rules import PYTHON_DIRECTION_RULES
from tests.unit.architecture_guardrails.rules import PYTHON_IMPORT_RULES
from tests.unit.architecture_guardrails.rules import REPO_ROOT
from tests.unit.architecture_guardrails.rules import V10_PYTHON_IMPORT_RULES
from tests.unit.architecture_guardrails.rules import V11_PYTHON_IMPORT_RULES
from tests.unit.architecture_guardrails.rules import V13_PYTHON_IMPORT_RULES
from tests.unit.architecture_guardrails.rules import V14_PYTHON_IMPORT_RULES
from tests.unit.architecture_guardrails.rules import (
    V17_RUNTIME_HANDOFF_FORBIDDEN_IMPORTS,
)
from tests.unit.architecture_guardrails.rules import V17_STORE_HANDOFF_FORBIDDEN_IMPORTS


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


def test_v10_python_boundaries_avoid_transport_and_raw_store_imports() -> None:
    violations: list[str] = []

    for file_path, forbidden_prefixes, message in V10_PYTHON_IMPORT_RULES:
        violations.extend(
            _python_import_violations(file_path, forbidden_prefixes, message)
        )

    assert violations == []


def test_v11_python_boundaries_avoid_presentation_imports() -> None:
    violations: list[str] = []

    for file_path, forbidden_prefixes, message in V11_PYTHON_IMPORT_RULES:
        violations.extend(
            _python_import_violations(file_path, forbidden_prefixes, message)
        )

    assert violations == []


def test_v13_python_boundaries_avoid_transport_and_presentation_imports() -> None:
    violations: list[str] = []

    for file_path, forbidden_prefixes, message in V13_PYTHON_IMPORT_RULES:
        violations.extend(
            _python_import_violations(file_path, forbidden_prefixes, message)
        )

    assert violations == []


def test_v14_python_boundaries_avoid_transport_and_presentation_imports() -> None:
    violations: list[str] = []

    for file_path, forbidden_prefixes, message in V14_PYTHON_IMPORT_RULES:
        violations.extend(
            _python_import_violations(file_path, forbidden_prefixes, message)
        )

    assert violations == []


def test_v17_runtime_handoff_helpers_avoid_concrete_store_and_transport_imports() -> (
    None
):
    violations: list[str] = []

    for file_path in sorted(
        (REPO_ROOT / "src" / "glassbox" / "runtime").glob("handoff_*.py")
    ):
        violations.extend(
            _python_import_violations(
                file_path,
                V17_RUNTIME_HANDOFF_FORBIDDEN_IMPORTS,
                (
                    "post-v17 runtime handoff helpers should stay "
                    "transport-agnostic and avoid concrete sqlite, web, "
                    "frontend, or CLI presentation imports"
                ),
            )
        )

    assert violations == []


def test_v17_store_handoff_modules_stay_below_runtime_and_transport_layers() -> None:
    violations: list[str] = []

    for file_path in sorted(
        [
            *(REPO_ROOT / "src" / "glassbox" / "store").glob("repository_handoff.py"),
            *(REPO_ROOT / "src" / "glassbox" / "store").glob("sqlite_query_handoff.py"),
            *(REPO_ROOT / "src" / "glassbox" / "store").glob(
                "sqlite_projection_handoff*.py"
            ),
            *(REPO_ROOT / "src" / "glassbox" / "store").glob(
                "sqlite_schema_handoff.py"
            ),
        ]
    ):
        violations.extend(
            _python_import_violations(
                file_path,
                V17_STORE_HANDOFF_FORBIDDEN_IMPORTS,
                (
                    "post-v17 store handoff helpers should stay below runtime, "
                    "web, and CLI layers"
                ),
            )
        )

    assert violations == []
