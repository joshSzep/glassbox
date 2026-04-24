"""CLI command handlers for replay and eval workflows."""

import argparse
import asyncio
import json
from pathlib import Path

from glassbox.cli.path_helpers import resolve_eval_report_output_dir
from glassbox.cli.path_helpers import resolve_optional_explicit_path
from glassbox.cli.path_helpers import resolve_optional_output_path
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.cli.replay_eval_formatters import _print_eval_baseline_update
from glassbox.cli.replay_eval_formatters import _print_eval_coverage_audit
from glassbox.cli.replay_eval_formatters import _print_eval_profiles
from glassbox.cli.replay_eval_formatters import _print_eval_suite_report
from glassbox.cli.replay_eval_formatters import _print_replay_report
from glassbox.cli.replay_eval_formatters import _replay_exit_code
from glassbox.cli.replay_eval_formatters import _replay_result_payload
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.eval_baselines import promote_eval_case
from glassbox.runtime.eval_baselines import refresh_eval_case
from glassbox.runtime.eval_coverage import audit_eval_coverage
from glassbox.runtime.eval_runner import EvalRunner
from glassbox.runtime.eval_summary import EvalReleaseSignoffProfileInput
from glassbox.runtime.eval_summary import EvalReleaseSignoffSkippedProfileInput
from glassbox.runtime.eval_summary import build_eval_release_signoff_report
from glassbox.runtime.eval_summary import build_eval_release_signoff_summary
from glassbox.runtime.evals import load_eval_profiles
from glassbox.runtime.evals import resolve_eval_suite_selection
from glassbox.runtime.replay import ReplayRunner


def _replay_command(args: argparse.Namespace) -> int:
    return asyncio.run(_replay_command_async(args))


async def _replay_command_async(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)

    if (args.session_id is None) == (args.bundle is None):
        raise ValueError("specify exactly one of session_id or --bundle")

    if args.bundle is not None:
        result = await ReplayRunner().replay_bundle_file(
            Path(args.bundle),
            workspace_root=cwd,
        )
    else:
        session_id = args.session_id
        assert session_id is not None

        with open_runtime_context(cwd, db_path=db_path) as runtime_context:
            result = await ReplayRunner(
                runtime_context.repositories.sessions,
                runtime_context.repositories.artifacts,
            ).replay_session(session_id)

    if args.json:
        print(
            json.dumps(
                _replay_result_payload(result),
                indent=2,
                sort_keys=True,
            )
        )
    else:
        _print_replay_report(result)

    return _replay_exit_code(result)


def _replay_export_command(args: argparse.Namespace) -> int:
    cwd, db_path = resolve_runtime_location(args)
    output_path = resolve_optional_output_path(
        cwd,
        args.output,
        default_name=f"glassbox-replay-{args.session_id}.json",
    )

    with open_runtime_context(cwd, db_path=db_path) as runtime_context:
        exported_path = ReplayRunner(
            runtime_context.repositories.sessions,
            runtime_context.repositories.artifacts,
        ).export_session_bundle(args.session_id, output_path)

    print(f"Exported replay bundle for session {args.session_id}: {exported_path}")
    return 0


def _eval_command(args: argparse.Namespace) -> int:
    return asyncio.run(_eval_command_async(args))


async def _eval_command_async(args: argparse.Namespace) -> int:
    if args.eval_command == "run":
        cwd, _db_path = resolve_runtime_location(args)
        del _db_path
        suite_result = await EvalRunner().run_suite(
            cwd,
            profile_id=args.profile,
            case_ids=list(args.case_ids) or None,
            tags=list(args.tags) or None,
            output_dir=resolve_optional_explicit_path(cwd, args.output_dir),
            refresh_output_dir=args.refresh_output_dir,
        )

        if args.json:
            print(
                json.dumps(
                    suite_result.model_dump(mode="json"),
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            _print_eval_suite_report(suite_result)

        return suite_result.exit_code

    if args.eval_command == "audit":
        cwd, _db_path = resolve_runtime_location(args)
        del _db_path
        audit_result = audit_eval_coverage(
            cwd,
            profile_id=args.profile,
            case_ids=list(args.case_ids) or None,
            tags=list(args.tags) or None,
        )

        if args.json:
            print(
                json.dumps(
                    audit_result.model_dump(mode="json"),
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            _print_eval_coverage_audit(result=audit_result, workspace_root=cwd)
        return 0

    if args.eval_command == "profiles":
        cwd, _db_path = resolve_runtime_location(args)
        del _db_path
        profiles = load_eval_profiles(cwd, track=args.track)

        if args.json:
            print(
                json.dumps(
                    [profile.model_dump(mode="json") for profile in profiles],
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            _print_eval_profiles(workspace_root=cwd, profiles=profiles)
        return 0

    if args.eval_command == "report":
        cwd, _db_path = resolve_runtime_location(args)
        del _db_path
        root_output_dir = resolve_eval_report_output_dir(cwd, args.output_dir)
        root_output_dir.mkdir(parents=True, exist_ok=True)

        profile_inputs: list[EvalReleaseSignoffProfileInput] = []
        skipped_profiles: list[EvalReleaseSignoffSkippedProfileInput] = []
        seen_profile_ids: set[str] = set()
        requested_profile_ids: list[str] = []
        runner = EvalRunner()
        tag_filters = list(args.tags) or None

        for profile_id in args.profile_ids:
            if profile_id in seen_profile_ids:
                continue
            seen_profile_ids.add(profile_id)
            requested_profile_ids.append(profile_id)

            selection = resolve_eval_suite_selection(
                cwd,
                profile_id=profile_id,
                tags=tag_filters,
            )
            profile = selection.profile
            if profile is None:
                raise ValueError(f"unknown eval profile: {profile_id}")
            if profile.track != "deterministic":
                raise ValueError(
                    "eval report only supports deterministic profiles; "
                    f"{profile.profile_id} is track {profile.track}. "
                    "Use 'glassbox eval profiles --track live-provider-canary' "
                    "for optional canary scaffolding instead."
                )
            if not selection.cases:
                skipped_profiles.append(
                    EvalReleaseSignoffSkippedProfileInput(
                        profile_id=profile.profile_id,
                        profile=profile,
                        reason="no eval cases selected after applying report filters",
                    )
                )
                continue

            suite_result = await runner.run_suite(
                cwd,
                profile_id=profile.profile_id,
                tags=tag_filters,
                output_dir=root_output_dir / "profiles" / profile.profile_id,
            )
            profile_inputs.append(
                EvalReleaseSignoffProfileInput(
                    profile=profile,
                    eval_cases=selection.cases,
                    suite_result=suite_result,
                )
            )

        report = build_eval_release_signoff_report(
            workspace_root=cwd,
            requested_profile_ids=requested_profile_ids,
            tag_filters=list(args.tags),
            profile_inputs=profile_inputs,
            skipped_profiles=skipped_profiles,
            artifact_root=root_output_dir,
        )
        report_json_path = root_output_dir / "release-signoff.json"
        report_summary_path = root_output_dir / "release-signoff.md"
        report_json_path.write_text(
            json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        report_summary_path.write_text(
            build_eval_release_signoff_summary(report),
            encoding="utf-8",
        )

        if args.json:
            print(json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True))
        else:
            print(build_eval_release_signoff_summary(report), end="")
        return report.exit_code

    if args.eval_command == "promote":
        cwd, db_path = resolve_runtime_location(args)
        report_output = resolve_optional_explicit_path(cwd, args.report_output)
        with open_runtime_context(cwd, db_path=db_path) as runtime_context:
            report = promote_eval_case(
                cwd,
                replay_runner=ReplayRunner(
                    runtime_context.repositories.sessions,
                    runtime_context.repositories.artifacts,
                ),
                session_id=args.session_id,
                case_id=args.case_id,
                title=args.title,
                tags=list(args.tags),
                notes=args.notes,
                expectation_mode=args.expectation_mode,
                invariants=list(args.invariants),
                owner=args.owner,
                capabilities=list(args.capabilities),
                severity=args.severity,
                verification_stages=None
                if args.verification_stages is None
                else list(args.verification_stages),
                baseline_refresh_policy=args.baseline_refresh_policy,
                rationale=args.reason,
                report_path=report_output,
            )

        if args.json:
            print(json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True))
        else:
            _print_eval_baseline_update(report)
        return 0

    if args.eval_command == "refresh":
        cwd, db_path = resolve_runtime_location(args)
        report_output = resolve_optional_explicit_path(cwd, args.report_output)
        with open_runtime_context(cwd, db_path=db_path) as runtime_context:
            report = refresh_eval_case(
                cwd,
                replay_runner=ReplayRunner(
                    runtime_context.repositories.sessions,
                    runtime_context.repositories.artifacts,
                ),
                session_id=args.session_id,
                case_id=args.case_id,
                rationale=args.reason,
                acknowledge_policy=args.acknowledge_policy,
                title=args.title,
                tags=None if args.tags is None else list(args.tags),
                notes=args.notes,
                expectation_mode=args.expectation_mode,
                invariants=None if args.invariants is None else list(args.invariants),
                owner=args.owner,
                capabilities=None
                if args.capabilities is None
                else list(args.capabilities),
                severity=args.severity,
                verification_stages=None
                if args.verification_stages is None
                else list(args.verification_stages),
                baseline_refresh_policy=args.baseline_refresh_policy,
                report_path=report_output,
            )

        if args.json:
            print(json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True))
        else:
            _print_eval_baseline_update(report)
        return 0

    raise ValueError("specify an eval subcommand")
