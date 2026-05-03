"""Shared command-risk pattern catalog for tool policy."""

import re

DESTRUCTIVE_COMMAND_PATTERNS = (
    re.compile(r"(^|\s)rm\s+-[A-Za-z-]*[rf][A-Za-z-]*\b"),
    re.compile(r"(^|\s)git\s+clean\b[^\n]*\s-f\b"),
    re.compile(r"(^|\s)git\s+reset\s+--hard\b"),
    re.compile(r"(^|\s)(mkfs|shutdown|reboot|poweroff)\b"),
)

PUBLISH_COMMAND_PATTERNS = (
    re.compile(r"(^|\s)(npm|pnpm|yarn)\s+publish\b"),
    re.compile(r"(^|\s)twine\s+upload\b"),
    re.compile(r"(^|\s)uv\s+publish\b"),
    re.compile(r"(^|\s)cargo\s+publish\b"),
    re.compile(r"(^|\s)gh\s+release\s+(create|delete|upload)\b"),
)

DEPLOY_COMMAND_PATTERNS = (
    re.compile(r"(^|\s)(vercel|netlify|fly)\s+deploy\b"),
    re.compile(r"(^|\s)kubectl\s+(apply|delete|replace|rollout)\b"),
    re.compile(r"(^|\s)terraform\s+(apply|destroy)\b"),
)

REMOTE_GIT_MUTATION_PATTERNS = (
    re.compile(r"(^|\s)git\s+push\b"),
    re.compile(r"(^|\s)git\s+rebase\b"),
    re.compile(r"(^|\s)git\s+filter-branch\b"),
)

DRY_RUN_FLAGS = (" --dry-run ", " --preview ")

__all__ = [
    "DEPLOY_COMMAND_PATTERNS",
    "DESTRUCTIVE_COMMAND_PATTERNS",
    "DRY_RUN_FLAGS",
    "PUBLISH_COMMAND_PATTERNS",
    "REMOTE_GIT_MUTATION_PATTERNS",
]
