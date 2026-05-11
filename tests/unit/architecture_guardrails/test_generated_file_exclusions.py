"""Generated and legacy dashboard source ownership guardrails."""

from tests.unit.architecture_guardrails.rules import REPO_ROOT
from tests.unit.architecture_guardrails.rules import SRC_ROOT


def test_spa_source_replaces_legacy_static_dashboard() -> None:
    legacy_static_dir = SRC_ROOT / "web" / "static"
    assert not any(legacy_static_dir.rglob("*"))
    assert (REPO_ROOT / "frontend" / "app" / "page.tsx").is_file()
    assert (REPO_ROOT / "frontend" / "components" / "console").is_dir()
