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
