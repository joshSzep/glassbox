import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { VerificationCues } from "../components/console/verification-cues";
import {
  deriveVerificationCueAnalysis,
  matchingTargetPaths,
} from "../components/console/verification-cues-analysis";
import { createDashboardState, hydrateSelectedSession } from "../state/session-state";
import { makeRuntimeContext, makeSessionSnapshot } from "./fixtures/session-state";

describe("verification cues", () => {
  it("renders replay/eval artifact drift, blocking evidence, and copyable artifact paths", () => {
    const data = hydrateSelectedSession(
      createDashboardState(),
      makeSessionSnapshot("session-1", {
        runtime_context: makeRuntimeContext({
          artifact_context: {
            additional_summary_count: 0,
            summaries: [
              {
                artifact_kind: "eval",
                artifact_path: "evals/cases/session-1.json",
                error_count: 0,
                failing_tests: [],
                failure_count: 0,
                freshness: "stale",
                inherited: true,
                keyword_filter: "drift",
                provenance_class: "artifact_backed_summary",
                source_tool_call_id: null,
                source_tool_name: "glassbox eval run",
                summary: "Eval fixture is older than the selected working set.",
                summary_kind: "context drift",
                target_paths: ["frontend/app/page.tsx"],
                timed_out: true,
              },
              {
                artifact_kind: "replay",
                artifact_path: "evals/replays/session-1.txt",
                error_count: 1,
                failing_tests: ["test_replay_runner.py::test_smoke"],
                failure_count: 1,
                freshness: "fresh",
                inherited: false,
                keyword_filter: null,
                provenance_class: "artifact_backed_summary",
                source_tool_call_id: null,
                source_tool_name: "glassbox replay",
                summary: "Replay smoke failed after branch drift.",
                summary_kind: "replay failure",
                target_paths: ["src/glassbox/runtime"],
                timed_out: false,
              },
              {
                artifact_kind: "eval",
                artifact_path: "evals/impact.json",
                error_count: 0,
                failing_tests: [],
                failure_count: 0,
                freshness: "fresh",
                inherited: false,
                keyword_filter: null,
                provenance_class: "artifact_backed_summary",
                source_tool_call_id: null,
                source_tool_name: "glassbox eval run",
                summary: "Eval impact is current for this branch.",
                summary_kind: "eval verified",
                target_paths: ["frontend/components/console/verification-cues.tsx"],
                timed_out: false,
              },
            ],
          },
          working_set: {
            additional_item_count: 0,
            items: [
              {
                inherited: true,
                reasons: ["artifact summary"],
                signal_types: ["eval", "working-set"],
                subject: "frontend/app/page.tsx",
                subject_kind: "file",
                summary: "Route shell changed after eval capture.",
              },
            ],
          },
        }),
      }),
    );

    const markup = renderToStaticMarkup(React.createElement(VerificationCues, { data }));

    expect(markup).toContain("Verification cues");
    expect(markup).toContain("Verification summary");
    expect(markup).toContain("Blocking evidence");
    expect(markup).toContain("Advisory evidence");
    expect(markup).toContain("Evidence interpretation");
    expect(markup).toContain('aria-label="Evidence interpretation"');
    expect(markup).toContain("Policy decision source");
    expect(markup).toContain("Eval coverage relevance");
    expect(markup).toContain("Replay drift");
    expect(markup).toContain("Provider canary status");
    expect(markup).toContain("Release evidence freshness");
    expect(markup).toContain("Verified state");
    expect(markup).toContain("verified");
    expect(markup).toContain("advisory eval");
    expect(markup).toContain("blocking replay");
    expect(markup).toContain("evals/cases/session-1.json");
    expect(markup).toContain("Copyable artifact path evals/cases/session-1.json");
    expect(markup).toContain("timed out");
    expect(markup).toContain("test_replay_runner.py::test_smoke");
    expect(markup).toContain("Working-set provenance");
    expect(markup).toContain("1 inherited item may explain drift");
    expect(markup).toContain("inherited working set");
  });

  it("derives evidence cue groups without rendering React", () => {
    const data = hydrateSelectedSession(
      createDashboardState(),
      makeSessionSnapshot("session-1", {
        runtime_context: makeRuntimeContext({
          artifact_context: {
            additional_summary_count: 0,
            summaries: [
              {
                artifact_kind: "replay",
                artifact_path: "evals/replays/session-1.txt",
                error_count: 1,
                failing_tests: ["test_replay_runner.py::test_smoke"],
                failure_count: 1,
                freshness: "fresh",
                inherited: false,
                keyword_filter: null,
                provenance_class: "artifact_backed_summary",
                source_tool_call_id: null,
                source_tool_name: "glassbox replay",
                summary: "Replay smoke failed after branch drift.",
                summary_kind: "replay failure",
                target_paths: ["src/glassbox/runtime"],
                timed_out: false,
              },
              {
                artifact_kind: "provider_canary",
                artifact_path: ".glassbox/provider-canary/summary.json",
                error_count: 0,
                failing_tests: [],
                failure_count: 1,
                freshness: "fresh",
                inherited: false,
                keyword_filter: null,
                provenance_class: "artifact_backed_summary",
                source_tool_call_id: null,
                source_tool_name: "glassbox provider canary run",
                summary: "Provider canary failed.",
                summary_kind: "provider capability matrix",
                target_paths: [],
                timed_out: false,
              },
            ],
          },
          working_set: {
            additional_item_count: 0,
            items: [
              {
                inherited: false,
                reasons: ["runtime edit"],
                signal_types: ["file"],
                subject: "src/glassbox/runtime",
                subject_kind: "directory",
                summary: "Runtime files changed.",
              },
            ],
          },
        }),
      }),
    );

    const analysis = deriveVerificationCueAnalysis(data);

    expect(analysis.blockingArtifacts).toHaveLength(1);
    expect(analysis.advisoryArtifacts).toHaveLength(1);
    expect(analysis.evidenceCues.map((cue) => cue.label)).toEqual([
      "Policy decision source",
      "Eval coverage relevance",
      "Replay drift",
      "Provider canary status",
      "Release evidence freshness",
    ]);
    expect(matchingTargetPaths(analysis.artifactSummaries, analysis.workingSetItems)).toEqual([
      "src/glassbox/runtime",
    ]);
  });

  it("renders a missing-artifact state distinctly from runtime health", () => {
    const data = hydrateSelectedSession(
      createDashboardState(),
      makeSessionSnapshot("session-1", { runtime_context: makeRuntimeContext() }),
    );

    const markup = renderToStaticMarkup(React.createElement(VerificationCues, { data }));

    expect(markup).toContain("No replay, eval, provider, or release artifacts are retained");
    expect(markup).toContain("Missing artifacts");
    expect(markup).toContain("Use CLI replay/eval commands");
  });

  it("keeps provider canary failures advisory while surfacing policy and release freshness", () => {
    const data = hydrateSelectedSession(
      createDashboardState(),
      makeSessionSnapshot("session-1", {
        pending_approval_id: "approval-1",
        pending_approvals: [
          {
            approval_id: "approval-1",
            policy_outcome: "approve",
            policy_risk_level: "workspace_write",
            policy_source_kind: "tool_policy",
            policy_source_label: "workspace-write",
            reason: "requires workspace write approval",
            requested_at: "2026-04-23T00:00:05Z",
            subject: "apply patch",
            turn_id: "turn-1",
          },
        ],
        runtime_context: makeRuntimeContext({
          artifact_context: {
            additional_summary_count: 0,
            summaries: [
              {
                artifact_kind: "provider_canary",
                artifact_path: ".glassbox/provider-canary/v7/provider-canary-summary.json",
                error_count: 0,
                failing_tests: [],
                failure_count: 1,
                freshness: "fresh",
                inherited: false,
                keyword_filter: null,
                provenance_class: "artifact_backed_summary",
                source_tool_call_id: null,
                source_tool_name: "glassbox provider canary run",
                summary: "Provider canary scenario failed against live provider.",
                summary_kind: "provider capability matrix",
                target_paths: [],
                timed_out: false,
              },
              {
                artifact_kind: "release_gate",
                artifact_path: ".glassbox/releases/v7/eval-summary.json",
                error_count: 0,
                failing_tests: [],
                failure_count: 0,
                freshness: "stale",
                inherited: false,
                keyword_filter: null,
                provenance_class: "artifact_backed_summary",
                source_tool_call_id: null,
                source_tool_name: "glassbox eval report",
                summary: "Release evidence predates this working set.",
                summary_kind: "release evidence",
                target_paths: ["frontend/components/console/verification-cues.tsx"],
                timed_out: false,
              },
            ],
          },
          working_set: {
            additional_item_count: 0,
            items: [
              {
                inherited: false,
                reasons: ["current edit"],
                signal_types: ["file"],
                subject: "frontend/components/console/verification-cues.tsx",
                subject_kind: "file",
                summary: "Verification cues changed in this session.",
              },
            ],
          },
        }),
      }),
    );

    const markup = renderToStaticMarkup(React.createElement(VerificationCues, { data }));

    expect(markup).toContain("approval policy");
    expect(markup).toContain("Sources: tool_policy:workspace-write");
    expect(markup).toContain("advisory provider");
    expect(markup).toContain("not deterministic release signoff");
    expect(markup).toContain("stale release");
    expect(markup).not.toContain("blocking provider");
  });
});
