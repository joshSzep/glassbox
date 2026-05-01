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
        SRC_ROOT / "store" / "sqlite_queries.py",
        ("glassbox.store.sqlite_query_",),
        50,
        "sqlite_queries should stay a thin facade over domain query modules",
    ),
    (
        SRC_ROOT / "store" / "repositories.py",
        (
            "sqlite3",
            "glassbox.store.repository_",
        ),
        60,
        "store.repositories should stay a thin facade over domain adapters",
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
        SRC_ROOT / "runtime" / "eval_recommendation_output.py",
        (
            "glassbox.runtime.eval_recommendation_common",
            "glassbox.runtime.eval_recommendation_long_run_surfaces",
            "glassbox.runtime.eval_recommendation_plans",
            "glassbox.runtime.eval_recommendation_reason_groups",
            "glassbox.runtime.eval_recommendation_recipes",
            "glassbox.runtime.eval_recommendation_release_surfaces",
            "glassbox.runtime.eval_recommendation_rows",
        ),
        80,
        (
            "eval_recommendation_output should stay a thin compatibility "
            "facade over v11 recommendation output helpers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "eval_recommendation_matching.py",
        (
            "glassbox.runtime.eval_recommendation_case_expansion",
            "glassbox.runtime.eval_recommendation_matching_common",
            "glassbox.runtime.eval_recommendation_path_matching",
            "glassbox.runtime.eval_recommendation_profile_expansion",
        ),
        80,
        (
            "eval_recommendation_matching should stay a thin compatibility "
            "facade over v11 recommendation matching helpers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "background_jobs.py",
        (
            "asyncio",
            "contextlib",
            "dataclasses",
            "datetime",
            "uuid",
            "glassbox.core.types",
            "glassbox.runtime.background_job_handlers",
            "glassbox.runtime.background_job_lifecycle",
            "glassbox.runtime.background_job_records",
            "glassbox.runtime.background_task_continuation",
            "glassbox.runtime.context",
        ),
        220,
        (
            "background_jobs should stay a bounded worker facade over "
            "lifecycle, handler, continuation, and record modules"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "workspace_memory_capture.py",
        (
            "collections.abc",
            "datetime",
            "typing",
            "glassbox.core.events",
            "glassbox.core.ids",
            "glassbox.core.models",
            "glassbox.core.types",
            "glassbox.runtime.workspace_memory_candidates",
            "glassbox.runtime.workspace_memory_commits",
            "glassbox.runtime.workspace_memory_extraction",
            "glassbox.runtime.workspace_memory_redaction",
        ),
        300,
        (
            "workspace_memory_capture should keep capture-service orchestration "
            "separate from candidates, extraction, redaction, and commits"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "observability.py",
        (
            "pathlib",
            "glassbox.runtime.daemon",
            "glassbox.runtime.observability_",
            "glassbox.runtime.provider_canary",
            "glassbox.runtime.transport",
            "glassbox.services",
        ),
        140,
        (
            "observability should stay a read-only aggregation facade over "
            "domain collectors"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "repository_index.py",
        (
            "datetime",
            "pathlib",
            "glassbox.core.models",
            "glassbox.core.types",
            "glassbox.runtime.repository_index_",
        ),
        90,
        (
            "repository_index should stay a deterministic local index facade "
            "over discovery, extraction, persistence, and search modules"
        ),
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
    (
        SRC_ROOT / "cli" / "tui" / "conversation.py",
        (
            "glassbox.cli.tui.conversation_hydration",
            "glassbox.cli.tui.conversation_models",
            "glassbox.cli.tui.conversation_reducer",
            "glassbox.cli.tui.conversation_selectors",
        ),
        80,
        (
            "TUI conversation facade should delegate state, hydration, "
            "reducers, and selectors"
        ),
    ),
    (
        SRC_ROOT / "cli" / "tui" / "widgets.py",
        (
            "glassbox.cli.tui.widget_action",
            "glassbox.cli.tui.widget_composer",
            "glassbox.cli.tui.widget_details",
            "glassbox.cli.tui.widget_header",
            "glassbox.cli.tui.widget_palette",
            "glassbox.cli.tui.widget_transcript",
        ),
        80,
        "TUI widgets facade should delegate to pane-family widget modules",
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
    (
        FRONTEND_ROOT / "components" / "console" / "task-autonomy-console.tsx",
        180,
        (
            "task-autonomy-console.tsx should stay a reviewable component "
            "entrypoint while task sections own detailed presentation"
        ),
    ),
    (
        FRONTEND_ROOT / "components" / "console" / "knowledge-autonomy-console.tsx",
        180,
        (
            "knowledge-autonomy-console.tsx should stay a reviewable component "
            "entrypoint while knowledge sections own detailed presentation"
        ),
    ),
    (
        FRONTEND_ROOT / "components" / "console" / "branch-search-console.tsx",
        140,
        (
            "branch-search-console.tsx should stay a reviewable component "
            "entrypoint while branch-search sections own detailed presentation"
        ),
    ),
    (
        FRONTEND_ROOT
        / "components"
        / "console"
        / "session-inspector"
        / "panes"
        / "diagnostics-panes.tsx",
        80,
        (
            "diagnostics-panes.tsx should stay a stable pane export facade "
            "while evidence-type panes own diagnostic rendering"
        ),
    ),
)

V10_PYTHON_PRESSURE_POINT_RULES: tuple[tuple[Path, int, str], ...] = (
    (
        SRC_ROOT / "web" / "routes" / "sessions.py",
        850,
        (
            "v10 session routes should move new query/action/serialization "
            "behavior into web route helper modules"
        ),
    ),
    (
        SRC_ROOT / "web" / "routes" / "tasks.py",
        780,
        (
            "v10 task routes should move new query/action/serialization "
            "behavior into web route helper modules"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "task_queries.py",
        820,
        (
            "v10 task_queries should move models, verification, and "
            "repair-history derivation into focused runtime helpers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "provider_canary.py",
        80,
        (
            "v10 provider_canary should stay a thin compatibility facade over "
            "provider-canary helper modules"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "provider_canary_models.py",
        140,
        "v10 provider canary retained models should stay owned by models.py",
    ),
    (
        SRC_ROOT / "runtime" / "provider_canary_scenarios.py",
        190,
        ("v10 provider canary scenario definitions should stay owned by scenarios.py"),
    ),
    (
        SRC_ROOT / "runtime" / "provider_canary_execution.py",
        240,
        ("v10 provider canary live execution should stay owned by execution.py"),
    ),
    (
        SRC_ROOT / "runtime" / "provider_canary_evidence.py",
        260,
        (
            "v10 provider canary evidence loading and freshness should stay "
            "owned by evidence.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "provider_canary_reporting.py",
        140,
        (
            "v10 provider canary summary persistence and outcome counting "
            "should stay owned by reporting.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "provider_recommendations.py",
        220,
        (
            "v10 provider_recommendations should stay a thin compatibility "
            "facade over provider recommendation scoring helpers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "provider_recommendation_models.py",
        190,
        "v10 provider recommendation models should stay owned by models.py",
    ),
    (
        SRC_ROOT / "runtime" / "provider_recommendation_capability.py",
        240,
        (
            "v10 provider recommendation capability fit should stay owned by "
            "capability.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "provider_recommendation_risk.py",
        230,
        ("v10 provider recommendation risk posture should stay owned by risk.py"),
    ),
    (
        SRC_ROOT / "runtime" / "provider_recommendation_credentials.py",
        80,
        (
            "v10 provider recommendation credential readiness should stay "
            "owned by credentials.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "provider_recommendation_failures.py",
        120,
        (
            "v10 provider recommendation failure and budget posture should "
            "stay owned by failures.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "provider_recommendation_actions.py",
        120,
        (
            "v10 provider recommendation action selection should stay owned "
            "by actions.py"
        ),
    ),
    (
        SRC_ROOT / "tools" / "policy.py",
        140,
        (
            "v10 tools.policy should stay a thin compatibility facade over "
            "tool-policy helper modules"
        ),
    ),
    (
        SRC_ROOT / "tools" / "policy_paths.py",
        190,
        "v10 tool-policy path scope should stay owned by policy_paths.py",
    ),
    (
        SRC_ROOT / "tools" / "policy_models.py",
        90,
        "v10 tool-policy context models should stay owned by policy_models.py",
    ),
    (
        SRC_ROOT / "tools" / "policy_rules.py",
        150,
        "v10 tool-policy rule matching should stay owned by policy_rules.py",
    ),
    (
        SRC_ROOT / "tools" / "policy_autonomy.py",
        240,
        (
            "v10 tool-policy autonomy budget behavior should stay owned by "
            "policy_autonomy.py"
        ),
    ),
    (
        SRC_ROOT / "tools" / "policy_messages.py",
        280,
        ("v10 tool-policy approval messages should stay owned by policy_messages.py"),
    ),
    (
        SRC_ROOT / "tools" / "policy_command_risk.py",
        80,
        (
            "v10 tool-policy command risk behavior should stay owned by "
            "policy_command_risk.py"
        ),
    ),
    (
        SRC_ROOT / "store" / "sqlite_schema.py",
        320,
        (
            "v10 sqlite_schema should stay a migration runner and explicit "
            "registry over projection-domain schema helper modules"
        ),
    ),
    (
        SRC_ROOT / "store" / "sqlite_schema_background_jobs.py",
        120,
        (
            "v10 background-job schema should stay owned by "
            "sqlite_schema_background_jobs.py"
        ),
    ),
    (
        SRC_ROOT / "store" / "sqlite_schema_branch_search.py",
        90,
        (
            "v10 branch-search schema should stay owned by "
            "sqlite_schema_branch_search.py"
        ),
    ),
    (
        SRC_ROOT / "store" / "sqlite_schema_checkpoints.py",
        140,
        "v10 checkpoint schema should stay owned by sqlite_schema_checkpoints.py",
    ),
    (
        SRC_ROOT / "store" / "sqlite_schema_compactions.py",
        100,
        "v10 compaction schema should stay owned by sqlite_schema_compactions.py",
    ),
    (
        SRC_ROOT / "store" / "sqlite_schema_helpers.py",
        40,
        "v10 schema helpers should stay small and shared only by migrations",
    ),
    (
        SRC_ROOT / "store" / "sqlite_schema_long_run.py",
        120,
        "v10 long-run schema should stay owned by sqlite_schema_long_run.py",
    ),
    (
        SRC_ROOT / "store" / "sqlite_schema_provider_recovery.py",
        80,
        (
            "v10 provider-recovery schema should stay owned by "
            "sqlite_schema_provider_recovery.py"
        ),
    ),
    (
        SRC_ROOT / "store" / "sqlite_schema_sessions.py",
        80,
        "v10 session lineage schema should stay owned by sqlite_schema_sessions.py",
    ),
    (
        SRC_ROOT / "store" / "sqlite_schema_tasks.py",
        220,
        (
            "v10 task, budget, and verification-ledger schema should stay "
            "owned by sqlite_schema_tasks.py"
        ),
    ),
    (
        SRC_ROOT / "store" / "sqlite_schema_tools.py",
        130,
        "v10 tool schema should stay owned by sqlite_schema_tools.py",
    ),
    (
        SRC_ROOT / "store" / "sqlite_schema_workspace_memory.py",
        90,
        (
            "v10 workspace-memory schema should stay owned by "
            "sqlite_schema_workspace_memory.py"
        ),
    ),
)

V10_FRONTEND_PRESSURE_POINT_RULES: tuple[tuple[Path, int, str], ...] = (
    (
        FRONTEND_ROOT / "components" / "console" / "task-autonomy-sections.tsx",
        80,
        (
            "v10 task-autonomy-sections should stay a thin compatibility "
            "surface over queue, inspector, actions, evidence, and formatting"
        ),
    ),
    (
        FRONTEND_ROOT / "components" / "console" / "task-autonomy" / "queue.tsx",
        240,
        "v10 task-autonomy queue rendering should stay owned by queue.tsx",
    ),
    (
        FRONTEND_ROOT / "components" / "console" / "task-autonomy" / "inspector.tsx",
        320,
        "v10 task-autonomy inspector layout should stay owned by inspector.tsx",
    ),
    (
        FRONTEND_ROOT / "components" / "console" / "task-autonomy" / "actions.tsx",
        240,
        "v10 task-autonomy action controls should stay owned by actions.tsx",
    ),
    (
        FRONTEND_ROOT / "components" / "console" / "task-autonomy" / "evidence.tsx",
        430,
        "v10 task-autonomy evidence drilldown should stay owned by evidence.tsx",
    ),
    (
        FRONTEND_ROOT / "components" / "console" / "task-autonomy" / "format.ts",
        320,
        "v10 task-autonomy derivation and formatting should stay pure in format.ts",
    ),
    (
        FRONTEND_ROOT / "components" / "console" / "verification-cues.tsx",
        240,
        (
            "v10 verification-cues should stay a thin renderer over pure "
            "verification analysis helpers"
        ),
    ),
    (
        FRONTEND_ROOT / "components" / "console" / "verification-cues-analysis.ts",
        540,
        (
            "v10 verification cue derivation should stay owned by "
            "verification-cues-analysis.ts"
        ),
    ),
    (
        FRONTEND_ROOT
        / "components"
        / "console"
        / "session-inspector"
        / "panes"
        / "compare-pane.tsx",
        380,
        (
            "v10 compare-pane should stay a thin renderer over pure session "
            "compare helpers"
        ),
    ),
    (
        FRONTEND_ROOT
        / "components"
        / "console"
        / "session-inspector"
        / "panes"
        / "compare-analysis.ts",
        280,
        "v10 session comparison derivation should stay owned by compare-analysis.ts",
    ),
    (
        FRONTEND_ROOT / "components" / "console" / "workspace-console.tsx",
        180,
        (
            "v10 workspace-console should stay a thin composer over routing "
            "and action binding helpers"
        ),
    ),
    (
        FRONTEND_ROOT / "components" / "console" / "workspace-console" / "routing.ts",
        160,
        "v10 workspace-console routing should stay owned by routing.ts",
    ),
    (
        FRONTEND_ROOT / "components" / "console" / "workspace-console" / "actions.ts",
        360,
        "v10 workspace-console action binding should stay owned by actions.ts",
    ),
)

V10_PYTHON_IMPORT_RULES: tuple[tuple[Path, tuple[str, ...], str], ...] = (
    (
        SRC_ROOT / "runtime" / "task_queries.py",
        ("glassbox.cli", "glassbox.store", "glassbox.web"),
        (
            "v10 runtime task query helpers must stay transport-agnostic and "
            "use repository contracts instead of CLI, raw store, or web imports"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "provider_canary.py",
        ("glassbox.cli", "glassbox.store", "glassbox.web"),
        (
            "v10 provider canary facade must keep execution/evidence logic "
            "separate from CLI, raw store, and web layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "provider_canary_models.py",
        ("glassbox.cli", "glassbox.store", "glassbox.web"),
        (
            "v10 provider canary models must stay independent from CLI, raw "
            "store, and web layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "provider_canary_scenarios.py",
        ("glassbox.cli", "glassbox.store", "glassbox.web"),
        (
            "v10 provider canary scenarios must stay independent from CLI, raw "
            "store, and web layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "provider_canary_execution.py",
        ("glassbox.cli", "glassbox.store", "glassbox.web"),
        (
            "v10 provider canary execution must stay separate from CLI, raw "
            "store, and web layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "provider_canary_evidence.py",
        ("glassbox.cli", "glassbox.store", "glassbox.web"),
        (
            "v10 provider canary evidence loading must stay separate from "
            "CLI, raw store, and web layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "provider_canary_reporting.py",
        ("glassbox.cli", "glassbox.store", "glassbox.web"),
        (
            "v10 provider canary reporting must stay separate from CLI, raw "
            "store, and web layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "provider_recommendations.py",
        ("glassbox.cli", "glassbox.store", "glassbox.web"),
        (
            "v10 provider recommendation facade must consume diagnostics and "
            "canary evidence without importing CLI, raw store, or web layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "provider_recommendation_models.py",
        ("glassbox.cli", "glassbox.store", "glassbox.web"),
        (
            "v10 provider recommendation models must stay independent from "
            "CLI, raw store, and web layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "provider_recommendation_capability.py",
        ("glassbox.cli", "glassbox.store", "glassbox.web"),
        (
            "v10 provider recommendation capability scoring must consume "
            "diagnostics and canary evidence without importing CLI, raw store, "
            "or web layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "provider_recommendation_risk.py",
        ("glassbox.cli", "glassbox.store", "glassbox.web"),
        (
            "v10 provider recommendation risk scoring must consume diagnostics "
            "and canary evidence without importing CLI, raw store, or web layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "provider_recommendation_credentials.py",
        ("glassbox.cli", "glassbox.store", "glassbox.web"),
        (
            "v10 provider recommendation credential scoring must consume "
            "diagnostics without importing CLI, raw store, or web layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "provider_recommendation_failures.py",
        ("glassbox.cli", "glassbox.store", "glassbox.web"),
        (
            "v10 provider recommendation failure scoring must consume recovery "
            "records without importing CLI, raw store, or web layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "provider_recommendation_actions.py",
        ("glassbox.cli", "glassbox.store", "glassbox.web"),
        (
            "v10 provider recommendation action selection must consume "
            "diagnostics and canary evidence without importing CLI, raw store, "
            "or web layers"
        ),
    ),
    (
        SRC_ROOT / "tools" / "policy.py",
        ("glassbox.cli", "glassbox.runtime", "glassbox.store", "glassbox.web"),
        (
            "v10 tool-policy facade must keep policy decisions independent "
            "from CLI, runtime orchestration, raw store, and web layers"
        ),
    ),
    (
        SRC_ROOT / "tools" / "policy_paths.py",
        ("glassbox.cli", "glassbox.runtime", "glassbox.store", "glassbox.web"),
        (
            "v10 tool-policy path helpers must keep policy decisions "
            "independent from CLI, runtime orchestration, raw store, and web layers"
        ),
    ),
    (
        SRC_ROOT / "tools" / "policy_models.py",
        ("glassbox.cli", "glassbox.runtime", "glassbox.store", "glassbox.web"),
        (
            "v10 tool-policy context models must keep policy decisions "
            "independent from CLI, runtime orchestration, raw store, and web layers"
        ),
    ),
    (
        SRC_ROOT / "tools" / "policy_rules.py",
        ("glassbox.cli", "glassbox.runtime", "glassbox.store", "glassbox.web"),
        (
            "v10 tool-policy rule helpers must keep policy decisions "
            "independent from CLI, runtime orchestration, raw store, and web layers"
        ),
    ),
    (
        SRC_ROOT / "tools" / "policy_autonomy.py",
        ("glassbox.cli", "glassbox.runtime", "glassbox.store", "glassbox.web"),
        (
            "v10 tool-policy autonomy helpers must keep policy decisions "
            "independent from CLI, runtime orchestration, raw store, and web layers"
        ),
    ),
    (
        SRC_ROOT / "tools" / "policy_messages.py",
        ("glassbox.cli", "glassbox.runtime", "glassbox.store", "glassbox.web"),
        (
            "v10 tool-policy message helpers must keep policy decisions "
            "independent from CLI, runtime orchestration, raw store, and web layers"
        ),
    ),
    (
        SRC_ROOT / "tools" / "policy_command_risk.py",
        ("glassbox.cli", "glassbox.runtime", "glassbox.store", "glassbox.web"),
        (
            "v10 tool-policy command-risk helpers must keep policy decisions "
            "independent from CLI, runtime orchestration, raw store, and web layers"
        ),
    ),
    (
        SRC_ROOT / "store" / "sqlite_schema.py",
        ("glassbox.cli", "glassbox.runtime", "glassbox.web"),
        (
            "v10 sqlite schema helpers must stay below runtime and transport "
            "layers with explicit migration ownership"
        ),
    ),
    (
        SRC_ROOT / "store" / "sqlite_schema_background_jobs.py",
        ("glassbox.cli", "glassbox.runtime", "glassbox.web"),
        "v10 schema domain helpers must stay below runtime and transport layers",
    ),
    (
        SRC_ROOT / "store" / "sqlite_schema_branch_search.py",
        ("glassbox.cli", "glassbox.runtime", "glassbox.web"),
        "v10 schema domain helpers must stay below runtime and transport layers",
    ),
    (
        SRC_ROOT / "store" / "sqlite_schema_checkpoints.py",
        ("glassbox.cli", "glassbox.runtime", "glassbox.web"),
        "v10 schema domain helpers must stay below runtime and transport layers",
    ),
    (
        SRC_ROOT / "store" / "sqlite_schema_compactions.py",
        ("glassbox.cli", "glassbox.runtime", "glassbox.web"),
        "v10 schema domain helpers must stay below runtime and transport layers",
    ),
    (
        SRC_ROOT / "store" / "sqlite_schema_helpers.py",
        ("glassbox.cli", "glassbox.runtime", "glassbox.web"),
        "v10 schema domain helpers must stay below runtime and transport layers",
    ),
    (
        SRC_ROOT / "store" / "sqlite_schema_long_run.py",
        ("glassbox.cli", "glassbox.runtime", "glassbox.web"),
        "v10 schema domain helpers must stay below runtime and transport layers",
    ),
    (
        SRC_ROOT / "store" / "sqlite_schema_provider_recovery.py",
        ("glassbox.cli", "glassbox.runtime", "glassbox.web"),
        "v10 schema domain helpers must stay below runtime and transport layers",
    ),
    (
        SRC_ROOT / "store" / "sqlite_schema_sessions.py",
        ("glassbox.cli", "glassbox.runtime", "glassbox.web"),
        "v10 schema domain helpers must stay below runtime and transport layers",
    ),
    (
        SRC_ROOT / "store" / "sqlite_schema_tasks.py",
        ("glassbox.cli", "glassbox.runtime", "glassbox.web"),
        "v10 schema domain helpers must stay below runtime and transport layers",
    ),
    (
        SRC_ROOT / "store" / "sqlite_schema_tools.py",
        ("glassbox.cli", "glassbox.runtime", "glassbox.web"),
        "v10 schema domain helpers must stay below runtime and transport layers",
    ),
    (
        SRC_ROOT / "store" / "sqlite_schema_workspace_memory.py",
        ("glassbox.cli", "glassbox.runtime", "glassbox.web"),
        "v10 schema domain helpers must stay below runtime and transport layers",
    ),
)

V10_FRONTEND_IMPORT_RULES: tuple[tuple[Path, tuple[str, ...], str], ...] = (
    (
        FRONTEND_ROOT / "components" / "console" / "task-autonomy-sections.tsx",
        ("@/api/sse", "next/", "src/glassbox"),
        (
            "v10 task autonomy presentation should consume store state and "
            "generated types without opening SSE, Next server, or backend seams"
        ),
    ),
    (
        FRONTEND_ROOT / "components" / "console" / "task-autonomy" / "format.ts",
        ("@/api/sse", "@/components", "next/", "react", "src/glassbox"),
        (
            "v10 task autonomy formatting helpers should stay pure and avoid "
            "React components, SSE, Next server, or backend seams"
        ),
    ),
    (
        FRONTEND_ROOT / "components" / "console" / "task-autonomy",
        ("@/api/sse", "next/", "src/glassbox"),
        (
            "v10 task autonomy owned modules should consume store state and "
            "generated types without opening SSE, Next server, or backend seams"
        ),
    ),
    (
        FRONTEND_ROOT / "components" / "console" / "verification-cues.tsx",
        ("@/api/", "@/stores", "next/", "src/glassbox"),
        (
            "v10 verification cue rendering should stay presentation-focused "
            "over pure derivation results and avoid transport or store imports"
        ),
    ),
    (
        FRONTEND_ROOT / "components" / "console" / "verification-cues-analysis.ts",
        ("@/api/", "@/stores", "next/", "react", "src/glassbox"),
        (
            "v10 verification cue derivation should stay pure and avoid "
            "transport, store, React, Next server, or backend imports"
        ),
    ),
    (
        FRONTEND_ROOT
        / "components"
        / "console"
        / "session-inspector"
        / "panes"
        / "compare-pane.tsx",
        ("@/api/", "@/stores", "next/", "src/glassbox"),
        (
            "v10 compare rendering should stay presentation-focused over pure "
            "comparison results and avoid transport or store imports"
        ),
    ),
    (
        FRONTEND_ROOT
        / "components"
        / "console"
        / "session-inspector"
        / "panes"
        / "compare-analysis.ts",
        ("@/api/", "@/stores", "next/", "react", "src/glassbox"),
        (
            "v10 compare derivation should stay pure and avoid transport, "
            "store, React, Next server, or backend imports"
        ),
    ),
    (
        FRONTEND_ROOT / "components" / "console" / "workspace-console.tsx",
        ("@/api/sse", "next/", "src/glassbox"),
        (
            "v10 workspace-console routing should stay in the frontend store "
            "and route layers without opening SSE, Next server, or backend seams"
        ),
    ),
    (
        FRONTEND_ROOT / "components" / "console" / "workspace-console",
        ("@/api/sse", "next/", "src/glassbox"),
        (
            "v10 workspace-console helpers should stay in the frontend store "
            "and route layers without opening SSE, Next server, or backend seams"
        ),
    ),
)

V11_PYTHON_PRESSURE_POINT_RULES: tuple[tuple[Path, int, str], ...] = (
    (
        SRC_ROOT / "runtime" / "eval_recommendation_output.py",
        720,
        (
            "v11 eval recommendation output should move new surface, recipe, "
            "plan, and terminal formatting behavior into focused helpers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "eval_recommendation_common.py",
        80,
        "v11 eval recommendation shared helpers should stay small and generic",
    ),
    (
        SRC_ROOT / "runtime" / "eval_recommendation_rows.py",
        120,
        "v11 eval recommendation case/profile rows should stay owned by rows.py",
    ),
    (
        SRC_ROOT / "runtime" / "eval_recommendation_plans.py",
        120,
        (
            "v11 eval recommendation command-plan construction should stay "
            "owned by plans.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "eval_recommendation_reason_groups.py",
        140,
        (
            "v11 eval recommendation reason grouping should stay owned by "
            "reason_groups.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "eval_recommendation_recipes.py",
        140,
        (
            "v11 eval recommendation recipes and release-gate command grouping "
            "should stay owned by recipes.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "eval_recommendation_release_surfaces.py",
        160,
        (
            "v11 eval recommendation daily release surfaces should stay owned "
            "by release_surfaces.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "eval_recommendation_long_run_surfaces.py",
        220,
        (
            "v11 eval recommendation long-run surfaces should stay owned by "
            "long_run_surfaces.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "eval_recommendation_engine.py",
        300,
        (
            "v11 eval recommendation engine should move new matching, "
            "capability expansion, release, and fallback behavior into helpers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "eval_recommendation_matching.py",
        80,
        (
            "v11 eval recommendation matching should stay a thin compatibility "
            "facade over matching helper modules"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "eval_recommendation_matching_common.py",
        60,
        "v11 eval recommendation matching shared types should stay small",
    ),
    (
        SRC_ROOT / "runtime" / "eval_recommendation_path_matching.py",
        180,
        (
            "v11 eval recommendation path and impact-rule matching should stay "
            "owned by path_matching.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "eval_recommendation_case_expansion.py",
        150,
        (
            "v11 eval recommendation owner and capability expansion should "
            "stay owned by case_expansion.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "eval_recommendation_profile_expansion.py",
        130,
        (
            "v11 eval recommendation stage and fallback expansion should stay "
            "owned by profile_expansion.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "knowledge_posture.py",
        140,
        (
            "v11 knowledge_posture should stay a thin compatibility facade "
            "over posture source, cue, ranking, provenance, and guidance helpers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "knowledge_posture_sources.py",
        170,
        (
            "v11 knowledge posture source collection should stay owned by "
            "knowledge_posture_sources.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "knowledge_posture_cues.py",
        320,
        (
            "v11 knowledge posture should move new source collection, ranking, "
            "provenance, and command guidance into focused helpers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "knowledge_posture_provenance.py",
        160,
        (
            "v11 knowledge posture provenance references should stay owned by "
            "knowledge_posture_provenance.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "knowledge_posture_guidance.py",
        90,
        (
            "v11 knowledge posture command guidance should stay owned by "
            "knowledge_posture_guidance.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "knowledge_posture_ranking.py",
        40,
        (
            "v11 knowledge posture aggregate ranking should stay owned by "
            "knowledge_posture_ranking.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "knowledge_posture_models.py",
        100,
        (
            "v11 knowledge posture API models should stay owned by "
            "knowledge_posture_models.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "branch_decision_support.py",
        430,
        (
            "v11 branch decision support should move new evidence, "
            "verification, cost, risk, and follow-up behavior into helpers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "session_export.py",
        1150,
        (
            "v11 session export should move new package assembly, handoff, "
            "artifact manifest, and redaction behavior into helpers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "session_import.py",
        320,
        (
            "v11 session import should move new validation, inspection-only "
            "creation, transcript, runtime-note, and handoff behavior into helpers"
        ),
    ),
    (
        SRC_ROOT / "services" / "contracts.py",
        560,
        (
            "v11 service contracts should split only by stable domain contract "
            "families while preserving public imports"
        ),
    ),
    (
        SRC_ROOT / "cli" / "status_formatters.py",
        780,
        (
            "v11 status formatters should move new session, task, "
            "observability, policy, and knowledge formatting into owned helpers"
        ),
    ),
    (
        SRC_ROOT / "cli" / "command_guide.py",
        540,
        (
            "v11 command guide should move new metadata, workflow grouping, "
            "JSON serialization, and terminal rendering into owned helpers"
        ),
    ),
    (
        SRC_ROOT / "cli" / "interactive_commands.py",
        600,
        (
            "v11 interactive commands should move new launch, daemon, local "
            "action, and autonomy-option behavior into owned helpers"
        ),
    ),
    (
        SRC_ROOT / "cli" / "parser_sessions.py",
        570,
        (
            "v11 session parser wiring should move new option-resolution "
            "behavior into parser/helper modules"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "tool_attempt_recovery.py",
        810,
        (
            "v11 tool-attempt recovery should move new inspection, retry, "
            "abandon, artifact, and result-model behavior into helpers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "context_compaction_service.py",
        680,
        (
            "v11 compaction service should move new range planning, artifact "
            "assembly, freshness, refresh, and invalidation behavior into helpers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "turn_event_recorder.py",
        690,
        (
            "v11 turn event recorder should move new artifact, replay, "
            "task-plan, and heartbeat behavior into helpers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "turn_tool_executor.py",
        670,
        (
            "v11 turn tool executor should move new artifact, replay, "
            "task-plan, and heartbeat behavior into helpers"
        ),
    ),
    (
        SRC_ROOT / "store" / "sqlite_projection_tasks.py",
        630,
        (
            "v11 task projection handlers should move new event-family "
            "behavior into focused projection helpers"
        ),
    ),
    (
        SRC_ROOT / "store" / "sqlite_background_jobs.py",
        580,
        (
            "v11 background-job projection handlers should move new "
            "event-family behavior into focused projection helpers"
        ),
    ),
)

V11_FRONTEND_PRESSURE_POINT_RULES: tuple[tuple[Path, int, str], ...] = (
    (
        FRONTEND_ROOT / "components" / "console" / "knowledge-autonomy-sections.tsx",
        700,
        (
            "v11 knowledge sections should move new summary, detail, "
            "provenance, action, and formatting behavior into owned modules"
        ),
    ),
    (
        FRONTEND_ROOT / "components" / "console" / "branch-search-sections.tsx",
        560,
        (
            "v11 branch-search sections should move new candidate, decision, "
            "evidence, verification, action, and formatting behavior into owned modules"
        ),
    ),
    (
        FRONTEND_ROOT / "stores" / "session-store.ts",
        610,
        (
            "v11 session store should move new stream, pagination, draft, "
            "and action behavior into store-owned helpers"
        ),
    ),
)

V11_PYTHON_IMPORT_RULES: tuple[tuple[Path, tuple[str, ...], str], ...] = (
    (
        SRC_ROOT / "runtime" / "eval_recommendation_output.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 recommendation output helpers must keep derivation separate "
            "from CLI and web presentation layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "eval_recommendation_engine.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 recommendation engine helpers must keep matching and expansion "
            "transport-agnostic"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "knowledge_posture.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 knowledge posture helpers must derive evidence without CLI or "
            "web presentation imports"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "knowledge_posture_sources.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 knowledge posture source collectors must stay independent "
            "from CLI and web presentation imports"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "knowledge_posture_cues.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 knowledge posture cue helpers must stay independent from "
            "CLI and web presentation imports"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "knowledge_posture_provenance.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 knowledge posture provenance helpers must stay independent "
            "from CLI and web presentation imports"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "knowledge_posture_guidance.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 knowledge posture command guidance must stay independent "
            "from CLI and web presentation imports"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "knowledge_posture_ranking.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 knowledge posture ranking must stay independent from CLI "
            "and web presentation imports"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "branch_decision_support.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 branch decision helpers must derive evidence without CLI or "
            "web presentation imports"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "session_export.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 session export helpers must keep package and handoff "
            "assembly independent from CLI and web presentation layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "session_import.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 session import helpers must keep validation and handoff-note "
            "assembly independent from CLI and web presentation layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "tool_attempt_recovery.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 tool-attempt recovery helpers must keep recovery derivation "
            "independent from CLI and web presentation layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "context_compaction_service.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 compaction helpers must keep range planning, freshness, and "
            "artifact assembly independent from CLI and web presentation layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "turn_event_recorder.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 turn event recorder helpers must keep event and artifact "
            "recording independent from CLI and web presentation layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "turn_tool_executor.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 turn tool executor helpers must keep tool side effects "
            "independent from CLI and web presentation layers"
        ),
    ),
    (
        SRC_ROOT / "store" / "sqlite_projection_tasks.py",
        ("glassbox.cli", "glassbox.runtime", "glassbox.web"),
        ("v11 task projection handlers must stay below runtime and transport layers"),
    ),
    (
        SRC_ROOT / "store" / "sqlite_background_jobs.py",
        ("glassbox.cli", "glassbox.runtime", "glassbox.web"),
        (
            "v11 background-job projection handlers must stay below runtime "
            "and transport layers"
        ),
    ),
)

V11_FRONTEND_IMPORT_RULES: tuple[tuple[Path, tuple[str, ...], str], ...] = (
    (
        FRONTEND_ROOT / "components" / "console" / "knowledge-autonomy-sections.tsx",
        ("@/api/client", "@/api/sse", "next/", "src/glassbox"),
        (
            "v11 knowledge section rendering should consume typed props and "
            "avoid transport, store, Next server, or backend imports"
        ),
    ),
    (
        FRONTEND_ROOT / "components" / "console" / "branch-search-sections.tsx",
        ("@/api/client", "@/api/sse", "next/", "src/glassbox"),
        (
            "v11 branch-search section rendering should consume typed props "
            "and avoid transport, store, Next server, or backend imports"
        ),
    ),
    (
        FRONTEND_ROOT / "stores" / "session-store.ts",
        ("@/components", "next/", "react", "src/glassbox"),
        (
            "v11 session store helpers should own transport and actions "
            "without importing React components, Next server, or backend source"
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


def test_v10_python_pressure_points_do_not_grow_before_split() -> None:
    violations = _line_count_violations(V10_PYTHON_PRESSURE_POINT_RULES)

    assert violations == []


def test_v10_frontend_pressure_points_do_not_grow_before_split() -> None:
    violations = _line_count_violations(V10_FRONTEND_PRESSURE_POINT_RULES)

    assert violations == []


def test_v10_python_boundaries_avoid_transport_and_raw_store_imports() -> None:
    violations: list[str] = []

    for file_path, forbidden_prefixes, message in V10_PYTHON_IMPORT_RULES:
        violations.extend(
            _python_import_violations(file_path, forbidden_prefixes, message)
        )

    assert violations == []


def test_v10_frontend_boundaries_avoid_transport_and_backend_imports() -> None:
    violations: list[str] = []

    for file_path, forbidden_prefixes, message in V10_FRONTEND_IMPORT_RULES:
        violations.extend(
            _frontend_import_violations(file_path, forbidden_prefixes, message)
        )

    assert violations == []


def test_v11_python_pressure_points_do_not_grow_before_split() -> None:
    violations = _line_count_violations(V11_PYTHON_PRESSURE_POINT_RULES)

    assert violations == []


def test_v11_frontend_pressure_points_do_not_grow_before_split() -> None:
    violations = _line_count_violations(V11_FRONTEND_PRESSURE_POINT_RULES)

    assert violations == []


def test_v11_python_boundaries_avoid_presentation_imports() -> None:
    violations: list[str] = []

    for file_path, forbidden_prefixes, message in V11_PYTHON_IMPORT_RULES:
        violations.extend(
            _python_import_violations(file_path, forbidden_prefixes, message)
        )

    assert violations == []


def test_v11_frontend_boundaries_avoid_transport_and_backend_imports() -> None:
    violations: list[str] = []

    for file_path, forbidden_prefixes, message in V11_FRONTEND_IMPORT_RULES:
        violations.extend(
            _frontend_import_violations(file_path, forbidden_prefixes, message)
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

    file_paths = [directory] if directory.is_file() else sorted(directory.rglob("*"))
    for file_path in file_paths:
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


def _line_count_violations(rules: tuple[tuple[Path, int, str], ...]) -> list[str]:
    violations: list[str] = []

    for file_path, max_lines, message in rules:
        line_count = _line_count(file_path)
        if line_count > max_lines:
            violations.append(
                _format_violation(
                    file_path,
                    message,
                    f"{line_count} lines exceeds {max_lines}",
                )
            )

    return violations


def _format_violation(file_path: Path, message: str, detail: str) -> str:
    try:
        display_path = file_path.relative_to(REPO_ROOT)
    except ValueError:
        display_path = file_path
    return f"{display_path}: {message}: {detail}"


def _matches_any_prefix(module: str, prefixes: tuple[str, ...]) -> bool:
    return any(module == prefix or module.startswith(prefix) for prefix in prefixes)
