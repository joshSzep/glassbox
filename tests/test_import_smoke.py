"""Smoke tests for the initial project scaffold."""

import glassbox
import glassbox.cli
import glassbox.core
import glassbox.llm
import glassbox.runtime
import glassbox.services
import glassbox.store
import glassbox.tools
import glassbox.web


def test_package_imports() -> None:
    assert glassbox.__version__ == "0.1.0"


def test_top_level_packages_import() -> None:
    assert glassbox.cli is not None
    assert glassbox.core is not None
    assert glassbox.llm is not None
    assert glassbox.runtime is not None
    assert glassbox.services is not None
    assert glassbox.store is not None
    assert glassbox.tools is not None
    assert glassbox.web is not None
