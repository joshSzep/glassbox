"""Replay bundle loading and export helpers."""

import json
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from glassbox.core.events import ApprovalResolved
from glassbox.core.events import AssistantMessageCompleted
from glassbox.core.events import AssistantMessageDelta
from glassbox.core.events import EventEnvelope
from glassbox.core.events import ModelCallCompleted
from glassbox.core.events import ModelCallStarted
from glassbox.core.events import ModelToolCallRequested
from glassbox.core.events import ReplayArtifactRecorded
from glassbox.core.events import RuntimeNoteImported
from glassbox.core.events import RuntimeNoteRecorded
from glassbox.core.events import TranscriptMessageImported
from glassbox.core.events import TurnCompleted
from glassbox.core.events import TurnFailed
from glassbox.core.events import UserAnswerProvided
from glassbox.core.events import UserMessageReceived
from glassbox.core.ids import SessionId
from glassbox.core.models import InheritedTranscriptMessage
from glassbox.core.models import ResolvedForkPoint
from glassbox.core.models import RuntimeNoteRecord
from glassbox.core.models import SessionConfig
from glassbox.core.models import SessionRecord
from glassbox.runtime.replay_compare import normalize_session
from glassbox.runtime.replay_failures import ReplayFailure
from glassbox.runtime.replay_failures import ReplayUnsupportedSession
from glassbox.runtime.replay_manifests import ReplayModelCallManifest
from glassbox.runtime.replay_manifests import ReplayToolRequestManifest
from glassbox.runtime.replay_manifests import ReplayToolResultManifest
from glassbox.runtime.replay_manifests import ReplayTurnOutputManifest
from glassbox.runtime.replay_manifests import load_replay_manifest
from glassbox.runtime.replay_models import REPLAY_BUNDLE_VERSION
from glassbox.runtime.replay_models import ReplayAction
from glassbox.runtime.replay_models import ReplayBundle
from glassbox.runtime.replay_models import ReplayRecordedModelCall
from glassbox.runtime.replay_models import ReplayRecordedToolCall
from glassbox.services import ArtifactRepository
from glassbox.services import SessionRepository
from glassbox.store.repositories import SQLiteSessionRepository


class ReplayBundleStore:
    """Load replay bundles from persisted sessions or serialized bundle files."""

    def __init__(
        self,
        session_repository: SessionRepository | None = None,
        artifact_repository: ArtifactRepository | None = None,
    ) -> None:
        self._session_repository = session_repository
        self._artifact_repository = artifact_repository

    def load_session_bundle(self, session_id: SessionId) -> ReplayBundle:
        session_repository, _artifact_repository = self._require_recorded_repositories()

        source_session = session_repository.get_session(session_id)
        if source_session is None:
            raise ValueError(f"unknown session_id: {session_id}")

        source_events = session_repository.read_session_events(session_id)
        replay_payloads = [
            event.payload
            for event in source_events
            if isinstance(event.payload, ReplayArtifactRecorded)
        ]
        if not replay_payloads:
            raise ReplayFailure("session does not contain replay artifacts")

        manifests = [self._load_manifest(payload) for payload in replay_payloads]
        model_calls = [
            manifest
            for manifest in manifests
            if isinstance(manifest, ReplayModelCallManifest)
        ]
        tool_requests = [
            manifest
            for manifest in manifests
            if isinstance(manifest, ReplayToolRequestManifest)
        ]
        tool_results = [
            manifest
            for manifest in manifests
            if isinstance(manifest, ReplayToolResultManifest)
        ]
        turn_outputs = [
            manifest
            for manifest in manifests
            if isinstance(manifest, ReplayTurnOutputManifest)
        ]
        has_cancelled_turn = any(
            output.outcome == "cancelled" for output in turn_outputs
        )
        if not model_calls and not has_cancelled_turn:
            raise ReplayFailure("session does not contain replay model call manifests")

        return ReplayBundle(
            source_session_id=session_id,
            session_config=build_replay_bundle_session_config(source_session),
            inherited_messages=build_inherited_messages(source_events),
            inherited_runtime_notes=build_inherited_runtime_notes(
                session_id,
                source_session,
                source_events,
                session_repository,
            ),
            actions=build_replay_actions(source_events),
            model_calls=build_recorded_model_calls(
                source_events,
                model_calls,
                tool_requests,
                allow_cancelled_incomplete=has_cancelled_turn,
            ),
            tool_requests=tool_requests,
            tool_results=tool_results,
            turn_outputs=turn_outputs,
            baseline=normalize_session(
                session_id,
                session_repository,
                source_events,
            ),
        )

    def export_session_bundle(
        self,
        session_id: SessionId,
        output_path: Path,
    ) -> Path:
        bundle = self.load_session_bundle(session_id)
        resolved_output = output_path.resolve()
        resolved_output.parent.mkdir(parents=True, exist_ok=True)
        serialized_bundle = json.dumps(
            bundle.model_dump(mode="json", exclude_none=True),
            indent=2,
            sort_keys=True,
        )
        resolved_output.write_text(f"{serialized_bundle}\n", encoding="utf-8")
        return resolved_output

    def load_bundle_file(self, bundle_path: Path) -> ReplayBundle:
        resolved_path = bundle_path.resolve()
        try:
            raw_bundle = resolved_path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise ReplayFailure(f"missing replay bundle file: {resolved_path}") from exc

        try:
            bundle = ReplayBundle.model_validate_json(raw_bundle)
        except ValueError as exc:
            raise ReplayFailure(
                f"invalid replay bundle file {resolved_path}: {exc}"
            ) from exc

        if bundle.bundle_version != REPLAY_BUNDLE_VERSION:
            raise ReplayUnsupportedSession(
                f"unsupported replay bundle version: {bundle.bundle_version}"
            )
        return bundle

    def _load_manifest(self, payload: ReplayArtifactRecorded):
        _, artifact_repository = self._require_recorded_repositories()

        if payload.path is None:
            raise ReplayFailure("replay artifact event is missing its path")

        try:
            raw_manifest = artifact_repository.read_text_artifact(Path(payload.path))
        except FileNotFoundError as exc:
            raise ReplayFailure(
                f"missing replay artifact for path: {payload.path}"
            ) from exc

        try:
            manifest = load_replay_manifest(raw_manifest)
        except ValueError as exc:
            raise ReplayFailure(
                f"invalid replay artifact for path {payload.path}: {exc}"
            ) from exc

        if getattr(manifest, "manifest_version", 1) != 1:
            raise ReplayUnsupportedSession(
                "unsupported replay manifest version: "
                f"{getattr(manifest, 'manifest_version', None)}"
            )
        return manifest

    def _require_recorded_repositories(
        self,
    ) -> tuple[SessionRepository, ArtifactRepository]:
        if self._session_repository is None or self._artifact_repository is None:
            raise ValueError(
                "session and artifact repositories are required for session-based "
                "replay operations"
            )
        return self._session_repository, self._artifact_repository


def build_replay_actions(events: Sequence[EventEnvelope]) -> list[ReplayAction]:
    actions: list[ReplayAction] = []
    for event in events:
        payload = event.payload
        if isinstance(payload, UserMessageReceived):
            actions.append(ReplayAction(action_type="user_message", text=payload.text))
        elif isinstance(payload, RuntimeNoteRecorded):
            actions.append(
                ReplayAction(
                    action_type="runtime_note",
                    category=payload.category,
                    message=payload.message,
                )
            )
        elif isinstance(payload, ApprovalResolved):
            actions.append(
                ReplayAction(
                    action_type="approval",
                    decision=payload.decision,
                )
            )
        elif isinstance(payload, UserAnswerProvided):
            actions.append(
                ReplayAction(
                    action_type="user_answer",
                    answer=payload.answer,
                )
            )
    return actions


def build_replay_bundle_session_config(source_session: SessionRecord) -> SessionConfig:
    return SessionConfig(
        model_name=source_session.model_name,
        cwd=source_session.cwd,
        approval_mode=source_session.approval_mode,
        parent_session_id=source_session.parent_session_id,
        forked_from_turn_id=source_session.forked_from_turn_id,
        forked_from_sequence=source_session.forked_from_sequence,
        branch_label=source_session.branch_label,
    )


def build_inherited_messages(
    events: Sequence[EventEnvelope],
) -> list[InheritedTranscriptMessage]:
    inherited_messages = [
        InheritedTranscriptMessage(
            source_message_id=payload.source_message_id,
            source_turn_id=payload.source_turn_id,
            role=payload.role,
            parts=payload.parts,
            created_at=payload.source_created_at,
        )
        for event in events
        if isinstance((payload := event.payload), TranscriptMessageImported)
    ]
    inherited_messages.sort(
        key=lambda message: (message.created_at, str(message.source_message_id))
    )
    return inherited_messages


def build_inherited_runtime_notes(
    session_id: SessionId,
    source_session: SessionRecord,
    events: Sequence[EventEnvelope],
    session_repository: SessionRepository,
) -> list[RuntimeNoteRecord]:
    imported_notes = [
        RuntimeNoteRecord(
            source_session_id=payload.source_session_id,
            source_sequence=payload.source_sequence,
            category=payload.category,
            message=payload.message,
            created_at=payload.source_created_at,
            inherited=True,
        )
        for event in events
        if isinstance((payload := event.payload), RuntimeNoteImported)
    ]
    if imported_notes or source_session.parent_session_id is None:
        return imported_notes

    return [
        note
        for note in session_repository.list_runtime_notes(session_id)
        if note.inherited
    ]


def build_replay_import_events(
    bundle: ReplayBundle,
    repository: SQLiteSessionRepository,
    session_id: SessionId,
) -> list[EventEnvelope]:
    if not bundle.inherited_messages:
        return []

    parent_session_id = bundle.session_config.parent_session_id
    forked_from_turn_id = bundle.session_config.forked_from_turn_id
    forked_from_sequence = bundle.session_config.forked_from_sequence
    if (
        parent_session_id is None
        or forked_from_turn_id is None
        or forked_from_sequence is None
    ):
        raise ReplayUnsupportedSession(
            "forked replay bundle is missing lineage metadata for inherited transcript"
        )

    return repository.build_imported_transcript_events(
        session_id,
        ResolvedForkPoint(
            parent_session_id=parent_session_id,
            turn_id=forked_from_turn_id,
            sequence=forked_from_sequence,
            inherited_messages=list(bundle.inherited_messages),
        ),
    )


def build_replay_runtime_note_import_events(
    bundle: ReplayBundle,
    session_id: SessionId,
) -> list[EventEnvelope]:
    return [
        EventEnvelope(
            session_id=session_id,
            sequence=0,
            payload=RuntimeNoteImported(
                source_session_id=note.source_session_id,
                source_sequence=note.source_sequence,
                category=note.category,
                message=note.message,
                source_created_at=note.created_at,
            ),
        )
        for note in bundle.inherited_runtime_notes
    ]


def build_recorded_model_calls(
    events: Sequence[EventEnvelope],
    model_call_manifests: Sequence[ReplayModelCallManifest],
    tool_request_manifests: Sequence[ReplayToolRequestManifest],
    *,
    allow_cancelled_incomplete: bool = False,
) -> list[ReplayRecordedModelCall]:
    model_start_indexes = [
        index
        for index, event in enumerate(events)
        if isinstance(event.payload, ModelCallStarted)
    ]
    if len(model_start_indexes) != len(model_call_manifests):
        raise ReplayFailure(
            "recorded model call manifests do not match the session event count"
        )

    recorded_calls: list[ReplayRecordedModelCall] = []
    tool_request_index = 0
    for model_index, start_index in enumerate(model_start_indexes):
        completed = find_model_call_completed_event(
            events,
            start_index=start_index,
            allow_missing=allow_cancelled_incomplete,
        )
        if completed is None:
            recorded_calls.append(
                ReplayRecordedModelCall(manifest=model_call_manifests[model_index])
            )
            continue
        completed_index, completed_payload = completed
        text_deltas = [
            event.payload.delta
            for event in events[start_index:completed_index]
            if isinstance(event.payload, AssistantMessageDelta)
        ]
        assistant_text: str | None = None
        tool_calls: list[ReplayRecordedToolCall] = []

        lookahead_index = completed_index + 1
        while lookahead_index < len(events):
            payload = events[lookahead_index].payload
            if isinstance(payload, ModelCallStarted):
                break
            if isinstance(payload, ModelToolCallRequested):
                if tool_request_index >= len(tool_request_manifests):
                    raise ReplayFailure(
                        "recorded tool request manifests ran out before session "
                        "event reconstruction finished"
                    )
                manifest = tool_request_manifests[tool_request_index]
                tool_request_index += 1
                tool_calls.append(
                    ReplayRecordedToolCall(
                        provider_tool_call_id=manifest.provider_tool_call_id,
                        tool_name=manifest.tool_name,
                        arguments=dict(manifest.validated_arguments),
                    )
                )
            elif isinstance(payload, AssistantMessageCompleted):
                assistant_text = assistant_message_text(payload)
            elif isinstance(payload, TurnCompleted | TurnFailed):
                break
            lookahead_index += 1

        if assistant_text is None and text_deltas:
            assistant_text = "".join(text_deltas).strip() or None
        if assistant_text is None and not tool_calls:
            raise ReplayFailure(
                "could not reconstruct a recorded model response from session events"
            )

        recorded_calls.append(
            ReplayRecordedModelCall(
                manifest=model_call_manifests[model_index],
                assistant_text=assistant_text,
                text_deltas=text_deltas,
                tool_calls=tool_calls,
                input_tokens=completed_payload.input_tokens,
                output_tokens=completed_payload.output_tokens,
            )
        )

    if tool_request_index != len(tool_request_manifests):
        raise ReplayFailure(
            "recorded tool request manifests were not fully consumed by replay "
            "session reconstruction"
        )
    return recorded_calls


def find_model_call_completed_event(
    events: Sequence[EventEnvelope],
    *,
    start_index: int,
    allow_missing: bool = False,
) -> tuple[int, ModelCallCompleted] | None:
    start_payload = cast(ModelCallStarted, events[start_index].payload)
    for event_index in range(start_index + 1, len(events)):
        payload = events[event_index].payload
        if (
            isinstance(payload, ModelCallCompleted)
            and payload.turn_id == start_payload.turn_id
        ):
            return event_index, payload
    if allow_missing:
        return None
    raise ReplayFailure("session is missing a matching ModelCallCompleted event")


def assistant_message_text(payload: AssistantMessageCompleted) -> str:
    return "\n".join(part.text for part in payload.parts if part.kind == "text")
