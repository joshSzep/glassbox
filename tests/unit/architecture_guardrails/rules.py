"""Rule tables for architecture guardrail tests."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
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
        80,
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
            "glassbox.runtime.eval_recommendation_repository_intelligence",
            "glassbox.runtime.eval_recommendation_release_surfaces",
            "glassbox.runtime.eval_recommendation_rows",
            "glassbox.runtime.eval_recommendation_test_targets",
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
        140,
        (
            "v11 branch_decision_support should stay a thin compatibility "
            "facade over decision evidence, verification, cost, risk, and "
            "follow-up helpers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "branch_decision_models.py",
        120,
        "v11 branch decision support API models should stay owned by models.py",
    ),
    (
        SRC_ROOT / "runtime" / "branch_decision_evidence.py",
        80,
        (
            "v11 branch decision retained evidence extraction should stay "
            "owned by branch_decision_evidence.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "branch_decision_files.py",
        40,
        (
            "v11 branch decision changed-file posture should stay owned by "
            "branch_decision_files.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "branch_decision_verification.py",
        140,
        (
            "v11 branch decision verification recommendations should stay "
            "owned by branch_decision_verification.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "branch_decision_cost.py",
        40,
        (
            "v11 branch decision cost estimates should stay owned by "
            "branch_decision_cost.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "branch_decision_risk.py",
        70,
        (
            "v11 branch decision risk and accepted-risk posture should stay "
            "owned by branch_decision_risk.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "branch_decision_followup.py",
        60,
        (
            "v11 branch decision follow-up guidance should stay owned by "
            "branch_decision_followup.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "session_export.py",
        80,
        (
            "v11 session_export should stay a thin compatibility facade over "
            "package assembly, handoff, manifest, and redaction helpers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "session_export_package.py",
        240,
        (
            "v11 session export package assembly should stay owned by "
            "session_export_package.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "session_export_handoff.py",
        430,
        (
            "v11 session export handoff summary behavior should stay owned by "
            "session_export_handoff.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "session_export_manifest.py",
        340,
        (
            "v11 session export artifact, policy, task, and event references "
            "should stay owned by session_export_manifest.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "session_export_redaction.py",
        190,
        (
            "v11 session export redaction behavior should stay owned by "
            "session_export_redaction.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "session_import.py",
        100,
        (
            "v11 session_import should stay a thin compatibility facade over "
            "validation, inspection-event, and handoff-note helpers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "session_import_validation.py",
        80,
        (
            "v11 session import package validation should stay owned by "
            "session_import_validation.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "session_import_events.py",
        180,
        (
            "v11 session import inspection-only event construction should stay "
            "owned by session_import_events.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "session_import_handoff.py",
        60,
        (
            "v11 session import handoff-note construction should stay owned "
            "by session_import_handoff.py"
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
        90,
        (
            "v11 status_formatters should stay a thin compatibility facade over "
            "session, task, observability, policy, and knowledge helpers"
        ),
    ),
    (
        SRC_ROOT / "cli" / "status_session.py",
        760,
        ("v11 session status formatting should stay owned by status_session.py"),
    ),
    (
        SRC_ROOT / "cli" / "status_task.py",
        180,
        ("v11 task status formatting should stay owned by status_task.py"),
    ),
    (
        SRC_ROOT / "cli" / "status_observability.py",
        190,
        (
            "v11 observability status formatting should stay owned by "
            "status_observability.py"
        ),
    ),
    (
        SRC_ROOT / "cli" / "status_knowledge.py",
        60,
        ("v11 knowledge status formatting should stay owned by status_knowledge.py"),
    ),
    (
        SRC_ROOT / "cli" / "command_guide.py",
        60,
        (
            "v11 command_guide should stay a thin compatibility facade over "
            "data, workflow grouping, JSON serialization, and terminal rendering"
        ),
    ),
    (
        SRC_ROOT / "cli" / "command_guide_data.py",
        480,
        ("v11 command guide metadata should stay owned by command_guide_data.py"),
    ),
    (
        SRC_ROOT / "cli" / "command_guide_workflows.py",
        90,
        (
            "v11 command guide workflow grouping should stay owned by "
            "command_guide_workflows.py"
        ),
    ),
    (
        SRC_ROOT / "cli" / "command_guide_json.py",
        60,
        (
            "v11 command guide JSON serialization should stay owned by "
            "command_guide_json.py"
        ),
    ),
    (
        SRC_ROOT / "cli" / "command_guide_render.py",
        60,
        (
            "v11 command guide terminal rendering should stay owned by "
            "command_guide_render.py"
        ),
    ),
    (
        SRC_ROOT / "cli" / "command_guide_models.py",
        50,
        ("v11 command guide models should stay owned by command_guide_models.py"),
    ),
    (
        SRC_ROOT / "cli" / "interactive_commands.py",
        460,
        (
            "v11 interactive_commands should keep command wrappers thin over "
            "launch, daemon, local action, and autonomy-option helpers"
        ),
    ),
    (
        SRC_ROOT / "cli" / "interactive_autonomy.py",
        100,
        (
            "v11 interactive autonomy option resolution should stay owned by "
            "interactive_autonomy.py"
        ),
    ),
    (
        SRC_ROOT / "cli" / "interactive_local_actions.py",
        160,
        (
            "v11 interactive local actions should stay owned by "
            "interactive_local_actions.py"
        ),
    ),
    (
        SRC_ROOT / "cli" / "interactive_daemon_actions.py",
        60,
        (
            "v11 interactive daemon-forwarded actions should stay owned by "
            "interactive_daemon_actions.py"
        ),
    ),
    (
        SRC_ROOT / "cli" / "parser_sessions.py",
        530,
        (
            "v11 session parser wiring should move new option-resolution "
            "behavior into parser/helper modules"
        ),
    ),
    (
        SRC_ROOT / "cli" / "parser_session_launch.py",
        50,
        (
            "v11 session launch parser options should stay owned by "
            "parser_session_launch.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "tool_attempt_recovery.py",
        80,
        (
            "v11 tool-attempt recovery should stay a thin facade over "
            "inspection, retry, abandon, artifact, and result-model helpers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "tool_attempt_recovery_models.py",
        90,
        (
            "v11 tool-attempt recovery result models should stay separated "
            "from recovery action orchestration"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "tool_attempt_recovery_common.py",
        120,
        (
            "v11 tool-attempt recovery common helpers should stay limited to "
            "shared attempt, source-call, and correlation lookups"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "tool_attempt_recovery_inspection.py",
        110,
        (
            "v11 tool-attempt inspection summaries should stay owned by "
            "tool_attempt_recovery_inspection.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "tool_attempt_recovery_artifacts.py",
        130,
        (
            "v11 tool-attempt output artifact lookup and recording should stay "
            "owned by tool_attempt_recovery_artifacts.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "tool_attempt_recovery_abandon.py",
        130,
        (
            "v11 tool-attempt abandon decisions should stay owned by "
            "tool_attempt_recovery_abandon.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "tool_attempt_recovery_retry.py",
        520,
        (
            "v11 tool-attempt retry eligibility and replay execution should "
            "stay owned by tool_attempt_recovery_retry.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "context_compaction_service.py",
        80,
        (
            "v11 compaction service should stay a thin facade over range "
            "planning, artifact assembly, freshness, and mutation helpers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "context_compaction_range.py",
        170,
        (
            "v11 compaction range planning and over-cap guidance should stay "
            "owned by context_compaction_range.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "context_compaction_artifact.py",
        300,
        (
            "v11 compaction artifact assembly should stay owned by "
            "context_compaction_artifact.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "context_compaction_freshness.py",
        160,
        (
            "v11 compaction freshness assessment should stay owned by "
            "context_compaction_freshness.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "context_compaction_mutations.py",
        220,
        (
            "v11 compaction refresh and invalidation mutations should stay "
            "owned by context_compaction_mutations.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "turn_event_recorder.py",
        590,
        (
            "v11 turn event recorder should keep artifact, replay, task-plan, "
            "and heartbeat behavior in focused helpers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "turn_tool_executor.py",
        610,
        (
            "v11 turn tool executor should keep artifact, replay, task-plan, "
            "and heartbeat behavior in focused helpers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "turn_artifacts.py",
        220,
        ("v11 turn artifact recording should stay owned by turn_artifacts.py"),
    ),
    (
        SRC_ROOT / "runtime" / "turn_replay_hooks.py",
        140,
        (
            "v11 turn replay capture forwarding should stay owned by "
            "turn_replay_hooks.py"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "turn_tool_attempt_heartbeats.py",
        80,
        (
            "v11 tool-attempt heartbeat construction should stay owned by "
            "turn_tool_attempt_heartbeats.py"
        ),
    ),
    (
        SRC_ROOT / "store" / "sqlite_projection_tasks.py",
        80,
        (
            "v11 task projection coordinator should stay a thin facade over "
            "event-family projection helpers"
        ),
    ),
    (
        SRC_ROOT / "store" / "sqlite_projection_task_common.py",
        260,
        "v11 shared task projection SQL helpers should stay focused",
    ),
    (
        SRC_ROOT / "store" / "sqlite_projection_task_plan.py",
        90,
        "v11 task-plan projection behavior should stay owned by its helper",
    ),
    (
        SRC_ROOT / "store" / "sqlite_projection_task_steps.py",
        140,
        "v11 task-step projection behavior should stay owned by its helper",
    ),
    (
        SRC_ROOT / "store" / "sqlite_projection_task_verifications.py",
        230,
        ("v11 task-verification projection behavior should stay owned by its helper"),
    ),
    (
        SRC_ROOT / "store" / "sqlite_projection_task_lifecycle.py",
        100,
        (
            "v11 task pause, resume, and terminal-state projections should "
            "stay owned by their helper"
        ),
    ),
    (
        SRC_ROOT / "store" / "sqlite_projection_background_jobs.py",
        80,
        (
            "v11 background-job projection coordinator should stay a thin "
            "facade over event-family projection helpers"
        ),
    ),
    (
        SRC_ROOT / "store" / "sqlite_projection_background_job_common.py",
        80,
        "v11 shared background-job projection SQL helpers should stay focused",
    ),
    (
        SRC_ROOT / "store" / "sqlite_projection_background_job_creation.py",
        90,
        "v11 background-job creation projections should stay owned by their helper",
    ),
    (
        SRC_ROOT / "store" / "sqlite_projection_background_job_lifecycle.py",
        160,
        ("v11 background-job lifecycle projections should stay owned by their helper"),
    ),
    (
        SRC_ROOT / "store" / "sqlite_projection_background_job_control.py",
        90,
        (
            "v11 background-job pause and cancellation projections should stay "
            "owned by their helper"
        ),
    ),
    (
        SRC_ROOT / "store" / "sqlite_projection_background_job_recovery.py",
        100,
        (
            "v11 background-job retry and recovery projections should stay "
            "owned by their helper"
        ),
    ),
)

V11_FRONTEND_PRESSURE_POINT_RULES: tuple[tuple[Path, int, str], ...] = (
    (
        FRONTEND_ROOT / "components" / "console" / "knowledge-autonomy-sections.tsx",
        60,
        (
            "v11 knowledge-autonomy-sections.tsx should stay a thin "
            "compatibility facade over knowledge section modules"
        ),
    ),
    (
        FRONTEND_ROOT / "components" / "console" / "knowledge-autonomy" / "memory.tsx",
        340,
        "v11 knowledge memory sections should stay owned by memory.tsx",
    ),
    (
        FRONTEND_ROOT
        / "components"
        / "console"
        / "knowledge-autonomy"
        / "repository.tsx",
        260,
        "v11 knowledge repository-index sections should stay owned by repository.tsx",
    ),
    (
        FRONTEND_ROOT / "components" / "console" / "knowledge-autonomy" / "format.ts",
        100,
        "v11 knowledge section formatting should stay owned by format.ts",
    ),
    (
        FRONTEND_ROOT / "components" / "console" / "knowledge-autonomy" / "shared.tsx",
        80,
        "v11 knowledge section shared controls should stay owned by shared.tsx",
    ),
    (
        FRONTEND_ROOT / "components" / "console" / "branch-search-sections.tsx",
        60,
        (
            "v11 branch-search-sections.tsx should stay a thin compatibility "
            "facade over branch-search section modules"
        ),
    ),
    (
        FRONTEND_ROOT / "components" / "console" / "branch-search" / "list.tsx",
        100,
        "v11 branch-search list sections should stay owned by list.tsx",
    ),
    (
        FRONTEND_ROOT / "components" / "console" / "branch-search" / "detail.tsx",
        240,
        "v11 branch-search candidate decision sections should stay owned by detail.tsx",
    ),
    (
        FRONTEND_ROOT / "components" / "console" / "branch-search" / "evidence.tsx",
        120,
        "v11 branch-search evidence sections should stay owned by evidence.tsx",
    ),
    (
        FRONTEND_ROOT / "components" / "console" / "branch-search" / "actions.tsx",
        100,
        "v11 branch-search action controls should stay owned by actions.tsx",
    ),
    (
        FRONTEND_ROOT / "components" / "console" / "branch-search" / "format.ts",
        90,
        "v11 branch-search formatting should stay owned by format.ts",
    ),
    (
        FRONTEND_ROOT / "stores" / "session-store.ts",
        240,
        (
            "v11 session-store should keep createSessionStore as a thin "
            "factory over stream, pagination, draft, and action helpers"
        ),
    ),
    (
        FRONTEND_ROOT / "stores" / "session-store-stream.ts",
        100,
        "v11 session stream lifecycle should stay owned by session-store-stream.ts",
    ),
    (
        FRONTEND_ROOT / "stores" / "session-store-pagination.ts",
        160,
        (
            "v11 session detail pagination should stay owned by "
            "session-store-pagination.ts"
        ),
    ),
    (
        FRONTEND_ROOT / "stores" / "session-store-drafts.ts",
        60,
        "v11 session drafts should stay owned by session-store-drafts.ts",
    ),
    (
        FRONTEND_ROOT / "stores" / "session-store-actions.ts",
        220,
        "v11 session actions should stay owned by session-store-actions.ts",
    ),
    (
        FRONTEND_ROOT / "stores" / "session-store-types.ts",
        120,
        "v11 session store types should stay owned by session-store-types.ts",
    ),
    (
        FRONTEND_ROOT / "stores" / "session-store-shared.ts",
        40,
        (
            "v11 session store shared guards should stay owned by "
            "session-store-shared.ts"
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
        SRC_ROOT / "runtime" / "branch_decision_models.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 branch decision models must stay independent from CLI and "
            "web presentation imports"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "branch_decision_evidence.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 branch decision evidence helpers must stay independent from "
            "CLI and web presentation imports"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "branch_decision_files.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 branch decision changed-file helpers must stay independent "
            "from CLI and web presentation imports"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "branch_decision_verification.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 branch decision verification helpers must stay independent "
            "from CLI and web presentation imports"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "branch_decision_cost.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 branch decision cost helpers must stay independent from CLI "
            "and web presentation imports"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "branch_decision_risk.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 branch decision risk helpers must stay independent from CLI "
            "and web presentation imports"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "branch_decision_followup.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 branch decision follow-up helpers must stay independent from "
            "CLI and web presentation imports"
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
        SRC_ROOT / "runtime" / "session_export_package.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 session export package assembly must stay independent from "
            "CLI and web presentation layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "session_export_handoff.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 session export handoff helpers must stay independent from "
            "CLI and web presentation layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "session_export_manifest.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 session export manifest helpers must stay independent from "
            "CLI and web presentation layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "session_export_redaction.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 session export redaction helpers must stay independent from "
            "CLI and web presentation layers"
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
        SRC_ROOT / "runtime" / "session_import_validation.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 session import validation helpers must stay independent from "
            "CLI and web presentation layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "session_import_events.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 session import inspection-event helpers must stay independent "
            "from CLI and web presentation layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "session_import_handoff.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 session import handoff helpers must stay independent from CLI "
            "and web presentation layers"
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
        SRC_ROOT / "runtime" / "tool_attempt_recovery_models.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 tool-attempt recovery result models must stay independent "
            "from CLI and web presentation layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "tool_attempt_recovery_common.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 tool-attempt recovery lookup helpers must stay independent "
            "from CLI and web presentation layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "tool_attempt_recovery_inspection.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 tool-attempt inspection summaries must stay independent "
            "from CLI and web presentation layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "tool_attempt_recovery_artifacts.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 tool-attempt output artifact helpers must stay independent "
            "from CLI and web presentation layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "tool_attempt_recovery_abandon.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 tool-attempt abandon helpers must stay independent from CLI "
            "and web presentation layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "tool_attempt_recovery_retry.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 tool-attempt retry helpers must stay independent from CLI "
            "and web presentation layers"
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
        SRC_ROOT / "runtime" / "context_compaction_range.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 compaction range planning helpers must stay independent from "
            "CLI and web presentation layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "context_compaction_artifact.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 compaction artifact assembly helpers must stay independent "
            "from CLI and web presentation layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "context_compaction_freshness.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 compaction freshness helpers must stay independent from CLI "
            "and web presentation layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "context_compaction_mutations.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 compaction mutation helpers must stay independent from CLI "
            "and web presentation layers"
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
        SRC_ROOT / "runtime" / "turn_artifacts.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 turn artifact helpers must stay independent from CLI and web "
            "presentation layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "turn_replay_hooks.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 turn replay hooks must stay independent from CLI and web "
            "presentation layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "turn_tool_attempt_heartbeats.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v11 tool-attempt heartbeat helpers must stay independent from CLI "
            "and web presentation layers"
        ),
    ),
    (
        SRC_ROOT / "store" / "sqlite_projection_tasks.py",
        ("glassbox.cli", "glassbox.runtime", "glassbox.web"),
        ("v11 task projection handlers must stay below runtime and transport layers"),
    ),
    (
        SRC_ROOT / "store" / "sqlite_projection_task_common.py",
        ("glassbox.cli", "glassbox.runtime", "glassbox.web"),
        ("v11 task projection helpers must stay below runtime and transport layers"),
    ),
    (
        SRC_ROOT / "store" / "sqlite_projection_task_plan.py",
        ("glassbox.cli", "glassbox.runtime", "glassbox.web"),
        ("v11 task projection helpers must stay below runtime and transport layers"),
    ),
    (
        SRC_ROOT / "store" / "sqlite_projection_task_steps.py",
        ("glassbox.cli", "glassbox.runtime", "glassbox.web"),
        ("v11 task projection helpers must stay below runtime and transport layers"),
    ),
    (
        SRC_ROOT / "store" / "sqlite_projection_task_verifications.py",
        ("glassbox.cli", "glassbox.runtime", "glassbox.web"),
        ("v11 task projection helpers must stay below runtime and transport layers"),
    ),
    (
        SRC_ROOT / "store" / "sqlite_projection_task_lifecycle.py",
        ("glassbox.cli", "glassbox.runtime", "glassbox.web"),
        ("v11 task projection helpers must stay below runtime and transport layers"),
    ),
    (
        SRC_ROOT / "store" / "sqlite_projection_background_jobs.py",
        ("glassbox.cli", "glassbox.runtime", "glassbox.web"),
        (
            "v11 background-job projection handlers must stay below runtime "
            "and transport layers"
        ),
    ),
    (
        SRC_ROOT / "store" / "sqlite_projection_background_job_common.py",
        ("glassbox.cli", "glassbox.runtime", "glassbox.web"),
        (
            "v11 background-job projection helpers must stay below runtime "
            "and transport layers"
        ),
    ),
    (
        SRC_ROOT / "store" / "sqlite_projection_background_job_creation.py",
        ("glassbox.cli", "glassbox.runtime", "glassbox.web"),
        (
            "v11 background-job projection helpers must stay below runtime "
            "and transport layers"
        ),
    ),
    (
        SRC_ROOT / "store" / "sqlite_projection_background_job_lifecycle.py",
        ("glassbox.cli", "glassbox.runtime", "glassbox.web"),
        (
            "v11 background-job projection helpers must stay below runtime "
            "and transport layers"
        ),
    ),
    (
        SRC_ROOT / "store" / "sqlite_projection_background_job_control.py",
        ("glassbox.cli", "glassbox.runtime", "glassbox.web"),
        (
            "v11 background-job projection helpers must stay below runtime "
            "and transport layers"
        ),
    ),
    (
        SRC_ROOT / "store" / "sqlite_projection_background_job_recovery.py",
        ("glassbox.cli", "glassbox.runtime", "glassbox.web"),
        (
            "v11 background-job projection helpers must stay below runtime "
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
        FRONTEND_ROOT / "components" / "console" / "knowledge-autonomy",
        ("@/api/client", "@/api/sse", "next/", "src/glassbox"),
        (
            "v11 knowledge section helpers should consume typed props and "
            "avoid transport, Next server, or backend imports"
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
        FRONTEND_ROOT / "components" / "console" / "branch-search",
        ("@/api/client", "@/api/sse", "next/", "src/glassbox"),
        (
            "v11 branch-search section helpers should consume typed props and "
            "avoid transport, Next server, or backend imports"
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

V11_COMPATIBILITY_FACADE_DELEGATES: tuple[tuple[Path, tuple[str, ...], str], ...] = (
    (
        SRC_ROOT / "runtime" / "eval_recommendation_output.py",
        (
            "glassbox.runtime.eval_recommendation_rows",
            "glassbox.runtime.eval_recommendation_plans",
            "glassbox.runtime.eval_recommendation_recipes",
            "glassbox.runtime.eval_recommendation_release_surfaces",
            "glassbox.runtime.eval_recommendation_long_run_surfaces",
            "glassbox.runtime.eval_recommendation_reason_groups",
        ),
        "v11 recommendation output facade should delegate to output helper owners",
    ),
    (
        SRC_ROOT / "runtime" / "eval_recommendation_matching.py",
        (
            "glassbox.runtime.eval_recommendation_path_matching",
            "glassbox.runtime.eval_recommendation_case_expansion",
            "glassbox.runtime.eval_recommendation_profile_expansion",
            "glassbox.runtime.eval_recommendation_matching_common",
        ),
        "v11 recommendation matching facade should delegate to matching helpers",
    ),
    (
        SRC_ROOT / "runtime" / "knowledge_posture.py",
        (
            "glassbox.runtime.knowledge_posture_sources",
            "glassbox.runtime.knowledge_posture_cues",
            "glassbox.runtime.knowledge_posture_guidance",
            "glassbox.runtime.knowledge_posture_ranking",
            "glassbox.runtime.knowledge_posture_models",
        ),
        "v11 knowledge posture facade should delegate to knowledge helpers",
    ),
    (
        SRC_ROOT / "runtime" / "branch_decision_support.py",
        (
            "glassbox.runtime.branch_decision_evidence",
            "glassbox.runtime.branch_decision_files",
            "glassbox.runtime.branch_decision_verification",
            "glassbox.runtime.branch_decision_cost",
            "glassbox.runtime.branch_decision_risk",
            "glassbox.runtime.branch_decision_followup",
            "glassbox.runtime.branch_decision_models",
        ),
        "v11 branch decision facade should delegate to branch helpers",
    ),
    (
        SRC_ROOT / "runtime" / "session_export.py",
        (
            "glassbox.runtime.session_export_models",
            "glassbox.runtime.session_export_package",
        ),
        "v11 session export facade should delegate to export helpers",
    ),
    (
        SRC_ROOT / "runtime" / "session_import.py",
        (
            "glassbox.runtime.session_import_events",
            "glassbox.runtime.session_import_validation",
        ),
        "v11 session import facade should delegate to import helpers",
    ),
    (
        SRC_ROOT / "runtime" / "tool_attempt_recovery.py",
        (
            "glassbox.runtime.tool_attempt_recovery_abandon",
            "glassbox.runtime.tool_attempt_recovery_artifacts",
            "glassbox.runtime.tool_attempt_recovery_inspection",
            "glassbox.runtime.tool_attempt_recovery_models",
            "glassbox.runtime.tool_attempt_recovery_retry",
        ),
        "v11 tool-attempt recovery facade should delegate to recovery helpers",
    ),
    (
        SRC_ROOT / "runtime" / "context_compaction_service.py",
        (
            "glassbox.runtime.context_compaction_freshness",
            "glassbox.runtime.context_compaction_mutations",
            "glassbox.runtime.context_compaction_range",
        ),
        "v11 compaction service facade should delegate to compaction helpers",
    ),
    (
        SRC_ROOT / "runtime" / "turn_event_recorder.py",
        (
            "glassbox.runtime.turn_artifacts",
            "glassbox.runtime.turn_replay_hooks",
        ),
        "v11 turn event recorder should delegate artifact and replay hooks",
    ),
    (
        SRC_ROOT / "runtime" / "turn_tool_executor.py",
        ("glassbox.runtime.turn_tool_attempt_heartbeats",),
        "v11 turn tool executor should delegate tool-attempt heartbeat shaping",
    ),
    (
        SRC_ROOT / "cli" / "status_formatters.py",
        ("glassbox.cli.status_session",),
        "v11 status formatter facade should delegate to status-domain helpers",
    ),
    (
        SRC_ROOT / "cli" / "command_guide.py",
        (
            "glassbox.cli.command_guide_data",
            "glassbox.cli.command_guide_json",
            "glassbox.cli.command_guide_models",
            "glassbox.cli.command_guide_render",
            "glassbox.cli.command_guide_workflows",
        ),
        "v11 command guide facade should delegate to command-guide helpers",
    ),
    (
        SRC_ROOT / "cli" / "interactive_commands.py",
        (
            "glassbox.cli.interactive_autonomy",
            "glassbox.cli.interactive_daemon_actions",
            "glassbox.cli.interactive_launch",
            "glassbox.cli.interactive_local_actions",
            "glassbox.cli.interactive_session",
        ),
        "v11 interactive command facade should delegate to interactive helpers",
    ),
    (
        SRC_ROOT / "store" / "sqlite_projection_tasks.py",
        (
            "glassbox.store.sqlite_projection_task_lifecycle",
            "glassbox.store.sqlite_projection_task_plan",
            "glassbox.store.sqlite_projection_task_steps",
            "glassbox.store.sqlite_projection_task_verifications",
        ),
        "v11 task projection facade should delegate to event-family helpers",
    ),
    (
        SRC_ROOT / "store" / "sqlite_projection_background_jobs.py",
        (
            "glassbox.store.sqlite_projection_background_job_control",
            "glassbox.store.sqlite_projection_background_job_creation",
            "glassbox.store.sqlite_projection_background_job_lifecycle",
            "glassbox.store.sqlite_projection_background_job_recovery",
        ),
        (
            "v11 background-job projection facade should delegate to "
            "event-family helpers"
        ),
    ),
)

V13_PYTHON_FACADE_RULES: tuple[tuple[Path, tuple[str, ...], int, str], ...] = (
    (
        SRC_ROOT / "runtime" / "changesets.py",
        ("glassbox.runtime.",),
        90,
        (
            "v13 changesets runtime facade should stay a thin public re-export "
            "surface over extracted review-loop helpers"
        ),
    ),
    (
        SRC_ROOT / "cli" / "changeset_commands.py",
        (
            "argparse",
            "glassbox.cli.changeset_command_handlers",
        ),
        100,
        (
            "v13 changeset CLI facade should stay a thin command dispatcher "
            "over command handler helpers"
        ),
    ),
    (
        SRC_ROOT / "cli" / "parser_changesets.py",
        (
            "argparse",
            "glassbox.cli.parser_changeset_",
            "glassbox.cli.parser_common",
        ),
        220,
        (
            "v13 changeset parser facade should stay a parser entrypoint over "
            "workflow-family parser helpers"
        ),
    ),
    (
        SRC_ROOT / "web" / "changeset_api.py",
        (
            "glassbox.web.changeset_api_builders",
            "glassbox.web.changeset_api_models",
            "glassbox.web.review_loop_api",
        ),
        220,
        (
            "v13 changeset API facade should stay a compatibility import "
            "surface over model and builder helpers"
        ),
    ),
    (
        SRC_ROOT / "web" / "routes" / "changesets.py",
        (
            "typing",
            "uuid",
            "fastapi",
            "glassbox.web.app",
            "glassbox.web.changeset_api",
            "glassbox.web.routes.changeset_route_",
            "glassbox.web.session_api",
        ),
        800,
        (
            "v13 changeset routes should stay a FastAPI declaration surface "
            "over route-local service, request, and error helpers"
        ),
    ),
)

V13_COMPATIBILITY_FACADE_DELEGATES: tuple[tuple[Path, tuple[str, ...], str], ...] = (
    (
        SRC_ROOT / "runtime" / "changesets.py",
        (
            "glassbox.runtime.changeset_actions",
            "glassbox.runtime.changeset_derivation",
            "glassbox.runtime.changeset_models",
            "glassbox.runtime.changeset_queries",
            "glassbox.runtime.changeset_repository_contracts",
            "glassbox.runtime.changeset_review_brief_service",
            "glassbox.runtime.changeset_verification",
            "glassbox.runtime.manual_evidence_actions",
            "glassbox.runtime.review_feedback_actions",
        ),
        "v13 changesets runtime facade should delegate to runtime helpers",
    ),
    (
        SRC_ROOT / "cli" / "changeset_commands.py",
        ("glassbox.cli.changeset_command_handlers",),
        "v13 changeset CLI facade should delegate to command handlers",
    ),
    (
        SRC_ROOT / "cli" / "parser_changesets.py",
        (
            "glassbox.cli.parser_changeset_evidence",
            "glassbox.cli.parser_changeset_feedback",
            "glassbox.cli.parser_changeset_review",
        ),
        "v13 changeset parser facade should delegate to parser helpers",
    ),
    (
        SRC_ROOT / "web" / "changeset_api.py",
        (
            "glassbox.web.changeset_api_builders",
            "glassbox.web.changeset_api_models",
            "glassbox.web.review_loop_api",
        ),
        "v13 changeset API facade should delegate to model and builder helpers",
    ),
    (
        SRC_ROOT / "web" / "routes" / "changesets.py",
        (
            "glassbox.web.routes.changeset_route_actions",
            "glassbox.web.routes.changeset_route_feedback",
            "glassbox.web.routes.changeset_route_requests",
            "glassbox.web.routes.changeset_route_services",
        ),
        "v13 changeset routes should delegate to route-local action helpers",
    ),
)

V13_PYTHON_PRESSURE_POINT_RULES: tuple[tuple[Path, int, str], ...] = (
    (
        SRC_ROOT / "runtime" / "changesets.py",
        4086,
        (
            "v13 changesets runtime facade should move new derivation, "
            "feedback, evidence, verification, brief, and readiness behavior "
            "into focused review-loop helpers"
        ),
    ),
    (
        SRC_ROOT / "cli" / "changeset_commands.py",
        1407,
        (
            "v13 changeset CLI facade should move new service wiring, JSON "
            "payloads, and terminal formatting into changeset command helpers"
        ),
    ),
    (
        SRC_ROOT / "cli" / "parser_changesets.py",
        687,
        (
            "v13 changeset parser facade should move new feedback, evidence, "
            "review, and commit-prep parser families into helper modules"
        ),
    ),
    (
        SRC_ROOT / "cli" / "tui" / "app_commands.py",
        246,
        (
            "v13 TUI app command helpers should move new review-loop routing "
            "and feedback messages into review command helpers"
        ),
    ),
    (
        SRC_ROOT / "cli" / "tui" / "commands.py",
        386,
        (
            "v13 TUI command registry should move new review-loop command "
            "families into review command helpers"
        ),
    ),
    (
        SRC_ROOT / "cli" / "interactive_session.py",
        479,
        (
            "v13 plain interactive review commands should move new review-loop "
            "routing into interactive review helpers"
        ),
    ),
    (
        SRC_ROOT / "web" / "changeset_api.py",
        1541,
        (
            "v13 changeset API facade should move new transport models and "
            "response builders into changeset API helper modules"
        ),
    ),
    (
        SRC_ROOT / "web" / "routes" / "changesets.py",
        837,
        (
            "v13 changeset routes should move new service factories, request "
            "helpers, and HTTP error mapping into route helper modules"
        ),
    ),
    (
        SRC_ROOT / "store" / "sqlite_projection_changesets.py",
        436,
        (
            "v13 changeset projection coordinator should move new event-family "
            "handlers into focused projection helpers"
        ),
    ),
    (
        SRC_ROOT / "store" / "sqlite_projection_review_loop.py",
        573,
        (
            "v13 review-loop projection coordinator should move new feedback "
            "and evidence handlers into focused projection helpers"
        ),
    ),
    (
        SRC_ROOT / "store" / "sqlite_query_changesets.py",
        324,
        (
            "v13 changeset query helpers should move new detail, inventory, "
            "and readiness reads into focused query modules"
        ),
    ),
    (
        SRC_ROOT / "store" / "sqlite_query_review_loop.py",
        393,
        (
            "v13 review-loop query helpers should move new feedback, response, "
            "and evidence reads into focused query modules"
        ),
    ),
    (
        SRC_ROOT / "store" / "repository_changesets.py",
        94,
        (
            "v13 changeset repository adapter should keep method ownership "
            "thin over store-owned query helpers"
        ),
    ),
    (
        SRC_ROOT / "store" / "repository_review_loop.py",
        120,
        (
            "v13 review-loop repository adapter should keep method ownership "
            "thin over store-owned query helpers"
        ),
    ),
)

V13_FRONTEND_PRESSURE_POINT_RULES: tuple[tuple[Path, int, str], ...] = (
    (
        FRONTEND_ROOT / "components" / "console" / "changeset-console.tsx",
        1382,
        (
            "v13 changeset-console should move new list, detail, feedback, "
            "evidence, verification, handoff, and commit-prep presentation "
            "into changeset section modules"
        ),
    ),
    (
        FRONTEND_ROOT / "stores" / "changeset-store.ts",
        435,
        (
            "v13 changeset store should move new API action groups and "
            "selectors into store-owned helpers"
        ),
    ),
)

V13_PYTHON_IMPORT_RULES: tuple[tuple[Path, tuple[str, ...], str], ...] = (
    (
        SRC_ROOT / "runtime" / "changesets.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "v13 changeset runtime helpers must keep review-loop derivation "
            "independent from CLI and web presentation layers"
        ),
    ),
    (
        SRC_ROOT / "cli" / "parser_changesets.py",
        ("glassbox.runtime", "glassbox.store", "glassbox.web"),
        (
            "v13 changeset parser helpers must stay parser-only and avoid "
            "runtime orchestration, raw store, or web imports"
        ),
    ),
    (
        SRC_ROOT / "web" / "changeset_api.py",
        ("fastapi",),
        (
            "v13 changeset API model and builder helpers should keep FastAPI "
            "dependencies in route modules"
        ),
    ),
    (
        SRC_ROOT / "store" / "sqlite_projection_changesets.py",
        ("glassbox.cli", "glassbox.runtime", "glassbox.web"),
        (
            "v13 changeset projection handlers must stay below runtime and "
            "transport layers"
        ),
    ),
    (
        SRC_ROOT / "store" / "sqlite_projection_review_loop.py",
        ("glassbox.cli", "glassbox.runtime", "glassbox.web"),
        (
            "v13 review-loop projection handlers must stay below runtime and "
            "transport layers"
        ),
    ),
)

V13_FRONTEND_IMPORT_RULES: tuple[tuple[Path, tuple[str, ...], str], ...] = (
    (
        FRONTEND_ROOT / "components" / "console" / "changeset-console.tsx",
        ("@/api/client", "@/api/sse", "next/", "src/glassbox"),
        (
            "v13 changeset console should consume store state and avoid API "
            "transport, SSE, Next server, or backend imports"
        ),
    ),
    (
        FRONTEND_ROOT / "stores" / "changeset-store.ts",
        ("@/components", "next/", "react", "src/glassbox"),
        (
            "v13 changeset store should own API transport without importing "
            "React components, Next server, or backend source"
        ),
    ),
)

V14_PYTHON_PRESSURE_POINT_RULES: tuple[tuple[Path, int, str], ...] = (
    (
        SRC_ROOT / "runtime" / "changeset_review_brief_sections.py",
        915,
        (
            "post-v14 review brief sections should move new limitation, "
            "section-family, skipped-evidence, and readiness behavior into "
            "focused review-brief helpers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "review_responses.py",
        722,
        (
            "post-v14 review responses should move new model, status, fixup, "
            "path-scope, and summary behavior into focused response helpers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "handoff_readiness.py",
        763,
        (
            "post-v14 handoff readiness should move shared signal aggregation "
            "into review_readiness_signals without merging handoff semantics"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "commit_readiness.py",
        750,
        (
            "post-v14 commit readiness should move shared signal aggregation "
            "into review_readiness_signals without merging commit semantics"
        ),
    ),
    (
        SRC_ROOT / "cli" / "interactive_client.py",
        1153,
        (
            "post-v14 interactive client should move protocols, SSE parsing, "
            "local actions, daemon actions, and review guidance into focused "
            "terminal helpers"
        ),
    ),
    (
        SRC_ROOT / "cli" / "changeset_command_handlers.py",
        847,
        (
            "post-v14 changeset command handlers should split lifecycle, "
            "feedback, evidence, verification, readiness, adoption, export, "
            "and commit-preparation command families"
        ),
    ),
    (
        SRC_ROOT / "web" / "routes" / "changesets.py",
        779,
        (
            "post-v14 changeset routes should move repeated action, reload, "
            "workspace-root, service, and error patterns into route helpers"
        ),
    ),
    (
        SRC_ROOT / "web" / "changeset_api_builders.py",
        878,
        (
            "post-v14 changeset API builders should split summary, detail, "
            "review-loop, readiness, verification, evidence, and commit-prep "
            "builder families"
        ),
    ),
    (
        REPO_ROOT / "scripts" / "v14_release_gate_helpers.py",
        301,
        (
            "post-v14 release-gate helpers should split inherited stages, "
            "v14 stages, advisory evidence, dry-run copy, evidence dirs, and "
            "summary metadata"
        ),
    ),
)

V14_FRONTEND_PRESSURE_POINT_RULES: tuple[tuple[Path, int, str], ...] = (
    (
        FRONTEND_ROOT / "api" / "client.ts",
        1067,
        (
            "post-v14 frontend API client should group endpoint families "
            "without moving transport into components"
        ),
    ),
    (
        FRONTEND_ROOT / "stores" / "changeset-store-actions.ts",
        405,
        (
            "post-v14 changeset store actions should split list, detail, "
            "review-loop, readiness, commit-prep, message, and branch-adjacent "
            "action families"
        ),
    ),
)

V16_PYTHON_PRESSURE_POINT_RULES: tuple[tuple[Path, int, str], ...] = (
    (
        SRC_ROOT / "runtime" / "evidence_graph.py",
        1159,
        (
            "post-v16 evidence_graph should move graph models, builder "
            "utilities, changeset/session derivation, and query helpers into "
            "focused evidence_graph modules"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "verification_plan_builder.py",
        585,
        (
            "post-v16 verification_plan_builder should move identity, "
            "recommendation, readiness, manual-only, and skipped-check behavior "
            "into focused verification_plan helpers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "operator_queue.py",
        504,
        (
            "post-v16 operator_queue should move session, runtime, "
            "maintenance, changeset, sorting, and count behavior into focused "
            "operator_queue helpers"
        ),
    ),
    (
        SRC_ROOT / "web" / "session_api_aggregate.py",
        101,
        (
            "post-v16 session aggregate API should move queue response models "
            "and builders into focused web helpers"
        ),
    ),
    (
        SRC_ROOT / "web" / "changeset_api_builders_detail.py",
        584,
        (
            "post-v16 changeset detail builders should move verification and "
            "evidence graph response shaping into focused web builders"
        ),
    ),
    (
        SRC_ROOT / "web" / "routes" / "session_route_queries.py",
        369,
        (
            "post-v16 session route queries should consume aggregate and graph "
            "helpers without owning queue or graph internals"
        ),
    ),
    (
        SRC_ROOT / "web" / "routes" / "changeset_route_actions.py",
        520,
        (
            "post-v16 changeset route actions should move verification, "
            "workup, evidence graph, feedback, and readiness helpers behind "
            "route-local boundaries"
        ),
    ),
    (
        REPO_ROOT / "scripts" / "validate_v16_release_gate.py",
        554,
        (
            "post-v16 release gate should move stage assembly, advisory rows, "
            "package evidence, dogfooding expectations, and summary metadata "
            "into focused v16 helper modules"
        ),
    ),
)

V16_FRONTEND_PRESSURE_POINT_RULES: tuple[tuple[Path, int, str], ...] = (
    (
        FRONTEND_ROOT
        / "components"
        / "console"
        / "workspace-overview"
        / "operator-queue-lanes.tsx",
        486,
        (
            "post-v16 operator queue lanes should move lane descriptors, "
            "rows, links, and formatting into focused cockpit helpers"
        ),
    ),
    (
        FRONTEND_ROOT / "components" / "console" / "evidence-graph-panel.tsx",
        345,
        (
            "post-v16 evidence graph panel should move summary, claims, "
            "nodes, relationships, limitations, and formatting into focused "
            "graph components"
        ),
    ),
    (
        FRONTEND_ROOT / "components" / "console" / "changeset" / "verification.tsx",
        493,
        (
            "post-v16 changeset verification panel should move table, action, "
            "and formatting behavior into focused verification components"
        ),
    ),
    (
        FRONTEND_ROOT / "stores" / "changeset-store-review-actions.ts",
        301,
        (
            "post-v16 changeset review store actions should move verification "
            "transport helpers into store-owned action modules"
        ),
    ),
)

V16_PYTHON_FACADE_RULES: tuple[
    tuple[Path, tuple[str, ...], int, str],
    ...,
] = (
    (
        SRC_ROOT / "runtime" / "evidence_graph.py",
        (
            "glassbox.runtime.evidence_graph_changeset",
            "glassbox.runtime.evidence_graph_models",
            "glassbox.runtime.evidence_graph_queries",
            "glassbox.runtime.evidence_graph_session",
        ),
        60,
        (
            "post-v16 evidence_graph facade should stay bounded over graph "
            "derivation, model, and query helpers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "verification_plan_builder.py",
        (
            "glassbox.core",
            "glassbox.runtime.changeset_models",
            "glassbox.runtime.changeset_verification_readiness",
            "glassbox.runtime.eval_recommendation_models",
            "glassbox.runtime.verification_plan_evals",
            "glassbox.runtime.verification_plan_identity",
            "glassbox.runtime.verification_plan_manual",
            "glassbox.runtime.verification_plan_readiness",
            "glassbox.runtime.verification_plan_recipes",
            "glassbox.runtime.verification_plan_recommendations",
            "glassbox.runtime.verification_plan_skips",
        ),
        130,
        (
            "post-v16 verification_plan_builder facade should stay bounded "
            "over identity, source-family, readiness, manual, and skip helpers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "operator_queue.py",
        (
            "collections.abc",
            "datetime",
            "glassbox.core",
            "glassbox.runtime.operator_queue_changeset_items",
            "glassbox.runtime.operator_queue_counts",
            "glassbox.runtime.operator_queue_maintenance_items",
            "glassbox.runtime.operator_queue_runtime_items",
            "glassbox.runtime.operator_queue_session_items",
            "glassbox.runtime.operator_queue_sorting",
            "glassbox.runtime.session_query_models",
        ),
        80,
        (
            "post-v16 operator_queue facade should stay bounded over item "
            "source, sorting, and count helpers"
        ),
    ),
)

V16_PYTHON_FACADE_DELEGATES: tuple[tuple[Path, tuple[str, ...], str], ...] = (
    (
        SRC_ROOT / "runtime" / "evidence_graph.py",
        (
            "glassbox.runtime.evidence_graph_changeset",
            "glassbox.runtime.evidence_graph_queries",
            "glassbox.runtime.evidence_graph_session",
        ),
        "post-v16 evidence_graph facade should delegate to graph owner modules",
    ),
    (
        SRC_ROOT / "runtime" / "verification_plan_builder.py",
        (
            "glassbox.runtime.verification_plan_evals",
            "glassbox.runtime.verification_plan_identity",
            "glassbox.runtime.verification_plan_manual",
            "glassbox.runtime.verification_plan_readiness",
            "glassbox.runtime.verification_plan_recipes",
            "glassbox.runtime.verification_plan_recommendations",
            "glassbox.runtime.verification_plan_skips",
        ),
        (
            "post-v16 verification_plan_builder facade should delegate to "
            "verification plan owner modules"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "operator_queue.py",
        (
            "glassbox.runtime.operator_queue_maintenance_items",
            "glassbox.runtime.operator_queue_runtime_items",
            "glassbox.runtime.operator_queue_session_items",
            "glassbox.runtime.operator_queue_changeset_items",
            "glassbox.runtime.operator_queue_sorting",
            "glassbox.runtime.operator_queue_counts",
        ),
        "post-v16 operator_queue facade should delegate to queue owner modules",
    ),
    (
        SRC_ROOT / "core" / "models.py",
        (
            "glassbox.core.models_evidence_graph",
            "glassbox.core.models_operator_flow",
            "glassbox.core.models_verification_plan",
        ),
        (
            "post-v16 core model facade should re-export operator-flow, "
            "evidence graph, and verification plan models from owner modules"
        ),
    ),
    (
        SRC_ROOT / "core" / "types.py",
        (
            "glassbox.core.types_evidence_graph",
            "glassbox.core.types_operator_flow",
            "glassbox.core.types_verification_plan",
        ),
        (
            "post-v16 core type facade should re-export operator-flow, "
            "evidence graph, and verification plan enums from owner modules"
        ),
    ),
    (
        SRC_ROOT / "core" / "__init__.py",
        (
            "glassbox.core.models_evidence_graph",
            "glassbox.core.models_operator_flow",
            "glassbox.core.models_verification_plan",
            "glassbox.core.types_evidence_graph",
            "glassbox.core.types_operator_flow",
            "glassbox.core.types_verification_plan",
        ),
        "post-v16 core package facade should delegate extracted core exports",
    ),
)

V14_PYTHON_FACADE_RULES: tuple[
    tuple[Path, tuple[str, ...], int, str],
    ...,
] = (
    (
        SRC_ROOT / "runtime" / "changeset_review_brief_sections.py",
        (
            "glassbox.core",
            "glassbox.runtime.change_inventory",
            "glassbox.runtime.changeset_models",
            "glassbox.runtime.changeset_review_brief_core_sections",
            "glassbox.runtime.changeset_review_brief_review_sections",
            "glassbox.runtime.changeset_safe_commands",
            "glassbox.runtime.review_briefs",
            "glassbox.runtime.review_responses",
        ),
        220,
        (
            "post-v14 review brief sections facade should stay bounded over "
            "core, review-loop, safe-command, and brief model helpers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "review_responses.py",
        (
            "glassbox.runtime.review_fixup_artifacts",
            "glassbox.runtime.review_response_models",
            "glassbox.runtime.review_response_status",
            "glassbox.runtime.review_response_summary",
        ),
        60,
        (
            "post-v14 review_responses facade should stay a compatibility "
            "surface over response model, status, fixup, and summary helpers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "handoff_readiness.py",
        (
            "asyncio",
            "collections.abc",
            "pathlib",
            "typing",
            "pydantic",
            "glassbox.core",
            "glassbox.runtime.changeset_models",
            "glassbox.runtime.changeset_queries",
            "glassbox.runtime.changeset_repository_contracts",
            "glassbox.runtime.changeset_verification",
            "glassbox.runtime.commit_readiness",
            "glassbox.runtime.handoff_readiness_evidence",
            "glassbox.runtime.handoff_readiness_signals",
            "glassbox.runtime.review_readiness_signals",
            "glassbox.runtime.review_responses",
            "glassbox.services",
        ),
        260,
        (
            "post-v14 handoff readiness should stay orchestration over "
            "evidence and signal helpers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "commit_readiness.py",
        (
            "asyncio",
            "collections.abc",
            "pathlib",
            "pydantic",
            "glassbox.core",
            "glassbox.runtime.changeset_models",
            "glassbox.runtime.changeset_queries",
            "glassbox.runtime.changeset_repository_contracts",
            "glassbox.runtime.changeset_verification",
            "glassbox.runtime.commit_readiness_git",
            "glassbox.runtime.commit_readiness_signals",
            "glassbox.runtime.review_readiness_signals",
            "glassbox.runtime.review_responses",
            "glassbox.services",
            "glassbox.tools.workflow",
        ),
        280,
        (
            "post-v14 commit readiness should stay orchestration over git "
            "and signal helpers"
        ),
    ),
    (
        SRC_ROOT / "cli" / "interactive_client.py",
        ("glassbox.cli.interactive_client_",),
        60,
        (
            "post-v14 interactive_client facade should stay a compatibility "
            "surface over client model, SSE, local, and daemon helpers"
        ),
    ),
    (
        SRC_ROOT / "cli" / "changeset_command_handlers.py",
        ("glassbox.cli.changeset_command_",),
        100,
        (
            "post-v14 changeset command handler facade should stay a "
            "compatibility surface over command-family helpers"
        ),
    ),
    (
        SRC_ROOT / "web" / "routes" / "changesets.py",
        (
            "typing",
            "uuid",
            "fastapi",
            "glassbox.web.app",
            "glassbox.web.changeset_api",
            "glassbox.web.routes.changeset_route_",
            "glassbox.web.session_api",
        ),
        620,
        (
            "post-v14 changeset route facade should stay a FastAPI declaration "
            "surface over route-local helpers"
        ),
    ),
    (
        SRC_ROOT / "web" / "changeset_api_builders.py",
        ("glassbox.web.changeset_api_builders_",),
        120,
        (
            "post-v14 changeset API builder facade should stay a compatibility "
            "surface over builder-family helpers"
        ),
    ),
    (
        REPO_ROOT / "scripts" / "v14_release_gate_helpers.py",
        ("scripts.v14_release_gate_",),
        50,
        (
            "post-v14 release-gate helper facade should stay a compatibility "
            "surface over stage, advisory, and summary helpers"
        ),
    ),
)

V14_PYTHON_FACADE_DELEGATES: tuple[tuple[Path, tuple[str, ...], str], ...] = (
    (
        SRC_ROOT / "runtime" / "changeset_review_brief_sections.py",
        (
            "glassbox.runtime.changeset_review_brief_core_sections",
            "glassbox.runtime.changeset_review_brief_review_sections",
        ),
        "post-v14 review brief sections facade should delegate to section families",
    ),
    (
        SRC_ROOT / "runtime" / "review_responses.py",
        (
            "glassbox.runtime.review_fixup_artifacts",
            "glassbox.runtime.review_response_models",
            "glassbox.runtime.review_response_status",
            "glassbox.runtime.review_response_summary",
        ),
        "post-v14 review_responses facade should delegate to response helpers",
    ),
    (
        SRC_ROOT / "runtime" / "handoff_readiness.py",
        (
            "glassbox.runtime.handoff_readiness_evidence",
            "glassbox.runtime.handoff_readiness_signals",
            "glassbox.runtime.review_readiness_signals",
        ),
        "post-v14 handoff readiness should delegate to evidence and signal helpers",
    ),
    (
        SRC_ROOT / "runtime" / "commit_readiness.py",
        (
            "glassbox.runtime.commit_readiness_git",
            "glassbox.runtime.commit_readiness_signals",
            "glassbox.runtime.review_readiness_signals",
        ),
        "post-v14 commit readiness should delegate to git and signal helpers",
    ),
    (
        SRC_ROOT / "cli" / "interactive_client.py",
        (
            "glassbox.cli.interactive_client_daemon",
            "glassbox.cli.interactive_client_local",
            "glassbox.cli.interactive_client_models",
            "glassbox.cli.interactive_client_sse",
        ),
        "post-v14 interactive client facade should delegate to client helpers",
    ),
    (
        SRC_ROOT / "cli" / "changeset_command_handlers.py",
        (
            "glassbox.cli.changeset_command_evidence",
            "glassbox.cli.changeset_command_feedback",
            "glassbox.cli.changeset_command_lifecycle",
            "glassbox.cli.changeset_command_readiness",
        ),
        "post-v14 changeset command facade should delegate to command-family helpers",
    ),
    (
        SRC_ROOT / "web" / "routes" / "changesets.py",
        (
            "glassbox.web.routes.changeset_route_actions",
            "glassbox.web.routes.changeset_route_feedback",
            "glassbox.web.routes.changeset_route_requests",
            "glassbox.web.routes.changeset_route_services",
        ),
        "post-v14 changeset route facade should delegate to route-local helpers",
    ),
    (
        SRC_ROOT / "web" / "changeset_api_builders.py",
        (
            "glassbox.web.changeset_api_builders_detail",
            "glassbox.web.changeset_api_builders_readiness",
            "glassbox.web.changeset_api_builders_review",
        ),
        "post-v14 changeset API builder facade should delegate to builder helpers",
    ),
    (
        REPO_ROOT / "scripts" / "v14_release_gate_helpers.py",
        (
            "scripts.v14_release_gate_advisory",
            "scripts.v14_release_gate_stages",
            "scripts.v14_release_gate_summary",
        ),
        "post-v14 release-gate helper facade should delegate to helper families",
    ),
)

V14_FRONTEND_FACADE_RULES: tuple[tuple[Path, int, str], ...] = (
    (
        FRONTEND_ROOT / "api" / "client.ts",
        130,
        (
            "post-v14 frontend API client facade should stay a compatibility "
            "surface over endpoint-family helpers"
        ),
    ),
    (
        FRONTEND_ROOT / "stores" / "changeset-store-actions.ts",
        80,
        (
            "post-v14 changeset store action facade should stay a "
            "compatibility surface over loader and review action helpers"
        ),
    ),
)

V14_FRONTEND_FACADE_DELEGATES: tuple[tuple[Path, tuple[str, ...], str], ...] = (
    (
        FRONTEND_ROOT / "api" / "client.ts",
        (
            "./client-changesets",
            "./client-core",
            "./client-sessions",
            "./client-tasks",
            "./client-workspace",
        ),
        "post-v14 frontend API client facade should delegate to endpoint helpers",
    ),
    (
        FRONTEND_ROOT / "stores" / "changeset-store-actions.ts",
        (
            "@/stores/changeset-store-loaders",
            "@/stores/changeset-store-review-actions",
        ),
        "post-v14 changeset store action facade should delegate to store helpers",
    ),
)

V14_PYTHON_IMPORT_RULES: tuple[tuple[Path, tuple[str, ...], str], ...] = (
    (
        SRC_ROOT / "runtime" / "changeset_review_brief_sections.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "post-v14 review brief helpers must keep lifecycle and limitation "
            "derivation independent from CLI and web presentation layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "review_responses.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "post-v14 review response helpers must keep status and fixup "
            "derivation independent from CLI and web presentation layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "handoff_readiness.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "post-v14 handoff readiness helpers must keep signal derivation "
            "independent from CLI and web presentation layers"
        ),
    ),
    (
        SRC_ROOT / "runtime" / "commit_readiness.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "post-v14 commit readiness helpers must keep signal derivation "
            "independent from CLI and web presentation layers"
        ),
    ),
    (
        SRC_ROOT / "web" / "changeset_api_builders.py",
        ("fastapi",),
        (
            "post-v14 changeset API builder helpers should keep FastAPI "
            "dependencies in route modules"
        ),
    ),
    (
        REPO_ROOT / "scripts" / "v14_release_gate_helpers.py",
        ("glassbox.cli", "glassbox.web"),
        (
            "post-v14 release-gate helpers must keep summary shaping separate "
            "from CLI and web presentation layers"
        ),
    ),
)

V14_FRONTEND_IMPORT_RULES: tuple[tuple[Path, tuple[str, ...], str], ...] = (
    (
        FRONTEND_ROOT / "api" / "client.ts",
        ("@/components", "@/stores", "next/", "react", "src/glassbox"),
        (
            "post-v14 frontend API client should own transport without "
            "importing components, stores, Next server modules, React, or "
            "backend source"
        ),
    ),
    (
        FRONTEND_ROOT / "stores" / "changeset-store-actions.ts",
        ("@/components", "next/", "react", "src/glassbox"),
        (
            "post-v14 changeset store actions should own transport/action "
            "state without importing React components, Next server modules, "
            "or backend source"
        ),
    ),
)
