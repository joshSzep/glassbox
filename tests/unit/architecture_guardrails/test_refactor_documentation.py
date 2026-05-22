"""Refactor documentation and guardrail message coverage."""

from pathlib import Path

from tests.unit.architecture_guardrails.helpers import _frontend_import_violations
from tests.unit.architecture_guardrails.helpers import _line_count_violations
from tests.unit.architecture_guardrails.helpers import _python_import_violations
from tests.unit.architecture_guardrails.rules import REPO_ROOT


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


def test_v10_guardrail_messages_point_to_next_owner(tmp_path: Path) -> None:
    route_file = tmp_path / "sessions.py"
    route_file.write_text(
        "from glassbox.store.sqlite import open_database\n",
        encoding="utf-8",
    )

    import_violations = _python_import_violations(
        route_file,
        ("glassbox.store",),
        (
            "v10 session route helpers should use service/query seams instead "
            "of raw store imports"
        ),
    )

    assert import_violations == [
        (
            f"{route_file}: v10 session route helpers should use service/query "
            "seams instead of raw store imports: glassbox.store.sqlite"
        )
    ]

    growth_violations = _line_count_violations(
        (
            (
                route_file,
                0,
                (
                    "v10 session routes should move new query/action/"
                    "serialization behavior into web route helper modules"
                ),
            ),
        )
    )

    assert growth_violations == [
        (
            f"{route_file}: v10 session routes should move new query/action/"
            "serialization behavior into web route helper modules: 1 lines "
            "exceeds 0"
        )
    ]


def test_v11_guardrail_messages_point_to_next_owner(tmp_path: Path) -> None:
    knowledge_file = tmp_path / "knowledge_posture.py"
    knowledge_file.write_text(
        "from glassbox.cli.status_formatters import format_status\n",
        encoding="utf-8",
    )

    import_violations = _python_import_violations(
        knowledge_file,
        ("glassbox.cli",),
        (
            "v11 knowledge posture helpers must derive evidence without CLI or "
            "web presentation imports"
        ),
    )

    assert import_violations == [
        (
            f"{knowledge_file}: v11 knowledge posture helpers must derive "
            "evidence without CLI or web presentation imports: "
            "glassbox.cli.status_formatters"
        )
    ]

    growth_violations = _line_count_violations(
        (
            (
                knowledge_file,
                0,
                (
                    "v11 knowledge posture should move new source collection, "
                    "ranking, provenance, and command guidance into focused helpers"
                ),
            ),
        )
    )

    assert growth_violations == [
        (
            f"{knowledge_file}: v11 knowledge posture should move new source "
            "collection, ranking, provenance, and command guidance into focused "
            "helpers: 1 lines exceeds 0"
        )
    ]


def test_v13_guardrail_messages_point_to_next_owner(tmp_path: Path) -> None:
    changesets_file = tmp_path / "changesets.py"
    changesets_file.write_text(
        "from glassbox.web.changeset_api import ChangesetDetailResponse\n",
        encoding="utf-8",
    )

    import_violations = _python_import_violations(
        changesets_file,
        ("glassbox.web",),
        (
            "v13 changeset runtime helpers must keep review-loop derivation "
            "independent from CLI and web presentation layers"
        ),
    )

    assert import_violations == [
        (
            f"{changesets_file}: v13 changeset runtime helpers must keep "
            "review-loop derivation independent from CLI and web presentation "
            "layers: glassbox.web.changeset_api"
        )
    ]

    growth_violations = _line_count_violations(
        (
            (
                changesets_file,
                0,
                (
                    "v13 changesets runtime facade should move new derivation, "
                    "feedback, evidence, verification, brief, and readiness "
                    "behavior into focused review-loop helpers"
                ),
            ),
        )
    )

    assert growth_violations == [
        (
            f"{changesets_file}: v13 changesets runtime facade should move new "
            "derivation, feedback, evidence, verification, brief, and readiness "
            "behavior into focused review-loop helpers: 1 lines exceeds 0"
        )
    ]


def test_v14_guardrail_messages_point_to_next_owner(tmp_path: Path) -> None:
    response_file = tmp_path / "review_responses.py"
    response_file.write_text(
        "from glassbox.web.changeset_api import ReviewFeedbackResponse\n",
        encoding="utf-8",
    )

    import_violations = _python_import_violations(
        response_file,
        ("glassbox.web",),
        (
            "post-v14 review response helpers must keep status and fixup "
            "derivation independent from CLI and web presentation layers"
        ),
    )

    assert import_violations == [
        (
            f"{response_file}: post-v14 review response helpers must keep "
            "status and fixup derivation independent from CLI and web "
            "presentation layers: glassbox.web.changeset_api"
        )
    ]

    growth_violations = _line_count_violations(
        (
            (
                response_file,
                0,
                (
                    "post-v14 review responses should move new model, status, "
                    "fixup, path-scope, and summary behavior into focused "
                    "response helpers"
                ),
            ),
        )
    )

    assert growth_violations == [
        (
            f"{response_file}: post-v14 review responses should move new "
            "model, status, fixup, path-scope, and summary behavior into "
            "focused response helpers: 1 lines exceeds 0"
        )
    ]


def test_v11_confidence_boundary_strategy_is_documented() -> None:
    boundary_doc = (REPO_ROOT / "docs" / "refactor-boundaries.md").read_text(
        encoding="utf-8"
    )

    for required_text in (
        "#### V11 Confidence Runtime Sub-Boundaries",
        "Eval recommendation output should keep a stable public facade",
        "Knowledge posture should derive only from canonical events",
        "Branch decision support should keep branch search non-mutating",
        "Session export should keep package JSON and import compatibility stable",
        "#### V11 Projection Sub-Boundaries",
        "#### V11 CLI Operator-Surface Sub-Boundaries",
        "#### V11 Frontend Confidence-Surface Sub-Boundaries",
        "v11 guardrails should extend the same narrow approach",
    ):
        assert required_text in boundary_doc


def test_v13_review_loop_boundary_strategy_is_documented() -> None:
    boundary_doc = (REPO_ROOT / "docs" / "refactor-boundaries.md").read_text(
        encoding="utf-8"
    )
    architecture_doc = (REPO_ROOT / "docs" / "architecture.md").read_text(
        encoding="utf-8"
    )

    for required_text in (
        "#### V13 Review-Loop Runtime Sub-Boundaries",
        "`runtime/changesets.py` is the stable changeset runtime facade",
        "Review feedback actions belong under `review_feedback_actions.py`",
        "#### V13 Store Review-Loop Sub-Boundaries",
        "#### V13 CLI And Terminal Review-Loop Sub-Boundaries",
        "#### V13 Changeset Web Sub-Boundaries",
        "#### V13 Frontend Changeset Sub-Boundaries",
        "### V13 Accepted Compatibility Shims",
        "v13 guardrails initially freeze the known review-loop pressure points",
        "`scripts/validate_v13_release_gate.py`: operator entrypoint",
    ):
        assert required_text in boundary_doc

    for required_text in (
        "## Current Post-v13 Review-Loop Refactor Shape",
        "`runtime/changesets.py` is the stable changeset runtime facade",
        "### Runtime Review-Loop Boundaries",
        "Publication-boundary behavior is part of this runtime contract",
        "[v13-review-loop-contract.md](./v13-review-loop-contract.md)",
        "[publication-boundary.md](./publication-boundary.md)",
    ):
        assert required_text in architecture_doc


def test_post_v14_review_loop_maturity_boundary_strategy_is_documented() -> None:
    boundary_doc = (REPO_ROOT / "docs" / "refactor-boundaries.md").read_text(
        encoding="utf-8"
    )
    architecture_doc = (REPO_ROOT / "docs" / "architecture.md").read_text(
        encoding="utf-8"
    )

    for required_text in (
        "#### Post-V14 Review-Loop Maturity Runtime Sub-Boundaries",
        "`changeset_review_brief_limitations.py`",
        "`review_response_models.py`",
        "`review_readiness_signals.py`",
        "#### Post-V14 Terminal Review-Loop Sub-Boundaries",
        "#### Post-V14 Changeset Web Sub-Boundaries",
        "#### Post-V14 Frontend Changeset Sub-Boundaries",
        "### Post-V14 Accepted Compatibility Shims",
        "post-v14 guardrails start with pre-extraction pressure-point caps",
        "`scripts/v14_release_gate_helpers.py`: v14 gate helper surface",
    ):
        assert required_text in boundary_doc

    for required_text in (
        "## Current Post-v14 Review-Loop Maturity Refactor Shape",
        "`runtime/changeset_review_brief_sections.py` remains the lifecycle brief",
        "`runtime/review_responses.py` remains the review response facade",
        "`cli/interactive_client.py` remains the plain interactive client entrypoint",
        "[v14-review-loop-maturity-contract.md](./v14-review-loop-maturity-contract.md)",
        "[publication-boundary.md](./publication-boundary.md)",
    ):
        assert required_text in architecture_doc


def test_post_v15_repository_intelligence_boundary_strategy_is_documented() -> None:
    boundary_doc = (REPO_ROOT / "docs" / "refactor-boundaries.md").read_text(
        encoding="utf-8"
    )
    architecture_doc = (REPO_ROOT / "docs" / "architecture.md").read_text(
        encoding="utf-8"
    )

    for required_text in (
        "The post-v15 repository-intelligence boundary map starts",
        "#### Post-V15 Repository-Intelligence Runtime Sub-Boundaries",
        "`repository_intelligence_layout_models.py`",
        "`repository_intelligence_refresh.py`",
        "`runtime_context_memory_use.py`",
        "`eval_recommendation_repository_matching.py`",
        "#### Post-V15 Repository CLI Sub-Boundaries",
        "`repository_command_status.py`",
        "#### Post-V15 Repository Web Sub-Boundaries",
        "`repository_intelligence_api_models.py`",
        "#### Post-V15 Frontend Repository Sub-Boundaries",
        "`repository-overview.tsx`",
        "`knowledge-store-repository.ts`",
        "#### Post-V15 Guardrail And Core-Domain Strategy",
        "tests/unit/architecture_guardrails/",
        "### Post-V15 Accepted Compatibility Shims",
    ):
        assert required_text in boundary_doc

    for required_text in (
        "## Current Post-v15 Repository-Intelligence Refactor Shape",
        "`cli/repository_commands.py` remains the repository command dispatcher",
        "`runtime/repository_intelligence_layout.py` remains the layout discovery",
        "`runtime/repository_intelligence_refresh.py` is the shared refresh",
        "`runtime/runtime_context_derivation.py` remains the runtime context",
        "`web/repository_intelligence_api.py` and",
        "`frontend/stores/knowledge-store.ts` remains the dashboard knowledge-store",
        "`tests/unit/test_architecture_guardrails.py` remains the legacy guardrail",
        "`tests/unit/architecture_guardrails/` owns the",
        "[v15-repository-intelligence-contract.md](./v15-repository-intelligence-contract.md)",
        "[repository-intelligence-index.md](./repository-intelligence-index.md)",
        "[runtime-context.md](./runtime-context.md)",
        "[workspace-memory.md](./workspace-memory.md)",
    ):
        assert required_text in architecture_doc


def test_post_v15_repository_intelligence_core_domain_strategy_is_documented() -> None:
    boundary_doc = (REPO_ROOT / "docs" / "refactor-boundaries.md").read_text(
        encoding="utf-8"
    )
    architecture_doc = (REPO_ROOT / "docs" / "architecture.md").read_text(
        encoding="utf-8"
    )

    for required_text in (
        "#### Post-V15 Repository-Intelligence Core Domain Strategy",
        "The current repository-intelligence model family stays in",
        "`RepositoryIntelligenceSourceManifest`",
        "`RepositoryIntelligenceCommandRecipe`",
        "`RepositoryIntelligenceMemoryReference`",
        "`RepositoryIndexSnapshot`",
        "`core/models_repository_intelligence.py`",
        "`core/events_repository_intelligence.py`",
        "Event payload registration must remain explicit and deterministic",
        "compatibility re-exports during any future extraction",
    ):
        assert required_text in boundary_doc

    for required_text in (
        "repository index and repository intelligence",
        "Repository-intelligence snapshot models currently remain in",
        "`core/models_repository_intelligence.py`",
        "`core/events_repository_intelligence.py`",
        "`EventPayloadType` assembly deterministic in `core/events.py`",
    ):
        assert required_text in architecture_doc


def test_post_v16_operator_flow_boundary_strategy_is_documented() -> None:
    boundary_doc = (REPO_ROOT / "docs" / "refactor-boundaries.md").read_text(
        encoding="utf-8"
    )
    architecture_doc = (REPO_ROOT / "docs" / "architecture.md").read_text(
        encoding="utf-8"
    )

    for required_text in (
        "The post-v16 operator-flow boundary map starts",
        "#### Post-V16 Operator-Flow Runtime Sub-Boundaries",
        "`evidence_graph_models.py`",
        "`verification_plan_identity.py`",
        "`operator_queue_session_items.py`",
        "#### Post-V16 Operator-Flow Web Sub-Boundaries",
        "`changeset_api_builders_verification.py`",
        "#### Post-V16 Dashboard Cockpit Sub-Boundaries",
        "`operator-queue-row.tsx`",
        "`evidence-graph/summary.tsx`",
        "`changeset-store-verification-actions.ts`",
        "#### Post-V16 Release-Gate And Guardrail Strategy",
        "`v16_release_gate_stages.py`",
        "### Post-V16 Accepted Compatibility Shims",
    ):
        assert required_text in boundary_doc

    for required_text in (
        "## Current Post-v16 Operator-Flow Refactor Shape",
        "`runtime/evidence_graph.py` remains the evidence graph facade",
        "`runtime/verification_plan_builder.py` remains the verification plan",
        "`runtime/operator_queue.py` remains the queue aggregator",
        "### Runtime Operator-Flow Boundaries",
        "### Core Operator-Flow Domain Strategy",
        "[v16-operator-flow-compression-contract.md](./v16-operator-flow-compression-contract.md)",
        "[operator-queue.md](./operator-queue.md)",
        "[evidence-graph.md](./evidence-graph.md)",
        "[verification-orchestrator.md](./verification-orchestrator.md)",
        "[maintenance-cues.md](./maintenance-cues.md)",
    ):
        assert required_text in architecture_doc


def test_post_v17_local_handoff_boundary_strategy_is_documented() -> None:
    boundary_doc = (REPO_ROOT / "docs" / "refactor-boundaries.md").read_text(
        encoding="utf-8"
    )
    architecture_doc = (REPO_ROOT / "docs" / "architecture.md").read_text(
        encoding="utf-8"
    )

    for required_text in (
        "The post-v17 local-handoff boundary map starts",
        "#### Post-V17 Local-Handoff Runtime Sub-Boundaries",
        "`handoff_package_models.py`",
        "`handoff_redaction_preview_shared.py`",
        "`handoff_import_triage_disposition.py`",
        "`handoff_decision_actions.py`",
        "`handoff_guidance_paths.py`",
        "#### Post-V17 Readiness And Export-Profile Sub-Boundaries",
        "`handoff_readiness_reasons.py`",
        "`handoff_local_only_inventory.py`",
        "#### Post-V17 Web, CLI, TUI, And Frontend Handoff Sub-Boundaries",
        "`handoff_route_queries.py`",
        "`handoff_api_builders.py`",
        "`frontend/stores/handoff-store.ts`",
        "#### Post-V17 Repository, Release-Gate, And Guardrail Strategy",
        "### Post-V17 Accepted Compatibility Shims",
    ):
        assert required_text in boundary_doc

    for required_text in (
        "## Current Post-v17 Local-Handoff Refactor Shape",
        "`runtime/handoff_package.py` remains the handoff package entrypoint",
        "`runtime/handoff_redaction_preview.py` remains the redaction preview",
        "`web/routes/handoffs.py`, `web/handoff_api.py`, `cli/handoff_commands.py`",
        "### Runtime Local-Handoff Boundaries",
        "[v17-local-handoff-contract.md](./v17-local-handoff-contract.md)",
        "[local-handoff.md](./local-handoff.md)",
    ):
        assert required_text in architecture_doc


def test_v10_core_domain_strategy_is_documented() -> None:
    boundary_doc = (REPO_ROOT / "docs" / "refactor-boundaries.md").read_text(
        encoding="utf-8"
    )
    architecture_doc = (REPO_ROOT / "docs" / "architecture.md").read_text(
        encoding="utf-8"
    )

    for required_text in (
        "#### V10 Core Domain Strategy",
        "`glassbox.core.events` and `glassbox.core.models` should remain stable",
        "sessions, turns, tools, tasks",
        "branch search, background jobs, workspace memory",
        "repository index",
        "provider recovery",
        "verification",
        "compaction",
        "single registration point",
        "dynamic discovery",
        "import-time filesystem scans",
        "Do not split model-heavy code for line count alone",
    ):
        assert required_text in boundary_doc

    for required_text in (
        "### Core Domain Module Strategy",
        "`src/glassbox/core/events.py` and `src/glassbox/core/models.py`",
        "`EventPayloadType` discriminated union",
        "Event registration",
        "explicit and deterministic",
        "`core/models.py` should follow the same compatibility rule",
    ):
        assert required_text in architecture_doc
