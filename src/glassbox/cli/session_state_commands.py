"""CLI command handlers for session inspection and projection state commands."""

from __future__ import annotations

import argparse

from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.session_queries import SessionQueryService

from .path_helpers import resolve_runtime_location
from .status_formatters import _print_session_status


def _status_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)

    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        query_service = SessionQueryService(
            runtime_context.repositories.sessions,
            runtime_context.repositories.artifacts,
        )
        _print_session_status(query_service.get_session_status_view(args.session_id))

    return 0


def _rebuild_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)

    if args.all == (args.session_id is not None):
        raise ValueError("specify exactly one of session_id or --all")

    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        repository = runtime_context.repositories.sessions

        if args.all:
            sessions = repository.list_sessions()
            if not sessions:
                print("No sessions found to rebuild")
                return 0

            for session in sessions:
                repository.rebuild_session_projections(session.session_id)
                print(f"Rebuilt projections for session {session.session_id}")
            print(f"Rebuilt projections for {len(sessions)} session(s)")
            return 0

        session_id = args.session_id
        assert session_id is not None
        if repository.get_session(session_id) is None:
            raise ValueError(f"unknown session_id: {session_id}")

        repository.rebuild_session_projections(session_id)
        print(f"Rebuilt projections for session {session_id}")
        return 0
