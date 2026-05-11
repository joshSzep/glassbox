"""Session evidence graph parser helpers."""

import argparse

from glassbox.cli.parser_common import _add_runtime_location_arguments
from glassbox.cli.parser_common import _parse_uuid


def _add_session_evidence_graph_parser(
    session_subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    evidence_graph_parser = session_subparsers.add_parser(
        "evidence-graph",
        help="inspect evidence graph support for a session",
        description=(
            "Inspect derived evidence graph support for a session without "
            "reading raw event logs or artifacts."
        ),
    )
    evidence_graph_parser.add_argument("session_id", type=_parse_uuid)
    evidence_graph_parser.add_argument("--json", action="store_true")
    evidence_graph_parser.add_argument(
        "--summary",
        action="store_true",
        help="print only graph counts and claim posture",
    )
    evidence_graph_parser.add_argument(
        "--claim-id",
        help="return one claim support record by ID",
    )
    evidence_graph_parser.add_argument(
        "--node-id",
        help="return a bounded neighborhood around one node ID",
    )
    evidence_graph_parser.add_argument(
        "--depth",
        type=int,
        default=1,
        help="neighborhood depth for --node-id",
    )
    _add_runtime_location_arguments(evidence_graph_parser)


__all__ = ["_add_session_evidence_graph_parser"]
