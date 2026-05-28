"""Frontend boundary, store, and facade guardrails."""

from tests.unit.architecture_guardrails.helpers import _format_violation
from tests.unit.architecture_guardrails.helpers import _frontend_import_modules
from tests.unit.architecture_guardrails.helpers import _frontend_import_violations
from tests.unit.architecture_guardrails.helpers import _line_count
from tests.unit.architecture_guardrails.helpers import _line_count_violations
from tests.unit.architecture_guardrails.helpers import _matches_any_prefix
from tests.unit.architecture_guardrails.rules import FRONTEND_FACADE_RULES
from tests.unit.architecture_guardrails.rules import FRONTEND_IMPORT_RULES
from tests.unit.architecture_guardrails.rules import FRONTEND_ROOT
from tests.unit.architecture_guardrails.rules import V10_FRONTEND_IMPORT_RULES
from tests.unit.architecture_guardrails.rules import V10_FRONTEND_PRESSURE_POINT_RULES
from tests.unit.architecture_guardrails.rules import V11_FRONTEND_IMPORT_RULES
from tests.unit.architecture_guardrails.rules import V11_FRONTEND_PRESSURE_POINT_RULES
from tests.unit.architecture_guardrails.rules import V13_FRONTEND_IMPORT_RULES
from tests.unit.architecture_guardrails.rules import V13_FRONTEND_PRESSURE_POINT_RULES
from tests.unit.architecture_guardrails.rules import V14_FRONTEND_FACADE_DELEGATES
from tests.unit.architecture_guardrails.rules import V14_FRONTEND_FACADE_RULES
from tests.unit.architecture_guardrails.rules import V14_FRONTEND_IMPORT_RULES
from tests.unit.architecture_guardrails.rules import V14_FRONTEND_PRESSURE_POINT_RULES
from tests.unit.architecture_guardrails.rules import V16_FRONTEND_PRESSURE_POINT_RULES
from tests.unit.architecture_guardrails.rules import V17_FRONTEND_PRESSURE_POINT_RULES
from tests.unit.architecture_guardrails.rules import (
    V17_HANDOFF_COMPONENT_FORBIDDEN_IMPORTS,
)
from tests.unit.architecture_guardrails.rules import V17_HANDOFF_STORE_FORBIDDEN_IMPORTS


def test_frontend_store_boundaries_stay_framework_light() -> None:
    violations: list[str] = []

    for directory, forbidden_prefixes, message in FRONTEND_IMPORT_RULES:
        violations.extend(
            _frontend_import_violations(directory, forbidden_prefixes, message)
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


def test_v10_frontend_pressure_points_do_not_grow_before_split() -> None:
    violations = _line_count_violations(V10_FRONTEND_PRESSURE_POINT_RULES)

    assert violations == []


def test_v10_frontend_boundaries_avoid_transport_and_backend_imports() -> None:
    violations: list[str] = []

    for file_path, forbidden_prefixes, message in V10_FRONTEND_IMPORT_RULES:
        violations.extend(
            _frontend_import_violations(file_path, forbidden_prefixes, message)
        )

    assert violations == []


def test_v11_frontend_pressure_points_do_not_grow_before_split() -> None:
    violations = _line_count_violations(V11_FRONTEND_PRESSURE_POINT_RULES)

    assert violations == []


def test_v11_frontend_boundaries_avoid_transport_and_backend_imports() -> None:
    violations: list[str] = []

    for file_path, forbidden_prefixes, message in V11_FRONTEND_IMPORT_RULES:
        violations.extend(
            _frontend_import_violations(file_path, forbidden_prefixes, message)
        )

    assert violations == []


def test_v13_frontend_pressure_points_do_not_grow_before_split() -> None:
    violations = _line_count_violations(V13_FRONTEND_PRESSURE_POINT_RULES)

    assert violations == []


def test_v13_frontend_boundaries_avoid_transport_and_backend_imports() -> None:
    violations: list[str] = []

    for file_path, forbidden_prefixes, message in V13_FRONTEND_IMPORT_RULES:
        violations.extend(
            _frontend_import_violations(file_path, forbidden_prefixes, message)
        )

    assert violations == []


def test_v14_frontend_pressure_points_do_not_grow_before_split() -> None:
    violations = _line_count_violations(V14_FRONTEND_PRESSURE_POINT_RULES)

    assert violations == []


def test_v16_frontend_pressure_points_do_not_grow_before_split() -> None:
    violations = _line_count_violations(V16_FRONTEND_PRESSURE_POINT_RULES)

    assert violations == []


def test_v17_frontend_pressure_points_do_not_grow_before_split() -> None:
    violations = _line_count_violations(V17_FRONTEND_PRESSURE_POINT_RULES)

    assert violations == []


def test_v17_handoff_store_helpers_stay_out_of_component_layers() -> None:
    violations: list[str] = []

    for file_path in sorted((FRONTEND_ROOT / "stores").glob("handoff-store*.ts")):
        violations.extend(
            _frontend_import_violations(
                file_path,
                V17_HANDOFF_STORE_FORBIDDEN_IMPORTS,
                (
                    "post-v17 handoff store helpers should own transport and "
                    "action state without importing React components, Next "
                    "server modules, or backend source"
                ),
            )
        )

    assert violations == []


def test_v17_handoff_components_do_not_call_api_directly() -> None:
    violations: list[str] = []

    for path in (
        FRONTEND_ROOT / "components" / "console" / "handoff-cockpit.tsx",
        FRONTEND_ROOT / "components" / "console" / "handoff",
    ):
        violations.extend(
            _frontend_import_violations(
                path,
                V17_HANDOFF_COMPONENT_FORBIDDEN_IMPORTS,
                (
                    "post-v17 handoff cockpit components should receive store "
                    "callbacks and typed props instead of importing API clients "
                    "or backend source"
                ),
            )
        )

    assert violations == []


def test_v14_extracted_frontend_facades_stay_thin_and_delegate_to_owned_helpers() -> (
    None
):
    violations = _line_count_violations(V14_FRONTEND_FACADE_RULES)

    for file_path, required_prefixes, message in V14_FRONTEND_FACADE_DELEGATES:
        modules = _frontend_import_modules(file_path)
        missing = [
            required_prefix
            for required_prefix in required_prefixes
            if not any(
                _matches_any_prefix(module, (required_prefix,)) for module in modules
            )
        ]
        if missing:
            violations.append(
                _format_violation(
                    file_path,
                    message,
                    f"missing delegate imports {missing}",
                )
            )

    assert violations == []


def test_v14_frontend_boundaries_avoid_transport_and_backend_imports() -> None:
    violations: list[str] = []

    for file_path, forbidden_prefixes, message in V14_FRONTEND_IMPORT_RULES:
        violations.extend(
            _frontend_import_violations(file_path, forbidden_prefixes, message)
        )

    assert violations == []
