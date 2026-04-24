"""Smoke tests for the initial project scaffold."""

import importlib

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


def test_runtime_package_surface_is_curated() -> None:
    assert glassbox.runtime.__all__ == [
        "default_database_path",
        "EventBus",
        "EventBusStats",
        "EventBusSubscription",
        "open_runtime_context",
        "RuntimeContext",
        "RuntimeInfrastructure",
        "RuntimeRepositories",
        "RuntimeServices",
    ]
    assert glassbox.runtime.EventBus is not None
    assert glassbox.runtime.RuntimeContext is not None
    assert glassbox.runtime.open_runtime_context is not None
    assert not hasattr(glassbox.runtime, "TurnEngine")
    assert not hasattr(glassbox.runtime, "TurnContextBuilder")
    assert not hasattr(glassbox.runtime, "ReplayRunner")
    assert not hasattr(glassbox.runtime, "EvalRunner")
    assert not hasattr(glassbox.runtime, "PolicyContext")
    assert not hasattr(glassbox.runtime, "ToolSchema")
    assert importlib.import_module("glassbox.runtime.context_builder") is not None
    assert importlib.import_module("glassbox.runtime.replay") is not None
    assert importlib.import_module("glassbox.runtime.turn_engine") is not None


def test_store_package_surface_is_curated() -> None:
    assert glassbox.store.__all__ == [
        "FilesystemArtifactRepository",
        "SCHEMA_VERSION",
        "SQLiteSessionRepository",
        "StoredArtifact",
        "initialize_database",
        "open_database",
    ]
    assert glassbox.store.SQLiteSessionRepository is not None
    assert glassbox.store.initialize_database is not None
    assert glassbox.store.open_database is not None
    assert not hasattr(glassbox.store, "append_event")
    assert not hasattr(glassbox.store, "resolve_fork_point")
    assert not hasattr(glassbox.store, "record_text_artifact")
    assert importlib.import_module("glassbox.store.artifacts") is not None
    assert importlib.import_module("glassbox.store.repositories") is not None
    assert importlib.import_module("glassbox.store.sqlite") is not None
