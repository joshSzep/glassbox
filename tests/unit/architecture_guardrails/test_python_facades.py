"""Python facade and delegate guardrails."""

from tests.unit.architecture_guardrails.helpers import _format_violation
from tests.unit.architecture_guardrails.helpers import _line_count
from tests.unit.architecture_guardrails.helpers import _matches_any_prefix
from tests.unit.architecture_guardrails.helpers import _python_import_modules
from tests.unit.architecture_guardrails.rules import PYTHON_FACADE_RULES
from tests.unit.architecture_guardrails.rules import V11_COMPATIBILITY_FACADE_DELEGATES
from tests.unit.architecture_guardrails.rules import V13_COMPATIBILITY_FACADE_DELEGATES
from tests.unit.architecture_guardrails.rules import V13_PYTHON_FACADE_RULES
from tests.unit.architecture_guardrails.rules import V14_PYTHON_FACADE_DELEGATES
from tests.unit.architecture_guardrails.rules import V14_PYTHON_FACADE_RULES
from tests.unit.architecture_guardrails.rules import V16_PYTHON_FACADE_DELEGATES
from tests.unit.architecture_guardrails.rules import V16_PYTHON_FACADE_RULES
from tests.unit.architecture_guardrails.rules import V17_PYTHON_FACADE_DELEGATES
from tests.unit.architecture_guardrails.rules import V17_PYTHON_FACADE_RULES


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


def test_v11_compatibility_facades_delegate_to_intended_owners() -> None:
    violations: list[str] = []

    for file_path, required_prefixes, message in V11_COMPATIBILITY_FACADE_DELEGATES:
        modules = _python_import_modules(file_path)
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


def test_v13_extracted_python_facades_stay_thin_and_import_owned_helpers() -> None:
    violations: list[str] = []

    for file_path, allowed_prefixes, max_lines, message in V13_PYTHON_FACADE_RULES:
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


def test_v13_compatibility_facades_delegate_to_intended_owners() -> None:
    violations: list[str] = []

    for file_path, required_prefixes, message in V13_COMPATIBILITY_FACADE_DELEGATES:
        modules = _python_import_modules(file_path)
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


def test_v14_extracted_python_facades_stay_thin_and_import_owned_helpers() -> None:
    violations: list[str] = []

    for file_path, allowed_prefixes, max_lines, message in V14_PYTHON_FACADE_RULES:
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


def test_v14_extracted_python_facades_delegate_to_intended_owners() -> None:
    violations: list[str] = []

    for file_path, required_prefixes, message in V14_PYTHON_FACADE_DELEGATES:
        modules = _python_import_modules(file_path)
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


def test_v16_extracted_python_facades_stay_thin_and_import_owned_helpers() -> None:
    violations: list[str] = []

    for file_path, allowed_prefixes, max_lines, message in V16_PYTHON_FACADE_RULES:
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


def test_v16_extracted_python_facades_delegate_to_intended_owners() -> None:
    violations: list[str] = []

    for file_path, required_prefixes, message in V16_PYTHON_FACADE_DELEGATES:
        modules = _python_import_modules(file_path)
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


def test_v17_extracted_python_facades_stay_thin_and_import_owned_helpers() -> None:
    violations: list[str] = []

    for file_path, allowed_prefixes, max_lines, message in V17_PYTHON_FACADE_RULES:
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


def test_v17_extracted_python_facades_delegate_to_intended_owners() -> None:
    violations: list[str] = []

    for file_path, required_prefixes, message in V17_PYTHON_FACADE_DELEGATES:
        modules = _python_import_modules(file_path)
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
