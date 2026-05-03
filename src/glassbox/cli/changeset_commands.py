"""Changeset CLI command dispatch."""

import argparse

from glassbox.cli.changeset_command_handlers import _changeset_adopt_candidate_command
from glassbox.cli.changeset_command_handlers import _changeset_adoption_preview_command
from glassbox.cli.changeset_command_handlers import _changeset_archive_command
from glassbox.cli.changeset_command_handlers import _changeset_brief_command
from glassbox.cli.changeset_command_handlers import _changeset_commit_message_command
from glassbox.cli.changeset_command_handlers import _changeset_commit_prep_command
from glassbox.cli.changeset_command_handlers import _changeset_create_command
from glassbox.cli.changeset_command_handlers import _changeset_evidence_command
from glassbox.cli.changeset_command_handlers import _changeset_export_command
from glassbox.cli.changeset_command_handlers import _changeset_feedback_command
from glassbox.cli.changeset_command_handlers import _changeset_handoff_readiness_command
from glassbox.cli.changeset_command_handlers import _changeset_list_command
from glassbox.cli.changeset_command_handlers import _changeset_record_precommit_command
from glassbox.cli.changeset_command_handlers import (
    _changeset_record_verification_command,
)
from glassbox.cli.changeset_command_handlers import _changeset_refresh_command
from glassbox.cli.changeset_command_handlers import _changeset_show_command
from glassbox.cli.changeset_command_handlers import _changeset_verification_plan_command


def _changeset_command(args: argparse.Namespace) -> int:
    command = getattr(args, "changeset_command", None)
    if command == "create":
        return _changeset_create_command(args)
    if command == "adoption-preview":
        return _changeset_adoption_preview_command(args)
    if command == "adopt-candidate":
        return _changeset_adopt_candidate_command(args)
    if command == "list":
        return _changeset_list_command(args)
    if command == "show":
        return _changeset_show_command(args)
    if command == "refresh":
        return _changeset_refresh_command(args)
    if command == "verification-plan":
        return _changeset_verification_plan_command(args)
    if command == "record-verification":
        return _changeset_record_verification_command(args)
    if command == "brief":
        return _changeset_brief_command(args)
    if command == "export":
        return _changeset_export_command(args)
    if command == "commit-message":
        return _changeset_commit_message_command(args)
    if command == "record-precommit":
        return _changeset_record_precommit_command(args)
    if command == "commit-prep":
        return _changeset_commit_prep_command(args)
    if command == "handoff-readiness":
        return _changeset_handoff_readiness_command(args)
    if command == "archive":
        return _changeset_archive_command(args)
    if command == "evidence":
        return _changeset_evidence_command(args)
    if command == "feedback":
        return _changeset_feedback_command(args)
    raise ValueError("specify a changeset subcommand")
