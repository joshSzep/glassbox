"""Repository-owned tool policy manifest models and loading helpers."""

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator

TOOL_POLICY_MANIFEST_VERSION = 1
DEFAULT_TOOL_POLICY_PATH = Path("glassbox-policy.json")

type ToolPolicyAction = Literal["allow", "approve", "deny"]
type ToolAutonomyPolicyAction = Literal[
    "allow-with-budget",
    "require-approval",
    "deny",
    "require-verification",
]
type ToolPolicyRiskBucket = Literal["read_only", "workspace_write", "command"]

_RULE_IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")


class ToolPolicyDefaults(BaseModel):
    """Default policy actions used when no workspace rule matches."""

    model_config = ConfigDict(extra="forbid")

    read_only: ToolPolicyAction = "allow"
    workspace_write: ToolPolicyAction = "approve"
    command: ToolPolicyAction = "approve"


class ToolPolicyRule(BaseModel):
    """One repository-owned rule that refines the baseline tool policy."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str | None = None
    tool_name: str
    action: ToolPolicyAction
    command_prefixes: list[str] = Field(default_factory=list)
    cwd_prefixes: list[str] = Field(default_factory=list)
    path_prefixes: list[str] = Field(default_factory=list)

    @field_validator("rule_id")
    @classmethod
    def validate_rule_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("rule_id must not be blank")
        if _RULE_IDENTIFIER_PATTERN.fullmatch(normalized) is None:
            raise ValueError(
                "rule_id must contain only lowercase letters, digits, dots, "
                "underscores, or hyphens"
            )
        return normalized

    @field_validator("tool_name")
    @classmethod
    def validate_tool_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("tool_name must not be blank")
        return normalized

    @field_validator("command_prefixes", "cwd_prefixes", "path_prefixes")
    @classmethod
    def validate_prefixes(cls, value: list[str]) -> list[str]:
        return _normalize_nonblank_values(value, kind="policy prefixes")


class ToolAutonomyRule(BaseModel):
    """Repository-owned selector for budgeted local autonomy."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str
    action: ToolAutonomyPolicyAction
    tool_name: str | None = None
    risk_buckets: list[ToolPolicyRiskBucket] = Field(default_factory=list)
    command_prefixes: list[str] = Field(default_factory=list)
    cwd_prefixes: list[str] = Field(default_factory=list)
    path_prefixes: list[str] = Field(default_factory=list)
    file_extensions: list[str] = Field(default_factory=list)
    test_path_prefixes: list[str] = Field(default_factory=list)
    generated_path_prefixes: list[str] = Field(default_factory=list)
    read_only_operation: bool | None = None
    max_timeout_seconds: int | None = Field(default=None, ge=1, le=300)

    @field_validator("rule_id")
    @classmethod
    def validate_rule_id(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("autonomy rule_id must not be blank")
        if _RULE_IDENTIFIER_PATTERN.fullmatch(normalized) is None:
            raise ValueError(
                "autonomy rule_id must contain only lowercase letters, digits, "
                "dots, underscores, or hyphens"
            )
        return normalized

    @field_validator("tool_name")
    @classmethod
    def validate_tool_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("autonomy tool_name must not be blank")
        return normalized

    @field_validator(
        "command_prefixes",
        "cwd_prefixes",
        "path_prefixes",
        "test_path_prefixes",
        "generated_path_prefixes",
    )
    @classmethod
    def validate_prefixes(cls, value: list[str]) -> list[str]:
        return _normalize_nonblank_values(value, kind="autonomy policy prefixes")

    @field_validator("risk_buckets")
    @classmethod
    def validate_risk_buckets(
        cls,
        value: list[ToolPolicyRiskBucket],
    ) -> list[ToolPolicyRiskBucket]:
        return list(dict.fromkeys(value))

    @field_validator("file_extensions")
    @classmethod
    def validate_file_extensions(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for extension in value:
            candidate = extension.strip().lower()
            if not candidate:
                raise ValueError("file_extensions must not contain blank values")
            if not candidate.startswith("."):
                candidate = f".{candidate}"
            if candidate not in normalized:
                normalized.append(candidate)
        return normalized


class ToolPolicyManifest(BaseModel):
    """Versioned workspace-owned tool policy manifest."""

    model_config = ConfigDict(extra="forbid")

    manifest_version: int = TOOL_POLICY_MANIFEST_VERSION
    defaults: ToolPolicyDefaults = Field(default_factory=ToolPolicyDefaults)
    rules: list[ToolPolicyRule] = Field(default_factory=list)
    autonomy_rules: list[ToolAutonomyRule] = Field(default_factory=list)

    @field_validator("manifest_version")
    @classmethod
    def validate_manifest_version(cls, value: int) -> int:
        if value != TOOL_POLICY_MANIFEST_VERSION:
            raise ValueError(f"unsupported tool policy manifest version: {value}")
        return value

    @field_validator("rules")
    @classmethod
    def validate_rule_ids(cls, value: list[ToolPolicyRule]) -> list[ToolPolicyRule]:
        seen_rule_ids: set[str] = set()
        for rule in value:
            if rule.rule_id is None:
                continue
            if rule.rule_id in seen_rule_ids:
                raise ValueError(f"duplicate tool policy rule_id: {rule.rule_id}")
            seen_rule_ids.add(rule.rule_id)
        return value

    @field_validator("autonomy_rules")
    @classmethod
    def validate_autonomy_rule_ids(
        cls,
        value: list[ToolAutonomyRule],
    ) -> list[ToolAutonomyRule]:
        seen_rule_ids: set[str] = set()
        for rule in value:
            if rule.rule_id in seen_rule_ids:
                raise ValueError(f"duplicate autonomy rule_id: {rule.rule_id}")
            seen_rule_ids.add(rule.rule_id)
        return value


def _normalize_nonblank_values(value: list[str], *, kind: str) -> list[str]:
    normalized: list[str] = []
    for raw_value in value:
        candidate = raw_value.strip()
        if not candidate:
            raise ValueError(f"{kind} must not be blank")
        if candidate not in normalized:
            normalized.append(candidate)
    return normalized


def load_tool_policy_manifest(
    workspace_root: Path,
    *,
    policy_path: Path | None = None,
) -> ToolPolicyManifest:
    """Load the repository-local tool policy manifest from disk."""

    resolved_workspace_root = workspace_root.resolve()
    resolved_policy_path = _resolve_policy_path(
        resolved_workspace_root,
        policy_path=policy_path,
    )
    _ensure_path_within_root(
        resolved_policy_path,
        resolved_workspace_root,
        kind="tool policy manifest",
    )
    if not resolved_policy_path.exists():
        return ToolPolicyManifest()

    try:
        raw_manifest = resolved_policy_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(
            f"unable to read tool policy manifest {resolved_policy_path}: {exc}"
        ) from exc

    try:
        manifest = ToolPolicyManifest.model_validate_json(raw_manifest)
    except ValueError as exc:
        raise ValueError(
            f"invalid tool policy manifest {resolved_policy_path}: {exc}"
        ) from exc

    _ensure_rule_prefixes_within_root(
        manifest,
        workspace_root=resolved_workspace_root,
        policy_path=resolved_policy_path,
    )
    return manifest


def _resolve_policy_path(workspace_root: Path, *, policy_path: Path | None) -> Path:
    if policy_path is None:
        return (workspace_root / DEFAULT_TOOL_POLICY_PATH).resolve()
    if policy_path.is_absolute():
        return policy_path.resolve()
    return (workspace_root / policy_path).resolve()


def _ensure_path_within_root(
    candidate: Path, workspace_root: Path, *, kind: str
) -> None:
    try:
        candidate.relative_to(workspace_root)
    except ValueError as exc:
        raise ValueError(f"{kind} is outside workspace root: {candidate}") from exc


def _ensure_rule_prefixes_within_root(
    manifest: ToolPolicyManifest,
    *,
    workspace_root: Path,
    policy_path: Path,
) -> None:
    policy_rules = [*manifest.rules, *manifest.autonomy_rules]
    for rule in policy_rules:
        prefixes = [*rule.cwd_prefixes, *rule.path_prefixes]
        if isinstance(rule, ToolAutonomyRule):
            prefixes.extend(rule.test_path_prefixes)
            prefixes.extend(rule.generated_path_prefixes)
        for prefix in prefixes:
            candidate = Path(prefix)
            if candidate.is_absolute():
                raise ValueError(
                    f"invalid tool policy manifest {policy_path}: "
                    f"workspace policy prefixes must be relative paths: {prefix}"
                )
            _ensure_path_within_root(
                (workspace_root / candidate).resolve(),
                workspace_root,
                kind=f"tool policy prefix '{prefix}'",
            )
