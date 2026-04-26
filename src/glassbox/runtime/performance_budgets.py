"""Repository-owned performance budgets for larger local workspaces."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PerformanceBudget:
    surface: str
    scenario: str
    fixture_size: str
    budget_ms: int
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
    return "\n".join(lines)
