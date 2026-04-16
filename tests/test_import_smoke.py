"""Smoke tests for the initial project scaffold."""

import glassbox


def test_package_imports() -> None:
    assert glassbox.__version__ == "0.1.0"
