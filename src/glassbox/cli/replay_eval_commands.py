"""CLI command handlers for replay and eval workflows."""

import argparse
import asyncio
from pathlib import Path

from glassbox.cli.json_output import format_json_output
from glassbox.cli.json_output import print_json_output
from glassbox.cli.path_helpers import resolve_eval_report_output_dir
from glassbox.cli.path_helpers import resolve_optional_explicit_path
from glassbox.cli.path_helpers import resolve_optional_output_path
from glassbox.cli.path_helpers import resolve_runtime_location
from glassbox.cli.replay_eval_formatters import _print_eval_baseline_update
from glassbox.cli.replay_eval_formatters import _print_eval_coverage_audit
from glassbox.cli.replay_eval_formatters import _print_eval_profile
from glassbox.cli.replay_eval_formatters import _print_eval_profiles
from glassbox.cli.replay_eval_formatters import _print_eval_recommendations
from glassbox.cli.replay_eval_formatters import _print_eval_suite_report
from glassbox.cli.replay_eval_formatters import _print_replay_report
from glassbox.cli.replay_eval_formatters import _replay_exit_code
from glassbox.cli.replay_eval_formatters import _replay_result_payload
from glassbox.runtime.bootstrap import open_runtime_context
from glassbox.runtime.eval_baselines import promote_eval_case
from glassbox.runtime.eval_baselines import refresh_eval_case
from glassbox.runtime.eval_coverage import audit_eval_coverage
from glassbox.runtime.eval_inputs import resolve_eval_suite_input
from glassbox.runtime.eval_recommendations import recommend_eval_change_impact
from glassbox.runtime.eval_runner import EvalRunner
from glassbox.runtime.eval_summary import EvalReleaseSignoffProfileInput
from glassbox.runtime.eval_summary import EvalReleaseSignoffSkippedProfileInput
from glassbox.runtime.eval_summary import build_eval_release_signoff_report
from glassbox.runtime.eval_summary import build_eval_release_signoff_summary
from glassbox.runtime.evals import EvalCase
from glassbox.runtime.evals import load_eval_profiles
from glassbox.runtime.evals import load_eval_suite
from glassbox.runtime.replay import ReplayRunner
from glassbox.runtime.workspace_profile import resolve_eval_profile_default


def _replay_command(args: argparse.Namespace) -> int:
    if args.replay_command == "run":
        return asyncio.run(_replay_run_command_async(args))
    if args.replay_command == "export":
        return _replay_export_command(args)
    raise ValueError("specify a replay subcommand")


async def _replay_run_command_async(args: argparse.Namespace) -> int:
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
        print_json_output(_replay_result_payload(result))
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
            profile_id=_resolve_eval_profile_id(cwd, args),
            case_ids=list(args.case_ids) or None,
            tags=list(args.tags) or None,
            output_dir=resolve_optional_explicit_path(cwd, args.output_dir),
            refresh_output_dir=args.refresh_output_dir,
        )

        if args.json:
            print_json_output(suite_result.model_dump(mode="json"))
        else:
            _print_eval_suite_report(suite_result)

        return suite_result.exit_code

    if args.eval_command == "audit":
        cwd, _db_path = resolve_runtime_location(args)
        del _db_path
        audit_result = audit_eval_coverage(
            cwd,
            profile_id=_resolve_eval_profile_id(cwd, args),
            case_ids=list(args.case_ids) or None,
            tags=list(args.tags) or None,
        )

        if args.json:
            print_json_output(audit_result.model_dump(mode="json"))
        else:
            _print_eval_coverage_audit(result=audit_result, workspace_root=cwd)
        return 0

    if args.eval_command == "profile":
        cwd, _db_path = resolve_runtime_location(args)
        del _db_path
        if args.eval_profile_command == "list":
            profiles = load_eval_profiles(cwd, track=args.track)

            if args.json:
                print_json_output(
                    [profile.model_dump(mode="json") for profile in profiles]
                )
            else:
                _print_eval_profiles(workspace_root=cwd, profiles=profiles)
            return 0

        if args.eval_profile_command == "show":
            profiles = load_eval_profiles(cwd)
            profile = next(
                (
                    candidate
                    for candidate in profiles
                    if candidate.profile_id == args.profile_id
                ),
                None,
            )
            if profile is None:
                raise ValueError(f"unknown eval profile: {args.profile_id}")

            if args.json:
                print_json_output(profile.model_dump(mode="json"))
            else:
                _print_eval_profile(workspace_root=cwd, profile=profile)
            return 0

        raise ValueError("specify an eval profile subcommand")

    if args.eval_command == "recommend":
        cwd, _db_path = resolve_runtime_location(args)
        del _db_path
        recommendation = recommend_eval_change_impact(
            cwd,
            touched_paths=list(args.paths),
        )

        if args.json:
            print_json_output(recommendation.model_dump(mode="json"))
        else:
            _print_eval_recommendations(recommendation)
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

            suite_input = resolve_eval_suite_input(
                cwd,
                profile_id=profile_id,
                tags=tag_filters,
                output_dir=root_output_dir / "profiles" / profile_id,
                require_cases=False,
            )
            selection = suite_input.selection
            profile = selection.profile
            if profile is None:
                raise ValueError(f"unknown eval profile: {profile_id}")
            if profile.track != "deterministic":
                raise ValueError(
                    "eval report only supports deterministic profiles; "
                    f"{profile.profile_id} is track {profile.track}. "
                    "Use 'glassbox eval profile list --track live-provider-canary' "
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
                output_dir=suite_input.output_dir,
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
            format_json_output(report.model_dump(mode="json")) + "\n",
            encoding="utf-8",
        )
        report_summary_path.write_text(
            build_eval_release_signoff_summary(report),
            encoding="utf-8",
        )

        if args.json:
            print_json_output(report.model_dump(mode="json"))
        else:
            print(build_eval_release_signoff_summary(report), end="")
        return report.exit_code

    if args.eval_command == "case":
        if args.eval_case_command == "list":
            return _eval_case_list_command(args)
        if args.eval_case_command == "show":
            return _eval_case_show_command(args)
        if args.eval_case_command == "promote":
            return _eval_case_promote_command(args)
        if args.eval_case_command == "refresh":
            return _eval_case_refresh_command(args)
        raise ValueError("specify an eval case subcommand")

    raise ValueError("specify an eval subcommand")


def _eval_case_list_command(args: argparse.Namespace) -> int:
    cwd, _db_path = resolve_runtime_location(args)
    del _db_path
    cases = load_eval_suite(
        cwd,
        tags=list(args.tags) or None,
        validate_bundle_exists=False,
    )

    if args.json:
        print_json_output([case.model_dump(mode="json") for case in cases])
    else:
        _print_eval_cases(cases)
    return 0


def _eval_case_show_command(args: argparse.Namespace) -> int:
    cwd, _db_path = resolve_runtime_location(args)
    del _db_path
    cases = load_eval_suite(
        cwd,
        case_ids=[args.case_id],
        validate_bundle_exists=False,
    )
    eval_case = cases[0]

    if args.json:
        print_json_output(eval_case.model_dump(mode="json"))
    else:
        _print_eval_case(eval_case)
    return 0


def _print_eval_cases(cases: list[EvalCase]) -> None:
    if not cases:
        print("No eval cases found")
        return

    print(f"Eval cases: {len(cases)}")
    for eval_case in cases:
        tags = ", ".join(eval_case.tags) if eval_case.tags else "none"
        stages = ", ".join(eval_case.release_contract.verification_stages)
        print(
            f"{eval_case.case_id}  {eval_case.release_contract.severity}  "
            f"stages {stages}  tags {tags}"
        )
        print(f"  Title: {eval_case.title}")


def _print_eval_case(eval_case: EvalCase) -> None:
    release_contract = eval_case.release_contract
    print(f"Case: {eval_case.case_id}")
    print(f"Title: {eval_case.title}")
    print(f"Tags: {', '.join(eval_case.tags) if eval_case.tags else 'none'}")
    print(f"Expectation: {eval_case.expectation.mode}")
    if eval_case.expectation.invariants:
        print(f"Invariants: {', '.join(eval_case.expectation.invariants)}")
    print(f"Severity: {release_contract.severity}")
    print(f"Verification stages: {', '.join(release_contract.verification_stages)}")
    print(f"Baseline refresh policy: {release_contract.baseline_refresh_policy}")
    if release_contract.owner is not None:
        print(f"Owner: {release_contract.owner}")
    if release_contract.capabilities:
        print(f"Capabilities: {', '.join(release_contract.capabilities)}")
    print(f"Case manifest: {eval_case.case_path}")
    print(f"Replay bundle: {eval_case.bundle_path}")


def _eval_case_promote_command(args: argparse.Namespace) -> int:
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
        print_json_output(report.model_dump(mode="json"))
    else:
        _print_eval_baseline_update(report)
    return 0


def _eval_case_refresh_command(args: argparse.Namespace) -> int:
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
            capabilities=None if args.capabilities is None else list(args.capabilities),
            severity=args.severity,
            verification_stages=None
            if args.verification_stages is None
            else list(args.verification_stages),
            baseline_refresh_policy=args.baseline_refresh_policy,
            report_path=report_output,
        )

    if args.json:
        print_json_output(report.model_dump(mode="json"))
    else:
        _print_eval_baseline_update(report)
    return 0


def _resolve_eval_profile_id(
    cwd: Path,
    args: argparse.Namespace,
) -> str | None:
    return resolve_eval_profile_default(
        cwd,
        explicit_profile=args.profile,
    ).profile_id
