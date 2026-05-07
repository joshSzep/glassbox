"""Changeset evidence parser construction."""

import argparse

from glassbox.cli.parser_common import _add_runtime_location_arguments
from glassbox.cli.parser_common import _parse_uuid


def _parse_viewport(value: str) -> tuple[int, int]:
    try:
        width_raw, height_raw = value.lower().split("x", 1)
        width = int(width_raw)
        height = int(height_raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "viewport must use WIDTHxHEIGHT, for example 1440x900"
        ) from exc
    if width < 1 or height < 1:
        raise argparse.ArgumentTypeError("viewport dimensions must be positive")
    return width, height


def _add_changeset_evidence_parsers(
    changeset_subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    evidence_parser = changeset_subparsers.add_parser(
        "evidence",
        help="attach and inspect manual review-loop evidence",
        description=(
            "Attach local manual evidence to a changeset without claiming "
            "Glassbox ran the command, check, or observation. Skipped advisory "
            "browser, dashboard, and accessibility evidence must stay distinct "
            "from passed or verified evidence."
        ),
    )
    evidence_subparsers = evidence_parser.add_subparsers(
        dest="evidence_command",
        required=True,
    )

    evidence_attach_parser = evidence_subparsers.add_parser(
        "attach",
        help="attach summary-first manual evidence to a changeset",
    )
    evidence_attach_parser.add_argument("changeset_id", type=_parse_uuid)
    evidence_attach_parser.add_argument(
        "--kind",
        choices=(
            "manual_command",
            "external_check",
            "reviewer_note",
            "screenshot",
            "browser_observation",
            "accessibility_note",
            "local_file_reference",
            "sanitized_log",
            "operator_assertion",
        ),
        required=True,
    )
    evidence_attach_parser.add_argument("--summary", required=True)
    evidence_attach_parser.add_argument("--source-label", required=True)
    evidence_attach_parser.add_argument("--note")
    evidence_attach_parser.add_argument("--command", dest="command_text")
    evidence_attach_parser.add_argument("--external-url-label")
    evidence_attach_parser.add_argument("--local-file")
    evidence_attach_parser.add_argument("--local-file-label")
    evidence_attach_parser.add_argument(
        "--feedback", dest="feedback_id", type=_parse_uuid
    )
    evidence_attach_parser.add_argument(
        "--target-kind",
        choices=(
            "changeset",
            "feedback",
            "response",
            "verification_requirement",
            "review_brief",
            "publication_boundary",
            "unknown",
        ),
        default="changeset",
    )
    evidence_attach_parser.add_argument("--target-id")
    evidence_attach_parser.add_argument(
        "--freshness",
        choices=("current", "needs_inspection", "stale", "unknown"),
        default="unknown",
    )
    evidence_attach_parser.add_argument("--actor", default="operator")
    evidence_attach_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(evidence_attach_parser)

    def add_browser_dashboard_arguments(
        parser: argparse.ArgumentParser,
        *,
        capture_kind: str,
    ) -> None:
        parser.add_argument("changeset_id", type=_parse_uuid)
        parser.add_argument("--summary", required=True)
        parser.add_argument("--source-label", required=True)
        parser.add_argument(
            "--capture-state",
            choices=("observed", "not_run", "not_applicable"),
            default="observed",
        )
        parser.add_argument("--route", dest="route_label")
        parser.add_argument("--environment")
        parser.add_argument("--browser", default="unknown")
        parser.add_argument("--viewport", type=_parse_viewport)
        parser.add_argument("--observed-at")
        parser.add_argument("--input-method", default="unknown")
        parser.add_argument("--console-checked", action="store_true", default=None)
        parser.add_argument(
            "--console-not-checked",
            action="store_false",
            dest="console_checked",
        )
        parser.add_argument("--skip-reason")
        parser.add_argument("--screenshot-file", dest="screenshot_path_hint")
        parser.add_argument(
            "--screenshot-label",
            default="local screenshot metadata",
        )
        parser.add_argument("--screenshot-media-type", default="image/png")
        parser.add_argument("--screenshot-size-bytes", type=int)
        parser.add_argument("--screenshot-width", type=int)
        parser.add_argument("--screenshot-height", type=int)
        parser.add_argument("--skipped-case", action="append", default=[])
        parser.add_argument("--limitation", action="append", default=[])
        parser.add_argument("--feedback", dest="feedback_id", type=_parse_uuid)
        parser.add_argument(
            "--target-kind",
            choices=(
                "changeset",
                "feedback",
                "response",
                "verification_requirement",
                "review_brief",
                "publication_boundary",
                "unknown",
            ),
            default="changeset",
        )
        parser.add_argument("--target-id")
        parser.add_argument(
            "--freshness",
            choices=("current", "needs_inspection", "stale", "unknown"),
            default="unknown",
        )
        parser.add_argument("--actor", default="operator")
        parser.add_argument("--json", action="store_true")
        parser.set_defaults(evidence_capture_kind=capture_kind)
        _add_runtime_location_arguments(parser)

    evidence_browser_parser = evidence_subparsers.add_parser(
        "browser",
        help="attach advisory browser observation evidence to a changeset",
        description=(
            "Attach advisory browser evidence. Use --skipped-case for not-run "
            "or untested cases; this command does not create deterministic "
            "verification or accessibility claims."
        ),
    )
    add_browser_dashboard_arguments(
        evidence_browser_parser,
        capture_kind="browser_check",
    )

    evidence_dashboard_parser = evidence_subparsers.add_parser(
        "dashboard",
        help="attach advisory dashboard walkthrough evidence to a changeset",
        description=(
            "Attach advisory dashboard walkthrough evidence. Use --skipped-case "
            "for not-run or untested cases; skipped evidence is not a pass."
        ),
    )
    add_browser_dashboard_arguments(
        evidence_dashboard_parser,
        capture_kind="dashboard_walkthrough",
    )

    evidence_accessibility_parser = evidence_subparsers.add_parser(
        "accessibility",
        help="attach advisory accessibility observation evidence to a changeset",
        description=(
            "Attach advisory accessibility evidence with covered checks, "
            "skipped cases, limitations, and non-claims. This is not "
            "certification or WCAG conformance."
        ),
    )
    evidence_accessibility_parser.add_argument("changeset_id", type=_parse_uuid)
    evidence_accessibility_parser.add_argument(
        "--kind",
        dest="observation_kind",
        choices=(
            "keyboard_pass",
            "screen_reader_note",
            "focus_order_issue",
            "wrapping_issue",
            "contrast_observation",
            "responsive_review",
        ),
        required=True,
    )
    evidence_accessibility_parser.add_argument("--summary", required=True)
    evidence_accessibility_parser.add_argument("--source-label", required=True)
    evidence_accessibility_parser.add_argument(
        "--capture-state",
        choices=("observed", "not_run", "not_applicable"),
        default="observed",
    )
    evidence_accessibility_parser.add_argument("--environment")
    evidence_accessibility_parser.add_argument("--observed-issue")
    evidence_accessibility_parser.add_argument("--tool", default="manual")
    evidence_accessibility_parser.add_argument("--route", dest="route_label")
    evidence_accessibility_parser.add_argument("--reviewer-label")
    evidence_accessibility_parser.add_argument(
        "--severity",
        choices=("info", "low", "medium", "high", "blocker"),
        default="medium",
    )
    evidence_accessibility_parser.add_argument(
        "--disposition",
        choices=(
            "open",
            "paired_with_feedback",
            "resolved_locally",
            "accepted_with_risk",
            "needs_follow_up",
        ),
        default="open",
    )
    evidence_accessibility_parser.add_argument("--follow-up")
    evidence_accessibility_parser.add_argument("--paired-tool-output-label")
    evidence_accessibility_parser.add_argument("--skip-reason")
    evidence_accessibility_parser.add_argument(
        "--skipped-case", action="append", default=[]
    )
    evidence_accessibility_parser.add_argument(
        "--limitation", action="append", default=[]
    )
    evidence_accessibility_parser.add_argument(
        "--feedback",
        dest="feedback_id",
        type=_parse_uuid,
    )
    evidence_accessibility_parser.add_argument(
        "--target-kind",
        choices=(
            "changeset",
            "feedback",
            "response",
            "verification_requirement",
            "review_brief",
            "publication_boundary",
            "unknown",
        ),
        default="changeset",
    )
    evidence_accessibility_parser.add_argument("--target-id")
    evidence_accessibility_parser.add_argument(
        "--freshness",
        choices=("current", "needs_inspection", "stale", "unknown"),
        default="unknown",
    )
    evidence_accessibility_parser.add_argument("--actor", default="operator")
    evidence_accessibility_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(evidence_accessibility_parser)

    evidence_list_parser = evidence_subparsers.add_parser(
        "list",
        help="list manual evidence for a changeset or target",
    )
    evidence_list_parser.add_argument(
        "--changeset", dest="changeset_id", type=_parse_uuid
    )
    evidence_list_parser.add_argument("--session", dest="session_id", type=_parse_uuid)
    evidence_list_parser.add_argument(
        "--state",
        choices=("attached", "superseded", "rejected", "archived"),
    )
    evidence_list_parser.add_argument("--include-archived", action="store_true")
    evidence_list_parser.add_argument("--include-rejected", action="store_true")
    evidence_list_parser.add_argument("--include-superseded", action="store_true")
    evidence_list_parser.add_argument("--limit", type=int, default=None)
    evidence_list_parser.add_argument("--json", action="store_true")
    _add_runtime_location_arguments(evidence_list_parser)
