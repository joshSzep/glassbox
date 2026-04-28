"""Deterministic larger-session fixtures for v7 scale characterization."""

import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from glassbox.core.events import AssistantMessageCompleted
from glassbox.core.events import EventEnvelope
from glassbox.core.events import ModelCallCompleted
from glassbox.core.events import SessionStarted
from glassbox.core.events import ToolArtifactRecorded
from glassbox.core.events import ToolExecutionCompleted
from glassbox.core.events import ToolExecutionStarted
from glassbox.core.events import TurnCompleted
from glassbox.core.events import TurnStarted
from glassbox.core.events import UserMessageReceived
from glassbox.core.ids import SessionId
from glassbox.core.ids import new_artifact_id
from glassbox.core.ids import new_message_id
from glassbox.core.ids import new_session_id
from glassbox.core.ids import new_tool_call_id
from glassbox.core.ids import new_turn_id
from glassbox.core.models import MessagePart
from glassbox.store.sqlite import append_events


@dataclass(frozen=True, slots=True)
class LargeSessionFixtureConfig:
    turn_count: int = 120
    tool_call_count: int = 80
    artifact_count: int = 40
    message_words: int = 24


@dataclass(frozen=True, slots=True)
class LargeSessionFixture:
    session_id: SessionId
    event_count: int
    transcript_message_count: int
    tool_call_count: int
    artifact_count: int


def append_large_session_fixture(
    connection: sqlite3.Connection,
    workspace_root: Path,
    *,
    config: LargeSessionFixtureConfig | None = None,
) -> LargeSessionFixture:
    """Append a provider-free larger session with mixed transcript and artifacts."""

    effective_config = config or LargeSessionFixtureConfig()
    _prepare_workspace(workspace_root)
    session_id = new_session_id()
    artifact_root = workspace_root / ".glassbox" / "sessions" / str(session_id)
    artifact_root = artifact_root / "artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)

    events: list[EventEnvelope] = [
        EventEnvelope(
            session_id=session_id,
            sequence=0,
            payload=SessionStarted(
                cwd=str(workspace_root),
                model_name="openai:gpt-5.4",
                approval_mode="confirm",
            ),
        )
    ]
    artifact_index = 0
    for turn_index in range(effective_config.turn_count):
        turn_id = new_turn_id()
        user_message_id = new_message_id()
        events.extend(
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=UserMessageReceived(
                        message_id=user_message_id,
                        text=_message_text("user", turn_index, effective_config),
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TurnStarted(
                        turn_id=turn_id,
                        trigger_message_id=user_message_id,
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ModelCallCompleted(
                        turn_id=turn_id,
                        input_tokens=120 + turn_index,
                        output_tokens=48 + turn_index,
                        duration_ms=35 + (turn_index % 8),
                    ),
                ),
            ]
        )

        if turn_index < effective_config.tool_call_count:
            tool_call_id = new_tool_call_id()
            events.append(
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ToolExecutionStarted(
                        turn_id=turn_id,
                        tool_call_id=tool_call_id,
                        tool_name="read_file",
                        policy_outcome="allow",
                        policy_risk_level="read_only",
                        policy_source_kind="invariant",
                        policy_source_label="fixture-policy",
                        policy_reason="deterministic read-only fixture tool",
                    ),
                )
            )
            if artifact_index < effective_config.artifact_count:
                artifact_path, artifact_sha256, artifact_size = _write_artifact(
                    artifact_root,
                    session_id=session_id,
                    artifact_index=artifact_index,
                )
                events.append(
                    EventEnvelope(
                        session_id=session_id,
                        sequence=0,
                        payload=ToolArtifactRecorded(
                            turn_id=turn_id,
                            tool_call_id=tool_call_id,
                            artifact_id=new_artifact_id(),
                            artifact_kind="fixture-output",
                            path=artifact_path.as_posix(),
                            content_sha256=artifact_sha256,
                            size_bytes=artifact_size,
                        ),
                    )
                )
                artifact_index += 1
            events.append(
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=ToolExecutionCompleted(
                        turn_id=turn_id,
                        tool_call_id=tool_call_id,
                        success=True,
                        exit_code=0,
                        summary=f"read fixture artifact {turn_index}",
                    ),
                )
            )

        events.extend(
            [
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=AssistantMessageCompleted(
                        message_id=new_message_id(),
                        parts=[
                            MessagePart(
                                kind="text",
                                text=_message_text(
                                    "assistant",
                                    turn_index,
                                    effective_config,
                                ),
                            )
                        ],
                    ),
                ),
                EventEnvelope(
                    session_id=session_id,
                    sequence=0,
                    payload=TurnCompleted(turn_id=turn_id, outcome="completed"),
                ),
            ]
        )

    append_events(connection, events)
    return LargeSessionFixture(
        session_id=session_id,
        event_count=len(events),
        transcript_message_count=effective_config.turn_count * 2,
        tool_call_count=effective_config.tool_call_count,
        artifact_count=effective_config.artifact_count,
    )


def _prepare_workspace(workspace_root: Path) -> None:
    (workspace_root / "src").mkdir(exist_ok=True)
    (workspace_root / "docs").mkdir(exist_ok=True)
    (workspace_root / "README.md").write_text(
        "# Larger Session Fixture\n",
        encoding="utf-8",
    )


def _message_text(
    role: str,
    turn_index: int,
    config: LargeSessionFixtureConfig,
) -> str:
    words = [
        f"{role}-{turn_index}-{word_index}"
        for word_index in range(config.message_words)
    ]
    return " ".join(words)


def _write_artifact(
    artifact_root: Path,
    *,
    session_id: SessionId,
    artifact_index: int,
) -> tuple[Path, str, int]:
    relative_path = (
        Path(".glassbox")
        / "sessions"
        / str(session_id)
        / "artifacts"
        / f"fixture-artifact-{artifact_index:03d}.txt"
    )
    artifact_path = artifact_root / relative_path.name
    content = (
        f"artifact {artifact_index}\nsession {session_id}\npayload {'x' * 256}\n"
    ).encode()
    artifact_path.write_bytes(content)
    return relative_path, hashlib.sha256(content).hexdigest(), len(content)
