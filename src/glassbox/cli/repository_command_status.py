"""Status and freshness command handlers for repository intelligence CLI."""

import argparse
from pathlib import Path
from typing import cast

from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.cli.repository_command_formatters import _print_next_actions
from glassbox.cli.repository_command_formatters import _print_status_summary
from glassbox.cli.repository_command_formatters import _print_topology_status
from glassbox.cli.repository_command_formatters import _print_topology_status_payload
from glassbox.runtime.repository_index_status import (
    build_repository_index_status_summary,
)
from glassbox.runtime.repository_intelligence_freshness import (
    workspace_topology_freshness_cues,
)
from glassbox.runtime.workspace_topology import WorkspaceTopologyNotFoundError
from glassbox.runtime.workspace_topology import WorkspaceTopologySnapshot
from glassbox.runtime.workspace_topology import load_workspace_topology
from glassbox.runtime.workspace_topology import workspace_topology_path


def _repo_status_command(args: argparse.Namespace) -> int:
    cwd, _ = resolve_runtime_location(args)
    index_summary = build_repository_index_status_summary(cwd)
    topology_payload = _load_topology_status_payload(cwd)
    payload = {
        "index": index_summary.model_dump(mode="json"),
        "topology": topology_payload,
        "next_actions": _repo_status_next_actions(
            index_summary.next_actions,
            topology_payload.get("next_actions", []),
            cwd,
        ),
    }
    if args.json:
        print_json_output(payload)
    else:
        print("Repository intelligence status")
        _print_status_summary(index_summary)
        print("")
        _print_topology_status_payload(topology_payload)
        _print_next_actions(payload["next_actions"])
    return 0


def _repo_stale_command(args: argparse.Namespace) -> int:
    cwd, _ = resolve_runtime_location(args)
    index_summary = build_repository_index_status_summary(cwd)
    topology_payload = _load_topology_status_payload(cwd)
    cues = [
        cue.model_dump(mode="json")
        for cue in index_summary.freshness_cues
        if cue.state != "fresh"
    ]
    topology_cues = topology_payload.get("freshness_cues", [])
    if isinstance(topology_cues, list):
        cues.extend(
            cue
            for cue in topology_cues
            if isinstance(cue, dict)
            and cast(dict[str, object], cue).get("state") != "fresh"
        )
    payload = {
        "cues": cues,
        "next_actions": _repo_status_next_actions(
            index_summary.next_actions,
            topology_payload.get("next_actions", []),
            cwd,
        ),
    }
    if args.json:
        print_json_output(payload)
    else:
        if not cues:
            print("Repository intelligence has no stale or missing cues.")
        else:
            print("Repository intelligence cues:")
            for cue in cues:
                print(
                    f"- {cue['source']}: {cue['state']} "
                    f"({cue['reason']}) - {cue['detail']}"
                )
        _print_next_actions(payload["next_actions"])
    return 0


def _repo_index_status_command(args: argparse.Namespace) -> int:
    cwd, _ = resolve_runtime_location(args)
    summary = build_repository_index_status_summary(cwd)
    if args.json:
        print_json_output(summary.model_dump(mode="json"))
    else:
        _print_status_summary(summary)
    return 0


def _repo_topology_status_command(args: argparse.Namespace) -> int:
    cwd, _ = resolve_runtime_location(args)
    path = workspace_topology_path(cwd)
    try:
        snapshot = load_workspace_topology(cwd)
    except WorkspaceTopologyNotFoundError:
        if args.json:
            print_json_output(_missing_topology_status_payload(cwd, path))
        else:
            print("Workspace topology: missing")
            print(f"Path: {path}")
            print(f"Next action: glassbox repo topology build --cwd {cwd.resolve()}")
        return 0
    payload = _topology_status_payload(snapshot, path)
    if args.json:
        print_json_output(payload)
    else:
        _print_topology_status(snapshot, path)
    return 0


def _load_topology_status_payload(cwd: Path) -> dict[str, object]:
    path = workspace_topology_path(cwd)
    try:
        snapshot = load_workspace_topology(cwd)
    except WorkspaceTopologyNotFoundError:
        return _missing_topology_status_payload(cwd, path)
    return _topology_status_payload(snapshot, path)


def _missing_topology_status_payload(cwd: Path, path: Path) -> dict[str, object]:
    return {
        "freshness": "missing",
        "path": str(path),
        "component_count": 0,
        "dependency_count": 0,
        "recommendation_posture": "unavailable",
        "detail": "workspace topology has not been built",
        "freshness_cues": [
            cue.model_dump(mode="json")
            for cue in workspace_topology_freshness_cues(cwd, None)
        ],
        "next_actions": [f"glassbox repo topology build --cwd {cwd.resolve()}"],
    }


def _repo_status_next_actions(
    index_actions: list[str],
    topology_actions: object,
    cwd: Path,
) -> list[str]:
    actions = [*index_actions]
    if isinstance(topology_actions, list):
        actions.extend(str(action) for action in topology_actions)
    actions.append(f"glassbox repo refresh --cwd {cwd.resolve()}")
    return list(dict.fromkeys(actions))


def _topology_status_payload(
    snapshot: WorkspaceTopologySnapshot,
    path: Path,
) -> dict[str, object]:
    return {
        "freshness": snapshot.freshness,
        "path": str(path),
        "component_count": len(snapshot.components),
        "dependency_count": len(snapshot.dependencies),
        "recommendation_posture": snapshot.recommendation_posture,
        "built_at": snapshot.built_at.isoformat() if snapshot.built_at else None,
        "builder_version": snapshot.builder_version,
        "source_digest": snapshot.source_digest,
        "limitations": snapshot.limitations,
        "failure_reason": snapshot.failure_reason,
        "freshness_cues": [
            cue.model_dump(mode="json")
            for cue in workspace_topology_freshness_cues(
                snapshot.workspace_root,
                snapshot,
            )
        ],
        "next_actions": (
            [f"glassbox repo topology build --cwd {path.parent.parent.resolve()}"]
            if snapshot.freshness != "fresh"
            else []
        ),
    }


__all__ = [
    "_repo_index_status_command",
    "_repo_stale_command",
    "_repo_status_command",
    "_repo_topology_status_command",
]
