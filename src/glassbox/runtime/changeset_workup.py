"""Read-only changeset workup preview for local workspace changes."""

import asyncio
from pathlib import Path

from glassbox.runtime.change_inventory import change_inventory_from_diff_summary
from glassbox.runtime.changeset_models import ChangesetPathVerificationTargetPreview
from glassbox.runtime.changeset_models import ChangesetVerificationRecipePreview
from glassbox.runtime.changeset_models import ChangesetWorkupCandidateGrouping
from glassbox.runtime.changeset_models import ChangesetWorkupMemoryCandidatePreview
from glassbox.runtime.changeset_models import ChangesetWorkupPreview
from glassbox.runtime.changeset_models import ChangesetWorkupReviewRisk
from glassbox.runtime.changeset_models import PathVerificationPlanPreview
from glassbox.runtime.changeset_topology import derive_changeset_topology_impacts
from glassbox.runtime.changeset_verification_preview import eval_profile_ids_for_preview
from glassbox.runtime.changeset_verification_preview import recommendation_for_preview
from glassbox.runtime.changeset_verification_preview import release_surface_previews
from glassbox.runtime.changeset_verification_preview import target_previews
from glassbox.runtime.verification_plan_builder import build_verification_plan_entries
from glassbox.tools.workflow import DiffSummaryArgs
from glassbox.tools.workflow import DiffSummaryResult
from glassbox.tools.workflow import DiffSummaryScope
from glassbox.tools.workflow import DiffSummaryTool


class ChangesetWorkupPreviewService:
    """Build non-mutating workup previews from the current git diff."""

    async def preview(
        self,
        workspace_root: Path,
        *,
        paths: list[str] | None = None,
        scope: DiffSummaryScope = DiffSummaryScope.WORKSPACE,
        session_id: str | None = None,
        max_files: int = 200,
    ) -> ChangesetWorkupPreview:
        resolved_root = workspace_root.resolve(strict=False)
        diff_summary = await DiffSummaryTool(resolved_root).execute(
            DiffSummaryArgs(
                scope=scope,
                paths=paths or [],
                max_files=max_files,
                inline_file_limit=min(max_files, 50),
            )
        )
        diff_summary = _without_internal_glassbox_paths(diff_summary)
        inventory = change_inventory_from_diff_summary(diff_summary)
        changed_paths = [entry.path for entry in inventory.paths]
        recommendation, recommendation_limitations = recommendation_for_preview(
            resolved_root,
            changed_paths,
        )
        plan_entries, skipped_checks = build_verification_plan_entries(
            changed_paths=changed_paths,
            recommendation=recommendation,
        )
        topology_impacts, topology_limitations = derive_changeset_topology_impacts(
            workspace_root=resolved_root,
            changed_paths=changed_paths,
        )
        verification_plan = PathVerificationPlanPreview(
            workspace_root=str(resolved_root),
            changed_paths=changed_paths,
            plan_entries=plan_entries,
            skipped_checks=skipped_checks,
            recommended_commands=(
                list(recommendation.suggested_commands)
                if recommendation is not None
                else []
            ),
            eval_profiles=eval_profile_ids_for_preview(recommendation),
            recipes=_recipe_previews(recommendation),
            recommended_targets=target_previews(recommendation),
            release_surfaces=release_surface_previews(recommendation),
            reason_groups=(
                recommendation.reason_groups if recommendation is not None else []
            ),
            limitations=recommendation_limitations,
            safe_next_actions=_verification_safe_next_actions(
                changed_paths,
                recommendation_commands=(
                    recommendation.suggested_commands
                    if recommendation is not None
                    else []
                ),
            ),
            non_claims=[
                "workup preview does not run verification commands",
                "workup preview is not persisted changeset evidence",
                "manual-only entries are advisory and are not passes",
            ],
        )
        limitations = _limitations(
            diff_error=diff_summary.error,
            inventory_limitations=inventory.limitations,
            recommendation_limitations=recommendation_limitations,
            topology_limitations=topology_limitations,
        )
        safe_next_actions = _safe_next_actions(
            changed_paths,
            session_id=session_id,
            verification_plan=verification_plan,
        )
        return ChangesetWorkupPreview(
            workspace_root=str(resolved_root),
            scope=scope,
            path_filters=diff_summary.path_filters,
            changed_paths=changed_paths,
            candidate_groupings=[
                _candidate_grouping(
                    inventory,
                    session_id=session_id,
                    changed_paths=changed_paths,
                )
            ],
            inventory=inventory,
            verification_plan=verification_plan,
            repository_intelligence_impacts=topology_impacts,
            review_risks=_review_risks(inventory),
            memory_candidates=_memory_candidates(
                changed_paths,
                recipes=verification_plan.recipes,
                recommended_targets=verification_plan.recommended_targets,
                session_id=session_id,
            ),
            stale_evidence=[],
            safe_next_actions=safe_next_actions,
            limitations=limitations,
            non_claims=[
                "workup preview inspected local state only",
                "no changeset was created",
                "no files were staged or committed",
                "no verification commands were run",
                "ignored paths are not included unless git diff or status reports them",
            ],
        )

    def preview_sync(
        self,
        workspace_root: Path,
        *,
        paths: list[str] | None = None,
        scope: DiffSummaryScope = DiffSummaryScope.WORKSPACE,
        session_id: str | None = None,
        max_files: int = 200,
    ) -> ChangesetWorkupPreview:
        return asyncio.run(
            self.preview(
                workspace_root,
                paths=paths,
                scope=scope,
                session_id=session_id,
                max_files=max_files,
            )
        )


def _candidate_grouping(
    inventory,
    *,
    session_id: str | None,
    changed_paths: list[str],
) -> ChangesetWorkupCandidateGrouping:
    if session_id is not None:
        create_command = (
            "glassbox changeset create --from workspace-diff "
            f"--session {session_id} --cwd ."
        )
    else:
        create_command = (
            "glassbox changeset create --from workspace-diff "
            "--session SESSION_ID --cwd ."
        )
    return ChangesetWorkupCandidateGrouping(
        title="Current workspace diff",
        changed_path_count=len(changed_paths),
        generated_path_count=inventory.summary.generated_path_count,
        test_path_count=inventory.summary.test_path_count,
        docs_path_count=inventory.summary.docs_path_count,
        policy_sensitive_path_count=inventory.summary.policy_sensitive_path_count,
        risk_level=inventory.summary.risk_level,
        create_command=create_command if changed_paths else None,
        limitations=(
            [] if changed_paths else ["workspace diff has no changed paths to group"]
        ),
    )


def _without_internal_glassbox_paths(
    diff_summary: DiffSummaryResult,
) -> DiffSummaryResult:
    files = [
        item for item in diff_summary.files if not _is_internal_glassbox_path(item.path)
    ]
    artifact_payload = None
    if diff_summary.artifact_payload is not None:
        artifact_files = [
            item
            for item in diff_summary.artifact_payload.files
            if not _is_internal_glassbox_path(item.path)
        ]
        artifact_payload = diff_summary.artifact_payload.model_copy(
            update={"files": artifact_files}
        )
    return diff_summary.model_copy(
        update={
            "files": files,
            "artifact_payload": artifact_payload,
            "clean": not files
            and (artifact_payload is None or not artifact_payload.files),
        }
    )


def _is_internal_glassbox_path(path: str) -> bool:
    return path == ".glassbox" or path.startswith(".glassbox/")


def _review_risks(inventory) -> list[ChangesetWorkupReviewRisk]:
    risks: list[ChangesetWorkupReviewRisk] = []
    risky_paths = [
        entry
        for entry in inventory.paths
        if entry.risk_level in {"high", "medium"}
        or entry.generated
        or entry.policy_sensitive
        or entry.binary_posture == "binary"
        or entry.staged_state == "untracked"
    ]
    if inventory.summary.risk_summary is not None:
        risks.append(
            ChangesetWorkupReviewRisk(
                level=inventory.summary.risk_level,
                summary=inventory.summary.risk_summary,
                paths=[entry.path for entry in risky_paths[:20]],
                tags=list(
                    dict.fromkeys(
                        tag for entry in risky_paths for tag in entry.risk_tags
                    )
                )[:20],
                safe_next_actions=[
                    "glassbox changeset workup-preview --json --cwd .",
                ],
            )
        )
    if inventory.summary.untracked_path_count:
        risks.append(
            ChangesetWorkupReviewRisk(
                level="medium",
                summary=(
                    f"{inventory.summary.untracked_path_count} untracked path(s) "
                    "need explicit review before handoff."
                ),
                paths=[
                    entry.path
                    for entry in inventory.paths
                    if entry.staged_state == "untracked"
                ][:20],
                tags=["untracked"],
                safe_next_actions=["git status --short"],
            )
        )
    return risks


def _memory_candidates(
    changed_paths: list[str],
    *,
    recipes: list[ChangesetVerificationRecipePreview],
    recommended_targets: list[ChangesetPathVerificationTargetPreview],
    session_id: str | None,
) -> list[ChangesetWorkupMemoryCandidatePreview]:
    safe_next_action = (
        f"glassbox memory candidates --session {session_id} --cwd ."
        if session_id is not None
        else "glassbox memory candidates --session SESSION_ID --cwd ."
    )
    candidates: list[ChangesetWorkupMemoryCandidatePreview] = []
    if recipes:
        candidates.append(
            ChangesetWorkupMemoryCandidatePreview(
                source="repository-intelligence",
                summary=(
                    "Matched verification recipes may reveal durable repository "
                    "workflow knowledge after operator review."
                ),
                matched_paths=list(
                    dict.fromkeys(
                        path for recipe in recipes for path in recipe.matched_paths
                    )
                )[:20],
                safe_next_actions=[safe_next_action],
                limitations=[
                    "workup preview does not confirm or activate workspace memory"
                ],
            )
        )
    docs_paths = [path for path in changed_paths if path.startswith("docs/")]
    if docs_paths:
        candidates.append(
            ChangesetWorkupMemoryCandidatePreview(
                source="changed-docs",
                summary=(
                    "Documentation changes may describe durable operator workflow "
                    "knowledge; confirm only if still true after review."
                ),
                matched_paths=docs_paths[:20],
                safe_next_actions=[safe_next_action],
                limitations=[
                    "documentation changes are memory candidates, not confirmed memory"
                ],
            )
        )
    if recommended_targets and not candidates:
        candidates.append(
            ChangesetWorkupMemoryCandidatePreview(
                source="verification-recommendation",
                summary=(
                    "Verification recommendations are available for this path set; "
                    "review before turning any repeated pattern into memory."
                ),
                matched_paths=changed_paths[:20],
                safe_next_actions=[safe_next_action],
                limitations=["memory capture remains explicit and review-gated"],
            )
        )
    return candidates


def _verification_safe_next_actions(
    changed_paths: list[str],
    *,
    recommendation_commands,
) -> list[str]:
    actions = list(recommendation_commands)
    if changed_paths:
        actions.append(_path_verification_command(changed_paths))
    return list(dict.fromkeys(actions))


def _safe_next_actions(
    changed_paths: list[str],
    *,
    session_id: str | None,
    verification_plan: PathVerificationPlanPreview,
) -> list[str]:
    actions: list[str] = []
    if session_id is None:
        actions.append("glassbox session list --cwd .")
    if changed_paths:
        actions.append(
            "glassbox changeset create --from workspace-diff "
            f"--session {session_id or 'SESSION_ID'} --cwd ."
        )
        actions.append(_path_verification_command(changed_paths))
    actions.extend(verification_plan.recommended_commands)
    return list(dict.fromkeys(actions))


def _path_verification_command(changed_paths: list[str]) -> str:
    path_args = " ".join(f"--path {path}" for path in changed_paths[:10])
    suffix = " # add remaining paths" if len(changed_paths) > 10 else ""
    return f"glassbox changeset verification-plan {path_args} --cwd .{suffix}"


def _limitations(
    *,
    diff_error: str | None,
    inventory_limitations: list[str],
    recommendation_limitations: list[str],
    topology_limitations: list[str],
) -> list[str]:
    limitations = [
        *inventory_limitations,
        *recommendation_limitations,
        *topology_limitations,
    ]
    if diff_error is not None:
        limitations.insert(0, f"workspace diff unavailable: {diff_error}")
    return list(dict.fromkeys(limitations))


def _recipe_previews(recommendation):
    if recommendation is None:
        return []
    return [
        ChangesetVerificationRecipePreview(
            recipe_id=recipe.recipe_id,
            title=recipe.title,
            confidence=recipe.confidence,
            source=recipe.source,
            matched_paths=recipe.matched_paths,
            component_ids=recipe.component_ids,
            commands=recipe.commands,
            profile_ids=recipe.profile_ids,
            case_ids=recipe.case_ids,
            notes=recipe.notes,
            limitations=recipe.limitations,
        )
        for recipe in recommendation.recipes
    ]


__all__ = ["ChangesetWorkupPreviewService"]
