"""Shared constants, type aliases, and helpers for replay-backed evals."""

import re
from pathlib import Path
from typing import Literal

EVAL_CASE_MANIFEST_VERSION = 1
EVAL_PROFILE_MANIFEST_VERSION = 1
DEFAULT_EVALS_ROOT = Path("evals")
DEFAULT_EVAL_CASES_DIR = DEFAULT_EVALS_ROOT / "cases"
DEFAULT_EVAL_BUNDLES_DIR = DEFAULT_EVALS_ROOT / "bundles"
DEFAULT_EVAL_PROFILES_PATH = DEFAULT_EVALS_ROOT / "profiles.json"

type EvalInvariant = Literal[
    "transcript",
    "tool_calls",
    "approvals",
    "questions",
    "event_families",
    "final_state",
]
type EvalCaseSeverity = Literal["critical", "high", "medium", "low"]
type EvalVerificationStage = Literal[
    "commit-time",
    "push-time",
    "release-candidate",
    "advisory",
]
type EvalProfileTrack = Literal["deterministic", "live-provider-canary"]
type EvalBaselineRefreshPolicy = Literal[
    "review_required",
    "intentional_only",
    "advisory",
]
type EvalBaselineOperation = Literal["promote", "refresh"]

IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
ALL_EVAL_INVARIANTS: tuple[EvalInvariant, ...] = (
    "transcript",
    "tool_calls",
    "approvals",
    "questions",
    "event_families",
    "final_state",
)


def default_verification_stages() -> list[EvalVerificationStage]:
    return ["advisory"]


def normalize_identifier(value: str, *, kind: str) -> str:
    normalized = value.strip().lower()
    if not normalized:
        raise ValueError(f"{kind} must not be empty")
    if not IDENTIFIER_PATTERN.fullmatch(normalized):
        raise ValueError(f"{kind} must match {IDENTIFIER_PATTERN.pattern}: {value!r}")
    return normalized


def ensure_path_within_root(path: Path, root: Path, *, kind: str) -> None:
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{kind} must stay within workspace root: {path}") from exc


_normalize_identifier = normalize_identifier
_ensure_path_within_root = ensure_path_within_root
