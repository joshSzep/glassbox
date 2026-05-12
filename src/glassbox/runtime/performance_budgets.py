"""Repository-owned performance budgets for larger local workspaces."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PerformanceBudget:
    surface: str
    scenario: str
    fixture_size: str
    budget_ms: int
    guidance: str


@dataclass(frozen=True)
class PayloadSizeBudget:
    surface: str
    scenario: str
    fixture_size: str
    budget_bytes: int
    guidance: str


PERFORMANCE_BUDGETS: tuple[PerformanceBudget, ...] = (
    PerformanceBudget(
        surface="event-stream append",
        scenario="append and project one 600-event session batch",
        fixture_size="600 canonical events in one session",
        budget_ms=2_000,
        guidance=(
            "If this regresses, inspect SQLite transaction scope and projection "
            "handlers before changing the event model."
        ),
    ),
    PerformanceBudget(
        surface="projection rebuild",
        scenario="rebuild projections for one large session",
        fixture_size="600 canonical events in one session",
        budget_ms=2_000,
        guidance=(
            "If this regresses, keep canonical events unchanged and optimize derived "
            "projection replay or add bounded operator guidance."
        ),
    ),
    PerformanceBudget(
        surface="session index",
        scenario="read recent persisted session rows",
        fixture_size="120 sessions",
        budget_ms=1_000,
        guidance=(
            "If this regresses, check session indexes and avoid fetching per-session "
            "detail in the index path."
        ),
    ),
    PerformanceBudget(
        surface="operator console aggregate",
        scenario="build prioritized dashboard queue rows",
        fixture_size="60 sessions",
        budget_ms=3_000,
        guidance=(
            "If this regresses, prefer narrower aggregate queries or explicit "
            "pagination over browser-only degraded behavior."
        ),
    ),
    PerformanceBudget(
        surface="operator queue aggregation",
        scenario="derive and sort the unified v16 operator queue",
        fixture_size="60 sessions plus workspace maintenance cues",
        budget_ms=1_000,
        guidance=(
            "If this regresses, keep queue producers summary-first, dedupe before "
            "transport, and move expensive evidence expansion behind detail routes."
        ),
    ),
    PerformanceBudget(
        surface="evidence graph derivation",
        scenario="derive a bounded graph for one dense changeset",
        fixture_size=(
            "80 verification requirements, 80 manual evidence rows, "
            "80 review feedback rows, and 80 command evidence rows"
        ),
        budget_ms=1_000,
        guidance=(
            "If this regresses, preserve bounded graph construction and expose "
            "truncation limitations instead of expanding raw artifacts inline."
        ),
    ),
    PerformanceBudget(
        surface="evidence graph neighborhood",
        scenario="derive one bounded evidence graph neighborhood",
        fixture_size="dense changeset graph capped to reviewer/operator summaries",
        budget_ms=250,
        guidance=(
            "If this regresses, keep neighborhood reads capped by node count and "
            "serve raw evidence through explicit detail inspection routes."
        ),
    ),
    PerformanceBudget(
        surface="verification plan generation",
        scenario="build a bounded plan from many changed paths and recommendations",
        fixture_size="80 changed paths and 160 recommendation rows",
        budget_ms=1_000,
        guidance=(
            "If this regresses, cap generated plan entries, surface skipped "
            "recommendations, and keep command execution outside preview paths."
        ),
    ),
    PerformanceBudget(
        surface="session snapshot build",
        scenario="build a full snapshot for a mixed larger session",
        fixture_size="120 turns, 80 tool calls, 40 artifacts",
        budget_ms=3_000,
        guidance=(
            "If this regresses, profile transcript, tool-call, runtime-context, "
            "and fork-point reads before changing the snapshot contract."
        ),
    ),
    PerformanceBudget(
        surface="projection health check",
        scenario="inspect projection lag for one larger session",
        fixture_size="120 turns, 80 tool calls, 40 artifacts",
        budget_ms=1_000,
        guidance=(
            "If this regresses, keep the check bounded to session_state and "
            "canonical sequence metadata."
        ),
    ),
    PerformanceBudget(
        surface="transcript read",
        scenario="read projected transcript rows for one larger session",
        fixture_size="240 transcript messages",
        budget_ms=1_000,
        guidance=(
            "If this regresses, add explicit transcript pagination and keep the "
            "full snapshot path backward compatible."
        ),
    ),
    PerformanceBudget(
        surface="event-log read",
        scenario="read canonical event history for one larger session",
        fixture_size="681 canonical events",
        budget_ms=1_500,
        guidance=(
            "If this regresses, prefer cursor-based event reads over widening "
            "dashboard snapshot payloads."
        ),
    ),
    PerformanceBudget(
        surface="artifact inspect",
        scenario="inspect retained and stale managed artifacts",
        fixture_size="40 event-referenced artifacts",
        budget_ms=2_000,
        guidance=(
            "If this regresses, summarize artifact pressure by category before "
            "hashing or printing every file in operator paths."
        ),
    ),
    PerformanceBudget(
        surface="repository intelligence index build",
        scenario="build a bounded v2 repository intelligence snapshot",
        fixture_size="2,050 source files plus manifests",
        budget_ms=5_000,
        guidance=(
            "If this regresses, keep discovery bounded, avoid full-tree sorting, "
            "and prefer manifest summaries over reading generated or excluded paths."
        ),
    ),
    PerformanceBudget(
        surface="repository intelligence path inspection",
        scenario="match one changed path to retained repository intelligence records",
        fixture_size="snapshot built from a 2,050-file synthetic repository",
        budget_ms=500,
        guidance=(
            "If this regresses, keep path inspection on retained summary records "
            "and move broad entry search behind explicit paginated routes."
        ),
    ),
    PerformanceBudget(
        surface="repository intelligence search",
        scenario="search retained repository index entries",
        fixture_size="snapshot built from a 2,050-file synthetic repository",
        budget_ms=750,
        guidance=(
            "If this regresses, bound result construction or add indexed lookup "
            "metadata without widening dashboard overview payloads."
        ),
    ),
)


PAYLOAD_SIZE_BUDGETS: tuple[PayloadSizeBudget, ...] = (
    PayloadSizeBudget(
        surface="dashboard render-critical payload",
        scenario="serialize the operator-console aggregate for initial render",
        fixture_size="60 sessions, 25 returned rows",
        budget_bytes=300_000,
        guidance=(
            "If this regresses, reduce aggregate row width or require paginated "
            "queue reads before adding browser-side-only filtering."
        ),
    ),
    PayloadSizeBudget(
        surface="operator queue payload",
        scenario="serialize the unified v16 queue inside the workspace aggregate",
        fixture_size="60 sessions plus workspace maintenance cues",
        budget_bytes=120_000,
        guidance=(
            "If this regresses, reduce queue item evidence width and link to "
            "evidence graph detail routes instead of embedding expanded support."
        ),
    ),
    PayloadSizeBudget(
        surface="evidence graph summary payload",
        scenario="serialize a dense changeset evidence graph summary",
        fixture_size="bounded summary counts and graph limitations",
        budget_bytes=20_000,
        guidance=(
            "If this regresses, keep summary responses count-based and avoid "
            "returning node or artifact detail from summary endpoints."
        ),
    ),
    PayloadSizeBudget(
        surface="evidence graph neighborhood payload",
        scenario="serialize one bounded graph neighborhood for dashboard inspection",
        fixture_size="dense changeset graph neighborhood capped to 100 nodes",
        budget_bytes=250_000,
        guidance=(
            "If this regresses, lower neighborhood node caps or move additional "
            "relationships behind explicit pagination."
        ),
    ),
    PayloadSizeBudget(
        surface="verification plan preview payload",
        scenario="serialize a bounded verification plan preview",
        fixture_size="80 changed paths and capped generated plan entries",
        budget_bytes=250_000,
        guidance=(
            "If this regresses, cap preview entries more aggressively and keep "
            "large recommendation rationale behind detail inspection."
        ),
    ),
    PayloadSizeBudget(
        surface="session snapshot payload",
        scenario="serialize a full selected-session snapshot",
        fixture_size="120 turns, 240 transcript messages, 80 tool calls",
        budget_bytes=1_500_000,
        guidance=(
            "If this regresses, move transcript, event, metric, or artifact "
            "details behind typed paginated endpoints."
        ),
    ),
    PayloadSizeBudget(
        surface="transcript payload",
        scenario="serialize projected transcript rows for one larger session",
        fixture_size="240 transcript messages",
        budget_bytes=500_000,
        guidance=(
            "If this regresses, page transcript reads and virtualize the "
            "dashboard transcript pane."
        ),
    ),
    PayloadSizeBudget(
        surface="event-log payload",
        scenario="serialize canonical event history for one larger session",
        fixture_size="681 canonical events",
        budget_bytes=1_500_000,
        guidance=(
            "If this regresses, use event cursors and lazy event-inspector "
            "loading instead of attaching raw events to snapshots."
        ),
    ),
    PayloadSizeBudget(
        surface="artifact inspection payload",
        scenario="serialize managed artifact retention inspection",
        fixture_size="40 event-referenced artifacts",
        budget_bytes=300_000,
        guidance=(
            "If this regresses, add category and size summaries and avoid "
            "printing every artifact by default in dashboard-facing paths."
        ),
    ),
    PayloadSizeBudget(
        surface="session transcript page payload",
        scenario="serialize one paginated transcript window for a larger session",
        fixture_size="80 of 240 transcript messages",
        budget_bytes=180_000,
        guidance=(
            "If this regresses, reduce transcript row width or lower the dashboard "
            "detail page size before widening the selected-session snapshot."
        ),
    ),
    PayloadSizeBudget(
        surface="session event-log page payload",
        scenario="serialize one paginated canonical event window for a larger session",
        fixture_size="80 of 681 canonical events",
        budget_bytes=300_000,
        guidance=(
            "If this regresses, keep raw event payload expansion out of the "
            "dashboard initial render path and inspect event serialization width."
        ),
    ),
    PayloadSizeBudget(
        surface="session tool-call page payload",
        scenario="serialize one paginated tool-call window for a larger session",
        fixture_size="80 tool calls",
        budget_bytes=180_000,
        guidance=(
            "If this regresses, keep tool-call detail reads paginated and avoid "
            "attaching verbose artifacts to tool-call rows."
        ),
    ),
    PayloadSizeBudget(
        surface="session turn-metrics page payload",
        scenario="serialize one paginated metric window for a larger session",
        fixture_size="80 of 120 turn metric rows",
        budget_bytes=120_000,
        guidance=(
            "If this regresses, summarize metrics for dashboard overviews and keep "
            "raw metric rows behind explicit detail loading."
        ),
    ),
    PayloadSizeBudget(
        surface="session artifact page payload",
        scenario="serialize one paginated artifact window for a larger session",
        fixture_size="40 event-referenced artifacts",
        budget_bytes=120_000,
        guidance=(
            "If this regresses, separate artifact summaries from file inspection "
            "metadata and keep artifact detail panes on demand."
        ),
    ),
    PayloadSizeBudget(
        surface="repository intelligence overview payload",
        scenario=(
            "serialize dashboard repository map data without raw entries or "
            "source inputs"
        ),
        fixture_size="2,050 source files plus manifests",
        budget_bytes=250_000,
        guidance=(
            "If this regresses, keep full entry search paginated and avoid "
            "attaching source_inputs, raw file contents, or full artifacts to the "
            "dashboard overview route."
        ),
    ),
)


def format_performance_budgets() -> str:
    lines = ["Glassbox performance budgets"]
    for budget in PERFORMANCE_BUDGETS:
        lines.extend(
            [
                f"- {budget.surface}: {budget.budget_ms} ms",
                f"  Scenario: {budget.scenario}",
                f"  Fixture: {budget.fixture_size}",
                f"  Guidance: {budget.guidance}",
            ]
        )
    lines.append("Glassbox payload size budgets")
    for budget in PAYLOAD_SIZE_BUDGETS:
        lines.extend(
            [
                f"- {budget.surface}: {budget.budget_bytes} bytes",
                f"  Scenario: {budget.scenario}",
                f"  Fixture: {budget.fixture_size}",
                f"  Guidance: {budget.guidance}",
            ]
        )
    return "\n".join(lines)
