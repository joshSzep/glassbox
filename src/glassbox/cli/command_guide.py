"""Workflow-oriented command discovery for Glassbox operators."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CommandGuideEntry:
    command: str
    purpose: str

    def to_json_payload(self) -> dict[str, str]:
        return {"command": self.command, "purpose": self.purpose}


@dataclass(frozen=True)
class CommandGuideSection:
    key: str
    title: str
    summary: str
    entries: tuple[CommandGuideEntry, ...]

    def to_json_payload(self) -> dict[str, object]:
        return {
            "key": self.key,
            "title": self.title,
            "summary": self.summary,
            "commands": [entry.to_json_payload() for entry in self.entries],
        }


COMMAND_GUIDE_SECTIONS: tuple[CommandGuideSection, ...] = (
    CommandGuideSection(
        key="start-work",
        title="Start Work",
        summary="Prepare a workspace and begin a local operator session.",
        entries=(
            CommandGuideEntry(
                "glassbox readiness check --cwd .",
                "Check first-run workspace readiness and get next actions.",
            ),
            CommandGuideEntry(
                "glassbox session chat --cwd .",
                "Start the default terminal session with dashboard handoff.",
            ),
            CommandGuideEntry(
                'glassbox session run "Inspect the repository" --cwd .',
                "Run a one-shot session when an interactive shell is unnecessary.",
            ),
            CommandGuideEntry(
                "glassbox dashboard serve --cwd .",
                "Serve the packaged dashboard when no chat process is hosting it.",
            ),
        ),
    ),
    CommandGuideSection(
        key="inspect-state",
        title="Inspect State",
        summary=(
            "Read sessions, tasks, memory, repository intelligence, and runtime "
            "posture."
        ),
        entries=(
            CommandGuideEntry(
                "glassbox session list --cwd .",
                "List persisted sessions in the workspace.",
            ),
            CommandGuideEntry(
                "glassbox session status SESSION_ID --cwd .",
                (
                    "Inspect one session's transcript, actions, evidence, and "
                    "runtime state."
                ),
            ),
            CommandGuideEntry(
                "glassbox task list --cwd .",
                "List durable task plans and their next actions.",
            ),
            CommandGuideEntry(
                "glassbox task show TASK_ID --cwd .",
                "Inspect task plan steps, budget posture, stop reasons, and evidence.",
            ),
            CommandGuideEntry(
                "glassbox memory list --cwd .",
                "Review confirmed and invalidated workspace memory.",
            ),
            CommandGuideEntry(
                "glassbox repo index status --cwd .",
                "Inspect rebuildable repository intelligence freshness.",
            ),
            CommandGuideEntry(
                "glassbox provider diagnostics --cwd .",
                "Inspect optional provider configuration without printing secrets.",
            ),
            CommandGuideEntry(
                "glassbox observability status --cwd .",
                "Summarize runtime, projection, and verification health.",
            ),
        ),
    ),
    CommandGuideSection(
        key="unblock-work",
        title="Unblock Work",
        summary="Resolve pending operator decisions and bounded continuation points.",
        entries=(
            CommandGuideEntry(
                "glassbox session answer SESSION_ID QUESTION_ID ANSWER --cwd .",
                "Answer a pending operator question.",
            ),
            CommandGuideEntry(
                "glassbox session approve SESSION_ID APPROVAL_ID --cwd .",
                "Approve a pending action after reviewing policy evidence.",
            ),
            CommandGuideEntry(
                "glassbox session deny SESSION_ID APPROVAL_ID --cwd .",
                "Deny a pending action and retain the decision.",
            ),
            CommandGuideEntry(
                "glassbox session cancel SESSION_ID --cwd .",
                "Request cancellation for an active turn.",
            ),
            CommandGuideEntry(
                "glassbox session message SESSION_ID PROMPT --cwd .",
                "Continue an existing session with a new prompt.",
            ),
            CommandGuideEntry(
                "glassbox task continue TASK_ID --cwd .",
                "Enqueue a bounded background continuation job for a task.",
            ),
        ),
    ),
    CommandGuideSection(
        key="verify-work",
        title="Verify Work",
        summary="Choose and run deterministic checks for local changes.",
        entries=(
            CommandGuideEntry(
                "glassbox eval recommend PATH --cwd .",
                "Ask Glassbox which replay or eval checks fit changed paths.",
            ),
            CommandGuideEntry(
                "glassbox eval run --profile commit-smoke --cwd .",
                "Run the cheap deterministic commit-time eval profile.",
            ),
            CommandGuideEntry(
                "glassbox replay run SESSION_ID --cwd .",
                "Replay a recorded session offline.",
            ),
            CommandGuideEntry(
                "glassbox eval audit --cwd .",
                "Audit capability coverage for the selected eval portfolio.",
            ),
        ),
    ),
    CommandGuideSection(
        key="recover-workspace",
        title="Recover Workspace",
        summary=(
            "Diagnose local runtime, projection, artifact, backup, and job problems."
        ),
        entries=(
            CommandGuideEntry(
                "glassbox daemon status --cwd .",
                "Inspect the workspace daemon and local mutation owner.",
            ),
            CommandGuideEntry(
                "glassbox job list --cwd .",
                "List daemon-owned background jobs and retryable failures.",
            ),
            CommandGuideEntry(
                "glassbox projection check --all --cwd .",
                "Inspect derived projection health without rebuilding.",
            ),
            CommandGuideEntry(
                "glassbox artifacts inspect --cwd .",
                "Inspect managed artifact state before pruning.",
            ),
            CommandGuideEntry(
                "glassbox backup create --cwd .",
                "Create a local workspace backup before risky maintenance.",
            ),
            CommandGuideEntry(
                "glassbox repo index build --cwd .",
                "Refresh rebuildable repository intelligence explicitly.",
            ),
        ),
    ),
    CommandGuideSection(
        key="release-evidence",
        title="Release Evidence",
        summary=(
            "Generate retained deterministic, package, and advisory evidence "
            "for reviewers."
        ),
        entries=(
            CommandGuideEntry(
                "glassbox command tree",
                "Print the exhaustive structural command surface.",
            ),
            CommandGuideEntry(
                (
                    "glassbox eval report commit-smoke push-confirmation "
                    "release-candidate --cwd ."
                ),
                "Generate deterministic release sign-off evidence from eval profiles.",
            ),
            CommandGuideEntry(
                "glassbox provider canary evidence --cwd .",
                "Inspect retained advisory provider canary evidence.",
            ),
            CommandGuideEntry(
                "python scripts/validate_package_contents.py",
                "Validate package contents before release publication.",
            ),
        ),
    ),
)


def command_guide_json_payload() -> dict[str, object]:
    """Return a stable JSON payload for workflow command discovery."""

    return {
        "schema_version": 1,
        "sections": [section.to_json_payload() for section in COMMAND_GUIDE_SECTIONS],
    }


def format_command_guide() -> str:
    """Format the workflow command guide for terminal output."""

    lines = [
        "Glassbox command guide",
        "Workflow-oriented discovery for common operator tasks.",
        "",
    ]
    for section in COMMAND_GUIDE_SECTIONS:
        lines.append(section.title)
        lines.append(f"  {section.summary}")
        for entry in section.entries:
            lines.append(f"  - {entry.command}")
            lines.append(f"    {entry.purpose}")
        lines.append("")
    lines.append(
        "Use `glassbox command tree` for the exhaustive structural command surface."
    )
    return "\n".join(lines)


__all__ = [
    "COMMAND_GUIDE_SECTIONS",
    "command_guide_json_payload",
    "format_command_guide",
]
