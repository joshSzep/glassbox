import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { VerificationCues } from "../components/console/verification-cues";
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
                timed_out: false,
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
    expect(markup).toContain("1 blocking evidence");
    expect(markup).toContain("1 advisory drift");
    expect(markup).toContain("evals/cases/session-1.json");
    expect(markup).toContain("test_replay_runner.py::test_smoke");
    expect(markup).toContain("Working-set provenance");
    expect(markup).toContain("inherited");
  });

  it("renders a missing-artifact state distinctly from runtime health", () => {
    const data = hydrateSelectedSession(
      createDashboardState(),
      makeSessionSnapshot("session-1", { runtime_context: makeRuntimeContext() }),
    );

    const markup = renderToStaticMarkup(React.createElement(VerificationCues, { data }));

    expect(markup).toContain("No replay or eval artifacts are retained in this snapshot.");
    expect(markup).toContain("0 blocking evidence");
    expect(markup).toContain("0 advisory drift");
  });
});
