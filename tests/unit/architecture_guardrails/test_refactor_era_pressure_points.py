"""Refactor-era backend pressure point size guardrails."""

from tests.unit.architecture_guardrails.helpers import _line_count_violations
from tests.unit.architecture_guardrails.rules import V10_PYTHON_PRESSURE_POINT_RULES
from tests.unit.architecture_guardrails.rules import V11_PYTHON_PRESSURE_POINT_RULES
from tests.unit.architecture_guardrails.rules import V13_PYTHON_PRESSURE_POINT_RULES
from tests.unit.architecture_guardrails.rules import V14_PYTHON_PRESSURE_POINT_RULES
from tests.unit.architecture_guardrails.rules import V16_PYTHON_PRESSURE_POINT_RULES


def test_v10_python_pressure_points_do_not_grow_before_split() -> None:
    violations = _line_count_violations(V10_PYTHON_PRESSURE_POINT_RULES)

    assert violations == []


def test_v11_python_pressure_points_do_not_grow_before_split() -> None:
    violations = _line_count_violations(V11_PYTHON_PRESSURE_POINT_RULES)

    assert violations == []


def test_v13_python_pressure_points_do_not_grow_before_split() -> None:
    violations = _line_count_violations(V13_PYTHON_PRESSURE_POINT_RULES)

    assert violations == []


def test_v14_python_pressure_points_do_not_grow_before_split() -> None:
    violations = _line_count_violations(V14_PYTHON_PRESSURE_POINT_RULES)

    assert violations == []


def test_v16_python_pressure_points_do_not_grow_before_split() -> None:
    violations = _line_count_violations(V16_PYTHON_PRESSURE_POINT_RULES)

    assert violations == []
